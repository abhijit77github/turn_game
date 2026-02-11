@echo off
REM Docker SSL Setup Script for Reaction Game (Windows Batch)
REM This script sets up SSL certificates and runs all services

setlocal enabledelayedexpansion

REM Configuration
set DOMAIN=%1
set EMAIL=%2

if "!DOMAIN!"=="" set DOMAIN=example.com
if "!EMAIL!"=="" set EMAIL=admin@example.com

set CERT_PATH=certbot\conf\live\!DOMAIN!
set WEB_ROOT=certbot\www

echo.
echo ==========================================
echo Reaction Game Docker Setup with SSL
echo ==========================================
echo Domain: !DOMAIN!
echo Email: !EMAIL!
echo.

REM Create necessary directories
echo [1/5] Creating directories...
if not exist "certbot\conf" mkdir "certbot\conf"
if not exist "certbot\www" mkdir "certbot\www"
if not exist "nginx\conf.d" mkdir "nginx\conf.d"

REM Update Nginx configuration with your domain
echo [2/5] Updating Nginx configuration...
setlocal enabledelayedexpansion
for /f "delims=" %%i in (nginx\conf.d\default.conf) do (
    set "line=%%i"
    set "line=!line:example.com=!DOMAIN!"
    echo !line! >> nginx\conf.d\default.conf.tmp
)
move /y nginx\conf.d\default.conf.tmp nginx\conf.d\default.conf

REM Download SSL certificates (if not already present)
if not exist "!CERT_PATH!" (
    echo [3/5] Obtaining SSL certificate from Let's Encrypt...
    
    REM Start nginx temporarily for certbot validation
    docker-compose up -d nginx
    
    REM Wait for nginx to be ready
    timeout /t 5 /nobreak
    
    REM Run certbot
    docker-compose run --rm certbot certbot certonly ^
        --webroot -w /var/www/certbot ^
        --agree-tos ^
        --no-eff-email ^
        --email !EMAIL! ^
        -d !DOMAIN! ^
        -d www.!DOMAIN! ^
        -d api.!DOMAIN!
    
    echo ✓ SSL certificate obtained successfully!
) else (
    echo [3/5] SSL certificate already exists, skipping...
)

REM Start all services
echo [4/5] Starting all services...
docker-compose up -d

REM Wait for services to be healthy
echo [5/5] Waiting for services to be healthy...
timeout /t 10 /nobreak

REM Check service status
echo.
echo ==========================================
echo Service Status
echo ==========================================

docker ps | find "reaction_app_backend" >nul
if !errorlevel! equ 0 (
    echo ✓ Backend API: http://localhost:8000 (http://api.!DOMAIN! via Nginx)
) else (
    echo ✗ Backend API: Not running
)

docker ps | find "reaction_app_frontend" >nul
if !errorlevel! equ 0 (
    echo ✓ Frontend: http://localhost:3000 (https://!DOMAIN! via Nginx)
) else (
    echo ✗ Frontend: Not running
)

docker ps | find "reaction_app_nginx" >nul
if !errorlevel! equ 0 (
    echo ✓ Nginx Proxy: Listening on 80 and 443
) else (
    echo ✗ Nginx: Not running
)

docker ps | find "reaction_app_certbot" >nul
if !errorlevel! equ 0 (
    echo ✓ Certbot: Running (auto-renewal enabled)
) else (
    echo ✗ Certbot: Not running
)

echo.
echo ==========================================
echo Access Your Application
echo ==========================================
echo Frontend: https://!DOMAIN!
echo API: https://api.!DOMAIN!
echo Frontend (dev): http://localhost:3000
echo API (dev): http://localhost:8000
echo.

echo ==========================================
echo Docker Commands
echo ==========================================
echo View logs:           docker-compose logs -f
echo Stop services:       docker-compose down
echo Restart services:    docker-compose restart
echo Renew certificate:   docker-compose run --rm certbot certbot renew --force-renewal
echo.

echo ✓ Setup complete!
pause
