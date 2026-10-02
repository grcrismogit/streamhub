"""Diagnóstico de conexión con AWS (RDS + S3 + IAM Role).

Ejecutar en la instancia EC2, dentro de /opt/streamhub/backend:

    sudo -u streamhub .venv/bin/python -m app.diagnostics

Comprueba, en orden, lo mismo que necesita la API para funcionar y explica
qué revisar si algo falla. Devuelve código de salida 0 si todo está bien.
"""

from __future__ import annotations

import sys
import urllib.request
import uuid
from collections.abc import Callable

import boto3
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings

OK, FAIL, WARN = "\033[32m✔\033[0m", "\033[31m✘\033[0m", "\033[33m!\033[0m"
results: list[bool] = []


def check(title: str, fn: Callable[[], str], hint: str) -> None:
    try:
        detail = fn()
        print(f"{OK} {title}: {detail}")
        results.append(True)
    except Exception as exc:  # noqa: BLE001 — queremos mostrar cualquier error
        print(f"{FAIL} {title}: {type(exc).__name__}: {exc}")
        print(f"    → Revisa: {hint}")
        results.append(False)


def main() -> int:
    print("\n=== StreamHub · diagnóstico de conexión con AWS ===\n")
    try:
        s = get_settings()
    except Exception as exc:  # noqa: BLE001
        print(f"{FAIL} Variables de entorno inválidas o incompletas:\n{exc}")
        print("    → Revisa /etc/streamhub/api.env (o .env en local).")
        return 1

    print(f"Región AWS ........ {s.aws_region}")
    print(f"Bucket videos ..... {s.s3_videos_bucket}")
    print(f"Bucket miniaturas . {s.s3_thumbnails_bucket}")
    print(f"Base de datos ..... {s.db_user}@{s.db_host}:{s.db_port}/{s.db_name} (sslmode={s.db_sslmode})")
    print(f"CORS permitido .... {', '.join(s.cors_origin_list)}\n")

    # 1) Credenciales: en EC2 deben venir del IAM Role, nunca de access keys.
    def credentials() -> str:
        if s.s3_endpoint_url:
            return f"emulador local ({s.s3_endpoint_url}) — en AWS se usará el IAM Role"
        creds = boto3.Session().get_credentials()
        if creds is None:
            raise RuntimeError("no hay credenciales disponibles")
        identity = boto3.client("sts", region_name=s.aws_region).get_caller_identity()
        if creds.method != "iam-role":
            print(f"{WARN} Las credenciales vienen de '{creds.method}', no de un IAM Role.")
        return f"{creds.method} → {identity['Arn']}"

    check(
        "Credenciales AWS (IAM Role)",
        credentials,
        "EC2 → Actions → Security → Modify IAM role; asigna StreamHubEC2Role o LabInstanceProfile.",
    )

    # 2) RDS
    def database() -> str:
        engine = create_engine(s.sqlalchemy_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar_one().split(",")[0]
            tables = set(inspect(conn).get_table_names())
            missing = {"users", "videos", "comments"} - tables
            if missing:
                raise RuntimeError(f"faltan tablas {sorted(missing)}: ejecuta `alembic upgrade head`")
            counts = {
                t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()  # noqa: S608 (nombres de tabla del propio esquema)
                for t in sorted(tables - {"alembic_version"})
            }
        return f"{version} · filas {counts}"

    check(
        "Conexión a RDS",
        database,
        "SG de RDS (5432 desde sg-streamhub-api), DB_HOST/DB_PASSWORD, que exista la BD 'streamhub', DB_SSLMODE=require.",
    )

    # 3) S3: escribir, leer con URL prefirmada y borrar un objeto de prueba en cada bucket.
    from app.services.storage import get_storage

    storage = get_storage()

    def s3_roundtrip(bucket: str) -> Callable[[], str]:
        def run() -> str:
            key = f"_diagnostico/{uuid.uuid4().hex}.txt"
            storage.client.put_object(Bucket=bucket, Key=key, Body=b"ok", ContentType="text/plain")
            try:
                url = storage.presigned_url(bucket, key)
                with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 — URL https de S3
                    if resp.read() != b"ok":
                        raise RuntimeError("la URL prefirmada no devolvió el contenido esperado")
            finally:
                storage.client.delete_object(Bucket=bucket, Key=key)
            return "PutObject ✓ · URL prefirmada ✓ · DeleteObject ✓"

        return run

    hint = "nombre del bucket en api.env, región correcta y política IAM con s3:PutObject/GetObject/DeleteObject."
    check(f"S3 videos ({s.s3_videos_bucket})", s3_roundtrip(s.s3_videos_bucket), hint)
    check(f"S3 miniaturas ({s.s3_thumbnails_bucket})", s3_roundtrip(s.s3_thumbnails_bucket), hint)

    ok = all(results)
    print(
        f"\n{'✅ Todo conectado correctamente.' if ok else '❌ Hay problemas: corrige lo marcado con ✘.'}\n"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
