from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash
import hashlib, time, os, re, sqlite3, uuid, secrets
from datetime import datetime, timedelta
import logging

# إعداد التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# الحماية الأمنية (بدون CSRF مؤقتاً)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://"
)

# إعداد الـ Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# متغيرات عامة
failed_attempts = {}
blocked_ips = {}

# إنشاء قاعدة البيانات
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    
    # جدول الطلبات
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        game_type TEXT NOT NULL,
        platform TEXT NOT NULL,
        account_type TEXT NOT NULL,
        price INTEGER NOT NULL,
        customer_phone TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT
    )''')
    
    # جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # إضافة مستخدم افتراضي
    admin_hash = generate_password_hash('admin123')
    c.execute('INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)',
              ('admin', admin_hash, 'admin'))
    
    conn.commit()
    conn.close()

# Headers أمنية
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# حماية من الـ Brute Force
def check_brute_force(ip):
    current_time = time.time()
    
    if ip in blocked_ips:
        block_time, block_duration = blocked_ips[ip]
        if current_time - block_time < block_duration:
            return False
        else:
            del blocked_ips[ip]
    
    if ip in failed_attempts:
        attempts, last_attempt = failed_attempts[ip]
        if current_time - last_attempt < 300:
            if attempts >= 5:
                blocked_ips[ip] = (current_time, 1800)
                logger.warning(f"IP {ip} blocked due to too many failed attempts")
                return False
    return True

def log_failed_attempt(ip):
    current_time = time.time()
    if ip in failed_attempts:
        attempts, _ = failed_attempts[ip]
        failed_attempts[ip] = (attempts + 1, current_time)
    else:
        failed_attempts[ip] = (1, current_time)

# تنظيف المدخلات
def sanitize_input(text, max_length=100):
    if not text or len(text) > max_length:
        return None
    text = re.sub(r'[<>"\';\\]', '', str(text))
    return text.strip()

def validate_phone(phone):
    phone = re.sub(r'[^\d+]', '', phone)
    if len(phone) >= 10 and len(phone) <= 15:
        return phone
    return None

# Simple CSRF protection
def generate_csrf_token():
    return secrets.token_hex(32)

def validate_csrf_token(token):
    return token and len(token) == 64

# الصفحة الرئيسية
@app.route('/')
def index():
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token
    return render_template('index.html', csrf_token=csrf_token)

# معالج الطلبات الجديدة
@app.route('/order', methods=['POST'])
@limiter.limit("5 per minute")
def create_order():
    try:
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        
        # Simple CSRF check
        token = request.form.get('csrf_token')
        if not validate_csrf_token(token) or token != session.get('csrf_token'):
            return jsonify({'error': 'Invalid security token'}), 400
        
        # تنظيف البيانات
        game_type = sanitize_input(request.form.get('game_type'))
        platform = sanitize_input(request.form.get('platform'))
        account_type = sanitize_input(request.form.get('account_type'))
        phone = validate_phone(request.form.get('phone', ''))
        
        if not all([game_type, platform, account_type, phone]):
            logger.warning(f"Invalid order data from IP: {client_ip}")
            return jsonify({'error': 'بيانات غير صحيحة'}), 400
        
        # حساب السعر
        prices = {
            ('FC25', 'PS4', 'Primary'): 85,
            ('FC25', 'PS4', 'Secondary'): 70,
            ('FC25', 'PS4', 'Full'): 120,
            ('FC25', 'PS5', 'Primary'): 90,
            ('FC25', 'PS5', 'Secondary'): 75,
            ('FC25', 'PS5', 'Full'): 125,
            ('FC25', 'Xbox', 'Primary'): 85,
            ('FC25', 'Xbox', 'Secondary'): 70,
            ('FC25', 'Xbox', 'Full'): 120,
            ('FC25', 'PC', 'Primary'): 80,
            ('FC25', 'PC', 'Secondary'): 65,
            ('FC25', 'PC', 'Full'): 115,
        }
        
        price = prices.get((game_type, platform, account_type))
        if not price:
            return jsonify({'error': 'نوع غير مدعوم'}), 400
        
        # إنشاء الطلب
        order_id = str(uuid.uuid4())[:8]
        
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute('''INSERT INTO orders 
                     (id, game_type, platform, account_type, price, customer_phone, ip_address)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (order_id, game_type, platform, account_type, price, phone, client_ip))
        conn.commit()
        conn.close()
        
        logger.info(f"New order created: {order_id} from IP: {client_ip}")
        
        # Generate new CSRF token
        new_token = generate_csrf_token()
        session['csrf_token'] = new_token
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'price': price,
            'message': 'تم إنشاء الطلب بنجاح!',
            'csrf_token': new_token
        })
        
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return jsonify({'error': 'حدث خطأ في النظام'}), 500

# صفحة تسجيل الدخول للمدير
@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def admin_login():
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
    
    if not check_brute_force(client_ip):
        logger.warning(f"Blocked login attempt from IP: {client_ip}")
        abort(429)
    
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username'))
        password = request.form.get('password', '')
        
        if not username or not password:
            log_failed_attempt(client_ip)
            flash('البيانات غير مكتملة', 'error')
            return render_template('login.html')
        
        # التحقق من المستخدم
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute('SELECT password_hash, role FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[0], password):
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            session['role'] = user[1]
            logger.info(f"Successful login: {username} from IP: {client_ip}")
            return redirect(url_for('admin_dashboard'))
        else:
            log_failed_attempt(client_ip)
            logger.warning(f"Failed login attempt for {username} from IP: {client_ip}")
            flash('بيانات خاطئة', 'error')
    
    return render_template('login.html')

# لوحة تحكم المدير
@app.route('/admin')
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    # جلب الطلبات
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''SELECT id, game_type, platform, account_type, price, 
                        customer_phone, status, created_at, ip_address 
                 FROM orders ORDER BY created_at DESC LIMIT 50''')
    orders = c.fetchall()
    conn.close()
    
    return render_template('admin.html', orders=orders)

# تحديث حالة الطلب
@app.route('/admin/update_order/<order_id>', methods=['POST'])
def update_order(order_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    new_status = sanitize_input(request.form.get('status'))
    if new_status not in ['pending', 'completed', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    conn.commit()
    conn.close()
    
    logger.info(f"Order {order_id} status updated to {new_status} by {session['username']}")
    return jsonify({'success': True})

# تسجيل الخروج
@app.route('/admin/logout')
def admin_logout():
    username = session.get('username')
    session.clear()
    logger.info(f"User {username} logged out")
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('admin_login'))

# Health check for Render
@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

# معالج الأخطاء
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
    return render_template('ratelimit.html'), 429

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# تشغيل التطبيق
if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
