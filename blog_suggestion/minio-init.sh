#!/bin/sh
# minio-init.sh - Initialize MinIO buckets

set -e

echo "Waiting for MinIO to be ready..."
sleep 10

# Configure MinIO client
mc config host add minio http://minio:9000 ${MINIO_ROOT_USER:-admin} ${MINIO_ROOT_PASSWORD:-admin123}

# Create buckets
echo "Creating buckets..."
mc mb --ignore-existing minio/blog-uploads
mc mb --ignore-existing minio/blog-assets
mc mb --ignore-existing minio/blog-backups

# Set bucket policies (optional)
echo "Setting bucket policies..."
cat > /tmp/policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": ["*"]
      },
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::blog-uploads/*"]
    }
  ]
}
EOF

mc policy set-json /tmp/policy.json minio/blog-uploads

echo "MinIO initialization complete!"
echo "MinIO Console: http://localhost:9001"
echo "Username: ${MINIO_ROOT_USER:-admin}"
echo "Password: ${MINIO_ROOT_PASSWORD:-admin123}"