#!/bin/sh

set -e

# minio might still be starting
until /usr/bin/mc alias set myminio http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null;
do
  echo "Waiting for MinIO to be ready..."
  sleep 1
done

check_create_bucket() {
    local BUCKET=$1
    if [ -z "$BUCKET" ]; then return; fi

    if /usr/bin/mc ls "myminio/$BUCKET" > /dev/null 2>&1; then
        echo "Bucket '$BUCKET' already exists."
    else
        echo "Creating bucket '$BUCKET'."
        /usr/bin/mc mb "myminio/$BUCKET"
        /usr/bin/mc anonymous set download "myminio/$BUCKET"
        echo "Bucket '$BUCKET' created successfully."
    fi
}

check_create_bucket "$AWS_S3_BUCKET_NAME_STATIC"
check_create_bucket "$AWS_S3_BUCKET_NAME_MEDIA"
check_create_bucket "$EXTERNAL_S3_BUCKET_NAME"

echo "Completed creating buckets."
