import os
import logging
import requests
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix
import threading
import time
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from telegram.ext import CallbackQueryHandler

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

# بيانات الأسعار المؤقتة (يمكن نقلها لقاعدة بيانات لاحقاً)
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
    """تحميل الأسعار من الملف"""
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
    """تحديث السعر في قاعدة البيانات وحفظه"""
    global PRICES_DATA
    try:
        if platform.lower() in PRICES_DATA['fc25'] and account_type in PRICES_DATA['fc25'][platform.lower()]:
            old_price = PRICES_DATA['fc25'][platform.lower()][account_type]
            PRICES_DATA['fc25'][platform.lower()][account_type] = int(new_price)
            
            # حفظ التحديث في الملف
            if save_prices(PRICES_DATA):
                logger.info(f"✅ تم تحديث السعر: {platform} {account_type} من {old_price} إلى {new_price}")
                
                # إشعار التحديث في التليجرام
                notification_msg = f"""
🔄 تحديث سعر تلقائي!

🎮 المنصة: {platform.upper()}
📝 النوع: {account_type}
💰 السعر القديم: {old_price} جنيه
💎 السعر الجديد: {new_price} جنيه

✅ تم تحديث الموقع تلقائياً
🌐 {WEBHOOK_URL}
                """
                
                # إرسال إشعار للمدير
                send_message(CHAT_ID, notification_msg)
                
                return True
        return False
    except Exception as e:
        logger.error(f"خطأ في تحديث السعر: {e}")
        return False

def format_prices_message():
    """تنسيق رسالة الأسعار الحالية"""
    try:
        message = "💰 الأسعار الحالية لـ FC 25:\n\n"
        
        platforms = {
            'ps4': '🎮 PS4',
            'ps5': '🎮 PS5', 
            'xbox': '🎮 Xbox',
            'pc': '💻 PC'
        }
        
        for platform_key, platform_name in platforms.items():
            if platform_key in PRICES_DATA['fc25']:
                message += f"{platform_name}:\n"
                prices = PRICES_DATA['fc25'][platform_key]
                for account_type, price in prices.items():
                    message += f"• {account_type}: {price} جنيه\n"
                message += "\n"
        
        message += "💡 لتعديل السعر استخدم:\n/setprice [المنصة] [النوع] [السعر]\n\n"
        message += "مثال: /setprice ps4 Primary 90\n\n"
        message += f"🌐 الموقع: {WEBHOOK_URL}"
        
        return message
    except Exception as e:
        logger.error(f"خطأ في تنسيق رسالة الأسعار: {e}")
        return "خطأ في عرض الأسعار"

def set_webhook():
    """تعيين الويبهوك"""
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook/{BOT_TOKEN}"
        url = f"{TELEGRAM_API}/setWebhook"
        data = {
            'url': webhook_url,
            'allowed_updates': ['message', 'callback_query'],
            'drop_pending_updates': True
        }
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"✅ تم تعيين الويبهوك بنجاح: {webhook_url}")
            return True
        else:
            logger.error(f"❌ فشل في تعيين الويبهوك: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في تعيين الويبهوك: {e}")
        return False

def delete_webhook():
    """حذف الويبهوك"""
    try:
        url = f"{TELEGRAM_API}/deleteWebhook"
        data = {'drop_pending_updates': True}
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get('ok'):
            logger.info("✅ تم حذف الويبهوك بنجاح")
            return True
        else:
            logger.error(f"❌ فشل في حذف الويبهوك: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في حذف الويبهوك: {e}")
        return False

def get_webhook_info():
    """الحصول على معلومات الويبهوك"""
    try:
        url = f"{TELEGRAM_API}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على معلومات الويبهوك: {e}")
        return None

def process_message(message):
    """معالجة الرسائل الواردة"""
    try:
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user_id = message.get('from', {}).get('id')
        
        # التأكد من صلاحية المدير
        is_admin = str(user_id) == CHAT_ID
        
        # رد تلقائي
        if text.lower() == '/start':
            welcome_text = f"""
🎮 مرحباً بك في منصة شهد السنيورة!

🏆 أرخص أسعار FC 25 في مصر
💎 جميع المنصات متوفرة
⚡ تسليم سريع خلال 15 ساعة
🛡️ ضمان سنة كاملة

🌐 زيارة المنصة: {WEBHOOK_URL}
📱 للطلب: /order
💬 المساعدة: /help
            """
            send_message(chat_id, welcome_text)
        
        elif text.lower() == '/help':
            if is_admin:
                help_text = f"""
📋 الأوامر المتاحة للمدير:

👥 أوامر عامة:
/start - بداية التفاعل
/help - هذه المساعدة
/order - طلب FC 25
/prices - عرض الأسعار الحالية
/status - حالة البوت
/support - الدعم الفني

👨‍💻 أوامر الإدارة:
/admin - لوحة الإدارة
/setprice - تعديل الأسعار
/editprices - تعديل الأسعار بالأزرار
/reloadprices - إعادة تحميل الأسعار

💡 تعديل الأسعار:
/setprice [المنصة] [النوع] [السعر]
مثال: /setprice ps4 Primary 90

المنصات المتاحة: ps4, ps5, xbox, pc
الأنواع المتاحة: Primary, Secondary, Full

🌐 الموقع الكامل: {WEBHOOK_URL}
                """
            else:
                help_text = f"""
📋 الأوامر المتاحة:

/start - بداية التفاعل
/order - طلب FC 25
/prices - عرض الأسعار
/status - حالة البوت
/support - الدعم الفني

🌐 الموقع الكامل: {WEBHOOK_URL}
                """
            send_message(chat_id, help_text)
        
        elif text.lower() == '/prices':
            prices_message = format_prices_message()
            send_message(chat_id, prices_message)
        
        elif text.lower() == '/reloadprices':
            if not is_admin:
                send_message(chat_id, "❌ هذا الأمر مخصص للمدير فقط")
                return True
            
            global PRICES_DATA
            PRICES_DATA = load_prices()
            send_message(chat_id, "🔄 تم إعادة تحميل الأسعار من الملف بنجاح!")
        
        elif text.lower().startswith('/setprice'):
            if not is_admin:
                send_message(chat_id, "❌ هذا الأمر مخصص للمدير فقط")
                return True
            
            # تحليل الأمر
            parts = text.split()
            if len(parts) != 4:
                send_message(chat_id, f"""
❌ صيغة الأمر غير صحيحة!

الصيغة الصحيحة:
/setprice [المنصة] [النوع] [السعر]

أمثلة:
/setprice ps4 Primary 90
/setprice ps5 Secondary 80
/setprice xbox Full 130

المنصات: ps4, ps5, xbox, pc
الأنواع: Primary, Secondary, Full

🌐 الموقع: {WEBHOOK_URL}
                """)
                return True
            
            _, platform, account_type, price_str = parts
            
            # التحقق من صحة البيانات
            valid_platforms = ['ps4', 'ps5', 'xbox', 'pc']
            valid_account_types = ['Primary', 'Secondary', 'Full']
            
            if platform.lower() not in valid_platforms:
                send_message(chat_id, f"❌ المنصة غير صحيحة. المنصات المتاحة: {', '.join(valid_platforms)}")
                return True
            
            if account_type not in valid_account_types:
                send_message(chat_id, f"❌ نوع الحساب غير صحيح. الأنواع المتاحة: {', '.join(valid_account_types)}")
                return True
            
            try:
                new_price = int(price_str)
                if new_price <= 0:
                    send_message(chat_id, "❌ السعر يجب أن يكون رقم موجب")
                    return True
            except ValueError:
                send_message(chat_id, "❌ السعر يجب أن يكون رقم صحيح")
                return True
            
            # تحديث السعر
            if update_price(platform.lower(), account_type, new_price):
                success_msg = f"""
✅ تم تحديث السعر بنجاح!

🎮 المنصة: {platform.upper()}
📝 النوع: {account_type}
💰 السعر الجديد: {new_price} جنيه

🔄 تم تحديث الموقع والملف تلقائياً
🌐 {WEBHOOK_URL}

💡 تأكد من التحديث: /prices
                """
                send_message(chat_id, success_msg)
                
                # إرسال الأسعار المحدثة للتأكيد
                updated_prices = format_prices_message()
                send_message(chat_id, f"📊 الأسعار بعد التحديث:\n\n{updated_prices}")
                
            else:
                send_message(chat_id, "❌ حدث خطأ أثناء تحديث السعر")
        
        elif text.lower() == '/editprices':
            if not is_admin:
                send_message(chat_id, "❌ هذا الأمر مخصص للمدير فقط")
                return True
            
            # إرسال كيبورد تعديل الأسعار
            keyboard = [
                [{"text": "🎮 PS4", "callback_data": "edit_ps4"}],
                [{"text": "🎮 PS5", "callback_data": "edit_ps5"}],
                [{"text": "🎮 Xbox", "callback_data": "edit_xbox"}],
                [{"text": "💻 PC", "callback_data": "edit_pc"}],
                [{"text": "📊 عرض الأسعار الحالية", "callback_data": "show_prices"}],
                [{"text": "🔄 إعادة تحميل الأسعار", "callback_data": "reload_prices"}]
            ]
            
            send_inline_keyboard(chat_id, "🔧 اختر المنصة لتعديل أسعارها:", keyboard)
        
        elif text.lower() == '/order':
            order_text = f"""
🛒 لطلب FC 25:

1️⃣ زيارة الموقع: {WEBHOOK_URL}
2️⃣ اختيار المنصة ونوع الحساب
3️⃣ التواصل عبر الواتساب: 01094591331

⚡ تسليم خلال 15 ساعة
🛡️ ضمان سنة كاملة
💎 أرخص الأسعار في مصر

📊 أحدث الأسعار: /prices
            """
            send_message(chat_id, order_text)
        
        elif text.lower() == '/status':
            if is_admin:
                # إحصائيات تفصيلية للمدير
                total_platforms = len(PRICES_DATA['fc25'])
                total_prices = sum(len(platform_prices) for platform_prices in PRICES_DATA['fc25'].values())
                
                status_text = f"""
📊 حالة المنصة والبوت - تقرير مفصل:

✅ البوت: يعمل بشكل طبيعي
✅ المنصة: نشطة
✅ الويبهوك: متصل
✅ نظام الأسعار: نشط
🌐 الموقع: {WEBHOOK_URL}
📱 الواتساب: 01094591331

📈 إحصائيات:
🎮 عدد المنصات: {total_platforms}
💰 إجمالي الأسعار: {total_prices}
💾 ملف الأسعار: محفوظ
🔄 آخر تحديث: متزامن

🚀 النظام جاهز لاستقبال الطلبات والتحديثات
                """
            else:
                status_text = "✅ البوت والمنصة يعملان بشكل طبيعي"
            send_message(chat_id, status_text)
        
        elif text.lower() == '/support':
            support_text = f"""
🆘 الدعم الفني:

📱 واتساب: 01094591331
🌐 الموقع: {WEBHOOK_URL}
⏰ نعمل 24/7

💬 يمكنك أيضاً كتابة مشكلتك هنا وسيتم الرد عليك

📊 للأسعار الحالية: /prices
🛒 للطلب: /order
            """
            send_message(chat_id, support_text)
        
        elif text.lower() == '/admin':
            if is_admin:
                admin_text = f"""
👨‍💻 لوحة الإدارة الشاملة:

🌐 رابط الإدارة: {WEBHOOK_URL}/admin
📊 إحصائيات: {WEBHOOK_URL}/stats
⚙️ API الأسعار: {WEBHOOK_URL}/api/prices

🔧 أوامر سريعة:
/prices - عرض الأسعار الحالية
/setprice - تعديل السعر مباشرة
/editprices - تعديل بالأزرار
/reloadprices - إعادة تحميل الأسعار
/status - حالة النظام كاملة

💡 مثال سريع:
/setprice ps4 Primary 95

🚀 استخدم الروابط أعلاه للوصول لجميع أدوات الإدارة
                """
                send_message(chat_id, admin_text)
            else:
                send_message(chat_id, "❌ غير مسموح لك بالوصول للوحة الإدارة")
        
        else:
            # رد عام
            if is_admin:
                reply_text = f"""
📝 مرحباً أيها المدير! تم استلام رسالتك: "{text}"

🔧 أوامر الإدارة السريعة:
• /prices - عرض الأسعار
• /setprice ps4 Primary 90 - تعديل السعر
• /editprices - تعديل بالأزرار
• /admin - لوحة الإدارة
• /status - حالة النظام

📱 للتواصل المباشر: 01094591331
                """
            else:
                reply_text = f"""
📝 تم استلام رسالتك: "{text}"

🤖 للمساعدة استخدم:
• /help - قائمة الأوامر
• /order - لطلب FC 25
• /prices - عرض الأسعار

📱 للتواصل المباشر: 01094591331
                """
            send_message(chat_id, reply_text)
        
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الرسالة: {e}")
        return False

def process_callback_query(callback_query):
    """معالجة أزرار الكيبورد"""
    try:
        data = callback_query.get('data', '')
        chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
        message_id = callback_query.get('message', {}).get('message_id')
        user_id = callback_query.get('from', {}).get('id')
        
        # التأكد من صلاحية المدير
        is_admin = str(user_id) == CHAT_ID
        
        if not is_admin:
            callback_url = f"{TELEGRAM_API}/answerCallbackQuery"
            requests.post(callback_url, json={
                'callback_query_id': callback_query.get('id'),
                'text': '❌ غير مسموح لك بهذا الإجراء'
            }, timeout=5)
            return True
        
        # معالجة البيانات
        if data == 'show_prices':
            prices_message = format_prices_message()
            send_message(chat_id, prices_message)
        
        elif data == 'reload_prices':
            global PRICES_DATA
            PRICES_DATA = load_prices()
            send_message(chat_id, "🔄 تم إعادة تحميل الأسعار من الملف بنجاح!")
            
            # إرسال الأسعار المحدثة
            prices_message = format_prices_message()
            send_message(chat_id, prices_message)
        
        elif data.startswith('edit_'):
            platform = data.replace('edit_', '')
            platform_names = {
                'ps4': '🎮 PlayStation 4',
                'ps5': '🎮 PlayStation 5', 
                'xbox': '🎮 Xbox Series',
                'pc': '💻 PC'
            }
            
            if platform in PRICES_DATA['fc25']:
                current_prices = PRICES_DATA['fc25'][platform]
                message = f"💰 الأسعار الحالية لـ {platform_names.get(platform, platform.upper())}:\n\n"
                
                for account_type, price in current_prices.items():
                    message += f"• {account_type}: {price} جنيه\n"
                
                message += f"\n💡 لتعديل السعر استخدم:\n/setprice {platform} [النوع] [السعر الجديد]\n\n"
                message += f"أمثلة:\n"
                message += f"/setprice {platform} Primary 95\n"
                message += f"/setprice {platform} Secondary 80\n"
                message += f"/setprice {platform} Full 130"
                
                send_message(chat_id, message)
        
        elif data == 'order_fc25':
            send_message(chat_id, f"🛒 لطلب FC 25، قم بزيارة: {WEBHOOK_URL}")
        elif data == 'view_prices':
            prices_message = format_prices_message()
            send_message(chat_id, prices_message)
        elif data == 'contact_support':
            send_message(chat_id, "📱 للدعم الفني: 01094591331")
        
        # إشعار بأن الزر تم الضغط عليه
        callback_url = f"{TELEGRAM_API}/answerCallbackQuery"
        requests.post(callback_url, json={
            'callback_query_id': callback_query.get('id'),
            'text': 'تم!'
        }, timeout=5)
        
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الكولباك: {e}")
        return False

# إعداد التطبيق والبوت الجديد
ptb_app = None

def get_ptb_app():
    """الحصول على تطبيق البوت مع إعداده"""
    global ptb_app
    if ptb_app is None:
        ptb_app = Application.builder().token(BOT_TOKEN).build()
        
        # إضافة معالج للرسائل
        async def handle_message(update: Update, context):
            if update.message:
                message_dict = update.message.to_dict()
                process_message(message_dict)
        
        # إضافة معالج للكولباك
        async def handle_callback(update: Update, context):
            if update.callback_query:
                callback_dict = update.callback_query.to_dict()
                process_callback_query(callback_dict)
        
        ptb_app.add_handler(MessageHandler(filters.ALL, handle_message))
        ptb_app.add_handler(CallbackQueryHandler(handle_callback))
        
        logger.info("✅ تم إعداد البوت بنجاح")
    
    return ptb_app

# إعداد الويبهوك عند بدء التشغيل
def setup_webhook():
    """إعداد الويبهوك عند بدء التطبيق"""
    logger.info("🚀 بدء إعداد الويبهوك...")
    success = set_webhook()
    if success:
        logger.info("✅ تم إعداد الويبهوك بنجاح!")
        
        # إرسال إشعار بدء التشغيل
        startup_msg = f"""
🚀 تم تشغيل منصة شهد السنيورة بنجاح!

✅ البوت: نشط
✅ الويبهوك: متصل
✅ الأسعار: محملة
🌐 الموقع: {WEBHOOK_URL}

💰 نظام تحديث الأسعار جاهز!
🔧 استخدم /help لعرض جميع الأوامر
        """
        
        send_message(CHAT_ID, startup_msg)
    else:
        logger.error("❌ فشل في إعداد الويبهوك!")

# Routes المنصة الرئيسية
@app.route('/')
def home():
    """الصفحة الرئيسية للمنصة"""
    try:
        # إعادة تحميل الأسعار لضمان التحديث
        global PRICES_DATA
        PRICES_DATA = load_prices()
        return render_template('index.html', prices=PRICES_DATA)
    except Exception as e:
        logger.error(f"خطأ في تحميل الصفحة الرئيسية: {e}")
        return jsonify({
            'status': 'active',
            'bot': BOT_USERNAME,
            'message': 'منصة شهد السنيورة - أرخص أسعار FC 25 في مصر! ✅'
        })

@app.route('/api/prices')
def api_prices():
    """API للأسعار - يعيد الأسعار المحدثة"""
    global PRICES_DATA
    PRICES_DATA = load_prices()  # تأكد من أحدث الأسعار
    return jsonify(PRICES_DATA)

@app.route('/api/update_price', methods=['POST'])
def api_update_price():
    """API لتحديث الأسعار"""
    try:
        data = request.get_json()
        platform = data.get('platform', '').lower()
        account_type = data.get('account_type', '')
        new_price = int(data.get('price', 0))
        
        if update_price(platform, account_type, new_price):
            return jsonify({
                'success': True,
                'message': 'تم تحديث السعر بنجاح',
                'updated_price': {
                    'platform': platform,
                    'account_type': account_type,
                    'price': new_price
                },
                'all_prices': PRICES_DATA
            })
        else:
            return jsonify({
                'success': False,
                'message': 'فشل في تحديث السعر'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ: {str(e)}'
        }), 500

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
            {'q': 'كيف يتم تحديث الأسعار؟', 'a': 'يتم التحديث تلقائياً من البوت مع الحفظ الدائم'}
        ]
    })

@app.route('/admin')
def admin():
    """لوحة الإدارة المحسنة"""
    webhook_info = get_webhook_info()
    
    # إعادة تحميل الأسعار للتأكد من أحدث البيانات
    global PRICES_DATA
    PRICES_DATA = load_prices()
    
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة إدارة منصة شهد السنيورة المحسنة</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 2px solid #667eea;
            }}
            .header h1 {{
                color: #667eea;
                margin: 0;
                font-size: 2.5rem;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .info-box {{
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .prices-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .price-platform {{
                background: linear-gradient(45deg, #28a745, #20a039);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .price-platform h4 {{
                margin: 0 0 15px 0;
                font-size: 1.3rem;
            }}
            .commands-box {{
                background: #e7f3ff;
                border-left: 4px solid #007bff;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .btn-group {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                justify-content: center;
                margin: 30px 0;
            }}
            .btn {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s;
                text-decoration: none;
                display: inline-block;
                font-weight: bold;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
            }}
            .btn-danger {{
                background: linear-gradient(45deg, #dc3545, #c82333);
            }}
            .btn-success {{
                background: linear-gradient(45deg, #28a745, #20a039);
            }}
            .btn-info {{
                background: linear-gradient(45deg, #17a2b8, #138496);
            }}
            .status-ok {{ color: #28a745; font-weight: bold; }}
            .status-error {{ color: #dc3545; font-weight: bold; }}
            .webhook-info {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                white-space: pre-wrap;
                max-height: 300px;
                overflow-y: auto;
            }}
            .feature-highlight {{
                background: linear-gradient(45deg, #ffc107, #ff8f00);
                color: white;
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                text-align: center;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎮 لوحة إدارة منصة شهد السنيورة المحسنة</h1>
                <p>نظام إدارة شامل مع حفظ دائم للأسعار</p>
            </div>
            
            <div class="feature-highlight">
                🚀 جديد: نظام حفظ الأسعار الدائم مع التحديث التلقائي للموقع!
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>🤖 البوت</h3>
                    <p>{BOT_USERNAME}</p>
                </div>
                <div class="stat-card">
                    <h3>💬 Chat ID</h3>
                    <p>{CHAT_ID}</p>
                </div>
                <div class="stat-card">
                    <h3>🌐 المنصة</h3>
                    <p>نشطة ✅</p>
                </div>
                <div class="stat-card">
                    <h3>📱 نظام الأسعار</h3>
                    <p>محفوظ دائماً 💾</p>
                </div>
            </div>
            
            <div class="commands-box">
                <h3>🔧 أوامر البوت للأسعار:</h3>
                <div style="background: white; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <p><strong>📝 تحديث السعر:</strong> <code>/setprice ps4 Primary 90</code></p>
                    <p><strong>🎛️ تحديث بالأزرار:</strong> <code>/editprices</code></p>
                    <p><strong>📊 عرض الأسعار:</strong> <code>/prices</code></p>
                    <p><strong>🔄 إعادة تحميل:</strong> <code>/reloadprices</code></p>
                    <p><strong>📈 حالة النظام:</strong> <code>/status</code></p>
                </div>
            </div>
            
            <div class="info-box">
                <h3>💰 الأسعار الحالية المحفوظة:</h3>
                <div class="prices-grid">
                    <div class="price-platform">
                        <h4>🎮 PS4</h4>
                        <p>Primary: {PRICES_DATA['fc25']['ps4']['Primary']} جنيه</p>
                        <p>Secondary: {PRICES_DATA['fc25']['ps4']['Secondary']} جنيه</p>
                        <p>Full: {PRICES_DATA['fc25']['ps4']['Full']} جنيه</p>
                    </div>
                    <div class="price-platform">
                        <h4>🎮 PS5</h4>
                        <p>Primary: {PRICES_DATA['fc25']['ps5']['Primary']} جنيه</p>
                        <p>Secondary: {PRICES_DATA['fc25']['ps5']['Secondary']} جنيه</p>
                        <p>Full: {PRICES_DATA['fc25']['ps5']['Full']} جنيه</p>
                    </div>
                    <div class="price-platform">
                        <h4>🎮 Xbox</h4>
                        <p>Primary: {PRICES_DATA['fc25']['xbox']['Primary']} جنيه</p>
                        <p>Secondary: {PRICES_DATA['fc25']['xbox']['Secondary']} جنيه</p>
                        <p>Full: {PRICES_DATA['fc25']['xbox']['Full']} جنيه</p>
                    </div>
                    <div class="price-platform">
                        <h4>💻 PC</h4>
                        <p>Primary: {PRICES_DATA['fc25']['pc']['Primary']} جنيه</p>
                        <p>Secondary: {PRICES_DATA['fc25']['pc']['Secondary']} جنيه</p>
                        <p>Full: {PRICES_DATA['fc25']['pc']['Full']} جنيه</p>
                    </div>
                </div>
            </div>
            
            <div class="info-box">
                <h3>🔗 روابط المنصة:</h3>
                <p><strong>الموقع الرئيسي:</strong> <a href="{WEBHOOK_URL}" target="_blank">{WEBHOOK_URL}</a></p>
                <p><strong>API الأسعار:</strong> <a href="{WEBHOOK_URL}/api/prices" target="_blank">{WEBHOOK_URL}/api/prices</a></p>
                <p><strong>Webhook URL:</strong> {WEBHOOK_URL}/webhook/{BOT_TOKEN}</p>
            </div>
            
            <div class="info-box">
                <h3>📊 حالة الويبهوك:</h3>
                <div class="webhook-info">{webhook_info}</div>
            </div>
            
            <div class="btn-group">
                <button class="btn btn-success" onclick="setWebhook()">✅ تعيين الويبهوك</button>
                <button class="btn btn-danger" onclick="deleteWebhook()">❌ حذف الويبهوك</button>
                <button class="btn btn-info" onclick="testBot()">🔧 اختبار البوت</button>
                <button class="btn btn-info" onclick="refreshPrices()">🔄 تحديث الأسعار</button>
                <a href="{WEBHOOK_URL}" class="btn">🌐 زيارة المنصة</a>
                <a href="{WEBHOOK_URL}/api/prices" class="btn">📊 API الأسعار</a>
                <button class="btn" onclick="location.reload()">🔄 تحديث الصفحة</button>
            </div>
            
            <div id="result" style="margin-top: 30px;"></div>
        </div>
        
        <script>
            function setWebhook() {{
                fetch('/set_webhook')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="info-box ' + (data.success ? 'status-ok' : 'status-error') + '">' + 
                            '🎯 ' + data.message + '</div>';
                    }});
            }}
            
            function deleteWebhook() {{
                fetch('/delete_webhook')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="info-box ' + (data.success ? 'status-ok' : 'status-error') + '">' + 
                            '🗑️ ' + data.message + '</div>';
                    }});
            }}
            
            function testBot() {{
                fetch('/test_bot')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="info-box ' + (data.success ? 'status-ok' : 'status-error') + '">' + 
                            '🔧 ' + data.message + '</div>';
                    }});
            }}
            
            function refreshPrices() {{
                fetch('/api/prices')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="info-box status-ok">🔄 تم تحديث الأسعار بنجاح!</div>';
                        setTimeout(() => {{
                            location.reload();
                        }}, 2000);
                    }});
            }}
        </script>
    </body>
    </html>
    """
    return html

@app.route('/set_webhook')
def set_webhook_route():
    """تعيين الويبهوك عبر HTTP"""
    success = set_webhook()
    return jsonify({
        'success': success,
        'message': '✅ تم تعيين الويبهوك بنجاح!' if success else '❌ فشل في تعيين الويبهوك'
    })

@app.route('/delete_webhook')
def delete_webhook_route():
    """حذف الويبهوك عبر HTTP"""
    success = delete_webhook()
    return jsonify({
        'success': success,
        'message': '✅ تم حذف الويبهوك بنجاح!' if success else '❌ فشل في حذف الويبهوك'
    })

@app.route('/test_bot')
def test_bot():
    """اختبار البوت والنظام"""
    try:
        test_message = f"""
🔧 اختبار شامل للمنصة والبوت

🌐 الموقع: {WEBHOOK_URL}
🤖 البوت: {BOT_USERNAME}
⏰ الوقت: {os.getenv('TZ', 'UTC')}
📱 المنصة: نشطة ✅
💾 نظام الأسعار: محفوظ دائماً

💎 منصة شهد السنيورة - أرخص أسعار FC 25 في مصر!

🚀 النظام المحسن نشط:
✅ /setprice - تعديل وحفظ دائم
✅ /editprices - تحديث بالأزرار
✅ /prices - عرض الأسعار المحدثة
✅ /reloadprices - إعادة التحميل

📊 النظام جاهز لاستقبال التحديثات!
        """
        result = send_message(CHAT_ID, test_message)
        success = result is not None
        return jsonify({
            'success': success,
            'message': '✅ تم إرسال رسالة اختبار شاملة بنجاح!' if success else '❌ فشل في إرسال الرسالة'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'❌ خطأ في الاختبار: {str(e)}'
        })

# معالج الويبهوك المحدث
@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook_handler():
    """معالج الويبهوك المحسن مع البوت الجديد"""
    try:
        logger.info("📨 استلام طلب ويبهوك")
        
        # التأكد من Content-Type
        if request.content_type != 'application/json':
            logger.warning(f"Content-Type غير صحيح: {request.content_type}")
            return jsonify({'error': 'Invalid Content-Type'}), 400
        
        # الحصول على البيانات
        update_data = request.get_json(force=True)
        
        if not update_data:
            logger.warning("لم يتم استلام بيانات")
            return jsonify({'error': 'No data received'}), 400
        
        logger.info(f"📊 استلام تحديث: {update_data}")
        
        # الحصول على تطبيق البوت
        app_instance = get_ptb_app()
        
        # تحويل البيانات إلى كائن Update
        update = Update.de_json(update_data, app_instance.bot)
        
        # معالجة التحديث بشكل غير متزامن
        async def process_update():
            await app_instance.process_update(update)
        
        # تشغيل المعالجة
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # إنشاء مهمة جديدة إذا كان الحلقة تعمل
                asyncio.create_task(process_update())
            else:
                # تشغيل الحلقة إذا لم تكن تعمل
                loop.run_until_complete(process_update())
        except RuntimeError:
            # إنشاء حلقة جديدة إذا لزم الأمر
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(process_update())
            loop.close()
        
        logger.info("✅ تم معالجة التحديث بنجاح")
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالج الويبهوك: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook_info')
def webhook_info():
    """معلومات الويبهوك"""
    info = get_webhook_info()
    return jsonify(info)

@app.route('/ping')
def ping():
    """نقطة فحص للخدمة"""
    return jsonify({
        'status': 'alive', 
        'platform': 'شهد السنيورة',
        'service': 'FC 25 Platform',
        'features': 'Enhanced Price Management with Persistent Storage',
        'prices_system': 'active',
        'timestamp': str(os.getenv('TZ', 'UTC'))
    })

@app.route('/stats')
def stats():
    """إحصائيات المنصة المحسنة"""
    global PRICES_DATA
    PRICES_DATA = load_prices()  # تأكد من أحدث البيانات
    
    # حساب إحصائيات تفصيلية
    total_platforms = len(PRICES_DATA['fc25'])
    total_price_points = sum(len(platform_prices) for platform_prices in PRICES_DATA['fc25'].values())
    
    # حساب متوسط الأسعار
    all_prices = []
    for platform in PRICES_DATA['fc25'].values():
        all_prices.extend(platform.values())
    
    avg_price = sum(all_prices) / len(all_prices) if all_prices else 0
    min_price = min(all_prices) if all_prices else 0
    max_price = max(all_prices) if all_prices else 0
    
    return jsonify({
        'platform': 'منصة شهد السنيورة المحسنة',
        'game': 'EA Sports FC 25',
        'platforms': ['PS4', 'PS5', 'Xbox', 'PC'],
        'account_types': ['Primary', 'Secondary', 'Full'],
        'current_prices': PRICES_DATA,
        'statistics': {
            'total_platforms': total_platforms,
            'total_price_points': total_price_points,
            'average_price': round(avg_price, 2),
            'min_price': min_price,
            'max_price': max_price
        },
        'features': [
            'Dynamic Price Management',
            'Persistent File Storage', 
            'Telegram Integration',
            'Admin Controls',
            'Auto Website Updates',
            'Real-time Price Sync'
        ],
        'system_status': {
            'prices_file': 'active',
            'bot_status': 'running',
            'webhook': 'connected',
            'auto_sync': 'enabled'
        },
        'guarantee': '1 year',
        'delivery': '15 hours max',
        'whatsapp': '01094591331',
        'status': 'active'
    })

# معالج الأخطاء
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'error': 'صفحة غير موجودة',
        'platform': 'منصة شهد السنيورة',
        'home': WEBHOOK_URL,
        'prices': f"{WEBHOOK_URL}/api/prices"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'خطأ في الخادم',
        'platform': 'منصة شهد السنيورة',
        'support': '01094591331'
    }), 500

# تشغيل إعداد الويبهوك عند بدء التطبيق
with app.app_context():
    setup_webhook()

if __name__ == '__main__':
    # تشغيل Flask فقط (لا نحتاج thread منفصل للبوت الآن)
    print("🌐 تشغيل Flask مع البوت المدمج...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
