from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for
import os
import json
import requests
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# إعدادات الموقع
SITE_NAME = "منصة شهد السنيورة"
WHATSAPP_NUMBER = "01234567890"
EMAIL_INFO = "info@senioraa.com"
MAINTENANCE_MODE = False
MAINTENANCE_MESSAGE = "الموقع تحت الصيانة"
DEBUG_MODE = False
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

# إعدادات التليجرام
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# إعدادات الإشعارات
NOTIFICATION_SETTINGS = {
    'new_order': True,
    'price_update': True,
    'customer_message': True
}

# الألعاب المدعومة
SUPPORTED_GAMES = {
    'fc25': {
        'name': 'EA Sports FC 25',
        'description': 'أحدث إصدار من لعبة كرة القدم',
        'platforms': ['PS4', 'PS5', 'Xbox', 'PC']
    }
}

# الأسعار الافتراضية
DEFAULT_PRICES = {
    'fc25': {
        'PS4': {'Primary': 50, 'Secondary': 30, 'Full': 80},
        'PS5': {'Primary': 60, 'Secondary': 40, 'Full': 100},
        'Xbox': {'Primary': 55, 'Secondary': 35, 'Full': 90},
        'PC': {'Primary': 45, 'Secondary': 25, 'Full': 70}
    }
}

# قوالب الرسائل
MESSAGE_TEMPLATES = {
    'order_confirmation': """
🎮 طلب جديد من منصة شهد السنيورة

📱 اللعبة: {game}
🎯 المنصة: {platform}
💎 نوع الحساب: {account_type}
💰 السعر: {price} جنيه
💳 طريقة الدفع: {payment_method}
⏰ وقت الطلب: {timestamp}

سيتم التواصل معك خلال 15 دقيقة! 🚀
"""
}

# === دوال مساعدة ===

def send_telegram_message(message):
    """إرسال رسالة للتليجرام"""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return {"status": "error", "message": "إعدادات التليجرام غير مكتملة"}
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return {"status": "success", "message": "تم إرسال الرسالة بنجاح"}
        else:
            return {"status": "error", "message": f"خطأ في إرسال الرسالة: {response.status_code}"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def send_order_notification(order_data):
    """إرسال إشعار طلب جديد"""
    message = f"""
🚨 طلب جديد!

🆔 رقم الطلب: {order_data['order_id']}
🎮 اللعبة: {order_data['game']}
📱 المنصة: {order_data['platform']}
💎 نوع الحساب: {order_data['account_type']}
💰 السعر: {order_data['price']} جنيه
💳 طريقة الدفع: {order_data['payment_method']}
📞 رقم العميل: {order_data['customer_phone']}
💸 رقم الدفع: {order_data['payment_number']}
⏰ الوقت: {order_data['timestamp']}
"""
    return send_telegram_message(message)

def send_test_message(message):
    """إرسال رسالة تجريبية"""
    test_message = f"🧪 رسالة تجريبية:\n{message}"
    return send_telegram_message(test_message)

def send_price_update(game, platform, account_type, old_price, new_price):
    """إرسال إشعار تحديث السعر"""
    message = f"""
💰 تحديث سعر!

🎮 اللعبة: {game}
📱 المنصة: {platform}
💎 نوع الحساب: {account_type}
📉 السعر القديم: {old_price} جنيه
📈 السعر الجديد: {new_price} جنيه
⏰ وقت التحديث: {datetime.now().strftime(DATETIME_FORMAT)}
"""
    return send_telegram_message(message)

def send_customer_message(name, phone, subject, message):
    """إرسال رسالة عميل"""
    customer_message = f"""
📨 رسالة جديدة من عميل!

👤 الاسم: {name}
📞 الهاتف: {phone}
📝 الموضوع: {subject}
💬 الرسالة: {message}
⏰ الوقت: {datetime.now().strftime(DATETIME_FORMAT)}
"""
    return send_telegram_message(customer_message)

# === الدوال الأساسية ===

def load_prices():
    """تحميل الأسعار من ملف JSON"""
    try:
        with open('data/prices.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_PRICES

def save_prices(prices):
    """حفظ الأسعار في ملف JSON"""
    os.makedirs('data', exist_ok=True)
    with open('data/prices.json', 'w', encoding='utf-8') as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)

def load_orders():
    """تحميل الطلبات من ملف JSON"""
    try:
        with open('data/orders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_orders(orders):
    """حفظ الطلبات في ملف JSON"""
    os.makedirs('data', exist_ok=True)
    with open('data/orders.json', 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def generate_order_id():
    """توليد رقم طلب فريد"""
    return f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

# === صفحات الموقع ===

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    if MAINTENANCE_MODE:
        return render_template('maintenance.html', message=MAINTENANCE_MESSAGE)
    
    prices = load_prices()
    return render_template('index.html', 
                         prices=prices, 
                         site_name=SITE_NAME,
                         whatsapp_number=WHATSAPP_NUMBER)

@app.route('/admin')
def admin():
    """صفحة الإدارة"""
    prices = load_prices()
    orders = load_orders()
    
    # إحصائيات بسيطة
    today = datetime.now().strftime('%Y-%m-%d')
    today_orders = [order for order in orders if order.get('date', '').startswith(today)]
    
    stats = {
        'orders_today': len(today_orders),
        'revenue_today': sum(order.get('price', 0) for order in today_orders),
        'total_orders': len(orders),
        'popular_platform': 'PS5',
        'popular_account_type': 'Primary'
    }
    
    return render_template('admin.html', 
                         prices=prices, 
                         stats=stats,
                         site_name=SITE_NAME)

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

# === API Routes ===

@app.route('/update_prices', methods=['POST'])
def update_prices():
    """تحديث الأسعار"""
    try:
        prices = load_prices()
        game = request.json.get('game')
        platform = request.json.get('platform')
        account_type = request.json.get('account_type')
        new_price = request.json.get('price')
        
        if game and platform and account_type and new_price:
            old_price = prices.get(game, {}).get(platform, {}).get(account_type, 0)
            
            if game not in prices:
                prices[game] = {}
            if platform not in prices[game]:
                prices[game][platform] = {}
            
            prices[game][platform][account_type] = int(new_price)
            save_prices(prices)
            
            if NOTIFICATION_SETTINGS['price_update']:
                send_price_update(game, platform, account_type, old_price, int(new_price))
            
            return jsonify({"status": "success", "message": "تم تحديث السعر بنجاح"})
        else:
            return jsonify({"status": "error", "message": "بيانات غير صحيحة"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/send_order', methods=['POST'])
def send_order():
    """إرسال الطلب للتليجرام والواتساب"""
    try:
        data = request.json
        
        order_id = generate_order_id()
        
        order_data = {
            'order_id': order_id,
            'game': data.get('game', 'FC 25'),
            'platform': data.get('platform'),
            'account_type': data.get('account_type'),
            'price': data.get('price'),
            'payment_method': data.get('payment_method'),
            'customer_phone': data.get('customer_phone'),
            'payment_number': data.get('payment_number'),
            'timestamp': datetime.now().strftime(DATETIME_FORMAT),
            'date': datetime.now().strftime(DATE_FORMAT),
            'status': 'pending'
        }
        
        orders = load_orders()
        orders.append(order_data)
        save_orders(orders)
        
        if NOTIFICATION_SETTINGS['new_order']:
            telegram_result = send_order_notification(order_data)
            if telegram_result.get('status') != 'success':
                print(f"خطأ في إرسال إشعار التليجرام: {telegram_result.get('message')}")
        
        whatsapp_message = MESSAGE_TEMPLATES['order_confirmation'].format(
            game=order_data['game'],
            platform=order_data['platform'],
            account_type=order_data['account_type'],
            price=order_data['price'],
            payment_method=order_data['payment_method'],
            timestamp=order_data['timestamp']
        )
        
        return jsonify({
            "status": "success",
            "whatsapp_message": whatsapp_message,
            "phone": WHATSAPP_NUMBER,
            "order_id": order_id
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/test_telegram', methods=['POST'])
def test_telegram():
    """اختبار بوت التليجرام"""
    try:
        message = request.json.get('message', 'رسالة تجريبية')
        result = send_test_message(message)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/send_customer_message', methods=['POST'])
def send_customer_message_route():
    """إرسال رسالة عميل"""
    try:
        data = request.json
        name = data.get('name')
        phone = data.get('phone')
        subject = data.get('subject')
        message = data.get('message')
        
        if name and phone and subject and message:
            if NOTIFICATION_SETTINGS['customer_message']:
                telegram_result = send_customer_message(name, phone, subject, message)
                
                if telegram_result.get('status') == 'success':
                    return jsonify({"status": "success", "message": "تم إرسال الرسالة بنجاح"})
                else:
                    return jsonify({"status": "error", "message": telegram_result.get('message')})
            else:
                return jsonify({"status": "success", "message": "تم إرسال الرسالة بنجاح"})
        else:
            return jsonify({"status": "error", "message": "يرجى ملء جميع الحقول"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_stats')
def get_stats():
    """الحصول على إحصائيات الطلبات"""
    try:
        orders = load_orders()
        today = datetime.now().strftime('%Y-%m-%d')
        
        today_orders = [order for order in orders if order.get('date', '').startswith(today)]
        
        platform_stats = {}
        for order in today_orders:
            platform = order.get('platform', 'Unknown')
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
        
        account_type_stats = {}
        for order in today_orders:
            account_type = order.get('account_type', 'Unknown')
            account_type_stats[account_type] = account_type_stats.get(account_type, 0) + 1
        
        popular_platform = max(platform_stats.items(), key=lambda x: x[1])[0] if platform_stats else 'PS5'
        popular_account_type = max(account_type_stats.items(), key=lambda x: x[1])[0] if account_type_stats else 'Primary'
        
        stats = {
            'orders_today': len(today_orders),
            'revenue_today': sum(order.get('price', 0) for order in today_orders),
            'total_orders': len(orders),
            'popular_platform': popular_platform,
            'popular_account_type': popular_account_type,
            'platform_stats': platform_stats,
            'account_type_stats': account_type_stats,
            'ps4_orders': platform_stats.get('PS4', 0),
            'ps5_orders': platform_stats.get('PS5', 0),
            'xbox_orders': platform_stats.get('Xbox', 0),
            'pc_orders': platform_stats.get('PC', 0)
        }
        
        return jsonify({"status": "success", "stats": stats})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_orders')
def get_orders():
    """الحصول على قائمة الطلبات"""
    try:
        orders = load_orders()
        sorted_orders = sorted(orders, key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({"status": "success", "orders": sorted_orders})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    """تحديث حالة الطلب"""
    try:
        data = request.json
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        if order_id and new_status:
            orders = load_orders()
            
            for order in orders:
                if order.get('order_id') == order_id:
                    order['status'] = new_status
                    order['updated_at'] = datetime.now().strftime(DATETIME_FORMAT)
                    break
            
            save_orders(orders)
            return jsonify({"status": "success", "message": "تم تحديث حالة الطلب"})
        else:
            return jsonify({"status": "error", "message": "بيانات غير صحيحة"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/toggle_maintenance', methods=['POST'])
def toggle_maintenance():
    """تبديل وضع الصيانة"""
    try:
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = not MAINTENANCE_MODE
        status = "تم تفعيل" if MAINTENANCE_MODE else "تم إلغاء"
        return jsonify({"status": "success", "message": f"{status} وضع الصيانة"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/dashboard')
def dashboard():
    """Dashboard redirect"""
    return redirect(url_for('admin'))

@app.route('/api/prices')
def api_prices():
    """API للحصول على الأسعار"""
    try:
        prices = load_prices()
        return jsonify({"status": "success", "prices": prices})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/game/<game_id>')
def api_game_info(game_id):
    """API للحصول على معلومات اللعبة"""
    try:
        if game_id in SUPPORTED_GAMES:
            game_info = SUPPORTED_GAMES[game_id]
            prices = load_prices()
            game_prices = prices.get(game_id, {})
            
            return jsonify({
                "status": "success",
                "game_info": game_info,
                "prices": game_prices
            })
        else:
            return jsonify({"status": "error", "message": "اللعبة غير موجودة"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# === معالجات الأخطاء ===

@app.errorhandler(404)
def not_found_error(error):
    """معالج الأخطاء 404"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """معالج الأخطاء 500"""
    return render_template('500.html'), 500

@app.route('/ping')
def ping():
    """Health check للـ Render"""
    return "OK", 200

# === إعداد النظام ===

@app.before_request
def before_request():
    """إعداد النظام عند بدء التشغيل"""
    # إنشاء المجلدات المطلوبة
    os.makedirs('data', exist_ok=True)
    os.makedirs('backups', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # التحقق من وجود ملف الأسعار
    if not os.path.exists('data/prices.json'):
        save_prices(DEFAULT_PRICES)
    
    # التحقق من وجود ملف الطلبات
    if not os.path.exists('data/orders.json'):
        save_orders([])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 {SITE_NAME} يعمل الآن على البورت {port}!")
    print(f"🌐 الوضع: {'تطوير' if DEBUG_MODE else 'إنتاج'}")
    print(f"🔧 الصيانة: {'مفعلة' if MAINTENANCE_MODE else 'معطلة'}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG_MODE
    )
