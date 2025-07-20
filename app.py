from flask import Flask, render_template, request, jsonify, session, abort
import json, os, secrets, time, re, hashlib
from datetime import datetime, timedelta
import logging
from functools import wraps
from collections import defaultdict
import urllib.parse

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

# إعدادات الواتساب
WHATSAPP_NUMBER = "+201094591331"  # غير الرقم هنا
BUSINESS_NAME = "Senior Gaming Store"

# Rate Limiting يدوي بسيط وقوي
def rate_limit(max_requests=10, window=60):
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
        return get_default_prices()

# إنشاء ملف أسعار افتراضي
def create_default_prices():
    global prices_cache
    default_prices = get_default_prices()
    
    try:
        with open('prices.json', 'w', encoding='utf-8') as f:
            json.dump(default_prices, f, ensure_ascii=False, indent=2)
        logger.info("✅ تم إنشاء ملف الأسعار الافتراضي")
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء ملف الأسعار: {e}")
    
    prices_cache = default_prices
    return default_prices

# الأسعار الافتراضية
def get_default_prices():
    return {
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
            "delivery_time": "15 ساعة كحد أقصى",
            "whatsapp_number": "+201234567890"
        }
    }

# Headers أمنية قوية
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://wa.me"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# تنظيف المدخلات
def sanitize_input(text, max_length=100):
    if not text:
        return None
    
    text = str(text).strip()
    
    if len(text) > max_length:
        return None
    
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
@rate_limit(max_requests=20, window=60)
def index():
    try:
        prices = load_prices()
        csrf_token = generate_csrf_token()
        
        logger.info("✅ تم تحميل الصفحة الرئيسية بنجاح")
        
        return render_template('index.html', 
                             prices=prices, 
                             csrf_token=csrf_token)
    except Exception as e:
        logger.error(f"❌ خطأ في الصفحة الرئيسية: {e}")
        abort(500)

# إنشاء رابط واتساب مباشر - بدون حفظ
@app.route('/whatsapp', methods=['POST'])
@rate_limit(max_requests=15, window=60)
def create_whatsapp_link():
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    try:
        # التحقق من CSRF
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token):
            logger.warning(f"🚨 محاولة CSRF من IP: {client_ip}")
            return jsonify({'error': 'رمز الأمان غير صحيح'}), 400
        
        # تنظيف البيانات
        game_type = sanitize_input(request.form.get('game_type'))
        platform = sanitize_input(request.form.get('platform'))
        account_type = sanitize_input(request.form.get('account_type'))
        
        if not all([game_type, platform, account_type]):
            return jsonify({'error': 'يرجى اختيار جميع الخيارات أولاً'}), 400
        
        # تحميل الأسعار والتحقق
        prices = load_prices()
        
        if (game_type not in prices.get('games', {}) or
            platform not in prices['games'][game_type].get('platforms', {}) or
            account_type not in prices['games'][game_type]['platforms'][platform].get('accounts', {})):
            logger.warning(f"🚨 اختيار منتج غير صحيح من IP: {client_ip}")
            return jsonify({'error': 'اختيار المنتج غير صحيح'}), 400
        
        # بيانات المنتج
        game_name = prices['games'][game_type]['name']
        platform_name = prices['games'][game_type]['platforms'][platform]['name']
        account_name = prices['games'][game_type]['platforms'][platform]['accounts'][account_type]['name']
        price = prices['games'][game_type]['platforms'][platform]['accounts'][account_type]['price']
        currency = prices.get('settings', {}).get('currency', 'جنيه')
        
        # إنشاء ID مرجعي (للتتبع فقط - لا يُحفظ)
        timestamp = str(int(time.time()))
        reference_id = hashlib.md5(f"{timestamp}{client_ip}{game_type}{platform}".encode()).hexdigest()[:8].upper()
        
        # إنشاء رسالة الواتساب
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        message = f"""🎮 *استفسار من {BUSINESS_NAME}*

🆔 *المرجع:* {reference_id}

🎯 *المطلوب:*
• اللعبة: {game_name}
• المنصة: {platform_name}
• نوع الحساب: {account_name}
• السعر: {price} {currency}

⏰ *وقت الاستفسار:* {current_time}

👋 *السلام عليكم، أريد الاستفسار عن هذا المنتج*

شكراً 🌟"""
        
        # ترميز الرسالة للـ URL
        encoded_message = urllib.parse.quote(message)
        
        # رقم الواتساب من الإعدادات
        whatsapp_number = prices.get('settings', {}).get('whatsapp_number', WHATSAPP_NUMBER)
        clean_number = whatsapp_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # إنشاء رابط الواتساب
        whatsapp_url = f"https://wa.me/{clean_number}?text={encoded_message}"
        
        logger.info(f"✅ فتح واتساب: {reference_id} - {platform} {account_type} - {price} {currency} - IP: {client_ip}")
        
        # CSRF token جديد
        new_csrf_token = generate_csrf_token()
        
        return jsonify({
            'success': True,
            'reference_id': reference_id,
            'whatsapp_url': whatsapp_url,
            'price': price,
            'currency': currency,
            'message': 'سيتم فتح الواتساب الآن...',
            'csrf_token': new_csrf_token
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء رابط الواتساب: {e}")
        return jsonify({'error': 'حدث خطأ في النظام - يرجى المحاولة مرة أخرى'}), 500

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

# Health check
@app.route('/health')
@app.route('/ping')
def health_check():
    try:
        # فحص الأسعار فقط
        prices = load_prices()
        
        return {
            'status': 'healthy',
            'prices': 'ok' if prices else 'error',
            'timestamp': datetime.now().isoformat()
        }, 200
    except Exception as e:
        logger.error(f"❌ خطأ في Health Check: {e}")
        return {'status': 'error', 'message': str(e)}, 500

# Robots.txt
@app.route('/robots.txt')
def robots():
    return '''User-agent: *
Disallow: /admin/
Disallow: /api/
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
    load_prices()
    logger.info("🚀 تم تشغيل التطبيق بنجاح - واتساب مباشر")
    
    app.run(
        debug=False, 
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000))
    )
else:
    # تشغيل تلقائي عند استخدام gunicorn
    load_prices()
    logger.info("🚀 تم تشغيل التطبيق عبر gunicorn - واتساب مباشر")
