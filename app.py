import os
import json
import logging
from flask import Flask, request, jsonify, render_template
import requests
from datetime import datetime
import traceback

# إعداد التطبيق
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعداد Telegram Bot
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7607085569:AAFE_NO4pVcgfVenU5R_GSEnauoFIQ0iVXo')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '1124247595')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://senioraaa.onrender.com')

# ملف الأسعار
PRICES_FILE = 'prices.json'

# تحميل الأسعار
def load_prices():
    try:
        if os.path.exists(PRICES_FILE):
            with open(PRICES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("✅ تم تحميل الأسعار من الملف")
                return data
        else:
            # أسعار افتراضية
            default_prices = {
                "ps4_primary": 100,
                "ps4_secondary": 80,
                "ps5_primary": 150,
                "ps5_secondary": 120
            }
            save_prices(default_prices)
            logger.info("✅ تم إنشاء ملف الأسعار الافتراضية")
            return default_prices
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الأسعار: {e}")
        return {
            "ps4_primary": 100,
            "ps4_secondary": 80,
            "ps5_primary": 150,
            "ps5_secondary": 120
        }

# تنسيق الأسعار للـ template
def format_prices_for_template(prices):
    """تحويل الأسعار للشكل المطلوب في الـ template"""
    try:
        platforms = {
            'ps4': {
                'primary': prices.get('ps4_primary', 100),
                'secondary': prices.get('ps4_secondary', 80)
            },
            'ps5': {
                'primary': prices.get('ps5_primary', 150),
                'secondary': prices.get('ps5_secondary', 120)
            }
        }
        return platforms
    except Exception as e:
        logger.error(f"❌ خطأ في تنسيق الأسعار: {e}")
        return {
            'ps4': {'primary': 100, 'secondary': 80},
            'ps5': {'primary': 150, 'secondary': 120}
        }

# حفظ الأسعار
def save_prices(prices):
    try:
        with open(PRICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(prices, f, ensure_ascii=False, indent=2)
        logger.info("✅ تم حفظ الأسعار")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الأسعار: {e}")
        return False

# إرسال رسالة Telegram
def send_telegram_message(message, chat_id=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id or CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ تم إرسال الرسالة: {message[:50]}...")
            return True
        else:
            logger.error(f"❌ فشل إرسال الرسالة: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال رسالة Telegram: {e}")
        return False

# معالجة أوامر التليجرام
def process_telegram_command(message):
    try:
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        user_first_name = message['from'].get('first_name', 'المستخدم')
        
        logger.info(f"📨 تم استلام أمر: {text} من {user_first_name}")
        
        if text == '/start':
            response = f"🎮 مرحباً {user_first_name}!\n\n"
            response += "🔹 /prices - عرض الأسعار الحالية\n"
            response += "🔹 /editprices - تعديل الأسعار\n"
            response += "🔹 /setprice - تحديد سعر معين\n"
            response += "🔹 /help - عرض المساعدة\n"
            response += "🔹 /status - حالة النظام\n\n"
            response += "تم تشغيل منصة شهد السيطرة بنجاح! 🚀"
            send_telegram_message(response, chat_id)
            
        elif text == '/prices':
            prices = load_prices()
            response = "💰 الأسعار الحالية:\n\n"
            response += f"🎮 PS4 Primary: {prices['ps4_primary']} جنيه\n"
            response += f"🎮 PS4 Secondary: {prices['ps4_secondary']} جنيه\n"
            response += f"🎮 PS5 Primary: {prices['ps5_primary']} جنيه\n"
            response += f"🎮 PS5 Secondary: {prices['ps5_secondary']} جنيه\n"
            send_telegram_message(response, chat_id)
            
        elif text == '/editprices':
            prices = load_prices()
            response = "✏️ لتعديل الأسعار، أرسل الأمر بالشكل التالي:\n\n"
            response += "<code>/setprice ps4_primary 120</code>\n"
            response += "<code>/setprice ps4_secondary 100</code>\n"
            response += "<code>/setprice ps5_primary 180</code>\n"
            response += "<code>/setprice ps5_secondary 150</code>\n\n"
            response += "الأسعار الحالية:\n"
            response += f"PS4 Primary: {prices['ps4_primary']} جنيه\n"
            response += f"PS4 Secondary: {prices['ps4_secondary']} جنيه\n"
            response += f"PS5 Primary: {prices['ps5_primary']} جنيه\n"
            response += f"PS5 Secondary: {prices['ps5_secondary']} جنيه"
            send_telegram_message(response, chat_id)
            
        elif text.startswith('/setprice'):
            parts = text.split()
            if len(parts) != 3:
                response = "❌ خطأ في الأمر!\n\n"
                response += "الشكل الصحيح:\n"
                response += "<code>/setprice ps4_primary 120</code>\n\n"
                response += "الأنواع المتاحة:\n"
                response += "• ps4_primary\n• ps4_secondary\n• ps5_primary\n• ps5_secondary"
                send_telegram_message(response, chat_id)
                return
                
            try:
                _, price_type, new_price = parts
                new_price = int(new_price)
                
                if price_type not in ['ps4_primary', 'ps4_secondary', 'ps5_primary', 'ps5_secondary']:
                    response = "❌ نوع السعر غير صحيح!\n\n"
                    response += "الأنواع المتاحة:\n"
                    response += "• ps4_primary\n• ps4_secondary\n• ps5_primary\n• ps5_secondary"
                    send_telegram_message(response, chat_id)
                    return
                
                if new_price <= 0:
                    send_telegram_message("❌ السعر يجب أن يكون أكبر من صفر!", chat_id)
                    return
                    
                prices = load_prices()
                old_price = prices[price_type]
                prices[price_type] = new_price
                
                if save_prices(prices):
                    response = f"✅ تم تحديث السعر بنجاح!\n\n"
                    response += f"🎮 {price_type.replace('_', ' ').title()}\n"
                    response += f"السعر القديم: {old_price} جنيه\n"
                    response += f"السعر الجديد: {new_price} جنيه\n\n"
                    response += f"💰 تم التحديث في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    send_telegram_message(response, chat_id)
                else:
                    send_telegram_message("❌ فشل في حفظ السعر الجديد!", chat_id)
                    
            except ValueError:
                send_telegram_message("❌ السعر يجب أن يكون رقم صحيح!", chat_id)
            except Exception as e:
                logger.error(f"❌ خطأ في setprice: {e}")
                send_telegram_message("❌ حدث خطأ في تحديث السعر!", chat_id)
                
        elif text == '/help':
            response = "📋 قائمة الأوامر المتاحة:\n\n"
            response += "🔹 <code>/start</code> - بدء البوت\n"
            response += "🔹 <code>/prices</code> - عرض جميع الأسعار\n"
            response += "🔹 <code>/editprices</code> - دليل تعديل الأسعار\n"
            response += "🔹 <code>/setprice [نوع] [سعر]</code> - تحديد سعر معين\n"
            response += "🔹 <code>/status</code> - حالة النظام\n"
            response += "🔹 <code>/help</code> - عرض هذه المساعدة\n\n"
            response += "مثال لتغيير السعر:\n"
            response += "<code>/setprice ps4_primary 120</code>"
            send_telegram_message(response, chat_id)
            
        elif text == '/status':
            prices = load_prices()
            response = "📊 حالة النظام:\n\n"
            response += f"🟢 البوت: يعمل بنجاح\n"
            response += f"🟢 قاعدة البيانات: متصلة\n"
            response += f"🟢 الأسعار: محدثة\n"
            response += f"⏰ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            response += f"📈 إجمالي الأسعار: {len(prices)} سعر"
            send_telegram_message(response, chat_id)
            
        else:
            response = f"❌ أمر غير معروف: {text}\n\n"
            response += "أرسل /help لعرض الأوامر المتاحة"
            send_telegram_message(response, chat_id)
            
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الأمر: {e}")
        logger.error(traceback.format_exc())

# Routes
@app.route('/')
def home():
    try:
        prices = load_prices()
        # 🚨 التصحيح: تحويل الأسعار للشكل المطلوب
        platforms = format_prices_for_template(prices)
        return render_template('index.html', platforms=platforms, prices=prices)
    except Exception as e:
        logger.error(f"❌ خطأ في الصفحة الرئيسية: {e}")
        # في حالة الخطأ، إرسال بيانات افتراضية
        default_platforms = {
            'ps4': {'primary': 100, 'secondary': 80},
            'ps5': {'primary': 150, 'secondary': 120}
        }
        default_prices = {
            "ps4_primary": 100,
            "ps4_secondary": 80,
            "ps5_primary": 150,
            "ps5_secondary": 120
        }
        return render_template('index.html', platforms=default_platforms, prices=default_prices)

@app.route('/admin')
def admin():
    try:
        return render_template('admin.html')
    except Exception as e:
        logger.error(f"❌ خطأ في صفحة الأدمن: {e}")
        return f"خطأ في تحميل صفحة الإدارة: {e}", 500

@app.route('/api/prices')
def get_prices():
    try:
        prices = load_prices()
        return jsonify(prices)
    except Exception as e:
        logger.error(f"❌ خطأ في API الأسعار: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/prices', methods=['POST'])
def update_prices():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "لا توجد بيانات"}), 400
            
        if save_prices(data):
            return jsonify({"success": True, "message": "تم تحديث الأسعار بنجاح"})
        else:
            return jsonify({"success": False, "message": "فشل في تحديث الأسعار"}), 500
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الأسعار: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/ping')
def ping():
    return "pong"

# 🚨 الجزء المهم - Webhook للتليجرام
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.json
        logger.info(f"📨 Webhook استلم: {json.dumps(data, ensure_ascii=False)}")
        
        if 'message' in data:
            message = data['message']
            if 'text' in message:
                # معالجة الأمر
                process_telegram_command(message)
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"❌ خطأ في webhook: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# معالجة الأخطاء العامة
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "الصفحة غير موجودة"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ خطأ داخلي: {error}")
    return jsonify({"error": "خطأ داخلي في الخادم"}), 500

# إعداد الـ webhook عند بدء التطبيق
def setup_webhook():
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
        data = {'url': webhook_url}
        
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ تم إعداد Webhook: {webhook_url}")
                return True
            else:
                logger.error(f"❌ فشل إعداد Webhook: {result}")
                return False
        else:
            logger.error(f"❌ فشل طلب Webhook: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في إعداد Webhook: {e}")
        return False

if __name__ == '__main__':
    # إعداد الـ webhook
    setup_webhook()
    
    # بدء التطبيق
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
