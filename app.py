from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import os
import random
import string
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv

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
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'من فضلك سجل دخولك أولاً'

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

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email'].lower().strip()
            password = request.form['password']
            
            # Validate email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                flash('البريد الإلكتروني غير صالح', 'error')
                return render_template('register.html')
            
            # Check if email is from trusted domain
            if not is_valid_email(email):
                flash('يجب استخدام بريد إلكتروني من Gmail أو Hotmail أو iCloud أو Yahoo', 'error')
                return render_template('register.html')
            
            # Check password length
            if len(password) < 6:
                flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
                return render_template('register.html')
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('هذا البريد الإلكتروني مستخدم بالفعل', 'error')
                return render_template('register.html')
            
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
            print(f"Registration error: {e}")
            flash('حدث خطأ أثناء التسجيل، حاول مرة أخرى', 'error')
    
    return render_template('register.html')

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
        
        # Create default admin user
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                is_verified=True,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created successfully")
        else:
            print("Admin user already exists")
            
    except Exception as e:
        print(f"Database initialization error: {e}")

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
