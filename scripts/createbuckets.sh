#!/bin/sh

set -e

# S3 server might still be starting
until /usr/bin/mc alias set myrustfs http://rustfs:9000 "$RUSTFS_ACCESS_KEY" "$RUSTFS_SECRET_KEY" 2>/dev/null;
do
  echo "Waiting for s3 server(RustFS) to be ready..."
  sleep 1
done

check_create_bucket() {
    local BUCKET=$1
    if [ -z "$BUCKET" ]; then return; fi

    if /usr/bin/mc ls "myrustfs/$BUCKET" > /dev/null 2>&1; then
        echo "Bucket '$BUCKET' already exists."
    else
        echo "Creating bucket '$BUCKET'."
        /usr/bin/mc mb "myrustfs/$BUCKET"
        /usr/bin/mc anonymous set download "myrustfs/$BUCKET"
        echo "Bucket '$BUCKET' created successfully."
    fi
}

check_create_bucket "$AWS_S3_BUCKET_NAME_STATIC"
check_create_bucket "$AWS_S3_BUCKET_NAME_MEDIA"
check_create_bucket "$EXTERNAL_S3_BUCKET_NAME"

echo "Completed creating buckets."
