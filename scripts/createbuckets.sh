#!/bin/sh

set -e

until /usr/bin/mc alias set myminio http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null;
do
  echo "Waiting for MinIO to be ready..."
  sleep 2
done

echo "Creating buckets..."
if [ -n "$AWS_S3_BUCKET_NAME_STATIC" ]; then
  /usr/bin/mc mb --quiet myminio/"$AWS_S3_BUCKET_NAME_STATIC" 2>/dev/null || true
  /usr/bin/mc anonymous set none myminio/"$AWS_S3_BUCKET_NAME_STATIC" 2>/dev/null || true
fi
if [ -n "$AWS_S3_BUCKET_NAME_MEDIA" ]; then
  /usr/bin/mc mb --quiet myminio/"$AWS_S3_BUCKET_NAME_MEDIA" 2>/dev/null || true
  /usr/bin/mc anonymous set none myminio/"$AWS_S3_BUCKET_NAME_MEDIA" 2>/dev/null || true
fi
if [ -n "$EXTERNAL_S3_BUCKET_NAME" ]; then
  /usr/bin/mc mb --quiet myminio/"$EXTERNAL_S3_BUCKET_NAME" 2>/dev/null || true
  /usr/bin/mc anonymous set none myminio/"$EXTERNAL_S3_BUCKET_NAME" 2>/dev/null || true
fi
echo "Completed creating buckets."
