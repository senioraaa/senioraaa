from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for, flash
import os
import json
import requests
from datetime import datetime
import uuid
from functools import wraps
import logging
from pathlib import Path

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

# إنشاء التطبيق
app = Flask(__name__)

# إضافة secret key للـ sessions
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-it')

# تسجيل الـ admin blueprint (إذا كان متوفراً)
try:
    from admin.admin_routes import admin_bp
    app.register_blueprint(admin_bp)
    logger.info("تم تسجيل admin blueprint بنجاح")
except ImportError:
    logger.warning("admin blueprint غير متوفر")

# إعدادات الأدمن
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# إعدادات الموقع
SITE_NAME = "منصة شهد السنيورة"
WHATSAPP_NUMBER = "201094591331"
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

# === دوال التحقق من صحة البيانات والإصلاح ===

def ensure_directories():
    """إنشاء جميع المجلدات المطلوبة"""
    directories = ['data', 'backups', 'logs', 'static', 'templates']
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"تم إنشاء/التحقق من المجلد: {directory}")
        except Exception as e:
            logger.error(f"خطأ في إنشاء المجلد {directory}: {str(e)}")

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
        
        # التأكد من أن البيانات من نوع dict
        if not isinstance(prices[game], dict):
            prices[game] = default_prices[game]
            logger.warning(f"إصلاح بنية البيانات للعبة: {game}")
        
        for platform in default_prices[game]:
            if platform not in prices[game]:
                prices[game][platform] = default_prices[game][platform]
                logger.info(f"إضافة منصة مفقودة: {platform} للعبة {game}")
            
            # التأكد من أن بيانات المنصة من نوع dict
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
    
    # التحقق من صحة رقم الهاتف - تحسين التحقق
    phone = str(order_data['customer_phone']).strip()
    # إزالة الأحرف غير الرقمية
    phone_digits = ''.join(filter(str.isdigit, phone))
    
    if len(phone_digits) < 10:
        return False, "رقم الهاتف يجب أن يكون 10 أرقام على الأقل"
    
    return True, "البيانات صحيحة"

# === الدوال الأساسية المحسنة ===

def load_prices():
    """تحميل الأسعار من ملف JSON مع التحقق من صحتها"""
    try:
        ensure_directories()
        
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
        ensure_directories()
        
        # التحقق من صحة البيانات قبل الحفظ
        validated_prices = validate_and_fix_prices(prices)
        
        # إنشاء نسخة احتياطية قبل الحفظ
        if os.path.exists('data/prices.json'):
            backup_filename = f"backups/prices_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open('data/prices.json', 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                with open(backup_filename, 'w', encoding='utf-8') as f:
                    f.write(backup_data)
                logger.info(f"تم إنشاء نسخة احتياطية: {backup_filename}")
            except Exception as e:
                logger.warning(f"فشل في إنشاء نسخة احتياطية: {str(e)}")
        
        with open('data/prices.json', 'w', encoding='utf-8') as f:
            json.dump(validated_prices, f, ensure_ascii=False, indent=2)
        
        logger.info("تم حفظ الأسعار بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ في حفظ الأسعار: {str(e)}")
        raise

def load_orders():
    """تحميل الطلبات من ملف JSON مع التحقق من صحتها"""
    try:
        ensure_directories()
        
        if os.path.exists('data/orders.json'):
            with open('data/orders.json', 'r', encoding='utf-8') as f:
                orders = json.load(f)
            
            # التأكد من أن البيانات عبارة عن قائمة
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
    """حفظ الطلبات في ملف JSON مع التحقق من صحتها"""
    try:
        ensure_directories()
        
        # التأكد من أن البيانات عبارة عن قائمة
        if not isinstance(orders, list):
            logger.error("البيانات المراد حفظها ليست قائمة")
            raise ValueError("البيانات يجب أن تكون قائمة")
        
        # إنشاء نسخة احتياطية قبل الحفظ
        if os.path.exists('data/orders.json'):
            backup_filename = f"backups/orders_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open('data/orders.json', 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                with open(backup_filename, 'w', encoding='utf-8') as f:
                    f.write(backup_data)
                logger.info(f"تم إنشاء نسخة احتياطية للطلبات: {backup_filename}")
            except Exception as e:
                logger.warning(f"فشل في إنشاء نسخة احتياطية للطلبات: {str(e)}")
        
        with open('data/orders.json', 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        
        logger.info(f"تم حفظ {len(orders)} طلب بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ في حفظ الطلبات: {str(e)}")
        raise

def generate_order_id():
    """توليد رقم طلب فريد"""
    return f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

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

# === دوال حماية الأدمن ===

def admin_required(f):
    """Decorator للتحقق من تسجيل دخول الأدمن"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# === دوال مساعدة ===

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
    message = f"""
🚨 طلب جديد!

🆔 رقم الطلب: {order_data['order_id']}
🎮 اللعبة: {order_data['game']}
📱 المنصة: {order_data['platform']}
💎 نوع الحساب: {order_data['account_type']}
💰 السعر: {order_data['price']} جنيه
💳 طريقة الدفع: {order_data['payment_method']}
📞 رقم العميل: {order_data['customer_phone']}
💸 رقم الدفع: {order_data.get('payment_number', 'غير محدد')}
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

# === routes إدارة الأدمن ===

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """صفحة تسجيل دخول الأدمن"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            logger.info(f"تم تسجيل دخول الأدمن: {username}")
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            logger.warning(f"محاولة تسجيل دخول فاشلة: {username}")
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """لوحة إدارة الأدمن"""
    try:
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
        
        logger.info("تم تحميل داشبورد الأدمن بنجاح")
        return render_template('admin_dashboard.html', 
                             prices=prices, 
                             orders=orders[:10],  # آخر 10 طلبات
                             stats=stats,
                             site_name=SITE_NAME,
                             maintenance_mode=MAINTENANCE_MODE)
    except Exception as e:
        logger.error(f"خطأ في تحميل داشبورد الأدمن: {str(e)}")
        flash(f'خطأ في تحميل البيانات: {str(e)}', 'error')
        return render_template('admin_dashboard.html', 
                             prices=get_default_prices(), 
                             orders=[],
                             stats={},
                             site_name=SITE_NAME,
                             maintenance_mode=MAINTENANCE_MODE)

@app.route('/admin/prices', methods=['GET', 'POST'])
@admin_required
def admin_prices():
    """صفحة إدارة الأسعار"""
    if request.method == 'POST':
        try:
            # تحديث الأسعار
            new_prices = {
                'fc25': {
                    'PS4': {
                        'Primary': int(request.form.get('ps4_primary', 50)),
                        'Secondary': int(request.form.get('ps4_secondary', 30)),
                        'Full': int(request.form.get('ps4_full', 80))
                    },
                    'PS5': {
                        'Primary': int(request.form.get('ps5_primary', 60)),
                        'Secondary': int(request.form.get('ps5_secondary', 40)),
                        'Full': int(request.form.get('ps5_full', 100))
                    },
                    'Xbox': {
                        'Primary': int(request.form.get('xbox_primary', 55)),
                        'Secondary': int(request.form.get('xbox_secondary', 35)),
                        'Full': int(request.form.get('xbox_full', 90))
                    },
                    'PC': {
                        'Primary': int(request.form.get('pc_primary', 45)),
                        'Secondary': int(request.form.get('pc_secondary', 25)),
                        'Full': int(request.form.get('pc_full', 70))
                    }
                }
            }
            
            # التحقق من صحة الأسعار وحفظها
            old_prices = load_prices()
            validated_prices = validate_and_fix_prices(new_prices)
            save_prices(validated_prices)
            
            logger.info("تم تحديث الأسعار بواسطة الأدمن")
            flash('تم تحديث الأسعار بنجاح', 'success')
            
            # إرسال إشعار التحديث مع تفاصيل التغيير
            if NOTIFICATION_SETTINGS['price_update']:
                changes = []
                for game in validated_prices:
                    for platform in validated_prices[game]:
                        for account_type in validated_prices[game][platform]:
                            old_price = old_prices.get(game, {}).get(platform, {}).get(account_type, 0)
                            new_price = validated_prices[game][platform][account_type]
                            if old_price != new_price:
                                changes.append(f"{game} {platform} {account_type}: {old_price} -> {new_price}")
                
                if changes:
                    update_message = f"🔄 تحديث الأسعار:\n" + "\n".join(changes[:5])  # أول 5 تغييرات
                    send_telegram_message(update_message)
            
            return redirect(url_for('admin_prices'))
            
        except Exception as e:
            logger.error(f"خطأ في حفظ الأسعار: {str(e)}")
            flash(f'خطأ في حفظ الأسعار: {str(e)}', 'error')
    
    # تحميل الأسعار الحالية
    try:
        prices = load_prices()
    except Exception as e:
        logger.error(f"خطأ في تحميل الأسعار: {str(e)}")
        prices = get_default_prices()
        flash(f'تم تحميل الأسعار الافتراضية: {str(e)}', 'warning')
    
    return render_template('admin_prices.html', 
                         prices=prices,
                         site_name=SITE_NAME)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    """صفحة إدارة الطلبات"""
    try:
        orders = load_orders()
        sorted_orders = sorted(orders, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        logger.info(f"تم تحميل {len(orders)} طلب في صفحة الأدمن")
        return render_template('admin_orders.html',
                             orders=sorted_orders,
                             site_name=SITE_NAME)
    except Exception as e:
        logger.error(f"خطأ في تحميل الطلبات: {str(e)}")
        flash(f'خطأ في تحميل الطلبات: {str(e)}', 'error')
        return render_template('admin_orders.html',
                             orders=[],
                             site_name=SITE_NAME)

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    """صفحة إعدادات الأدمن"""
    global MAINTENANCE_MODE, NOTIFICATION_SETTINGS
    
    if request.method == 'POST':
        try:
            # تحديث إعدادات الصيانة
            MAINTENANCE_MODE = request.form.get('maintenance_mode') == 'on'
            
            # تحديث إعدادات الإشعارات
            NOTIFICATION_SETTINGS['new_order'] = request.form.get('notify_new_order') == 'on'
            NOTIFICATION_SETTINGS['price_update'] = request.form.get('notify_price_update') == 'on'
            NOTIFICATION_SETTINGS['customer_message'] = request.form.get('notify_customer_message') == 'on'
            
            logger.info("تم تحديث إعدادات الأدمن")
            flash('تم حفظ الإعدادات بنجاح', 'success')
            
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعدادات: {str(e)}")
            flash(f'خطأ في حفظ الإعدادات: {str(e)}', 'error')
    
    return render_template('admin_settings.html',
                         maintenance_mode=MAINTENANCE_MODE,
                         notification_settings=NOTIFICATION_SETTINGS,
                         site_name=SITE_NAME)

@app.route('/admin/logout')
@admin_required
def admin_logout():
    """تسجيل خروج الأدمن"""
    logger.info("تم تسجيل خروج الأدمن")
    session.pop('admin_logged_in', None)
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('admin_login'))

# === صفحات الموقع ===

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

@app.route('/admin')
def admin():
    """صفحة الإدارة - توجيه للداشبورد"""
    return redirect(url_for('admin_dashboard'))

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

@app.route('/api/get_prices')
def get_prices():
    """API للحصول على الأسعار للموقع الرئيسي"""
    try:
        prices = load_prices()
        return jsonify(prices)
    except Exception as e:
        logger.error(f"خطأ في API الأسعار: {str(e)}")
        return jsonify(get_default_prices())

@app.route('/update_prices', methods=['POST'])
def update_prices():
    """تحديث الأسعار - محسن لحل مشكلة عدم التحديث"""
    try:
        # تحميل الأسعار الحالية
        current_prices = load_prices()
        
        # الحصول على البيانات المرسلة
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "لا توجد بيانات"})
        
        game = data.get('game')
        platform = data.get('platform')
        account_type = data.get('account_type')
        new_price = data.get('price')
        
        # التحقق من صحة البيانات
        if not all([game, platform, account_type, new_price]):
            return jsonify({"status": "error", "message": "بيانات غير صحيحة أو مفقودة"})
        
        try:
            new_price = int(new_price)
            if new_price < 0:
                return jsonify({"status": "error", "message": "السعر لا يمكن أن يكون سالباً"})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "السعر يجب أن يكون رقماً صحيحاً"})
        
        # الحصول على السعر القديم
        old_price = current_prices.get(game, {}).get(platform, {}).get(account_type, 0)
        
        # تحديث السعر
        if game not in current_prices:
            current_prices[game] = {}
        if platform not in current_prices[game]:
            current_prices[game][platform] = {}
        
        current_prices[game][platform][account_type] = new_price
        
        # حفظ الأسعار المحدثة
        save_prices(current_prices)
        
        logger.info(f"تم تحديث سعر {game} {platform} {account_type} من {old_price} إلى {new_price}")
        
        # إرسال إشعار التحديث
        if NOTIFICATION_SETTINGS['price_update'] and old_price != new_price:
            send_price_update(game, platform, account_type, old_price, new_price)
        
        return jsonify({
            "status": "success", 
            "message": "تم تحديث السعر بنجاح",
            "old_price": old_price,
            "new_price": new_price,
            "game": game,
            "platform": platform,
            "account_type": account_type
        })
        
    except Exception as e:
        logger.error(f"خطأ في تحديث الأسعار: {str(e)}")
        return jsonify({"status": "error", "message": f"خطأ في تحديث السعر: {str(e)}"})

@app.route('/send_order', methods=['POST'])
def send_order():
    """إرسال الطلب للتليجرام والواتساب"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "لا توجد بيانات"})
        
        # التحقق من صحة البيانات
        is_valid, message = validate_order_data(data)
        if not is_valid:
            logger.warning(f"بيانات طلب غير صحيحة: {message}")
            return jsonify({"status": "error", "message": message})
        
        order_id = generate_order_id()
        
        order_data = {
            'order_id': order_id,
            'game': data.get('game', 'FC 25'),
            'platform': data.get('platform'),
            'account_type': data.get('account_type'),
            'price': int(data.get('price')),
            'payment_method': data.get('payment_method'),
            'customer_phone': data.get('customer_phone'),
            'payment_number': data.get('payment_number', ''),
            'timestamp': datetime.now().strftime(DATETIME_FORMAT),
            'date': datetime.now().strftime(DATE_FORMAT),
            'status': 'pending'
        }
        
        # حفظ الطلب
        orders = load_orders()
        orders.append(order_data)
        save_orders(orders)
        
        logger.info(f"تم إنشاء طلب جديد: {order_id}")
        
        # إرسال إشعار التليجرام
        if NOTIFICATION_SETTINGS['new_order']:
            telegram_result = send_order_notification(order_data)
            if telegram_result.get('status') != 'success':
                logger.warning(f"خطأ في إرسال إشعار التليجرام: {telegram_result.get('message')}")
        
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
        logger.error(f"خطأ في إرسال الطلب: {str(e)}")
        return jsonify({"status": "error", "message": f"خطأ في إرسال الطلب: {str(e)}"})

@app.route('/test_telegram', methods=['POST'])
def test_telegram():
    """اختبار بوت التليجرام"""
    try:
        data = request.get_json()
        message = data.get('message', 'رسالة تجريبية') if data else 'رسالة تجريبية'
        result = send_test_message(message)
        return jsonify(result)
    except Exception as e:
        logger.error(f"خطأ في اختبار التليجرام: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/send_customer_message', methods=['POST'])
def send_customer_message_route():
    """إرسال رسالة عميل"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "لا توجد بيانات"})
        
        name = data.get('name')
        phone = data.get('phone')
        subject = data.get('subject')
        message = data.get('message')
        
        if not all([name, phone, subject, message]):
            return jsonify({"status": "error", "message": "يرجى ملء جميع الحقول"})
        
        if NOTIFICATION_SETTINGS['customer_message']:
            telegram_result = send_customer_message(name, phone, subject, message)
            
            if telegram_result.get('status') == 'success':
                logger.info(f"تم إرسال رسالة عميل من {name}")
                return jsonify({"status": "success", "message": "تم إرسال الرسالة بنجاح"})
            else:
                return jsonify({"status": "error", "message": telegram_result.get('message')})
        else:
            return jsonify({"status": "success", "message": "تم إرسال الرسالة بنجاح"})
            
    except Exception as e:
        logger.error(f"خطأ في إرسال رسالة العميل: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_stats')
def get_stats():
    """الحصول على إحصائيات الطلبات"""
    try:
        orders = load_orders()
        today = datetime.now().strftime('%Y-%m-%d')
        
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
        
        # إحصائيات طرق الدفع
        payment_method_stats = {}
        for order in today_orders:
            payment_method = order.get('payment_method', 'Unknown')
            payment_method_stats[payment_method] = payment_method_stats.get(payment_method, 0) + 1
        
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
            'payment_method_stats': payment_method_stats,
            'ps4_orders': platform_stats.get('PS4', 0),
            'ps5_orders': platform_stats.get('PS5', 0),
            'xbox_orders': platform_stats.get('Xbox', 0),
            'pc_orders': platform_stats.get('PC', 0),
            'average_order_value': sum(order.get('price', 0) for order in today_orders) / len(today_orders) if today_orders else 0
        }
        
        return jsonify({"status": "success", "stats": stats})
        
    except Exception as e:
        logger.error(f"خطأ في الحصول على الإحصائيات: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/get_orders')
def get_orders():
    """الحصول على قائمة الطلبات"""
    try:
        orders = load_orders()
        sorted_orders = sorted(orders, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # إضافة ترقيم للطلبات
        for i, order in enumerate(sorted_orders):
            order['index'] = i + 1
        
        return jsonify({"status": "success", "orders": sorted_orders})
    except Exception as e:
        logger.error(f"خطأ في الحصول على الطلبات: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    """تحديث حالة الطلب"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "لا توجد بيانات"})
        
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        if not order_id or not new_status:
            return jsonify({"status": "error", "message": "بيانات غير صحيحة"})
        
        orders = load_orders()
        order_found = False
        
        for order in orders:
            if order.get('order_id') == order_id:
                old_status = order.get('status', 'pending')
                order['status'] = new_status
                order['updated_at'] = datetime.now().strftime(DATETIME_FORMAT)
                order_found = True
                
                # إرسال إشعار تحديث الحالة
                if NOTIFICATION_SETTINGS['new_order']:
                    status_message = f"""
📋 تحديث حالة الطلب

🆔 رقم الطلب: {order_id}
📊 الحالة القديمة: {old_status}
🔄 الحالة الجديدة: {new_status}
⏰ وقت التحديث: {order['updated_at']}
"""
                    send_telegram_message(status_message)
                
                break
        
        if not order_found:
            return jsonify({"status": "error", "message": "الطلب غير موجود"})
        
        save_orders(orders)
        logger.info(f"تم تحديث حالة الطلب {order_id} إلى {new_status}")
        return jsonify({"status": "success", "message": "تم تحديث حالة الطلب بنجاح"})
            
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة الطلب: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/delete_order', methods=['POST'])
def delete_order():
    """حذف طلب"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "لا توجد بيانات"})
        
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({"status": "error", "message": "رقم الطلب مطلوب"})
        
        orders = load_orders()
        original_count = len(orders)
        
        # حذف الطلب
        orders = [order for order in orders if order.get('order_id') != order_id]
        
        if len(orders) == original_count:
            return jsonify({"status": "error", "message": "الطلب غير موجود"})
        
        save_orders(orders)
        logger.info(f"تم حذف الطلب {order_id}")
        return jsonify({"status": "success", "message": "تم حذف الطلب بنجاح"})
            
    except Exception as e:
        logger.error(f"خطأ في حذف الطلب: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/toggle_maintenance', methods=['POST'])
def toggle_maintenance():
    """تبديل وضع الصيانة"""
    try:
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = not MAINTENANCE_MODE
        status = "تم تفعيل" if MAINTENANCE_MODE else "تم إلغاء"
        logger.info(f"{status} وضع الصيانة")
        
        # إرسال إشعار تغيير وضع الصيانة
        maintenance_message = f"""
🔧 تغيير وضع الصيانة

🔄 الحالة: {status} وضع الصيانة
⏰ الوقت: {datetime.now().strftime(DATETIME_FORMAT)}
"""
        send_telegram_message(maintenance_message)
        
        return jsonify({"status": "success", "message": f"{status} وضع الصيانة", "maintenance_mode": MAINTENANCE_MODE})
    except Exception as e:
        logger.error(f"خطأ في تبديل وضع الصيانة: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/dashboard')
def dashboard():
    """Dashboard redirect"""
    return redirect(url_for('admin_dashboard'))

@app.route('/api/prices')
def api_prices():
    """API للحصول على الأسعار"""
    try:
        prices = load_prices()
        return jsonify({"status": "success", "prices": prices})
    except Exception as e:
        logger.error(f"خطأ في API الأسعار: {str(e)}")
        return jsonify({"status": "error", "message": str(e), "prices": get_default_prices()})

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
        logger.error(f"خطأ في API معلومات اللعبة: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/export_orders')
@admin_required
def export_orders():
    """تصدير الطلبات كملف JSON"""
    try:
        orders = load_orders()
        
        # إنشاء ملف التصدير
        export_data = {
            'export_date': datetime.now().strftime(DATETIME_FORMAT),
            'total_orders': len(orders),
            'orders': orders
        }
        
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = f'attachment; filename=orders_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        logger.info("تم تصدير الطلبات")
        return response
        
    except Exception as e:
        logger.error(f"خطأ في تصدير الطلبات: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/backup_data')
@admin_required
def backup_data():
    """إنشاء نسخة احتياطية من جميع البيانات"""
    try:
        backup_data = {
            'backup_date': datetime.now().strftime(DATETIME_FORMAT),
            'prices': load_prices(),
            'orders': load_orders(),
            'site_settings': {
                'site_name': SITE_NAME,
                'whatsapp_number': WHATSAPP_NUMBER,
                'email_info': EMAIL_INFO,
                'maintenance_mode': MAINTENANCE_MODE,
                'notification_settings': NOTIFICATION_SETTINGS
            }
        }
        
        # حفظ النسخة الاحتياطية
        backup_filename = f"backups/full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"تم إنشاء نسخة احتياطية شاملة: {backup_filename}")
        
        response = jsonify(backup_data)
        response.headers['Content-Disposition'] = f'attachment; filename={backup_filename.split("/")[-1]}'
        
        return response
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

# === معالجات الأخطاء ===

@app.errorhandler(404)
def not_found_error(error):
    """معالج الأخطاء 404"""
    logger.warning(f"صفحة غير موجودة: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """معالج الأخطاء 500"""
    logger.error(f"خطأ داخلي: {str(error)}")
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden_error(error):
    """معالج الأخطاء 403"""
    logger.warning(f"وصول مرفوض: {request.url}")
    return render_template('403.html'), 403

@app.route('/ping')
def ping():
    """Health check للـ Render"""
    return jsonify({
        "status": "OK",
        "timestamp": datetime.now().strftime(DATETIME_FORMAT),
        "maintenance_mode": MAINTENANCE_MODE
    }), 200

@app.route('/health')
def health():
    """Health check شامل"""
    try:
        # فحص الملفات الأساسية
        prices_status = "OK" if os.path.exists('data/prices.json') else "MISSING"
        orders_status = "OK" if os.path.exists('data/orders.json') else "MISSING"
        
        # فحص المجلدات
        directories_status = {}
        for directory in ['data', 'backups', 'logs']:
            directories_status[directory] = "OK" if os.path.exists(directory) else "MISSING"
        
        health_data = {
            "status": "OK",
            "timestamp": datetime.now().strftime(DATETIME_FORMAT),
            "files": {
                "prices": prices_status,
                "orders": orders_status
            },
            "directories": directories_status,
            "maintenance_mode": MAINTENANCE_MODE,
            "telegram_configured": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        }
        
        return jsonify(health_data), 200
        
    except Exception as e:
        logger.error(f"خطأ في فحص الصحة: {str(e)}")
        return jsonify({
            "status": "ERROR",
            "message": str(e),
            "timestamp": datetime.now().strftime(DATETIME_FORMAT)
        }), 500

# === إعداد النظام ===

@app.before_first_request
def initialize_app():
    """إعداد النظام عند بدء التشغيل لأول مرة"""
    try:
        logger.info("🚀 بدء تهيئة التطبيق...")
        
        # إنشاء جميع المجلدات المطلوبة
        ensure_directories()
        
        # التحقق من وجود ملف الأسعار وإنشاؤه إذا لم يكن موجوداً
        if not os.path.exists('data/prices.json'):
            default_prices = get_default_prices()
            save_prices(default_prices)
            logger.info("تم إنشاء ملف الأسعار الافتراضي")
        else:
            # التحقق من صحة بيانات الأسعار الموجودة
            try:
                prices = load_prices()
                validated_prices = validate_and_fix_prices(prices)
                if prices != validated_prices:
                    save_prices(validated_prices)
                    logger.info("تم إصلاح وتحديث بيانات الأسعار")
            except Exception as e:
                logger.error(f"خطأ في التحقق من بيانات الأسعار: {str(e)}")
                save_prices(get_default_prices())
        
        # التحقق من وجود ملف الطلبات وإنشاؤه إذا لم يكن موجوداً
        if not os.path.exists('data/orders.json'):
            save_orders([])
            logger.info("تم إنشاء ملف الطلبات الفارغ")
        
        logger.info("✅ تم تهيئة التطبيق بنجاح")
        
    except Exception as e:
        logger.error(f"❌ خطأ في تهيئة التطبيق: {str(e)}")

# === بدء التطبيق ===

if __name__ == '__main__':
    # تهيئة التطبيق
    try:
        logger.info("🔧 تهيئة التطبيق...")
        ensure_directories()
        
        # التحقق من الإعدادات
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("⚠️ إعدادات التليجرام غير مكتملة")
        else:
            logger.info("✅ إعدادات التليجرام مكتملة")
        
        # إعداد البورت
        port = int(os.environ.get('PORT', 5000))
        
        # رسائل بدء التشغيل
        logger.info(f"🚀 {SITE_NAME} يعمل الآن على البورت {port}!")
        logger.info(f"🌐 الوضع: {'تطوير' if DEBUG_MODE else 'إنتاج'}")
        logger.info(f"🔧 الصيانة: {'مفعلة' if MAINTENANCE_MODE else 'معطلة'}")
        logger.info(f"👤 أدمن: {ADMIN_USERNAME}")
        logger.info(f"📱 واتساب: {WHATSAPP_NUMBER}")
        
        # إرسال رسالة بدء التشغيل للتليجرام
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            startup_message = f"""
🚀 تم تشغيل {SITE_NAME}

🌐 الوضع: {'تطوير' if DEBUG_MODE else 'إنتاج'}
🔧 الصيانة: {'مفعلة' if MAINTENANCE_MODE else 'معطلة'}
👤 أدمن: {ADMIN_USERNAME}
📱 واتساب: {WHATSAPP_NUMBER}
⏰ الوقت: {datetime.now().strftime(DATETIME_FORMAT)}
"""
            send_telegram_message(startup_message)
        
        # تشغيل التطبيق
        app.run(
            host='0.0.0.0',
            port=port,
            debug=DEBUG_MODE,
            use_reloader=False  # منع إعادة التشغيل المتكرر
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء التشغيل: {str(e)}")
        raise
