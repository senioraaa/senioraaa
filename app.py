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
            help_text = """
📋 الأوامر المتاحة:

/start - بداية التفاعل
/order - طلب FC 25
/prices - عرض الأسعار
/status - حالة البوت
/support - الدعم الفني
/admin - لوحة الإدارة (للمدير فقط)

🌐 الموقع الكامل: {WEBHOOK_URL}
            """.format(WEBHOOK_URL=WEBHOOK_URL)
            send_message(chat_id, help_text)
        
        elif text.lower() == '/prices':
            prices_text = """
💰 أسعار FC 25 - جميع المنصات:

🎮 PS4/PS5:
• Primary: 85/90 جنيه
• Secondary: 70/75 جنيه  
• Full: 120/125 جنيه

🎮 Xbox:
• Primary: 85 جنيه
• Secondary: 70 جنيه
• Full: 120 جنيه

💻 PC:
• Primary: 80 جنيه
• Secondary: 65 جنيه
• Full: 115 جنيه

🛒 للطلب: /order
🌐 الموقع: {WEBHOOK_URL}
            """.format(WEBHOOK_URL=WEBHOOK_URL)
            send_message(chat_id, prices_text)
        
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
            status_text = "✅ البوت والمنصة يعملان بشكل طبيعي"
            send_message(chat_id, status_text)
        
        elif text.lower() == '/support':
            support_text = """
🆘 الدعم الفني:

📱 واتساب: 01094591331
🌐 الموقع: {WEBHOOK_URL}
⏰ نعمل 24/7

💬 يمكنك أيضاً كتابة مشكلتك هنا وسيتم الرد عليك
            """.format(WEBHOOK_URL=WEBHOOK_URL)
            send_message(chat_id, support_text)
        
        elif text.lower() == '/admin':
            if str(user_id) == CHAT_ID:
                admin_text = f"""
👨‍💻 لوحة الإدارة:

🌐 رابط الإدارة: {WEBHOOK_URL}/admin
📊 إحصائيات: {WEBHOOK_URL}/stats
⚙️ إعدادات: {WEBHOOK_URL}/settings

استخدم الروابط أعلاه للوصول لجميع أدوات الإدارة
                """
                send_message(chat_id, admin_text)
            else:
                send_message(chat_id, "❌ غير مسموح لك بالوصول للوحة الإدارة")
        
        else:
            # رد عام
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
        
        # معالجة البيانات
        if data == 'order_fc25':
            send_message(chat_id, f"🛒 لطلب FC 25، قم بزيارة: {WEBHOOK_URL}")
        elif data == 'view_prices':
            send_message(chat_id, "💰 لعرض الأسعار الكاملة، استخدم /prices")
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
                <p>نظام إدارة شامل لمنصة FC 25</p>
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
