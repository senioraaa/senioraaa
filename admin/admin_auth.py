# admin_system.py - نظام الإدارة الكامل
import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import json
import hashlib

# ========================== نظام الحماية ==========================
class AdminAuth:
    def __init__(self):
        # كلمة مرور الأدمن من متغيرات البيئة
        self.admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        self.admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    
    def hash_password(self, password):
        """تشفير كلمة المرور"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, username, password):
        """التحقق من كلمة المرور"""
        if username == self.admin_username:
            return self.hash_password(password) == self.hash_password(self.admin_password)
        return False
    
    def login_required(self, f):
        """ديكوريتر للتحقق من تسجيل الدخول"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' not in session:
                flash('يجب تسجيل الدخول للوصول لهذه الصفحة', 'error')
                return redirect(url_for('admin.login'))
            return f(*args, **kwargs)
        return decorated_function

# إنشاء instance
admin_auth = AdminAuth()

# ========================== المسارات والروتس ==========================
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# مسار ملف الأسعار
PRICES_FILE = 'data/prices.json'

def load_prices():
    """تحميل الأسعار من الملف"""
    if os.path.exists(PRICES_FILE):
        with open(PRICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "fc25": {
            "ps4": {"primary": 50, "secondary": 30, "full": 80},
            "ps5": {"primary": 60, "secondary": 40, "full": 100},
            "xbox": {"primary": 55, "secondary": 35, "full": 90},
            "pc": {"primary": 45, "secondary": 25, "full": 70}
        }
    }

def save_prices(prices):
    """حفظ الأسعار في الملف"""
    os.makedirs(os.path.dirname(PRICES_FILE), exist_ok=True)
    with open(PRICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(prices, f, ensure_ascii=False, indent=2)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if admin_auth.verify_password(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """تسجيل الخروج"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
@admin_auth.login_required
def dashboard():
    """لوحة الإدارة الرئيسية"""
    prices = load_prices()
    return render_template('admin/dashboard.html', prices=prices)

@admin_bp.route('/prices')
@admin_auth.login_required
def prices():
    """صفحة تعديل الأسعار"""
    current_prices = load_prices()
    return render_template('admin/prices.html', prices=current_prices)

@admin_bp.route('/update_prices', methods=['POST'])
@admin_auth.login_required
def update_prices():
    """تحديث الأسعار"""
    try:
        # استقبال البيانات من الـ form
        new_prices = {
            "fc25": {
                "ps4": {
                    "primary": int(request.form['ps4_primary']),
                    "secondary": int(request.form['ps4_secondary']),
                    "full": int(request.form['ps4_full'])
                },
                "ps5": {
                    "primary": int(request.form['ps5_primary']),
                    "secondary": int(request.form['ps5_secondary']),
                    "full": int(request.form['ps5_full'])
                },
                "xbox": {
                    "primary": int(request.form['xbox_primary']),
                    "secondary": int(request.form['xbox_secondary']),
                    "full": int(request.form['xbox_full'])
                },
                "pc": {
                    "primary": int(request.form['pc_primary']),
                    "secondary": int(request.form['pc_secondary']),
                    "full": int(request.form['pc_full'])
                }
            }
        }
        
        # حفظ الأسعار الجديدة
        save_prices(new_prices)
        
        flash('تم تحديث الأسعار بنجاح!', 'success')
        return redirect(url_for('admin.prices'))
        
    except Exception as e:
        flash(f'خطأ في تحديث الأسعار: {str(e)}', 'error')
        return redirect(url_for('admin.prices'))

@admin_bp.route('/api/prices')
@admin_auth.login_required
def api_prices():
    """API للحصول على الأسعار"""
    return jsonify(load_prices())
