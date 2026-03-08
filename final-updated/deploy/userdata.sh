#!/bin/bash
set -ex
exec > /var/log/draftbridge-setup.log 2>&1

echo "=== DraftBridge Setup Starting ==="

# Add 2GB swap as safety net for Next.js build
dd if=/dev/zero of=/swapfile bs=1M count=2048
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

dnf update -y
dnf install -y docker git nginx
systemctl enable docker
systemctl start docker

# Install Node.js 18 from NodeSource
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
dnf install -y nodejs

echo "Node version: $(node --version)"
echo "npm version: $(npm --version)"

cd /home/ec2-user
git clone https://github.com/madhumithaa-08/DraftBridge-1.git draftbridge
chown -R ec2-user:ec2-user draftbridge
cd draftbridge/final-updated

# NOTE: .env is created at launch time via EC2 user-data injection.
# The template below uses placeholders — replace them before launching.
# See deploy instructions in README or use the launch command that
# injects real values via sed/envsubst at runtime.

cat > .env << 'ENVEOF'
APP_NAME=DraftBridge API
ENVIRONMENT=production
PORT=8000
LOG_LEVEL=info
AWS_REGION=__AWS_REGION__
AWS_ACCESS_KEY_ID=__AWS_ACCESS_KEY_ID__
AWS_SECRET_ACCESS_KEY=__AWS_SECRET_ACCESS_KEY__
S3_BUCKET_NAME=__S3_BUCKET_NAME__
DYNAMODB_TABLE_NAME=__DYNAMODB_TABLE_NAME__
BEDROCK_TEXT_MODEL=amazon.nova-lite-v1:0
BEDROCK_IMAGE_MODEL=amazon.nova-canvas-v1:0
BEDROCK_VIDEO_MODEL=amazon.nova-reel-v1:0
MAX_UPLOAD_SIZE_MB=10
PRESIGNED_URL_EXPIRY=3600
ENVEOF

# Build and start backend via Docker
docker build -t draftbridge-backend .
docker run -d --name draftbridge-backend --restart always -p 8000:8000 --env-file .env draftbridge-backend

# Wait for backend to be ready
echo "Waiting for backend..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 2
done

# Get public IP for frontend config
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)

# Build and start frontend
cd frontend

cat > .env.local << FENVEOF
NEXT_PUBLIC_API_URL=http://${PUBLIC_IP}/api
NODE_ENV=production
FENVEOF

export NODE_OPTIONS="--max-old-space-size=2048"
npm install
npm run build
nohup npx next start -p 3000 > /var/log/draftbridge-frontend.log 2>&1 &

# Wait for frontend to be ready
echo "Waiting for frontend..."
for i in $(seq 1 30); do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "Frontend is ready!"
        break
    fi
    sleep 2
done

# Configure Nginx reverse proxy
cat > /etc/nginx/conf.d/draftbridge.conf << 'NGINXEOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/api/health;
    }
}
NGINXEOF

rm -f /etc/nginx/conf.d/default.conf
systemctl enable nginx
systemctl start nginx

echo "=== DraftBridge Setup Complete ==="
echo "Backend health: $(curl -s http://localhost:8000/api/health)"
echo "Access at http://${PUBLIC_IP}/"
