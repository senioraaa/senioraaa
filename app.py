import os
import logging
import requests
from flask import Flask, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

# إعداد اللوجر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# المتغيرات البيئية
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7607085569:AAFE_NO4pVcgfVenU5R_GSEnauoFIQ0iVXo')
BOT_USERNAME = os.getenv('BOT_USERNAME', 'ea_fc_fifa_bot')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1124247595')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://senioraaa.onrender.com')

# التليجرام API URLs
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

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
            welcome_text = "مرحباً! أنا بوت FIFA EA FC ⚽\nاستخدم الأوامر التالية:\n\n/help - للمساعدة\n/status - حالة البوت"
            send_message(chat_id, welcome_text)
        
        elif text.lower() == '/help':
            help_text = "الأوامر المتاحة:\n\n/start - بداية التفاعل\n/help - هذه المساعدة\n/status - حالة البوت\n/admin - لوحة الإدارة"
            send_message(chat_id, help_text)
        
        elif text.lower() == '/status':
            status_text = "✅ البوت يعمل بشكل طبيعي"
            send_message(chat_id, status_text)
        
        elif text.lower() == '/admin':
            if str(user_id) == CHAT_ID:
                admin_text = f"لوحة الإدارة 👨‍💻\n\nرابط الإدارة: {WEBHOOK_URL}/admin"
                send_message(chat_id, admin_text)
            else:
                send_message(chat_id, "❌ غير مسموح لك بالوصول للوحة الإدارة")
        
        else:
            # رد عام
            reply_text = f"تم استلام رسالتك: {text}\n\nاستخدم /help للمساعدة"
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
        if data == 'test_button':
            send_message(chat_id, "تم الضغط على زر الاختبار! ✅")
        
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

@app.route('/')
def home():
    """الصفحة الرئيسية"""
    return jsonify({
        'status': 'active',
        'bot': BOT_USERNAME,
        'message': 'Bot is running successfully! ✅'
    })

@app.route('/admin')
def admin():
    """لوحة الإدارة"""
    webhook_info = get_webhook_info()
    
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة إدارة البوت</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            h1 {{
                color: #764ba2;
                text-align: center;
                margin-bottom: 30px;
            }}
            .info-box {{
                background: #f8f9fa;
                border-left: 4px solid #007bff;
                padding: 15px;
                margin: 15px 0;
                border-radius: 5px;
            }}
            .btn {{
                background: linear-gradient(45deg, #007bff, #0056b3);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 25px;
                cursor: pointer;
                margin: 5px;
                transition: all 0.3s;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,123,255,0.4);
            }}
            .status-ok {{ color: #28a745; }}
            .status-error {{ color: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 لوحة إدارة البوت</h1>
            
            <div class="info-box">
                <h3>معلومات البوت:</h3>
                <p><strong>اسم البوت:</strong> {BOT_USERNAME}</p>
                <p><strong>Chat ID:</strong> {CHAT_ID}</p>
                <p><strong>Webhook URL:</strong> {WEBHOOK_URL}/webhook/{BOT_TOKEN}</p>
            </div>
            
            <div class="info-box">
                <h3>حالة الويبهوك:</h3>
                <pre>{webhook_info}</pre>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <button class="btn" onclick="setWebhook()">تعيين الويبهوك</button>
                <button class="btn" onclick="deleteWebhook()">حذف الويبهوك</button>
                <button class="btn" onclick="testBot()">اختبار البوت</button>
                <button class="btn" onclick="location.reload()">تحديث الصفحة</button>
            </div>
            
            <div id="result" style="margin-top: 20px;"></div>
        </div>
        
        <script>
            function setWebhook() {{
                fetch('/set_webhook')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="info-box ' + (data.success ? 'status-ok' : 'status-error') + '">' + 
                            data.message + '</div>';
                    }});
            }}
            
            function deleteWebhook() {{
                fetch('/delete_webhook')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="info-box ' + (data.success ? 'status-ok' : 'status-error') + '">' + 
                            data.message + '</div>';
                    }});
            }}
            
            function testBot() {{
                fetch('/test_bot')
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('result').innerHTML = 
                            '<div class="info-box ' + (data.success ? 'status-ok' : 'status-error') + '">' + 
                            data.message + '</div>';
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
        result = send_message(CHAT_ID, "🔧 اختبار البوت - التوقيت: " + str(os.getenv('TZ', 'UTC')))
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
    return jsonify({'status': 'alive', 'timestamp': str(os.getenv('TZ', 'UTC'))})

if __name__ == '__main__':
    # للتطوير المحلي فقط
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
