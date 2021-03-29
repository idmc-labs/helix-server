#!/bin/sh

# requires
# s3cmd from s3tools
# requires proper .env file to setup aws keys

# setup environment vars for s3cmd from existing .env file
export $(cat .env | xargs)

# make bucket
s3cmd mb --access_key="$AWS_ACCESS_KEY_ID" --secret_key="$AWS_SECRET_ACCESS_KEY" "s3://$S3_BUCKET_NAME"
echo "Created bucket $S3_BUCKET_NAME"

# setup bucket policy
POLICY_FILENAME = "/tmp/bucket-policy.json"
touch "$POLICY_FILENAME"
cat <<EOL > "$POLICY_FILENAME"
{
  "Version": "2012-10-17",
  "Id": "$S3_BUCKET_NAME-read-only",
  "Statement": [
    {
      "Sid": "read-any",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
            "*"
        ]
      },
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::$S3_BUCKET_NAME/*"
      ]
    }
  ]
}
EOL

# write the bucket policy
s3cmd setpolicy --access_key="$AWS_ACCESS_KEY_ID" --secret_key="$AWS_SECRET_ACCESS_KEY" "$POLICY_FILENAME" "s3://$S3_BUCKET_NAME"
echo "Done setting the policy"

# remove the temp.json
rm "$POLICY_FILENAME"
