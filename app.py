import os
import logging
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix

# إعداد اللوجر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'senior_aaa_secret_key_2024'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# المتغيرات البيئية
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://senioraaa.onrender.com')

# ملف حفظ الأسعار
PRICES_FILE = 'prices_data.json'

# بيانات الأسعار - يتم التعديل من هنا فقط
DEFAULT_PRICES = {
    "fc25": {
        "ps4": {
            "Primary": 85,    # ← غير السعر هنا
            "Secondary": 70,  # ← غير السعر هنا
            "Full": 120       # ← غير السعر هنا
        },
        "ps5": {
            "Primary": 90,    # ← غير السعر هنا
            "Secondary": 75,  # ← غير السعر هنا
            "Full": 125       # ← غير السعر هنا
        },
        "xbox": {
            "Primary": 85,    # ← غير السعر هنا
            "Secondary": 70,  # ← غير السعر هنا
            "Full": 120       # ← غير السعر هنا
        },
        "pc": {
            "Primary": 80,    # ← غير السعر هنا
            "Secondary": 65,  # ← غير السعر هنا
            "Full": 115       # ← غير السعر هنا
        }
    }
}

def load_prices():
    """تحميل الأسعار من الملف أو إنشاء جديد"""
    try:
        if os.path.exists(PRICES_FILE):
            with open(PRICES_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info("✅ تم تحميل الأسعار من الملف")
                return data
        else:
            logger.info("📝 إنشاء ملف أسعار جديد")
            save_prices(DEFAULT_PRICES)
            return DEFAULT_PRICES.copy()
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الأسعار: {e}")
        # في حالة خطأ، استخدم الأسعار من الكود
        save_prices(DEFAULT_PRICES)
        return DEFAULT_PRICES.copy()

def save_prices(prices_data):
    """حفظ الأسعار في الملف"""
    try:
        with open(PRICES_FILE, 'w', encoding='utf-8') as file:
            json.dump(prices_data, file, ensure_ascii=False, indent=4)
        logger.info("✅ تم حفظ الأسعار في الملف")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الأسعار: {e}")
        return False

def update_prices_from_code():
    """تحديث الأسعار من الكود مباشرة"""
    global PRICES_DATA
    try:
        # تحديث الأسعار من الكود
        PRICES_DATA = DEFAULT_PRICES.copy()
        
        # حفظ في الملف
        if save_prices(PRICES_DATA):
            logger.info("🔄 تم تحديث الأسعار من الكود مباشرة")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الأسعار: {e}")
        return False

# تحميل الأسعار عند بدء التشغيل
PRICES_DATA = load_prices()

# Routes المنصة الرئيسية
@app.route('/')
def home():
    """الصفحة الرئيسية للمنصة"""
    try:
        # تحديث الأسعار من الكود دائماً
        update_prices_from_code()
        
        # إعادة تحميل لضمان التحديث
        global PRICES_DATA
        PRICES_DATA = load_prices()
        return render_template('index.html', prices=PRICES_DATA)
    except Exception as e:
        logger.error(f"خطأ في تحميل الصفحة الرئيسية: {e}")
        return jsonify({
            'status': 'active',
            'message': 'منصة شهد السنيورة - أرخص أسعار FC 25 في مصر! ✅'
        })

@app.route('/api/prices')
def api_prices():
    """API للأسعار - يعيد الأسعار المحدثة من الكود"""
    # تحديث من الكود أولاً
    update_prices_from_code()
    
    global PRICES_DATA
    PRICES_DATA = load_prices()
    return jsonify(PRICES_DATA)

@app.route('/order')
def order_page():
    """صفحة الطلب"""
    return redirect("https://wa.me/201094591331?text=مرحباً، أريد طلب FC 25")

@app.route('/faq')
def faq_page():
    """صفحة الأسئلة الشائعة"""
    return jsonify({
        'faq': [
            {'q': 'ما هو الفرق بين Primary و Secondary؟', 'a': 'Primary يتم تفعيله كحساب أساسي، Secondary للتحميل فقط'},
            {'q': 'كم مدة الضمان؟', 'a': 'سنة كاملة مع عدم مخالفة الشروط'},
            {'q': 'متى يتم التسليم؟', 'a': 'خلال 15 ساعة كحد أقصى'},
            {'q': 'هل يمكن تغيير بيانات الحساب؟', 'a': 'ممنوع نهائياً تغيير أي بيانات'},
            {'q': 'كيف يتم تحديث الأسعار؟', 'a': 'يتم التحديث من الكود مباشرة - آمن 100%'}
        ]
    })

@app.route('/status')  
def status_page():
    """صفحة حالة النظام"""
    return jsonify({
        'status': 'active',
        'system': 'Secure Code-Based Price Management',
        'admin_panel': 'disabled - for security',
        'prices_source': 'code only',
        'security_level': 'maximum',
        'website': WEBHOOK_URL,
        'message': 'نظام إدارة الأسعار الآمن نشط ✅'
    })

# إزالة route الإدارة نهائياً لأمان أقصى
# @app.route('/admin') - تم حذفها نهائياً
# @app.route('/api/update_price') - تم حذفها نهائياً

@app.errorhandler(404)
def page_not_found(e):
    """صفحة خطأ 404 مخصصة"""
    return jsonify({
        'error': '404 - الصفحة غير موجودة',
        'message': 'للعودة للرئيسية: ' + WEBHOOK_URL,
        'available_pages': [
            '/ - الصفحة الرئيسية',
            '/api/prices - عرض الأسعار',
            '/order - طلب FC25',
            '/faq - الأسئلة الشائعة',
            '/status - حالة النظام'
        ]
    }), 404

if __name__ == '__main__':
    logger.info("🚀 بدء تشغيل منصة شهد السنيورة - النظام الآمن")
    logger.info("🛡️ لوحة الإدارة معطلة للأمان")
    logger.info("🔧 تحديث الأسعار من الكود فقط")
    
    # تحديث الأسعار من الكود عند البداية
    update_prices_from_code()
    logger.info("✅ تم تحديث الأسعار من الكود")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
