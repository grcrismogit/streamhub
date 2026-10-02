from app.core.config import Settings

BASE = {"jwt_secret_key": "x" * 40, "s3_videos_bucket": "v", "s3_thumbnails_bucket": "t"}


def test_no_explicit_aws_credentials_by_default(monkeypatch):
    """En EC2 no hay access keys: boto3 debe usar el IAM Role."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    s = Settings(_env_file=None, **BASE)
    assert s.local_aws_credentials() == {}


def test_database_url_escapes_special_characters():
    s = Settings(
        _env_file=None, database_url=None, db_password="p@ss:w/rd#1", db_host="db.example.com", **BASE
    )
    url = s.sqlalchemy_url
    assert url.password == "p@ss:w/rd#1"
    assert url.host == "db.example.com"


def test_cors_origins_are_normalized():
    s = Settings(_env_file=None, cors_origins=" http://a.com/ ,http://b.com", **BASE)
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]
