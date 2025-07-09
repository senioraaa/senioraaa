# admin/admin_auth.py
import os
from functools import wraps
from flask import session, redirect, url_for, flash, request
import hashlib

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
