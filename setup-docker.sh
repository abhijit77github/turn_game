#!/bin/bash

# Docker SSL Setup Script for Reaction Game
# This script sets up SSL certificates and runs all services

set -e

# Configuration
DOMAIN="${1:-example.com}"
EMAIL="${2:-admin@example.com}"
CERT_PATH="./certbot/conf/live/$DOMAIN"
WEB_ROOT="./certbot/www"

echo "=========================================="
echo "Reaction Game Docker Setup with SSL"
echo "=========================================="
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Create necessary directories
echo "[1/5] Creating directories..."
mkdir -p certbot/conf certbot/www nginx/conf.d

# Update Nginx configuration with your domain
echo "[2/5] Updating Nginx configuration..."
sed -i "s/example.com/$DOMAIN/g" nginx/conf.d/default.conf

# Download SSL certificates (if not already present)
if [ ! -d "$CERT_PATH" ]; then
    echo "[3/5] Obtaining SSL certificate from Let's Encrypt..."
    
    # Start nginx temporarily for certbot validation
    docker-compose up -d nginx
    
    # Wait for nginx to be ready
    sleep 5
    
    # Run certbot
    docker-compose run --rm certbot certbot certonly \
        --webroot -w /var/www/certbot \
        --agree-tos \
        --no-eff-email \
        --email "$EMAIL" \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        -d "api.$DOMAIN"
    
    echo "✓ SSL certificate obtained successfully!"
else
    echo "[3/5] SSL certificate already exists, skipping..."
fi

# Start all services
echo "[4/5] Starting all services..."
docker-compose up -d

# Wait for services to be healthy
echo "[5/5] Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "=========================================="
echo "Service Status"
echo "=========================================="

if docker ps | grep -q reaction_app_backend; then
    echo "✓ Backend API: http://localhost:8000 (http://api.$DOMAIN via Nginx)"
else
    echo "✗ Backend API: Not running"
fi

if docker ps | grep -q reaction_app_frontend; then
    echo "✓ Frontend: http://localhost:3000 (https://$DOMAIN via Nginx)"
else
    echo "✗ Frontend: Not running"
fi

if docker ps | grep -q reaction_app_nginx; then
    echo "✓ Nginx Proxy: Listening on 80 and 443"
else
    echo "✗ Nginx: Not running"
fi

if docker ps | grep -q reaction_app_certbot; then
    echo "✓ Certbot: Running (auto-renewal enabled)"
else
    echo "✗ Certbot: Not running"
fi

echo ""
echo "=========================================="
echo "Access Your Application"
echo "=========================================="
echo "Frontend: https://$DOMAIN"
echo "API: https://api.$DOMAIN"
echo "Frontend (dev): http://localhost:3000"
echo "API (dev): http://localhost:8000"
echo ""

echo "=========================================="
echo "Docker Commands"
echo "=========================================="
echo "View logs:           docker-compose logs -f"
echo "Stop services:       docker-compose down"
echo "Restart services:    docker-compose restart"
echo "Renew certificate:   docker-compose run --rm certbot certbot renew --force-renewal"
echo ""

echo "✓ Setup complete!"
