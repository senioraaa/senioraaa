from flask import Flask, render_template, request, jsonify, session, abort
import json, os, sqlite3, uuid, secrets, time, re, hashlib
from datetime import datetime, timedelta
import logging
from functools import wraps
from collections import defaultdict

# إعداد التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# إعداد الـ Logging للأمان
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# متغيرات الحماية العامة
blocked_ips = {}
request_counts = defaultdict(list)
failed_attempts = {}
prices_cache = {}
last_prices_update = 0

# Rate Limiting يدوي بسيط وقوي
def rate_limit(max_requests=5, window=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            current_time = time.time()
            
            # تنظيف الطلبات القديمة
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip]
                if current_time - req_time < window
            ]
            
            # فحص عدد الطلبات
            if len(request_counts[client_ip]) >= max_requests:
                logger.warning(f"🚨 Rate limit exceeded for IP: {client_ip}")
                abort(429)
            
            # إضافة الطلب الحالي
            request_counts[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# إنشاء قاعدة البيانات
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        game_type TEXT NOT NULL,
        platform TEXT NOT NULL,
        account_type TEXT NOT NULL,
        price INTEGER NOT NULL,
        customer_phone TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT
    )''')
    
    conn.commit()
    conn.close()
    logger.info("✅ تم إعداد قاعدة البيانات")

# تحميل الأسعار من JSON مع Cache
def load_prices():
    global prices_cache, last_prices_update
    
    try:
        if os.path.exists('prices.json'):
            file_time = os.path.getmtime('prices.json')
            if file_time > last_prices_update:
                with open('prices.json', 'r', encoding='utf-8') as f:
                    prices_cache = json.load(f)
                last_prices_update = file_time
                logger.info("🔄 تم تحديث الأسعار من ملف JSON")
        
        if not prices_cache:
            create_default_prices()
            
        return prices_cache
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الأسعار: {e}")
        return {}

# إنشاء ملف أسعار افتراضي
def create_default_prices():
    global prices_cache
    default_prices = {
        "games": {
            "FC25": {
                "name": "FIFA FC 25",
                "platforms": {
                    "PS4": {
                        "name": "PlayStation 4",
                        "icon": "🎮",
                        "accounts": {
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 85},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 70},
                            "Full": {"name": "Full - حساب كامل", "price": 120}
                        }
                    },
                    "PS5": {
                        "name": "PlayStation 5", 
                        "icon": "🎮",
                        "accounts": {
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 90},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 75},
                            "Full": {"name": "Full - حساب كامل", "price": 125}
                        }
                    },
                    "Xbox": {
                        "name": "Xbox Series X/S & Xbox One",
                        "icon": "✕",
                        "accounts": {
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 85},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 70},
                            "Full": {"name": "Full - حساب كامل", "price": 120}
                        }
                    },
                    "PC": {
                        "name": "PC (Steam/Epic Games)",
                        "icon": "🖥️",
                        "accounts": {
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 80},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 65},
                            "Full": {"name": "Full - حساب كامل", "price": 115}
                        }
                    }
                }
            }
        },
        "settings": {
            "currency": "جنيه مصري",
            "warranty": "1 سنة",
            "delivery_time": "15 ساعة كحد أقصى"
        }
    }
    
    with open('prices.json', 'w', encoding='utf-8') as f:
        json.dump(default_prices, f, ensure_ascii=False, indent=2)
    
    prices_cache = default_prices
    logger.info("✅ تم إنشاء ملف الأسعار الافتراضي")

# Headers أمنية قوية
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# حماية قوية من Brute Force
def security_check(ip_address):
    current_time = time.time()
    
    if ip_address in blocked_ips:
        block_time, duration = blocked_ips[ip_address]
        if current_time - block_time < duration:
            return False
        else:
            del blocked_ips[ip_address]
    
    return True

def log_suspicious_activity(ip_address, activity):
    current_time = time.time()
    
    if ip_address not in failed_attempts:
        failed_attempts[ip_address] = []
    
    failed_attempts[ip_address].append(current_time)
    
    # تنظيف المحاولات القديمة
    failed_attempts[ip_address] = [
        t for t in failed_attempts[ip_address] 
        if current_time - t < 300
    ]
    
    # حظر إذا تجاوز 5 محاولات في 5 دقائق
    if len(failed_attempts[ip_address]) >= 5:
        blocked_ips[ip_address] = (current_time, 1800)  # حظر 30 دقيقة
        logger.warning(f"🚨 تم حظر IP {ip_address} بسبب: {activity}")
        return True
    
    return False

# تنظيف المدخلات
def sanitize_input(text, max_length=100, allow_numbers_only=False):
    if not text:
        return None
    
    text = str(text).strip()
    
    if len(text) > max_length:
        return None
    
    if allow_numbers_only:
        text = re.sub(r'[^\d+]', '', text)
        if not re.match(r'^[\d+]{10,15}$', text):
            return None
    else:
        text = re.sub(r'[<>"\';\\&]', '', text)
        text = re.sub(r'(script|javascript|vbscript|onload|onerror)', '', text, flags=re.IGNORECASE)
    
    return text

# CSRF Protection
def generate_csrf_token():
    token = secrets.token_urlsafe(32)
    session['csrf_token'] = token
    return token

def validate_csrf_token(token):
    return token and session.get('csrf_token') == token

# الصفحة الرئيسية
@app.route('/')
@rate_limit(max_requests=10, window=60)
def index():
    try:
        prices = load_prices()
        csrf_token = generate_csrf_token()
        
        return render_template('index.html', 
                             prices=prices, 
                             csrf_token=csrf_token)
    except Exception as e:
        logger.error(f"❌ خطأ في الصفحة الرئيسية: {e}")
        abort(500)

# API للحصول على الأسعار
@app.route('/api/prices')
@rate_limit(max_requests=10, window=60)
def get_prices():
    try:
        prices = load_prices()
        return jsonify(prices)
    except Exception as e:
        logger.error(f"❌ خطأ في API الأسعار: {e}")
        return jsonify({'error': 'خطأ في النظام'}), 500

# معالج الطلبات
@app.route('/order', methods=['POST'])
@rate_limit(max_requests=3, window=60)
def create_order():
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    if not security_check(client_ip):
        logger.warning(f"🚨 محاولة وصول من IP محظور: {client_ip}")
        abort(429)
    
    try:
        # التحقق من CSRF
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            log_suspicious_activity(client_ip, 'Invalid CSRF Token')
            return jsonify({'error': 'رمز الأمان غير صحيح'}), 400
        
        # تنظيف البيانات
        game_type = sanitize_input(request.form.get('game_type'))
        platform = sanitize_input(request.form.get('platform'))
        account_type = sanitize_input(request.form.get('account_type'))
        phone = sanitize_input(request.form.get('phone'), 20, allow_numbers_only=True)
        
        if not all([game_type, platform, account_type, phone]):
            log_suspicious_activity(client_ip, 'Incomplete Data')
            return jsonify({'error': 'جميع البيانات مطلوبة'}), 400
        
        # تحميل الأسعار والتحقق
        prices = load_prices()
        
        if (game_type not in prices.get('games', {}) or
            platform not in prices['games'][game_type].get('platforms', {}) or
            account_type not in prices['games'][game_type]['platforms'][platform].get('accounts', {})):
            log_suspicious_activity(client_ip, 'Invalid Product Selection')
            return jsonify({'error': 'اختيار المنتج غير صحيح'}), 400
        
        # الحصول على السعر
        price = prices['games'][game_type]['platforms'][platform]['accounts'][account_type]['price']
        
        # إنشاء ID فريد
        order_id = hashlib.md5(f"{time.time()}{client_ip}{phone}".encode()).hexdigest()[:8].upper()
        
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        
        # فحص تكرار الرقم (منع الـ Spam)
        c.execute('''SELECT COUNT(*) FROM orders 
                     WHERE customer_phone = ? AND created_at > datetime('now', '-1 hour')''', (phone,))
        
        if c.fetchone()[0] >= 3:
            conn.close()
            log_suspicious_activity(client_ip, 'Phone Number Spam')
            return jsonify({'error': 'تم تجاوز الحد المسموح للطلبات لهذا الرقم'}), 429
        
        # حفظ الطلب
        c.execute('''INSERT INTO orders 
                     (id, game_type, platform, account_type, price, customer_phone, ip_address, user_agent)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (order_id, game_type, platform, account_type, price, phone, client_ip, user_agent))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ طلب جديد: {order_id} - {platform} {account_type} - {price} ج - {phone}")
        
        # CSRF token جديد
        new_csrf_token = generate_csrf_token()
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'price': price,
            'currency': prices.get('settings', {}).get('currency', 'جنيه'),
            'message': 'تم إنشاء طلبك بنجاح!',
            'csrf_token': new_csrf_token
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء الطلب: {e}")
        return jsonify({'error': 'حدث خطأ في النظام'}), 500

# Health check
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}, 200

# Robots.txt
@app.route('/robots.txt')
def robots():
    return '''User-agent: *
Disallow: /admin/
Disallow: /api/
Disallow: /order
Crawl-delay: 10''', 200, {'Content-Type': 'text/plain'}

# معالجات الأخطاء
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'طلب غير صحيح'}), 400

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(429)
def too_many_requests(error):
    return render_template('429.html'), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ خطأ داخلي: {error}")
    return render_template('500.html'), 500

# تشغيل التطبيق
if __name__ == '__main__':
    init_db()
    load_prices()
    app.run(
        debug=False, 
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000))
    )
