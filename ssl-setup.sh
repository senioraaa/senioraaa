#!/bin/bash

echo "🔒 إعداد شهادة SSL..."

DOMAIN="shahd-senior.com"
EMAIL="admin@shahd-senior.com"
WEBROOT="/var/www/shahd-senior"

# تثبيت Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# إنشاء الشهادة
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --no-eff-email

# إعداد التجديد التلقائي
sudo crontab -l | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -

# التحقق من الشهادة
echo "🔍 التحقق من الشهادة..."
openssl x509 -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem -text -noout | grep -A2 "Validity"

# إعداد إعادة التوجيه HTTPS
cat > /etc/nginx/sites-available/shahd-senior << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    # إعدادات SSL الأمنية
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # رؤوس الأمان
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    root $WEBROOT;
    index index.html;
    
    location / {
        try_files \$uri \$uri/ /index.html;
    }
    
    # ضغط الملفات
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # تخزين مؤقت للملفات الثابتة
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# تفعيل الموقع
sudo ln -s /etc/nginx/sites-available/shahd-senior /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

echo "✅ تم إعداد SSL بنجاح!"
    
