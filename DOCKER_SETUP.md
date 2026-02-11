# Docker Setup Instructions

## Prerequisites

- Docker and Docker Compose installed
- Domain name pointing to your server's IP address
- Port 80 and 443 accessible from the internet (for SSL certificate verification)

## Quick Start (One Command)

### Linux/macOS:
```bash
chmod +x setup-docker.sh
./setup-docker.sh your-domain.com your-email@example.com
```

### Windows:
```cmd
setup-docker.bat your-domain.com your-email@example.com
```

## What the Setup Does

1. **Creates directories** for SSL certificates and Nginx configuration
2. **Updates Nginx configuration** with your domain name
3. **Obtains SSL certificates** from Let's Encrypt using HTTP-01 challenge (certbot)
4. **Starts all services** with Docker Compose:
   - Backend API (FastAPI/Python)
   - Frontend (Vue.js/Node.js)
   - Nginx Reverse Proxy (SSL termination)
   - Certbot (automatic SSL renewal)

## Manual Setup (Step by Step)

### 1. Create Directories
```bash
mkdir -p certbot/conf certbot/www nginx/conf.d
```

### 2. Update Nginx Configuration
Edit `nginx/conf.d/default.conf` and replace `example.com` with your actual domain.

### 3. Start Nginx (for certificate validation)
```bash
docker-compose up -d nginx
```

### 4. Obtain SSL Certificate
```bash
docker-compose run --rm certbot certbot certonly \
    --webroot -w /var/www/certbot \
    --agree-tos \
    --no-eff-email \
    --email your-email@example.com \
    -d your-domain.com \
    -d www.your-domain.com \
    -d api.your-domain.com
```

### 5. Start All Services
```bash
docker-compose up -d
```

## Verify Services

```bash
# Check all services are running
docker ps

# View logs
docker-compose logs -f

# Test frontend
curl https://your-domain.com

# Test API
curl https://api.your-domain.com/api/games
```

## Environment Variables

Edit `docker-compose.yml` to configure:
- `VITE_API_URL`: Frontend API endpoint (defaults to https://api.example.com)
- `DATABASE_URL`: Backend database path (defaults to sqlite:///./game.db)

## SSL Certificate Renewal

Certbot automatically renews certificates before expiration. To manually renew:

```bash
docker-compose run --rm certbot certbot renew --force-renewal
```

## Troubleshooting

### Certificate validation fails
- Ensure port 80 is accessible from the internet
- Check that your domain DNS is pointing to the server
- Verify Nginx is running: `docker ps | grep nginx`

### Services not starting
- Check logs: `docker-compose logs`
- Ensure ports 80 and 443 are not in use: `netstat -tuln | grep -E ':(80|443)'`

### WebSocket connection issues
- Verify `proxy_read_timeout` in Nginx config is set to 3600s or higher
- Check that the connection is upgraded: `Upgrade: websocket`

## Monitoring

### View real-time logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx
```

### Check service health
```bash
docker-compose ps
```

### Monitor certificate expiry
```bash
docker-compose run --rm certbot certbot certificates
```

## Backup

### Backup SSL certificates
```bash
tar -czf backup-certs.tar.gz certbot/conf
```

### Backup database
```bash
tar -czf backup-database.tar.gz backend/game.db
```

## Production Recommendations

1. Use strong passwords and secure your JWT secrets
2. Enable rate limiting (already configured in Nginx)
3. Set up regular backups of certificates and database
4. Monitor logs for suspicious activity
5. Keep Docker images updated: `docker-compose pull && docker-compose up -d`

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend

# Rebuild images
docker-compose build --no-cache

# Execute command in container
docker-compose exec backend bash

# View resource usage
docker stats
```
