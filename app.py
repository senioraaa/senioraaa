import os
import logging
import requests
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
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7607085569:AAFE_NO4pVcgfVenU5R_GSEnauoFIQ0iVXo')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'ea_fc_fifa_bot')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1124247595')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://senioraaa.onrender.com')

# التليجرام API URLs
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# بيانات الأسعار المؤقتة (يمكن نقلها لقاعدة بيانات لاحقاً)
PRICES_DATA = {
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
    """تحديث السعر في قاعدة البيانات"""
    try:
        if platform.lower() in PRICES_DATA['fc25'] and account_type in PRICES_DATA['fc25'][platform.lower()]:
            PRICES_DATA['fc25'][platform.lower()][account_type] = int(new_price)
            logger.info(f"تم تحديث السعر: {platform} {account_type} = {new_price}")
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
        message += "مثال: /setprice ps4 Primary 90"
        
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
        
        elif text.lower().startswith('/setprice'):
            if not is_admin:
                send_message(chat_id, "❌ هذا الأمر مخصص للمدير فقط")
                return True
            
            # تحليل الأمر
            parts = text.split()
            if len(parts) != 4:
                send_message(chat_id, """
❌ صيغة الأمر غير صحيحة!

الصيغة الصحيحة:
/setprice [المنصة] [النوع] [السعر]

أمثلة:
/setprice ps4 Primary 90
/setprice ps5 Secondary 80
/setprice xbox Full 130

المنصات: ps4, ps5, xbox, pc
الأنواع: Primary, Secondary, Full
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

🔄 تم تحديث الموقع والأسعار تلقائياً
                """
                send_message(chat_id, success_msg)
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
                [{"text": "📊 عرض الأسعار الحالية", "callback_data": "show_prices"}]
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
            """
            send_message(chat_id, order_text)
        
        elif text.lower() == '/status':
            if is_admin:
                status_text = f"""
📊 حالة المنصة والبوت:

✅ البوت: يعمل بشكل طبيعي
✅ المنصة: نشطة
✅ الويبهوك: متصل
🌐 الموقع: {WEBHOOK_URL}
📱 الواتساب: 01094591331

💰 الأسعار الحالية محدثة
🔧 جاهز لاستقبال الطلبات
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
            """
            send_message(chat_id, support_text)
        
        elif text.lower() == '/admin':
            if is_admin:
                admin_text = f"""
👨‍💻 لوحة الإدارة:

🌐 رابط الإدارة: {WEBHOOK_URL}/admin
📊 إحصائيات: {WEBHOOK_URL}/stats
⚙️ API الأسعار: {WEBHOOK_URL}/api/prices

🔧 أوامر سريعة:
/prices - عرض الأسعار
/setprice - تعديل السعر
/editprices - تعديل بالأزرار
/status - حالة المنصة

استخدم الروابط أعلاه للوصول لجميع أدوات الإدارة
                """
                send_message(chat_id, admin_text)
            else:
                send_message(chat_id, "❌ غير مسموح لك بالوصول للوحة الإدارة")
        
        else:
            # رد عام
            if is_admin:
                reply_text = f"""
📝 مرحباً أيها المدير! تم استلام رسالتك: "{text}"

🔧 أوامر الإدارة:
• /prices - عرض الأسعار
• /setprice - تعديل السعر
• /editprices - تعديل بالأزرار
• /admin - لوحة الإدارة

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
                message += f"مثال: /setprice {platform} Primary 95"
                
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

# إعداد الويبهوك عند بدء التشغيل - الطريقة الجديدة
def setup_webhook():
    """إعداد الويبهوك عند بدء التطبيق"""
    logger.info("🚀 بدء إعداد الويبهوك...")
    success = set_webhook()
    if success:
        logger.info("✅ تم إعداد الويبهوك بنجاح!")
    else:
        logger.error("❌ فشل في إعداد الويبهوك!")

# استدعاء إعداد الويبهوك مباشرة عند تحميل التطبيق
with app.app_context():
    setup_webhook()

# Routes المنصة الرئيسية
@app.route('/')
def home():
    """الصفحة الرئيسية للمنصة"""
    try:
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
    """API للأسعار"""
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
                }
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
            {'q': 'هل يمكن تغيير بيانات الحساب؟', 'a': 'ممنوع نهائياً تغيير أي بيانات'}
        ]
    })

@app.route('/admin')
def admin():
    """لوحة الإدارة المحسنة"""
    webhook_info = get_webhook_info()
    
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة إدارة منصة شهد السنيورة</title>
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
                max-width: 1200px;
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
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .price-platform {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #28a745;
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎮 لوحة إدارة منصة شهد السنيورة</h1>
                <p>نظام إدارة شامل لمنصة FC 25 مع تحديث الأسعار</p>
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
                    <h3>📱 الألعاب</h3>
                    <p>FC 25</p>
                </div>
            </div>
            
            <div class="info-box">
                <h3>💰 الأسعار الحالية:</h3>
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
                <h3>📋 أوامر البوت لتحديث الأسعار:</h3>
                <p><strong>/setprice [المنصة] [النوع] [السعر]</strong></p>
                <p>مثال: <code>/setprice ps4 Primary 90</code></p>
                <p><strong>/editprices</strong> - تحديث بالأزرار</p>
                <p><strong>/prices</strong> - عرض الأسعار الحالية</p>
            </div>
            
            <div class="info-box">
                <h3>📊 حالة الويبهوك:</h3>
                <div class="webhook-info">{webhook_info}</div>
            </div>
            
            <div class="btn-group">
                <button class="btn btn-success" onclick="setWebhook()">✅ تعيين الويبهوك</button>
                <button class="btn btn-danger" onclick="deleteWebhook()">❌ حذف الويبهوك</button>
                <button class="btn" onclick="testBot()">🔧 اختبار البوت</button>
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
    """اختبار البوت"""
    try:
        test_message = f"""
🔧 اختبار المنصة والبوت

🌐 الموقع: {WEBHOOK_URL}
🤖 البوت: {BOT_USERNAME}
⏰ الوقت: {os.getenv('TZ', 'UTC')}
📱 المنصة: نشطة ✅

💎 منصة شهد السنيورة - أرخص أسعار FC 25 في مصر!

💰 نظام تحديث الأسعار نشط:
/setprice - تعديل السعر
/editprices - تحديث بالأزرار
/prices - عرض الأسعار
        """
        result = send_message(CHAT_ID, test_message)
        success = result is not None
        return jsonify({
            'success': success,
            'message': '✅ تم إرسال رسالة اختبار بنجاح!' if success else '❌ فشل في إرسال الرسالة'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'❌ خطأ في الاختبار: {str(e)}'
        })

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook_handler():
    """معالج الويبهوك الرئيسي"""
    try:
        # التأكد من Content-Type
        if request.content_type != 'application/json':
            logger.warning(f"Content-Type غير صحيح: {request.content_type}")
            return jsonify({'error': 'Invalid Content-Type'}), 400
        
        # الحصول على البيانات
        update = request.get_json(force=True)
        
        if not update:
            logger.warning("لم يتم استلام بيانات")
            return jsonify({'error': 'No data received'}), 400
        
        logger.info(f"استلام تحديث: {update}")
        
        # معالجة الرسائل
        if 'message' in update:
            success = process_message(update['message'])
            if not success:
                return jsonify({'error': 'Message processing failed'}), 500
        
        # معالجة الكولباك
        elif 'callback_query' in update:
            success = process_callback_query(update['callback_query'])
            if not success:
                return jsonify({'error': 'Callback processing failed'}), 500
        
        # رد إيجابي للتليجرام
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
        'features': 'Price Management System',
        'timestamp': str(os.getenv('TZ', 'UTC'))
    })

@app.route('/stats')
def stats():
    """إحصائيات المنصة"""
    return jsonify({
        'platform': 'منصة شهد السنيورة',
        'game': 'EA Sports FC 25',
        'platforms': ['PS4', 'PS5', 'Xbox', 'PC'],
        'account_types': ['Primary', 'Secondary', 'Full'],
        'current_prices': PRICES_DATA,
        'guarantee': '1 year',
        'delivery': '15 hours max',
        'whatsapp': '01094591331',
        'features': ['Dynamic Price Management', 'Telegram Integration', 'Admin Controls'],
        'status': 'active'
    })

# معالج الأخطاء
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'error': 'صفحة غير موجودة',
        'platform': 'منصة شهد السنيورة',
        'home': WEBHOOK_URL
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'خطأ في الخادم',
        'platform': 'منصة شهد السنيورة',
        'support': '01094591331'
    }), 500

if __name__ == '__main__':
    # للتطوير المحلي فقط
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
