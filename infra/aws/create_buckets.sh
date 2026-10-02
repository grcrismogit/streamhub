#!/usr/bin/env bash
# Crea y configura los 3 buckets S3 con AWS CLI (alternativa a la consola).
# Uso: SUFFIX=cris2026 REGION=us-east-1 bash infra/aws/create_buckets.sh
set -euo pipefail
SUFFIX="${SUFFIX:?Define SUFFIX (los nombres de bucket son globales y únicos)}"
REGION="${REGION:-us-east-1}"
FRONT="streamhub-frontend-$SUFFIX"; VIDEOS="streamhub-videos-$SUFFIX"; THUMBS="streamhub-thumbnails-$SUFFIX"
DIR="$(cd "$(dirname "$0")" && pwd)"

mk() { # us-east-1 no acepta LocationConstraint
  if [ "$REGION" = "us-east-1" ]; then aws s3api create-bucket --bucket "$1" --region "$REGION" >/dev/null
  else aws s3api create-bucket --bucket "$1" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION" >/dev/null; fi
  echo "✓ $1"
}

# --- Bucket 1: Frontend (público, hosting estático) ---
mk "$FRONT"
aws s3api put-public-access-block --bucket "$FRONT" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false
aws s3api put-bucket-website --bucket "$FRONT" --website-configuration "file://$DIR/s3-website-config.json"
sed "s/streamhub-frontend-XXXX/$FRONT/" "$DIR/s3-frontend-bucket-policy.json" > /tmp/front-policy.json
aws s3api put-bucket-policy --bucket "$FRONT" --policy file:///tmp/front-policy.json

# --- Buckets 2 y 3: Videos y Miniaturas (PRIVADOS, cifrados) ---
for B in "$VIDEOS" "$THUMBS"; do
  mk "$B"
  aws s3api put-public-access-block --bucket "$B" --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption --bucket "$B" --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-bucket-lifecycle-configuration --bucket "$B" --lifecycle-configuration "file://$DIR/s3-media-lifecycle.json"
done

echo
echo "Frontend: http://$FRONT.s3-website-$REGION.amazonaws.com"
echo "Usa en api.env:  S3_VIDEOS_BUCKET=$VIDEOS  S3_THUMBNAILS_BUCKET=$THUMBS"
