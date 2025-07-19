from flask import Flask, render_template, request, jsonify
import os
import json
import requests
from datetime import datetime
import uuid
import logging

# إعداد نظام السجلات المحسن
def setup_logging():
    """إعداد نظام السجلات مع إنشاء المجلد المطلوب"""
    handlers = []
    
    try:
        # إنشاء مجلد logs إذا لم يكن موجوداً
        os.makedirs('logs', exist_ok=True)
        
        # إضافة FileHandler
        file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
        handlers.append(file_handler)
        
    except Exception as e:
        print(f"تعذر إنشاء ملف السجلات: {str(e)}")
    
    # إضافة StreamHandler (دائماً متاح)
    handlers.append(logging.StreamHandler())
    
    # إعداد التسجيل
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )

# استدعاء الدالة قبل إنشاء logger
setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__)

# إضافة secret key للـ sessions
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-it')

# إعدادات الموقع
SITE_NAME = "منصة شهد السنيورة"
WHATSAPP_NUMBER = "201094591331"
EMAIL_INFO = "info@senioraa.com"
MAINTENANCE_MODE = False
MAINTENANCE_MESSAGE = "الموقع تحت الصيانة"
DEBUG_MODE = False
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# إعدادات التليجرام - البيانات مباشرة
TELEGRAM_BOT_TOKEN = '7607085569:AAFE_NO4pVcgfVenU5R_GSEnauoFIQ0iVXo'
TELEGRAM_CHAT_ID = '1124247595'

# إعدادات الإشعارات
NOTIFICATION_SETTINGS = {
    'new_order': True,
    'price_update': True,
    'customer_message': True
}

# === دوال التحقق من صحة البيانات ===

def get_default_prices():
    """إرجاع بنية البيانات الافتراضية للأسعار"""
    return {
        'fc25': {
            'PS4': {
                'Primary': 50,
                'Secondary': 30,
                'Full': 80
            },
            'PS5': {
                'Primary': 60,
                'Secondary': 40,
                'Full': 100
            },
            'Xbox': {
                'Primary': 55,
                'Secondary': 35,
                'Full': 90
            },
            'PC': {
                'Primary': 45,
                'Secondary': 25,
                'Full': 70
            }
        }
    }

def validate_and_fix_prices(prices):
    """التحقق من صحة بنية البيانات وإصلاح أي مشاكل"""
    default_prices = get_default_prices()
    
    # التأكد من وجود البنية الأساسية
    if not isinstance(prices, dict):
        logger.warning("البيانات ليست من نوع dict، استخدام القيم الافتراضية")
        return default_prices
    
    # إصلاح البيانات المفقودة
    for game in default_prices:
        if game not in prices:
            prices[game] = default_prices[game]
            logger.info(f"إضافة لعبة مفقودة: {game}")
        
        if not isinstance(prices[game], dict):
            prices[game] = default_prices[game]
            logger.warning(f"إصلاح بنية البيانات للعبة: {game}")
        
        for platform in default_prices[game]:
            if platform not in prices[game]:
                prices[game][platform] = default_prices[game][platform]
                logger.info(f"إضافة منصة مفقودة: {platform} للعبة {game}")
            
            if not isinstance(prices[game][platform], dict):
                prices[game][platform] = default_prices[game][platform]
                logger.warning(f"إصلاح بنية البيانات للمنصة: {platform} في {game}")
            
            for price_type in default_prices[game][platform]:
                if price_type not in prices[game][platform]:
                    prices[game][platform][price_type] = default_prices[game][platform][price_type]
                    logger.info(f"إضافة نوع سعر مفقود: {price_type} لـ {platform} في {game}")
                
                # التأكد من أن السعر رقم صحيح
                try:
                    prices[game][platform][price_type] = int(prices[game][platform][price_type])
                except (ValueError, TypeError):
                    prices[game][platform][price_type] = default_prices[game][platform][price_type]
                    logger.warning(f"إصلاح سعر غير صحيح: {price_type} لـ {platform} في {game}")
    
    return prices

def validate_order_data(order_data):
    """التحقق من صحة بيانات الطلب"""
    required_fields = ['game', 'platform', 'account_type', 'price', 'payment_method', 'customer_phone']
    
    for field in required_fields:
        if not order_data.get(field):
            logger.error(f"حقل مطلوب مفقود: {field}")
            return False, f"الحقل {field} مطلوب"
    
    # التحقق من صحة السعر
    try:
        price = int(order_data['price'])
        if price <= 0:
            return False, "السعر يجب أن يكون أكبر من صفر"
    except (ValueError, TypeError):
        return False, "السعر يجب أن يكون رقماً صحيحاً"
    
    # التحقق من صحة رقم الواتساب
    phone = order_data['customer_phone']
    import re
    phone_pattern = r'^01[0-2][0-9]{8}$'
    if not re.match(phone_pattern, phone):
        return False, "رقم الواتساب يجب أن يكون 11 رقم ويبدأ بـ 01"
    
    return True, "البيانات صحيحة"

# === الدوال الأساسية المحسنة ===

def load_prices():
    """تحميل الأسعار من ملف JSON مع التحقق من صحتها"""
    try:
        if os.path.exists('data/prices.json'):
            with open('data/prices.json', 'r', encoding='utf-8') as f:
                prices = json.load(f)
            
            # التحقق من صحة البيانات وإصلاحها
            prices = validate_and_fix_prices(prices)
            logger.info("تم تحميل الأسعار بنجاح")
            return prices
        else:
            logger.info("ملف الأسعار غير موجود، استخدام القيم الافتراضية")
            default_prices = get_default_prices()
            save_prices(default_prices)
            return default_prices
            
    except json.JSONDecodeError as e:
        logger.error(f"خطأ في تحليل ملف JSON: {str(e)}")
        default_prices = get_default_prices()
        save_prices(default_prices)
        return default_prices
    except Exception as e:
        logger.error(f"خطأ في تحميل الأسعار: {str(e)}")
        return get_default_prices()

def save_prices(prices):
    """حفظ الأسعار في ملف JSON مع التحقق من صحتها"""
    try:
        # التحقق من صحة البيانات قبل الحفظ
        validated_prices = validate_and_fix_prices(prices)
        
        os.makedirs('data', exist_ok=True)
        
        # إنشاء نسخة احتياطية قبل الحفظ
        if os.path.exists('data/prices.json'):
            backup_filename = f"backups/prices_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs('backups', exist_ok=True)
            with open('data/prices.json', 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write(backup_data)
            logger.info(f"تم إنشاء نسخة احتياطية: {backup_filename}")
        
        with open('data/prices.json', 'w', encoding='utf-8') as f:
            json.dump(validated_prices, f, ensure_ascii=False, indent=2)
        
        logger.info("تم حفظ الأسعار بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ في حفظ الأسعار: {str(e)}")
        raise

def load_orders():
    """تحميل الطلبات من ملف JSON"""
    try:
        if os.path.exists('data/orders.json'):
            with open('data/orders.json', 'r', encoding='utf-8') as f:
                orders = json.load(f)
            
            if not isinstance(orders, list):
                logger.warning("بيانات الطلبات ليست قائمة، استخدام قائمة فارغة")
                return []
            
            logger.info(f"تم تحميل {len(orders)} طلب بنجاح")
            return orders
        else:
            logger.info("ملف الطلبات غير موجود، إنشاء قائمة فارغة")
            return []
            
    except json.JSONDecodeError as e:
        logger.error(f"خطأ في تحليل ملف طلبات JSON: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"خطأ في تحميل الطلبات: {str(e)}")
        return []

def save_orders(orders):
    """حفظ الطلبات في ملف JSON"""
    try:
        if not isinstance(orders, list):
            logger.error("البيانات المراد حفظها ليست قائمة")
            raise ValueError("البيانات يجب أن تكون قائمة")
        
        os.makedirs('data', exist_ok=True)
        
        # إنشاء نسخة احتياطية قبل الحفظ
        if os.path.exists('data/orders.json'):
            backup_filename = f"backups/orders_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs('backups', exist_ok=True)
            with open('data/orders.json', 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write(backup_data)
            logger.info(f"تم إنشاء نسخة احتياطية للطلبات: {backup_filename}")
        
        with open('data/orders.json', 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        
        logger.info(f"تم حفظ {len(orders)} طلب بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ في حفظ الطلبات: {str(e)}")
        raise

def generate_order_id():
    """توليد رقم طلب فريد"""
    return f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

def get_cairo_time():
    """الحصول على التوقيت المصري بالتنسيق المطلوب"""
    try:
        from datetime import datetime
        import pytz
        
        # تحديد المنطقة الزمنية للقاهرة
        cairo_tz = pytz.timezone('Africa/Cairo')
        
        # الحصول على الوقت الحالي في القاهرة
        cairo_time = datetime.now(cairo_tz)
        
        # أسماء الأيام بالعربية
        arabic_days = {
            'Monday': 'الإثنين',
            'Tuesday': 'الثلاثاء', 
            'Wednesday': 'الأربعاء',
            'Thursday': 'الخميس',
            'Friday': 'الجمعة',
            'Saturday': 'السبت',
            'Sunday': 'الأحد'
        }
        
        # تنسيق التاريخ: اليوم ( الشهر/اليوم ) الساعة
        day_name = arabic_days.get(cairo_time.strftime('%A'), cairo_time.strftime('%A'))
        date_part = cairo_time.strftime('%m/%d')
        time_part = cairo_time.strftime('%I:%M %p')
        
        return f"{day_name} ( {date_part} ) {time_part}"
    except Exception as e:
        logger.error(f"خطأ في الحصول على التوقيت المصري: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def send_telegram_message(message):
    """إرسال رسالة للتليجرام"""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("إعدادات التليجرام غير مكتملة")
            return {"status": "error", "message": "إعدادات التليجرام غير مكتملة"}
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            logger.info("تم إرسال رسالة التليجرام بنجاح")
            return {"status": "success", "message": "تم إرسال الرسالة بنجاح"}
        else:
            logger.error(f"خطأ في إرسال رسالة التليجرام: {response.status_code}")
            return {"status": "error", "message": f"خطأ في إرسال الرسالة: {response.status_code}"}
            
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة التليجرام: {str(e)}")
        return {"status": "error", "message": str(e)}

def send_order_notification(order_data):
    """إرسال إشعار طلب جديد"""
    try:
        formatted_date = get_cairo_time()
        
        # ترجمة طرق الدفع
        payment_methods_ar = {
            'vodafone_cash': 'فودافون كاش',
            'etisalat_cash': 'اتصالات كاش',
            'we_cash': 'وي كاش',
            'orange_cash': 'أورانج كاش',
            'bank_wallet': 'محفظة بنكية',
            'instapay': 'إنستا باي'
        }
        
        payment_method_ar = payment_methods_ar.get(order_data['payment_method'], order_data['payment_method'])
        
        message = f"""
🚨 طلب جديد!

🆔 رقم الطلب: {order_data['order_id']}
🎮 اللعبة: {order_data['game']}
📱 المنصة: {order_data['platform']}
💎 نوع الحساب: {order_data['account_type']}
💰 السعر: {order_data['price']} جنيه
💳 طريقة الدفع: {payment_method_ar}
📞 رقم العميل: {order_data['customer_phone']}
💸 رقم الدفع: {order_data['payment_number']}
📅 {formatted_date}
"""
        return send_telegram_message(message)
        
    except Exception as e:
        logger.error(f"خطأ في إرسال إشعار الطلب: {str(e)}")
        return {"status": "error", "message": str(e)}

# === Routes الأساسية ===

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    if MAINTENANCE_MODE:
        return render_template('maintenance.html', message=MAINTENANCE_MESSAGE)
    
    try:
        prices = load_prices()
        logger.info("تم تحميل الصفحة الرئيسية بنجاح")
        return render_template('index.html', 
                             prices=prices, 
                             site_name=SITE_NAME,
                             whatsapp_number=WHATSAPP_NUMBER,
                             error=None)
    except Exception as e:
        logger.error(f"خطأ في تحميل الصفحة الرئيسية: {str(e)}")
        return render_template('index.html', 
                             prices=get_default_prices(), 
                             site_name=SITE_NAME,
                             whatsapp_number=WHATSAPP_NUMBER,
                             error="حدث خطأ في تحميل الأسعار")

@app.route('/faq')
def faq():
    """صفحة الأسئلة الشائعة"""
    return render_template('faq.html', site_name=SITE_NAME)

@app.route('/terms')
def terms():
    """صفحة الشروط والأحكام"""
    return render_template('terms.html', site_name=SITE_NAME)

@app.route('/contact')
def contact():
    """صفحة التواصل"""
    return render_template('contact.html', 
                         site_name=SITE_NAME,
                         whatsapp_number=WHATSAPP_NUMBER,
                         email_info=EMAIL_INFO)

# === حلول الـ Webhook الجديدة ===

@app.route('/setup_webhook')
def setup_webhook():
    """تسجيل الـ webhook من المتصفح - محسن للموبايل"""
    try:
        webhook_url = 'https://senioraaa.onrender.com/telegram_webhook'
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        
        data = {
            "url": webhook_url,
            "allowed_updates": ["message"]
        }
        
        response = requests.post(telegram_url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return f"""
                <!DOCTYPE html>
                <html dir="rtl" lang="ar">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>✅ نجح التسجيل - {SITE_NAME}</title>
                    <style>
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            margin: 0;
                            padding: 20px;
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        }}
                        .container {{
                            background: white;
                            padding: 30px;
                            border-radius: 20px;
                            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                            max-width: 500px;
                            width: 100%;
                            text-align: center;
                        }}
                        .success-icon {{
                            font-size: 4rem;
                            color: #4CAF50;
                            margin-bottom: 20px;
                        }}
                        h1 {{
                            color: #4CAF50;
                            margin-bottom: 20px;
                            font-size: 1.8rem;
                        }}
                        .info-box {{
                            background: #e8f5e8;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 20px 0;
                            border-right: 4px solid #4CAF50;
                        }}
                        .command {{
                            background: #f0f0f0;
                            padding: 10px;
                            border-radius: 5px;
                            font-family: monospace;
                            margin: 10px 0;
                            font-size: 0.9rem;
                        }}
                        .btn {{
                            display: inline-block;
                            padding: 12px 25px;
                            background: #4CAF50;
                            color: white;
                            text-decoration: none;
                            border-radius: 8px;
                            margin: 10px;
                            font-weight: bold;
                            transition: all 0.3s;
                        }}
                        .btn:hover {{
                            background: #45a049;
                            transform: translateY(-2px);
                        }}
                        .btn-secondary {{
                            background: #2196F3;
                        }}
                        .btn-secondary:hover {{
                            background: #1976D2;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="success-icon">✅</div>
                        <h1>تم تسجيل الـ Webhook بنجاح!</h1>
                        <p><strong>🌐 URL:</strong><br>{webhook_url}</p>
                        <p style="color: #4CAF50; font-size: 1.1rem;">🤖 البوت جاهز للاستخدام الآن</p>
                        
                        <div class="info-box">
                            <h3>اختبر الأوامر التالية في تليجرام:</h3>
                            <div class="command">/prices</div>
                            <small>عرض جميع الأسعار الحالية</small>
                            
                            <div class="command">/price PS5 Primary 150</div>
                            <small>تحديث سعر معين</small>
                            
                            <div class="command">/price PC Secondary 80</div>
                            <small>مثال آخر لتحديث الأسعار</small>
                        </div>
                        
                        <div>
                            <a href="/check_webhook" class="btn">📊 فحص حالة الـ Webhook</a>
                            <a href="/test_bot" class="btn btn-secondary">🧪 اختبار البوت</a>
                        </div>
                        
                        <p style="margin-top: 20px; color: #666; font-size: 0.9rem;">
                            يمكنك الآن إغلاق هذه الصفحة والبدء في استخدام البوت
                        </p>
                    </div>
                </body>
                </html>
                """
            else:
                error_desc = result.get('description', 'خطأ غير معروف')
                return f"""
                <!DOCTYPE html>
                <html dir="rtl" lang="ar">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>❌ خطأ - {SITE_NAME}</title>
                    <style>
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                            margin: 0;
                            padding: 20px;
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        }}
                        .container {{
                            background: white;
                            padding: 30px;
                            border-radius: 20px;
                            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                            max-width: 500px;
                            width: 100%;
                            text-align: center;
                        }}
                        .error-icon {{
                            font-size: 4rem;
                            color: #f44336;
                            margin-bottom: 20px;
                        }}
                        h1 {{
                            color: #f44336;
                            margin-bottom: 20px;
                        }}
                        .btn {{
                            display: inline-block;
                            padding: 12px 25px;
                            background: #f44336;
                            color: white;
                            text-decoration: none;
                            border-radius: 8px;
                            margin: 10px;
                            font-weight: bold;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="error-icon">❌</div>
                        <h1>خطأ في التسجيل</h1>
                        <p><strong>السبب:</strong> {error_desc}</p>
                        <a href="/setup_webhook" class="btn">🔄 إعادة المحاولة</a>
                    </div>
                </body>
                </html>
                """
        else:
            return f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>❌ خطأ اتصال - {SITE_NAME}</title>
            </head>
            <body>
                <div style="text-align: center; padding: 50px; font-family: Arial;">
                    <h1 style="color: #f44336;">❌ خطأ HTTP: {response.status_code}</h1>
                    <a href="/setup_webhook" style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔄 إعادة المحاولة</a>
                </div>
            </body>
            </html>
            """
            
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>❌ خطأ - {SITE_NAME}</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h1 style="color: #f44336;">❌ خطأ في الاتصال</h1>
                <p>{str(e)}</p>
                <a href="/setup_webhook" style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔄 إعادة المحاولة</a>
            </div>
        </body>
        </html>
        """

@app.route('/check_webhook')
def check_webhook():
    """فحص حالة الـ webhook - محسن للموبايل"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                webhook_info = result.get('result', {})
                webhook_url = webhook_info.get('url', 'غير محدد')
                pending_count = webhook_info.get('pending_update_count', 0)
                last_error_date = webhook_info.get('last_error_date', 'لا يوجد أخطاء')
                last_error_message = webhook_info.get('last_error_message', '')
                
                status_color = "#4CAF50" if webhook_url != 'غير محدد' else "#f44336"
                status_text = "🟢 متصل" if webhook_url != 'غير محدد' else "🔴 غير متصل"
                
                return f"""
                <!DOCTYPE html>
                <html dir="rtl" lang="ar">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>📊 حالة Webhook - {SITE_NAME}</title>
                    <style>
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            margin: 0;
                            padding: 20px;
                            min-height: 100vh;
                        }}
                        .container {{
                            background: white;
                            padding: 30px;
                            border-radius: 20px;
                            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                            max-width: 600px;
                            margin: 0 auto;
                        }}
                        .status-header {{
                            text-align: center;
                            color: {status_color};
                            margin-bottom: 30px;
                        }}
                        .info-grid {{
                            background: #f8f9fa;
                            padding: 20px;
                            border-radius: 10px;
                            margin: 20px 0;
                        }}
                        .info-item {{
                            display: flex;
                            justify-content: space-between;
                            padding: 10px 0;
                            border-bottom: 1px solid #e9ecef;
                        }}
                        .info-item:last-child {{
                            border-bottom: none;
                        }}
                        .btn {{
                            display: inline-block;
                            padding: 12px 20px;
                            color: white;
                            text-decoration: none;
                            border-radius: 8px;
                            margin: 5px;
                            font-weight: bold;
                            text-align: center;
                        }}
                        .btn-success {{ background: #4CAF50; }}
                        .btn-primary {{ background: #2196F3; }}
                        .btn-warning {{ background: #ff9800; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="status-header">
                            <h1>📊 معلومات الـ Webhook</h1>
                            <h2>{status_text}</h2>
                        </div>
                        
                        <div class="info-grid">
                            <div class="info-item">
                                <strong>🔗 URL:</strong>
                                <span style="word-break: break-all;">{webhook_url}</span>
                            </div>
                            <div class="info-item">
                                <strong>📈 الطلبات المعلقة:</strong>
                                <span>{pending_count}</span>
                            </div>
                            <div class="info-item">
                                <strong>⏰ آخر خطأ:</strong>
                                <span>{last_error_date}</span>
                            </div>
                            {f'<div class="info-item"><strong>❌ رسالة الخطأ:</strong><span>{last_error_message}</span></div>' if last_error_message else ''}
                        </div>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="/setup_webhook" class="btn btn-success">🔧 إعادة تسجيل Webhook</a>
                            <a href="/test_bot" class="btn btn-primary">🧪 اختبار البوت</a>
                            <a href="/check_webhook" class="btn btn-warning">🔄 تحديث المعلومات</a>
                        </div>
                    </div>
                </body>
                </html>
                """
        
        return """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>❌ خطأ - """ + SITE_NAME + """</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h1 style="color: #f44336;">❌ خطأ في الاتصال</h1>
                <a href="/check_webhook" style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔄 إعادة المحاولة</a>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>❌ خطأ - {SITE_NAME}</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h1 style="color: #f44336;">❌ خطأ:</h1>
                <p>{str(e)}</p>
                <a href="/check_webhook" style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔄 إعادة المحاولة</a>
            </div>
        </body>
        </html>
        """

@app.route('/test_bot')
def test_bot():
    """اختبار البوت بإرسال رسالة تجريبية"""
    try:
        test_message = "🧪 رسالة اختبار من الموقع\n⏰ " + get_cairo_time()
        result = send_telegram_message(test_message)
        
        if result['status'] == 'success':
            return f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>✅ نجح الاختبار - {SITE_NAME}</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                        margin: 0;
                        padding: 20px;
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 20px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                        max-width: 500px;
                        width: 100%;
                        text-align: center;
                    }}
                    .success-icon {{
                        font-size: 5rem;
                        color: #4CAF50;
                        margin-bottom: 20px;
                    }}
                    .btn {{
                        display: inline-block;
                        padding: 15px 30px;
                        background: #4CAF50;
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        margin: 10px;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✅</div>
                    <h1 style="color: #4CAF50;">تم إرسال رسالة اختبار بنجاح!</h1>
                    <p style="font-size: 1.1rem;">تحقق من تليجرام لرؤية الرسالة</p>
                    <p style="color: #666;">🤖 البوت يعمل بشكل صحيح الآن</p>
                    <a href="/check_webhook" class="btn">📊 فحص Webhook</a>
                </div>
            </body>
            </html>
            """
        else:
            return f"""
            <!DOCTYPE html>
            <html dir="rtl" lang="ar">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>❌ فشل الاختبار - {SITE_NAME}</title>
                <style>
                    body {{
                        font-family: Arial;
                        background: #f44336;
                        margin: 0;
                        padding: 20px;
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    .container {{
                        background: white;
                        padding: 40px;
                        border-radius: 20px;
                        max-width: 500px;
                        width: 100%;
                        text-align: center;
                    }}
                    .btn {{
                        display: inline-block;
                        padding: 15px 30px;
                        background: #f44336;
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        margin: 10px;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 style="color: #f44336;">❌ فشل في إرسال الرسالة</h1>
                    <p><strong>السبب:</strong> {result['message']}</p>
                    <a href="/setup_webhook" class="btn">🔧 إعادة تسجيل Webhook</a>
                </div>
            </body>
            </html>
            """
            
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>❌ خطأ - {SITE_NAME}</title>
        </head>
        <body>
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h1 style="color: #f44336;">❌ خطأ:</h1>
                <p>{str(e)}</p>
                <a href="/test_bot" style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔄 إعادة المحاولة</a>
            </div>
        </body>
        </html>
        """

# === API Routes ===

@app.route('/api/get_prices')
def get_prices():
    """API للحصول على الأسعار"""
    try:
        prices = load_prices()
        return jsonify(prices)
    except Exception as e:
        logger.error(f"خطأ في API الأسعار: {str(e)}")
        return jsonify(get_default_prices())

@app.route('/api/submit_order', methods=['POST'])
def submit_order():
    """API لإرسال طلب جديد"""
    try:
        order_data = request.get_json()
        
        # التحقق من صحة البيانات
        is_valid, error_message = validate_order_data(order_data)
        if not is_valid:
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400
        
        # إضافة معلومات إضافية للطلب
        order_data['order_id'] = generate_order_id()
        order_data['timestamp'] = get_cairo_time()
        order_data['status'] = 'pending'
        
        # حفظ الطلب
        orders = load_orders()
        orders.append(order_data)
        save_orders(orders)
        
        # إرسال إشعار
        if NOTIFICATION_SETTINGS['new_order']:
            send_order_notification(order_data)
        
        logger.info(f"تم استلام طلب جديد: {order_data['order_id']}")
        
        return jsonify({
            "status": "success",
            "message": "تم إرسال طلبك بنجاح!",
            "order_id": order_data['order_id']
        })
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الطلب: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "حدث خطأ في معالجة طلبك"
        }), 500

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    """معالج webhook للتليجرام لتحديث الأسعار"""
    try:
        # إضافة logging مُحسن للـ debugging
        logger.info("🤖 تم استقبال webhook request من التليجرام")
        
        data = request.get_json()
        logger.info(f"📥 البيانات المستقبلة: {data}")
        
        if 'message' in data and 'text' in data['message']:
            text = data['message']['text']
            chat_id = data['message']['chat']['id']
            
            logger.info(f"💬 الرسالة: {text}")
            logger.info(f"👤 Chat ID: {chat_id}")
            logger.info(f"🔐 Expected Chat ID: {TELEGRAM_CHAT_ID}")
            
            # التحقق من أن المرسل هو الأدمن
            if str(chat_id) != TELEGRAM_CHAT_ID:
                logger.warning(f"⚠️ رسالة من chat ID غير مصرح: {chat_id}")
                return jsonify({"status": "unauthorized"})
            
            # تحديث الأسعار عبر أمر: /price PS5 Primary 100
            if text.startswith('/price'):
                logger.info("💰 معالجة أمر تحديث الأسعار")
                parts = text.split()
                if len(parts) == 4:
                    _, platform, account_type, price = parts
                    
                    logger.info(f"🎮 تحديث: {platform} {account_type} = {price}")
                    
                    prices = load_prices()
                    old_price = prices.get('fc25', {}).get(platform, {}).get(account_type, 0)
                    
                    if 'fc25' not in prices:
                        prices['fc25'] = {}
                    if platform not in prices['fc25']:
                        prices['fc25'][platform] = {}
                    
                    prices['fc25'][platform][account_type] = int(price)
                    save_prices(prices)
                    
                    # إرسال رسالة تأكيد
                    confirm_msg = f"✅ تم تحديث سعر {platform} {account_type} من {old_price} إلى {price} جنيه"
                    send_telegram_message(confirm_msg)
                    
                    logger.info("✅ تم تحديث السعر بنجاح")
                    
                else:
                    # إرسال رسالة مساعدة
                    help_msg = """
❌ تنسيق الأمر غير صحيح

✅ استخدم التنسيق التالي:
/price PS5 Primary 100

📱 المنصات المتاحة: PS4, PS5, Xbox, PC
💎 أنواع الحسابات: Primary, Secondary, Full
                    """
                    send_telegram_message(help_msg)
            
            # عرض الأسعار الحالية
            elif text.startswith('/prices'):
                logger.info("📊 عرض الأسعار الحالية")
                prices = load_prices()
                prices_msg = "💰 الأسعار الحالية:\n\n"
                
                for game, platforms in prices.items():
                    prices_msg += f"🎮 {game.upper()}:\n"
                    for platform, types in platforms.items():
                        prices_msg += f"📱 {platform}:\n"
                        for price_type, price in types.items():
                            prices_msg += f"   💎 {price_type}: {price} جنيه\n"
                        prices_msg += "\n"
                
                send_telegram_message(prices_msg)
                logger.info("✅ تم إرسال الأسعار")
            
            # رسالة ترحيب
            elif text.startswith('/start'):
                welcome_msg = f"""
🎮 مرحباً بك في بوت {SITE_NAME}

🤖 الأوامر المتاحة:
• /prices - عرض جميع الأسعار
• /price PS5 Primary 100 - تحديث سعر معين

📱 المنصات: PS4, PS5, Xbox, PC
💎 الأنواع: Primary, Secondary, Full

⏰ {get_cairo_time()}
                """
                send_telegram_message(welcome_msg)
        
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"❌ خطأ في webhook التليجرام: {str(e)}")
        return jsonify({"status": "error"})

# === معالج الأخطاء ===

@app.errorhandler(404)
def not_found(error):
    """صفحة الخطأ 404"""
    return render_template('404.html', site_name=SITE_NAME), 404

@app.errorhandler(500)
def internal_error(error):
    """صفحة الخطأ 500"""
    logger.error(f"خطأ داخلي في الخادم: {str(error)}")
    return render_template('500.html', site_name=SITE_NAME), 500

# === تشغيل التطبيق ===

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 {SITE_NAME} يعمل الآن على البورت {port}!")
    logger.info(f"🌐 الوضع: {'تطوير' if DEBUG_MODE else 'إنتاج'}")
    logger.info(f"🤖 البوت Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    logger.info(f"👤 Chat ID: {TELEGRAM_CHAT_ID}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG_MODE
    )
