import os
import random
import string
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import hashlib
import time
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from sqlalchemy import text # <--- هذا هو السطر الذي تم إضافته لإصلاح مشكلة Textual SQL expression

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# إعداد المهام الدورية لـ APScheduler
scheduler = BackgroundScheduler()

def scheduled_cleanup():
    """مهمة دورية لتنظيف البيانات"""
    with app.app_context():
        cleanup_old_verification_codes()
        app.logger.info("Scheduled cleanup completed")

# تشغيل التنظيف كل 6 ساعات
scheduler.add_job(
    func=scheduled_cleanup,
    trigger=IntervalTrigger(hours=6),
    id='cleanup_job',
    name='Clean up expired verification codes',
    replace_existing=True
)

# بدء المجدول
scheduler.start()

# إيقاف المجدول عند إغلاق التطبيق
atexit.register(lambda: scheduler.shutdown())

# Load environment variables (فقط في التطوير المحلي)
if os.path.exists('.env'):
    load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration - استخدام متغيرات البيئة مع قيم افتراضية آمنة
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("SECRET_KEY environment variable is required")

# Database configuration - handle both development and production
if os.environ.get('DATABASE_URL'):
    # Production (Render) - fix postgres:// to postgresql://
    database_url = os.environ.get('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///freelancer.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 20,
    'max_overflow': 0
}

# Mail configuration - التحقق من وجود المتغيرات المطلوبة
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

# التحقق من إعدادات البريد الإلكتروني
if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
    print("تحذير: إعدادات البريد الإلكتروني غير مكتملة")

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)

# إعداد Rate Limiter المتقدم مع Redis
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'memory://'),
    strategy="moving-window"
)

# إعدادات reCAPTCHA
app.config['RECAPTCHA_SITE_KEY'] = os.environ.get('RECAPTCHA_SITE_KEY', '')
app.config['RECAPTCHA_SECRET_KEY'] = os.environ.get('RECAPTCHA_SECRET_KEY', '')
app.config['CAPTCHA_SECRET'] = os.environ.get('CAPTCHA_SECRET', 'default-secret-key-change-this')

# قائمة الـ endpoints المستثناة من Captcha
EXEMPT_ENDPOINTS = ['/ping', '/health', '/static']

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'من فضلك سجل دخولك أولاً'

# إعداد نظام السجلات
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')

# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicit table name
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6))
    code_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define relationship
    orders = db.relationship('Order', backref='user', lazy=True)

class Order(db.Model):
    __tablename__ = 'orders'  # Explicit table name
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    coins_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_valid_email(email):
    """Check if email is from trusted domains"""
    trusted_domains = ['gmail.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'yahoo.com']
    try:
        domain = email.split('@')[1].lower()
        return domain in trusted_domains
    except:
        return False

def generate_verification_code():
    """Generate 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code):
    """Send verification email with OTP"""
    try:
        if not app.config['MAIL_USERNAME']:
            print("Mail not configured, skipping email send")
            return True  # For development without mail config
            
        msg = Message(
            subject='كود التفعيل لموقع الفريلانسر',
            recipients=[email],
            body=f'''
مرحباً بك في موقع الفريلانسر!

كود التفعيل الخاص بك هو: {code}

هذا الكود صالح لمدة 10 دقائق فقط.

شكراً لك!
            '''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return True  # Don't block registration if email fails

def verify_recaptcha(token):
    """التحقق من رمز reCAPTCHA v3"""
    if not app.config['RECAPTCHA_SECRET_KEY']:
        return True  # إذا لم يتم تكوين reCAPTCHA، اسمح بالمرور
    
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': app.config['RECAPTCHA_SECRET_KEY'],
                'response': token
            },
            timeout=10
        )
        result = response.json()
        
        # التحقق من النتيجة والدرجة (0.0 = bot, 1.0 = human)
        if result.get('success') and result.get('score', 0) >= 0.5:
            return True
        else:
            app.logger.warning(f"reCAPTCHA failed: {result}")
            return False
    except Exception as e:
        app.logger.error(f"reCAPTCHA verification error: {e}")
        return True  # في حالة الخطأ، اسمح بالمرور لتجنب منع المستخدمين الشرعيين

def check_honeypot(form_data):
    """فحص Honeypot fields (فخاخ البوتات)"""
    honeypot_fields = ['website', 'url', 'homepage', 'company']
    
    for field in honeypot_fields:
        if form_data.get(field, '').strip():
            app.logger.warning(f"Honeypot field '{field}' was filled")
            return False
    
    return True

def generate_time_token():
    """إنشاء رمز مؤقت للتحقق من الوقت"""
    timestamp = str(int(time.time()))
    secret = app.config['CAPTCHA_SECRET']
    return hashlib.md5((timestamp + secret).encode()).hexdigest(), timestamp

def verify_time_token(token, timestamp):
    """التحقق من الرمز المؤقت"""
    try:
        current_time = int(time.time())
        form_time = int(timestamp)
        
        # التحقق من أن النموذج لم يتم إرساله بسرعة مشبوهة (أقل من 3 ثواني)
        if current_time - form_time < 3:
            return False
        
        # التحقق من أن النموذج لم يتم إرساله بعد وقت طويل جداً (أكثر من 30 دقيقة)
        if current_time - form_time > 1800:
            return False
        
        # التحقق من صحة الرمز
        secret = app.config['CAPTCHA_SECRET']
        expected_token = hashlib.md5((timestamp + secret).encode()).hexdigest()
        
        return token == expected_token
    except:
        return False

def is_bot_behavior(request):
    """فحص سلوك البوت"""
    # فحص User-Agent
    user_agent = request.headers.get('User-Agent', '').lower()
    bot_indicators = ['bot', 'crawler', 'spider', 'scraper', 'automated']
    
    if any(indicator in user_agent for indicator in bot_indicators):
        return True
    
    # فحص الـ headers المشبوهة
    if not request.headers.get('Accept'):
        return True
    
    if not request.headers.get('Accept-Language'):
        return True
    
    return False

def comprehensive_captcha_check(request, form_data):
    """فحص شامل للـ Captcha"""
    # فحص الـ endpoints المستثناة
    if any(request.path.startswith(endpoint) for endpoint in EXEMPT_ENDPOINTS):
        return True
    
    # فحص سلوك البوت
    if is_bot_behavior(request):
        app.logger.warning(f"Bot behavior detected from {get_remote_address()}")
        return False
    
    # فحص Honeypot
    if not check_honeypot(form_data):
        return False
    
    # فحص Time Token
    time_token = form_data.get('time_token', '')
    timestamp = form_data.get('timestamp', '')
    
    if not verify_time_token(time_token, timestamp):
        app.logger.warning("Time token verification failed")
        return False
    
    # فحص reCAPTCHA v3
    recaptcha_token = form_data.get('g-recaptcha-response', '')
    if recaptcha_token and not verify_recaptcha(recaptcha_token):
        return False
    
    return True

# Routes
@app.route('/')
def home():
    return render_template('home.html')
    
@app.route('/ping', methods=['GET'])
def ping():
    """Endpoint للـ ping لمنع Cold Start"""
    try:
        # فحص بسيط لحالة التطبيق باستخدام text()
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'alive',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Application is running'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint للفحص الصحي المفصل"""
    try:
        # فحص قاعدة البيانات باستخدام text()
        db.session.execute(text('SELECT 1'))
        db_status = "healthy"
        
        # فحص عدد المستخدمين (كمثال على أن التطبيق يعمل)
        user_count = User.query.count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_status,
            'user_count': user_count,
            'uptime': 'running'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500
        
@app.route('/stats')
@login_required
def stats():
    """إحصائيات التطبيق للمراقبة"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        total_users = User.query.count()
        verified_users = User.query.filter_by(is_verified=True).count()
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        completed_orders = Order.query.filter_by(status='completed').count()
        
        # إحصائيات الأسبوع الماضي
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = User.query.filter(User.created_at >= week_ago).count()
        new_orders_week = Order.query.filter(Order.created_at >= week_ago).count()
        
        return jsonify({
            'total_users': total_users,
            'verified_users': verified_users,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'new_users_this_week': new_users_week,
            'new_orders_this_week': new_orders_week,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/setup-admin', methods=['GET', 'POST'])
def setup_admin():
    """صفحة إعداد المستخدم الإداري الأولي"""
    
    # التحقق من وجود مستخدم إداري
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    existing_admin = User.query.filter_by(email=admin_email).first()
    
    if existing_admin:
        return render_template('admin_exists.html')
    
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            setup_key = request.form.get('setup_key', '')
            
            # التحقق من مفتاح الإعداد (اختياري للأمان الإضافي)
            expected_setup_key = os.environ.get('SETUP_KEY', '')
            if expected_setup_key and setup_key != expected_setup_key:
                flash('مفتاح الإعداد غير صحيح', 'error')
                return render_template('setup_admin.html')
            
            # التحقق من صحة البيانات
            if not email or not password:
                flash('البريد الإلكتروني وكلمة المرور مطلوبان', 'error')
                return render_template('setup_admin.html')
            
            if password != confirm_password:
                flash('كلمات المرور غير متطابقة', 'error')
                return render_template('setup_admin.html')
            
            if len(password) < 8:
                flash('كلمة المرور يجب أن تكون 8 أحرف على الأقل', 'error')
                return render_template('setup_admin.html')
            
            # إنشاء المستخدم الإداري
            admin = User(
                email=email,
                password_hash=generate_password_hash(password),
                is_verified=True,
                is_admin=True
            )
            
            db.session.add(admin)
            db.session.commit()
            
            app.logger.info(f"Admin user created: {email}")
            flash('تم إنشاء المستخدم الإداري بنجاح!', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating admin user: {e}")
            flash('حدث خطأ أثناء إنشاء المستخدم الإداري', 'error')
    
    return render_template('setup_admin.html')

@app.route('/reset-admin-password', methods=['GET', 'POST'])
@login_required
def reset_admin_password():
    """صفحة إعادة تعيين كلمة مرور المستخدم الإداري"""
    
    if not current_user.is_admin:
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # التحقق من كلمة المرور الحالية
            if not check_password_hash(current_user.password_hash, current_password):
                flash('كلمة المرور الحالية غير صحيحة', 'error')
                return render_template('reset_admin_password.html')
            
            # التحقق من كلمة المرور الجديدة
            if not new_password or len(new_password) < 8:
                flash('كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل', 'error')
                return render_template('reset_admin_password.html')
            
            if new_password != confirm_password:
                flash('كلمات المرور غير متطابقة', 'error')
                return render_template('reset_admin_password.html')
            
            # تحديث كلمة المرور
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            app.logger.info(f"Admin password reset for user: {current_user.email}")
            flash('تم تغيير كلمة المرور بنجاح!', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error resetting admin password: {e}")
            flash('حدث خطأ أثناء تغيير كلمة المرور', 'error')
    
    return render_template('reset_admin_password.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # تحديد عدد محاولات التسجيل
def register():
    if request.method == 'GET':
        # إنشاء time token للنموذج
        time_token, timestamp = generate_time_token()
        return render_template('register.html', time_token=time_token, timestamp=timestamp)
    
    if request.method == 'POST':
        try:
            # فحص Captcha الشامل
            if not comprehensive_captcha_check(request, request.form):
                flash('فشل في التحقق من الأمان. يرجى المحاولة مرة أخرى.', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            email = request.form['email'].lower().strip()
            password = request.form['password']
            
            # Validate email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                flash('البريد الإلكتروني غير صالح', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            # Check if email is from trusted domain
            if not is_valid_email(email):
                flash('يجب استخدام بريد إلكتروني من Gmail أو Hotmail أو iCloud أو Yahoo', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            # Check password length
            if len(password) < 6:
                flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('هذا البريد الإلكتروني مستخدم بالفعل', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            # Generate verification code
            verification_code = generate_verification_code()
            code_expiry = datetime.utcnow() + timedelta(minutes=10)
            
            # Create new user
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                verification_code=verification_code,
                code_expiry=code_expiry
            )
            
            # Send verification email
            if send_verification_email(email, verification_code):
                db.session.add(user)
                db.session.commit()
                session['user_email'] = email
                flash('تم إرسال كود التفعيل إلى بريدك الإلكتروني', 'success')
                return redirect(url_for('verify_email'))
            else:
                flash('خطأ في إرسال البريد الإلكتروني، حاول مرة أخرى', 'error')
                
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            flash('حدث خطأ أثناء التسجيل، حاول مرة أخرى', 'error')
        
        # في حالة الخطأ، إنشاء tokens جديدة
        time_token, timestamp = generate_time_token()
        return render_template('register.html', time_token=time_token, timestamp=timestamp)

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if 'user_email' not in session:
        flash('يجب التسجيل أولاً', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        try:
            code = request.form['code'].strip()
            user = User.query.filter_by(email=session['user_email']).first()
            
            if not user:
                flash('المستخدم غير موجود', 'error')
                return redirect(url_for('register'))
            
            if user.is_verified:
                flash('حسابك مفعل بالفعل', 'success')
                session.pop('user_email', None)
                return redirect(url_for('login'))
            
            if not user.verification_code:
                flash('لا يوجد كود تفعيل، يرجى طلب كود جديد', 'error')
                return render_template('verify_email.html')
            
            if user.verification_code != code:
                flash('كود التفعيل غير صحيح', 'error')
                return render_template('verify_email.html')
            
            if datetime.utcnow() > user.code_expiry:
                flash('كود التفعيل منتهي الصلاحية، يرجى طلب كود جديد', 'error')
                return render_template('verify_email.html')
            
            # تفعيل المستخدم
            user.is_verified = True
            user.verification_code = None
            user.code_expiry = None
            db.session.commit()
            
            session.pop('user_email', None)
            flash('تم تفعيل حسابك بنجاح! يمكنك الآن تسجيل الدخول', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Verification error: {e}")
            flash('حدث خطأ أثناء التفعيل، حاول مرة أخرى', 'error')
    
    return render_template('verify_email.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email'].lower().strip()
            password = request.form['password']
            
            user = User.query.filter_by(email=email).first()
            
            if user and check_password_hash(user.password_hash, password):
                if user.is_verified:
                    login_user(user)
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('dashboard'))
                else:
                    # إذا كان الحساب غير مفعل، نوجه المستخدم لصفحة التفعيل
                    session['user_email'] = email
                    flash('حسابك غير مفعل. تم إرسال كود تفعيل جديد إلى بريدك الإلكتروني', 'error')
                    
                    # إرسال كود تفعيل جديد
                    verification_code = generate_verification_code()
                    code_expiry = datetime.utcnow() + timedelta(minutes=10)
                    
                    user.verification_code = verification_code
                    user.code_expiry = code_expiry
                    db.session.commit()
                    
                    send_verification_email(email, verification_code)
                    return redirect(url_for('verify_email'))
            else:
                flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'error')
                
        except Exception as e:
            print(f"Login error: {e}")
            flash('حدث خطأ أثناء تسجيل الدخول، حاول مرة أخرى', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        return render_template('dashboard.html', user=current_user, orders=orders)
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash('حدث خطأ في تحميل البيانات', 'error')
        return render_template('dashboard.html', user=current_user, orders=[])

@app.route('/new-order', methods=['GET', 'POST'])
@login_required
def new_order():
    if request.method == 'POST':
        try:
            platform = request.form['platform']
            payment_method = request.form['payment_method']
            coins_amount = int(request.form['coins_amount'])
            
            if coins_amount < 300000:
                flash('الحد الأدنى للكوينز هو 300,000', 'error')
                return render_template('new_order.html', 
                                     platforms=['PS', 'Xbox', 'PC'],
                                     payment_methods=['جميع المنصات', 'جميع المحافظات'])
            
            order = Order(
                user_id=current_user.id,
                platform=platform,
                payment_method=payment_method,
                coins_amount=coins_amount
            )
            
            db.session.add(order)
            db.session.commit()
            
            flash('تم إرسال طلبك بنجاح! سيتم التواصل معك قريباً', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"New order error: {e}")
            flash('حدث خطأ أثناء إرسال الطلب، حاول مرة أخرى', 'error')
    
    platforms = ['PS', 'Xbox', 'PC']
    payment_methods = ['جميع المنصات', 'جميع المحافظات']
    
    return render_template('new_order.html', platforms=platforms, payment_methods=payment_methods)

@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    if 'user_email' not in session:
        flash('يجب التسجيل أولاً', 'error')
        return redirect(url_for('register'))
    
    try:
        user = User.query.filter_by(email=session['user_email']).first()
        
        if not user:
            flash('المستخدم غير موجود', 'error')
            return redirect(url_for('register'))
        
        if user.is_verified:
            flash('حسابك مفعل بالفعل', 'success')
            return redirect(url_for('login'))
        
        # إنشاء كود جديد
        verification_code = generate_verification_code()
        code_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        user.verification_code = verification_code
        user.code_expiry = code_expiry
        db.session.commit()
        
        # إرسال الكود الجديد
        if send_verification_email(user.email, verification_code):
            flash('تم إرسال كود تفعيل جديد إلى بريدك الإلكتروني', 'success')
        else:
            flash('خطأ في إرسال البريد الإلكتروني', 'error')
            
    except Exception as e:
        print(f"Resend verification error: {e}")
        flash('حدث خطأ، حاول مرة أخرى', 'error')
    
    return redirect(url_for('verify_email'))

@app.route('/admin')
@login_required
def admin_dashboard():
    try:
        if not current_user.is_admin:
            flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
            return redirect(url_for('dashboard'))
        
        orders = Order.query.order_by(Order.created_at.desc()).all()
        users = User.query.all()
        
        return render_template('admin_dashboard.html', orders=orders, users=users)
    except Exception as e:
        print(f"Admin dashboard error: {e}")
        flash('حدث خطأ في تحميل البيانات', 'error')
        return render_template('admin_dashboard.html', orders=[], users=[])

@app.route('/admin/order/<int:order_id>/update', methods=['POST'])
@login_required
def update_order_status(order_id):
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        new_status = request.json.get('status')
        
        order = Order.query.get_or_404(order_id)
        order.status = new_status
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update order error: {e}")
        return jsonify({'error': 'Server error'}), 500

def init_database():
    """Initialize database and create default admin user"""
    try:
        # Create all tables
        db.create_all()
        print("Database tables created successfully")
        
        # تحسين قاعدة البيانات
        optimize_database()
        
        # تنظيف البيانات القديمة
        cleanup_old_verification_codes()
        
        # التحقق من وجود مستخدم إداري
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin = User.query.filter_by(email=admin_email).first()
        
        if not admin:
            print("=" * 60)
            print("لا يوجد مستخدم إداري في قاعدة البيانات")
            print("يرجى إنشاء المستخدم الإداري عبر الرابط:")
            print(f"https://senioraa.onrender.com/setup-admin")
            print("=" * 60)
        else:
            print("Admin user already exists")
            
    except Exception as e:
        print(f"Database initialization error: {e}")

def optimize_database():
    """تحسين قاعدة البيانات وإنشاء الفهارس"""
    try:
        with app.app_context():
            # إنشاء فهارس لتحسين الأداء باستخدام text() لتحديد SQL صراحة
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_email ON users(email)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_user_verified ON users(is_verified)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_order_user_id ON orders(user_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_order_status ON orders(status)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_order_created_at ON orders(created_at)'))
            db.session.commit()
            print("Database indexes created successfully")
    except Exception as e:
        print(f"Database optimization error: {e}")

def cleanup_old_verification_codes():
    """تنظيف رموز التفعيل المنتهية الصلاحية"""
    try:
        with app.app_context():
            expired_time = datetime.utcnow() - timedelta(hours=24)
            expired_users = User.query.filter(
                User.code_expiry < expired_time,
                User.is_verified == False
            ).all()
            
            for user in expired_users:
                user.verification_code = None
                user.code_expiry = None
            
            db.session.commit()
            print(f"Cleaned up {len(expired_users)} expired verification codes")
    except Exception as e:
        print(f"Cleanup error: {e}")

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Initialize database when app starts
with app.app_context():
    init_database()

if __name__ == '__main__':
    app.run(debug=True)
