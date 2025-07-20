import os
import logging
import requests
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix
import threading
import time
from threading import Lock

# إعداد اللوجر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'senior_aaa_secret_key_2024'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# المتغيرات البيئية
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7607085569:AAFE_NO4pVcgfVenU5R_GSEnauoFIQ0iVXo')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'ea_fc_fifa_bot')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1124247595')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://senioraaa.onrender.com')

# التليجرام API URLs
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ملف حفظ الأسعار
PRICES_FILE = 'prices_data.json'

# قفل الحماية للملف - هذا هو الحل الأهم! 🔒
PRICES_LOCK = Lock()

# بيانات الأسعار المؤقتة
DEFAULT_PRICES = {
    "fc25": {
        "ps4": {
            "Primary": 85,
            "Secondary": 70,
            "Full": 120
        },
        "ps5": {
            "Primary": 90,
            "Secondary": 75,
            "Full": 125
        },
        "xbox": {
            "Primary": 85,
            "Secondary": 70,
            "Full": 120
        },
        "pc": {
            "Primary": 80,
            "Secondary": 65,
            "Full": 115
        }
    }
}

def load_prices():
    """تحميل الأسعار من الملف مع حماية من التداخل"""
    with PRICES_LOCK:  # 🔒 حماية مضمونة!
        try:
            if os.path.exists(PRICES_FILE):
                with open(PRICES_FILE, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    logger.info("✅ تم تحميل الأسعار من الملف بأمان")
                    return data
            else:
                logger.info("📝 إنشاء ملف أسعار جديد")
                save_prices_unsafe(DEFAULT_PRICES)  # استخدام النسخة الداخلية
                return DEFAULT_PRICES.copy()
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل الأسعار: {e}")
            return DEFAULT_PRICES.copy()

def save_prices_unsafe(prices_data):
    """حفظ الأسعار داخلياً بدون قفل إضافي"""
    try:
        with open(PRICES_FILE, 'w', encoding='utf-8') as file:
            json.dump(prices_data, file, ensure_ascii=False, indent=4)
        logger.info("✅ تم حفظ الأسعار في الملف بأمان")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الأسعار: {e}")
        return False

def save_prices(prices_data):
    """حفظ الأسعار في الملف مع حماية من التداخل"""
    with PRICES_LOCK:  # 🔒 حماية مضمونة!
        return save_prices_unsafe(prices_data)

# تحميل الأسعار عند بدء التشغيل
PRICES_DATA = load_prices()

def send_message(chat_id, text, reply_markup=None):
    """إرسال رسالة عبر التليجرام"""
    try:
        url = f"{TELEGRAM_API}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = reply_markup
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"خطأ في إرسال الرسالة: {e}")
        return None

def send_inline_keyboard(chat_id, text, keyboard):
    """إرسال رسالة مع كيبورد inline"""
    try:
        reply_markup = {
            'inline_keyboard': keyboard
        }
        return send_message(chat_id, text, reply_markup)
    except Exception as e:
        logger.error(f"خطأ في إرسال الكيبورد: {e}")
        return None

def update_price(platform, account_type, new_price):
    """تحديث السعر في قاعدة البيانات وحفظه - الحل النهائي! 🎯"""
    global PRICES_DATA
    
    with PRICES_LOCK:  # 🔒 حماية شاملة للتحديث كاملاً!
        try:
            # تحميل أحدث البيانات من الملف مباشرة
            current_data = load_prices_direct()
            
            if platform.lower() in current_data['fc25'] and account_type in current_data['fc25'][platform.lower()]:
                old_price = current_data['fc25'][platform.lower()][account_type]
                current_data['fc25'][platform.lower()][account_type] = int(new_price)
                
                # حفظ التحديث في الملف مباشرة
                if save_prices_unsafe(current_data):
                    # تحديث المتغير العام
                    PRICES_DATA = current_data.copy()
                    
                    logger.info(f"🎯 تم تحديث السعر نهائياً: {platform} {account_type} من {old_price} إلى {new_price}")
                    
                    # إشعار التحديث في التليجرام
                    notification_msg = f"""
🔥 تحديث سعر نجح 100%!

🎮 المنصة: {platform.upper()}
📝 النوع: {account_type}
💰 السعر القديم: {old_price} جنيه
💎 السعر الجديد: {new_price} جنيه

✅ تم الحفظ الدائم والآمن
🌐 الموقع محدث: {WEBHOOK_URL}
🔒 نظام الحماية نشط
                    """
                    
                    # إرسال إشعار للمدير
                    send_message(CHAT_ID, notification_msg)
                    
                    return True
                else:
                    logger.error("❌ فشل في حفظ الملف")
                    return False
            return False
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث السعر: {e}")
            return False

def load_prices_direct():
    """تحميل مباشر من الملف بدون قفل إضافي - للاستخدام الداخلي فقط"""
    try:
        if os.path.exists(PRICES_FILE):
            with open(PRICES_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        return DEFAULT_PRICES.copy()
    except:
        return DEFAULT_PRICES.copy()

def format_prices_message():
    """تنسيق رسالة الأسعار الحالية"""
    try:
        # تحميل أحدث الأسعار
        with PRICES_LOCK:
            current_prices = load_prices_direct()
        
        message = "💰 الأسعار الحالية لـ FC 25:\n\n"
        
        platforms = {
            'ps4': '🎮 PS4',
            'ps5': '🎮 PS5', 
            'xbox': '🎮 Xbox',
            'pc': '💻 PC'
        }
        
        for platform_key, platform_name in platforms.items():
            if platform_key in current_prices['fc25']:
                message += f"{platform_name}:\n"
                prices = current_prices['fc25'][platform_key]
                for account_type, price in prices.items():
                    message += f"• {account_type}: {price} جنيه\n"
                message += "\n"
        
        message += "💡 لتعديل السعر استخدم:\n/setprice [المنصة] [النوع] [السعر]\n\n"
        message += "مثال: /setprice ps4 Primary 90\n\n"
        message += f"🌐 الموقع: {WEBHOOK_URL}\n🔒 نظام الحماية نشط"
        
        return message
    except Exception as e:
        logger.error(f"خطأ في تنسيق رسالة الأسعار: {e}")
        return "خطأ في عرض الأسعار"

# باقي الكود يبقى كما هو...
# فقط نضيف هذه التحديثات في الدوال المهمة:

@app.route('/api/prices')
def api_prices():
    """API للأسعار - يعيد أحدث الأسعار بأمان"""
    global PRICES_DATA
    with PRICES_LOCK:
        PRICES_DATA = load_prices_direct()  # تأكد من أحدث البيانات
    return jsonify(PRICES_DATA)

@app.route('/')
def home():
    """الصفحة الرئيسية للمنصة"""
    try:
        # إعادة تحميل الأسعار لضمان التحديث بأمان
        global PRICES_DATA
        with PRICES_LOCK:
            PRICES_DATA = load_prices_direct()
        return render_template('index.html', prices=PRICES_DATA)
    except Exception as e:
        logger.error(f"خطأ في تحميل الصفحة الرئيسية: {e}")
        return jsonify({
            'status': 'active',
            'bot': BOT_USERNAME,
            'message': 'منصة شهد السنيورة - أرخص أسعار FC 25 في مصر! ✅'
        })

# باقي الكود كما هو...
