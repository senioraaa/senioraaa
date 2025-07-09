from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# تحميل الأسعار من ملف JSON
def load_prices():
    try:
        with open('data/prices.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # أسعار افتراضية إذا لم يوجد الملف
        return {
            "fc25": {
                "ps4": {"primary": 50, "secondary": 30, "full": 80},
                "ps5": {"primary": 60, "secondary": 40, "full": 100},
                "xbox": {"primary": 55, "secondary": 35, "full": 90},
                "pc": {"primary": 45, "secondary": 25, "full": 70}
            }
        }

# حفظ الأسعار في ملف JSON
def save_prices(prices):
    os.makedirs('data', exist_ok=True)
    with open('data/prices.json', 'w', encoding='utf-8') as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)

# الصفحة الرئيسية
@app.route('/')
def index():
    prices = load_prices()
    return render_template('index.html', prices=prices)

# صفحة الإدارة
@app.route('/admin')
def admin():
    prices = load_prices()
    return render_template('admin.html', prices=prices)

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
            prices[game][platform][account_type] = int(new_price)
            save_prices(prices)
            return jsonify({"status": "success", "message": "تم تحديث السعر بنجاح"})
        else:
            return jsonify({"status": "error", "message": "بيانات غير صحيحة"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# إرسال الطلب للتليجرام
@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.json
        game = data.get('game', 'FC 25')
        platform = data.get('platform')
        account_type = data.get('account_type')
        price = data.get('price')
        payment_method = data.get('payment_method')
        customer_phone = data.get('customer_phone')
        
        # إعداد رسالة التليجرام
        telegram_message = f"""
🚨 طلب جديد!
🎮 اللعبة: {game}
📱 المنصة: {platform}
💎 نوع الحساب: {account_type}
💰 السعر: {price} جنيه
💳 طريقة الدفع: {payment_method}
📞 رقم العميل: {customer_phone}
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # هنا تحط التوكن بتاع البوت
        # send_telegram_notification(telegram_message)
        
        # إعداد رسالة الواتساب
        whatsapp_message = f"""مرحباً بك في منصة شهد السنيورة! 🎮

طلب جديد:
🎯 اللعبة: {game}
📱 المنصة: {platform}
💎 نوع الحساب: {account_type}
💰 السعر: {price} جنيه
📞 طريقة الدفع: {payment_method}
⏰ وقت الطلب: {datetime.now().strftime('%H:%M')}

سيتم التواصل معك خلال 15 دقيقة لتأكيد الطلب! 🚀"""
        
        return jsonify({
            "status": "success",
            "whatsapp_message": whatsapp_message,
            "phone": "201234567890"  # ضع رقم الواتساب هنا
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# صفحة الأسئلة الشائعة
@app.route('/faq')
def faq():
    return render_template('faq.html')

# صفحة الشروط والأحكام
@app.route('/terms')
def terms():
    return render_template('terms.html')

# صفحة التواصل
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Dashboard redirect
@app.route('/dashboard')
def dashboard():
    return redirect(url_for('admin'))

# Health check للـ Render
@app.route('/ping')
def ping():
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)
