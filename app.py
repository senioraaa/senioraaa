from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from datetime import datetime
import requests
from telegram_bot import send_order_notification, send_test_message, send_price_update, send_customer_message
from config import *
import uuid

app = Flask(__name__)
app.secret_key = get_env_setting('SECRET_KEY', 'your-secret-key-here')

# تحميل الأسعار من ملف JSON
def load_prices():
    try:
        with open('data/prices.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_PRICES

# حفظ الأسعار في ملف JSON
def save_prices(prices):
    os.makedirs('data', exist_ok=True)
    with open('data/prices.json', 'w', encoding='utf-8') as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)

# تحميل الطلبات من ملف JSON
def load_orders():
    try:
        with open('data/orders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# حفظ الطلبات في ملف JSON
def save_orders(orders):
    os.makedirs('data', exist_ok=True)
    with open('data/orders.json', 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

# توليد رقم طلب فريد
def generate_order_id():
    return f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

# الصفحة الرئيسية
@app.route('/')
def index():
    if MAINTENANCE_MODE:
        return render_template('maintenance.html', message=MAINTENANCE_MESSAGE)
    
    prices = load_prices()
    return render_template('index.html', 
                         prices=prices, 
                         site_name=SITE_NAME,
                         whatsapp_number=WHATSAPP_NUMBER)

# صفحة الإدارة
@app.route('/admin')
def admin():
    prices = load_prices()
    orders = load_orders()
    
    # إحصائيات بسيطة
    today = datetime.now().strftime('%Y-%m-%d')
    today_orders = [order for order in orders if order.get('date', '').startswith(today)]
    
    stats = {
        'orders_today': len(today_orders),
        'revenue_today': sum(order.get('price', 0) for order in today_orders),
        'total_orders': len(orders),
        'popular_platform': 'PS5',  # يمكن حسابها من البيانات
        'popular_account_type': 'Primary'  # يمكن حسابها من البيانات
    }
    
    return render_template('admin.html', 
                         prices=prices, 
                         stats=stats,
                         site_name=SITE_NAME)

# صفحة الأسئلة الشائعة
@app.route('/faq')
def faq():
    return render_template('faq.html', site_name=SITE_NAME)

# صفحة الشروط والأحكام
@app.route('/terms')
def terms():
    return render_template('terms.html', site_name=SITE_NAME)

# صفحة التواصل
@app.route('/contact')
def contact():
    return render_template('contact.html', 
                         site_name=SITE_NAME,
                         whatsapp_number=WHATSAPP_NUMBER,
                         email_info=EMAIL_INFO)

# تحديث الأسعار
@app.route('/update_prices', methods=['POST'])
def update_prices():
    try:
        prices = load_prices()
        game = request.json.get('game')
        platform = request.json.get('platform')
        account_type = request.json.get('account_type')
        new_price = request.json.get('price')
        
        if game and platform and account_type and new_price:
            # حفظ السعر القديم للإشعار
            old_price = prices.get(game, {}).get(platform, {}).get(account_type, 0)
            
            # تحديث السعر
            if game not in prices:
                prices[game] = {}
            if platform not in prices[game]:
                prices[game][platform] = {}
            
            prices[game][platform][account_type] = int(new_price)
            save_prices(prices)
            
            # إرسال إشعار تحديث السعر للتليجرام
            if NOTIFICATION_SETTINGS['price_update']:
                send_price_update(game, platform, account_type, old_price, int(new_price))
            
            return jsonify({"status": "success", "message": "تم تحديث السعر بنجاح"})
        else:
            return jsonify({"status": "error", "message": "بيانات غير صحيحة"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# إرسال الطلب للتليجرام والواتساب
@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.json
        
        # إنشاء رقم طلب فريد
        order_id = generate_order_id()
        
        # بيانات الطلب
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
        
        # حفظ الطلب في قاعدة البيانات
        orders = load_orders()
        orders.append(order_data)
        save_orders(orders)
        
        # إرسال إشعار للتليجرام
        if NOTIFICATION_SETTINGS['new_order']:
            telegram_result = send_order_notification(order_data)
            if telegram_result.get('status') != 'success':
                print(f"خطأ في إرسال إشعار التليجرام: {telegram_result.get('message')}")
        
        # إعداد رسالة الواتساب
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

# اختبار بوت التليجرام
@app.route('/test_telegram', methods=['POST'])
def test_telegram():
    try:
        message = request.json.get('message', 'رسالة تجريبية')
        result = send_test_message(message)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# إرسال رسالة عميل
@app.route('/send_customer_message', methods=['POST'])
def send_customer_message_route():
    try:
        data = request.json
        name = data.get('name')
        phone = data.get('phone')
        subject = data.get('subject')
        message = data.get('message')
        
        if name and phone and subject and message:
            # إرسال للتليجرام
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

# الحصول على إحصائيات الطلبات
@app.route('/get_stats')
def get_stats():
    try:
        orders = load_orders()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # إحصائيات اليوم
        today_orders = [order for order in orders if order.get('date', '').startswith(today)]
        
        # إحصائيات المنصات
        platform_stats = {}
        for order in today_orders:
            platform = order.get('platform', 'Unknown')
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
        
        # إحصائيات أنواع الحسابات
        account_type_stats = {}
        for order in today_orders:
            account_type = order.get('account_type', 'Unknown')
            account_type_stats[account_type] = account_type_stats.get(account_type, 0) + 1
        
        # أشهر منصة ونوع حساب
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

# الحصول على قائمة الطلبات
@app.route('/get_orders')
def get_orders():
    try:
        orders = load_orders()
        # ترتيب الطلبات حسب التاريخ (الأحدث أولاً)
        sorted_orders = sorted(orders, key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({"status": "success", "orders": sorted_orders})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# تحديث حالة الطلب
@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    try:
        data = request.json
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        if order_id and new_status:
            orders = load_orders()
            
            # البحث عن الطلب وتحديث حالته
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

# صفحة الصيانة
@app.route('/maintenance')
def maintenance():
    return render_template('maintenance.html', message=MAINTENANCE_MESSAGE)

# تبديل وضع الصيانة
@app.route('/toggle_maintenance', methods=['POST'])
def toggle_maintenance():
    try:
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = not MAINTENANCE_MODE
        status = "تم تفعيل" if MAINTENANCE_MODE else "تم إلغاء"
        return jsonify({"status": "success", "message": f"{status} وضع الصيانة"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# Dashboard redirect
@app.route('/dashboard')
def dashboard():
    return redirect(url_for('admin'))

# API للحصول على الأسعار
@app.route('/api/prices')
def api_prices():
    try:
        prices = load_prices()
        return jsonify({"status": "success", "prices": prices})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# API للحصول على معلومات اللعبة
@app.route('/api/game/<game_id>')
def api_game_info(game_id):
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

# معالج الأخطاء 404
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# معالج الأخطاء 500
@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Health check للـ Render
@app.route('/ping')
def ping():
    return "OK", 200

# إعداد النظام عند بدء التشغيل
@app.before_first_request
def setup_system():
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
    
    print(f"🚀 {SITE_NAME} يعمل الآن!")
    print(f"🌐 الوضع: {'تطوير' if DEBUG_MODE else 'إنتاج'}")
    print(f"🔧 الصيانة: {'مفعلة' if MAINTENANCE_MODE else 'معطلة'}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG_MODE
    )
