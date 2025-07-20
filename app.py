from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import json
import os
import logging
import time
import re
from datetime import datetime

# إنشاء التطبيق
app = Flask(__name__)

# 🔐 الإعدادات الأمنية
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32))
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

# 🛡️ حماية CSRF
csrf = CSRFProtect(app)

# 🚫 Rate Limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour", "20 per minute"],
    storage_uri="memory://"
)

# 📝 تسجيل الأحداث
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🛡️ Headers أمنية
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response

# 📄 تنظيف المدخلات
def sanitize_input(text, max_length=100):
    """تنظيف وتحقق من صحة المدخلات"""
    if not text or not isinstance(text, str):
        return None
    
    if len(text) > max_length:
        return None
    
    # إزالة الأحرف الخطرة
    text = re.sub(r'[<>"\';]', '', text)
    return text.strip()

# 📊 تحميل الأسعار من JSON
def load_prices():
    """تحميل الأسعار من ملف JSON"""
    try:
        with open('data/prices.json', 'r', encoding='utf-8') as f:
            prices_data = json.load(f)
        return prices_data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"خطأ في تحميل ملف الأسعار: {e}")
        return get_default_prices()

def get_default_prices():
    """الأسعار الافتراضية في حالة عدم وجود ملف"""
    return {
        "games": [
            {
                "id": "fc25",
                "name": "FC 25",
                "platforms": {
                    "ps4": {
                        "primary": 85,
                        "secondary": 70,
                        "full": 120
                    },
                    "ps5": {
                        "primary": 90,
                        "secondary": 75,
                        "full": 125
                    },
                    "xbox": {
                        "primary": 85,
                        "secondary": 70,
                        "full": 120
                    },
                    "pc": {
                        "primary": 80,
                        "secondary": 65,
                        "full": 115
                    }
                }
            }
        ],
        "last_updated": "2025-01-20T10:00:00Z"
    }

# 💾 حفظ الطلبات
def save_order(order):
    """حفظ الطلب في ملف JSON"""
    try:
        # قراءة الطلبات الموجودة
        try:
            with open('orders.json', 'r', encoding='utf-8') as f:
                orders = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            orders = []
        
        # إضافة الطلب الجديد
        orders.append(order)
        
        # حفظ البيانات المحدثة
        with open('orders.json', 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"خطأ في حفظ الطلب: {e}")
        raise

# 🏠 الصفحة الرئيسية
@app.route('/')
def index():
    try:
        prices_data = load_prices()
        return render_template('index.html', prices=prices_data)
    except Exception as e:
        logger.error(f"خطأ في الصفحة الرئيسية: {e}")
        return render_template('index.html', prices=get_default_prices())

# 🎮 صفحة FC25
@app.route('/fc25')
def fc25():
    try:
        prices_data = load_prices()
        fc25_game = next((game for game in prices_data['games'] if game['id'] == 'fc25'), None)
        return render_template('fc25.html', game=fc25_game, prices=prices_data)
    except Exception as e:
        logger.error(f"خطأ في صفحة FC25: {e}")
        return render_template('fc25.html', game=None, prices=get_default_prices())

# 📞 صفحة التواصل
@app.route('/contact')
def contact():
    return render_template('contact.html')

# ❓ صفحة الأسئلة الشائعة
@app.route('/faq')
def faq():
    return render_template('faq.html')

# 📋 صفحة الشروط والأحكام
@app.route('/terms')
def terms():
    return render_template('terms.html')

# 🔧 API للحصول على الأسعار
@app.route('/api/prices')
@limiter.limit("30 per minute")
def api_prices():
    try:
        prices_data = load_prices()
        return jsonify({
            'success': True,
            'data': prices_data
        })
    except Exception as e:
        logger.error(f"خطأ في API الأسعار: {e}")
        return jsonify({
            'success': False,
            'error': 'خطأ في تحميل الأسعار'
        }), 500

# 🔧 API للحصول على أسعار لعبة معينة
@app.route('/api/prices/<game_id>')
@limiter.limit("30 per minute")
def api_game_prices(game_id):
    try:
        prices_data = load_prices()
        game = next((g for g in prices_data['games'] if g['id'] == game_id), None)
        
        if game:
            return jsonify({
                'success': True,
                'data': game
            })
        else:
            return jsonify({
                'success': False,
                'error': 'اللعبة غير موجودة'
            }), 404
            
    except Exception as e:
        logger.error(f"خطأ في API أسعار اللعبة: {e}")
        return jsonify({
            'success': False,
            'error': 'خطأ في تحميل أسعار اللعبة'
        }), 500

# 📦 إنشاء طلب جديد
@app.route('/order', methods=['POST'])
@limiter.limit("5 per minute")
def create_order():
    try:
        # تنظيف المدخلات
        game_type = sanitize_input(request.form.get('game_type'))
        platform = sanitize_input(request.form.get('platform'))
        account_type = sanitize_input(request.form.get('account_type'))
        customer_name = sanitize_input(request.form.get('customer_name'))
        customer_phone = sanitize_input(request.form.get('customer_phone'))
        customer_notes = sanitize_input(request.form.get('customer_notes', ''), 500)
        
        # التحقق من صحة البيانات
        if not all([game_type, platform, account_type, customer_name, customer_phone]):
            return jsonify({
                'success': False,
                'error': 'جميع البيانات مطلوبة'
            }), 400
        
        # التحقق من صحة رقم الهاتف
        phone_pattern = r'^\+?[0-9]{10,15}$'
        if not re.match(phone_pattern, customer_phone.replace(' ', '').replace('-', '')):
            return jsonify({
                'success': False,
                'error': 'رقم الهاتف غير صحيح'
            }), 400
        
        # حساب السعر
        prices_data = load_prices()
        game = next((g for g in prices_data['games'] if g['id'] == game_type), None)
        
        if not game or platform not in game['platforms'] or account_type not in game['platforms'][platform]:
            return jsonify({
                'success': False,
                'error': 'بيانات غير صحيحة'
            }), 400
        
        price = game['platforms'][platform][account_type]
        
        # إنشاء الطلب
        order = {
            'id': int(time.time() * 1000),  # ID فريد
            'game_type': game_type,
            'game_name': game['name'],
            'platform': platform,
            'account_type': account_type,
            'price': price,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'customer_notes': customer_notes,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', 
                                            request.environ.get('REMOTE_ADDR'))
        }
        
        # حفظ الطلب
        save_order(order)
        
        # تسجيل العملية
        logger.info(f"طلب جديد تم إنشاؤه - ID: {order['id']}, العميل: {customer_name}")
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء الطلب بنجاح! سيتم التواصل معك قريباً',
            'order_id': order['id'],
            'whatsapp_message': f"طلب جديد رقم: {order['id']}\nاللعبة: {game['name']}\nالمنصة: {platform}\nنوع الحساب: {account_type}\nالسعر: {price} جنيه\nالعميل: {customer_name}\nالهاتف: {customer_phone}"
        })
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء الطلب: {e}")
        return jsonify({
            'success': False,
            'error': 'حدث خطأ في النظام'
        }), 500

# 🚨 مصيدة أمنية للـ admin (بدون وجود admin حقيقي)
@app.route('/admin')
@app.route('/admin/<path:path>')
def admin_security_trap(path=None):
    """مصيدة أمنية للمتطفلين - لا يوجد admin حقيقي"""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                   request.environ.get('REMOTE_ADDR'))
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # تسجيل تفصيلي للمحاولة المشبوهة
    logger.warning(
        f"🚨 محاولة دخول مشبوهة للـ admin - "
        f"IP: {client_ip}, "
        f"Path: /admin{('/' + path) if path else ''}, "
        f"User-Agent: {user_agent[:100]}, "
        f"Time: {datetime.now()}"
    )
    
    # إعادة 404 طبيعية
    abort(404)

# ❌ معالجة الأخطاء 404
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# ❌ معالجة الأخطاء 500
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"خطأ داخلي في الخادم: {error}")
    return render_template('500.html'), 500

# ❌ معالجة أخطاء Rate Limiting
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'success': False,
        'error': 'تم تجاوز الحد المسموح من الطلبات'
    }), 429

# 🔄 تحديث الأسعار تلقائياً (من ملف JSON فقط)
def update_prices_from_file():
    """تحديث الأسعار من ملف JSON عند تشغيل التطبيق"""
    try:
        # فحص وجود ملف الأسعار
        if os.path.exists('data/prices.json'):
            with open('data/prices.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"تم تحميل الأسعار من الملف - آخر تحديث: {data.get('last_updated', 'غير محدد')}")
        else:
            # إنشاء ملف الأسعار الافتراضي
            os.makedirs('data', exist_ok=True)
            default_prices = get_default_prices()
            default_prices['last_updated'] = datetime.now().isoformat()
            
            with open('data/prices.json', 'w', encoding='utf-8') as f:
                json.dump(default_prices, f, ensure_ascii=False, indent=2)
            
            logger.info("تم إنشاء ملف أسعار افتراضي")
            
    except Exception as e:
        logger.error(f"خطأ في تحديث الأسعار: {e}")

if __name__ == '__main__':
    # تحديث الأسعار عند بدء التطبيق
    update_prices_from_file()
    
    # تشغيل التطبيق
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
