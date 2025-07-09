#!/bin/bash

echo "🔨 بدء عملية البناء..."

# تنظيف المجلدات السابقة
rm -rf dist/
mkdir -p dist/

# نسخ الملفات الأساسية
cp -r css/ dist/
cp -r js/ dist/
cp -r images/ dist/
cp -r data/ dist/
cp -r docs/ dist/

# نسخ صفحات HTML
cp index.html dist/
cp fc25.html dist/
cp faq.html dist/
cp terms.html dist/
cp contact.html dist/

# تحسين الملفات
echo "⚡ تحسين الملفات..."

# ضغط CSS
for file in dist/css/*.css; do
    if [ -f "$file" ]; then
        echo "ضغط $file..."
        # إزالة التعليقات والمسافات الزائدة
        sed -i 's/\/\*.*\*\///g' "$file"
        sed -i 's/[[:space:]]*{[[:space:]]*/{/g' "$file"
        sed -i 's/[[:space:]]*}[[:space:]]*/}/g' "$file"
        sed -i 's/[[:space:]]*:[[:space:]]*/:/g' "$file"
        sed -i 's/[[:space:]]*;[[:space:]]*/;/g' "$file"
    fi
done

# ضغط JavaScript
for file in dist/js/*.js; do
    if [ -f "$file" ]; then
        echo "ضغط $file..."
        # إزالة التعليقات والمسافات الزائدة
        sed -i 's/\/\/.*$//g' "$file"
        sed -i 's/\/\*.*\*\///g' "$file"
        sed -i '/^[[:space:]]*$/d' "$file"
    fi
done

# تحسين الصور
echo "🖼️ تحسين الصور..."
for file in dist/images/*.{jpg,jpeg,png}; do
    if [ -f "$file" ]; then
        echo "تحسين $file..."
        # تقليل جودة الصور (يحتاج imagemagick)
        # convert "$file" -quality 85 "$file"
    fi
done

# إنشاء ملف الموقع
echo "📄 إنشاء sitemap.xml..."
cat > dist/sitemap.xml << EOF


    
        https://shahd-senior.onrender.com/
        $(date -Iseconds)
        daily
        1.0
    
    
        https://shahd-senior.onrender.com/fc25.html
        $(date -Iseconds)
        weekly
        0.8
    
    
        https://shahd-senior.onrender.com/faq.html
        $(date -Iseconds)
        monthly
        0.6
    
    
        https://shahd-senior.onrender.com/terms.html
        $(date -Iseconds)
        monthly
        0.5
    
    
        https://shahd-senior.onrender.com/contact.html
        $(date -Iseconds)
        monthly
        0.4
    

EOF

# إنشاء ملف robots.txt
echo "🤖 إنشاء robots.txt..."
cat > dist/robots.txt << EOF
User-agent: *
Allow: /
Sitemap: https://shahd-senior.onrender.com/sitemap.xml

# منع الزحف لملفات النظام
Disallow: /js/
Disallow: /css/
Disallow: /data/
Disallow: /*.json$
EOF

# إنشاء ملف manifest.json
echo "📱 إنشاء manifest.json..."
cat > dist/manifest.json << EOF
{
    "name": "منصة شهد السنيورة",
    "short_name": "شهد السنيورة",
    "description": "أفضل منصة لبيع الألعاب الرقمية في مصر",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#0066cc",
    "orientation": "portrait-primary",
    "icons": [
        {
            "src": "images/icon-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "images/icon-512x512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}
EOF

# إنشاء Service Worker
echo "⚙️ إنشاء Service Worker..."
cat > dist/sw.js << EOF
const CACHE_NAME = 'shahd-senior-v1';
const urlsToCache = [
    '/',
    '/index.html',
    '/fc25.html',
    '/css/style.css',
    '/js/main.js',
    '/images/fc25.jpg',
    '/data/games.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});
EOF

echo "✅ تم إنهاء عملية البناء بنجاح!"
echo "📊 إحصائيات البناء:"
echo "حجم المجلد: $(du -sh dist/ | cut -f1)"
echo "عدد الملفات: $(find dist/ -type f | wc -l)"
    
