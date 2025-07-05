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

import ipaddress
from functools import wraps
import json
from collections import defaultdict, deque
from threading import Lock
import uuid

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from datetime import datetime
from sqlalchemy import text # <--- هذا هو السطر الذي تم إضافته لإصلاح مشكلة Textual SQL expression

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# استيراد نظام التليجرام
from telegram_bot import telegram_system
import atexit

# إعداد المهام الدورية لـ APScheduler
scheduler = BackgroundScheduler()

class SmartRateLimiter:
    """نظام Rate Limiting ذكي ومتقدم متعدد المستويات"""
    
    def __init__(self, app=None, redis_client=None):
        self.app = app
        self.redis_client = redis_client
        self.memory_store = defaultdict(lambda: defaultdict(deque))
        self.suspicious_ips = defaultdict(lambda: {"score": 0, "last_seen": 0})
        self.user_reputation = defaultdict(lambda: {"score": 100, "last_activity": 0})
        self.lock = Lock()
        
        # إعدادات الشبكات الموثوقة
        self.trusted_networks = [
            ipaddress.ip_network('127.0.0.0/8'),    # localhost
            ipaddress.ip_network('10.0.0.0/8'),     # private networks
            ipaddress.ip_network('172.16.0.0/12'),  # private networks
            ipaddress.ip_network('192.168.0.0/16'), # private networks
        ]
        
        # User Agents للخدمات الموثوقة
        self.trusted_user_agents = [
            'uptimerobot', 'pingdom', 'googlebot', 'bingbot', 'monitor', 
            'health-check', 'render', 'nginx', 'apache', 'cloudflare'
        ]
        
        # نقاط السلوك المشبوه
        self.suspicious_patterns = {
            'rapid_requests': -10,      # طلبات سريعة جداً
            'failed_login': -15,        # فشل في تسجيل الدخول
            'invalid_form': -5,         # نموذج غير صالح
            'honeypot_hit': -25,        # وقوع في فخ البوتات
            'successful_action': +5,     # عمل ناجح
            'normal_browsing': +2,       # تصفح طبيعي
            'account_verified': +20      # تفعيل حساب
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """تهيئة التطبيق"""
        self.app = app
        
        # محاولة الاتصال بـ Redis
        try:
            import redis
            redis_url = app.config.get('REDIS_URL', os.environ.get('REDIS_URL'))
            if redis_url and redis_url != 'memory://':
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # اختبار الاتصال
                self.redis_client.ping()
                app.logger.info("Connected to Redis for advanced rate limiting")
            else:
                self.redis_client = None
                app.logger.info("Using memory storage for rate limiting")
        except Exception as e:
            app.logger.warning(f"Redis connection failed, using memory storage: {e}")
            self.redis_client = None
    
    def is_trusted_source(self, request):
        """فحص ما إذا كان المصدر موثوقاً"""
        try:
            # فحص IP
            client_ip = ipaddress.ip_address(get_remote_address())
            for network in self.trusted_networks:
                if client_ip in network:
                    return True
        except:
            pass
        
        # فحص User-Agent
        user_agent = request.headers.get('User-Agent', '').lower()
        for trusted_agent in self.trusted_user_agents:
            if trusted_agent in user_agent:
                return True
        
        return False
    
    def get_client_fingerprint(self, request):
        """إنشاء بصمة فريدة للعميل"""
        ip = get_remote_address()
        user_agent = request.headers.get('User-Agent', '')[:100]
        accept_language = request.headers.get('Accept-Language', '')[:50]
        accept_encoding = request.headers.get('Accept-Encoding', '')[:50]
        
        # إنشاء بصمة مركبة
        fingerprint_data = f"{ip}:{user_agent}:{accept_language}:{accept_encoding}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def get_client_identifier(self, request):
        """الحصول على معرف فريد للعميل (للتوافق مع الكود القديم)"""
        return self.get_client_fingerprint(request)
    
    def update_reputation(self, identifier, action, user_id=None):
        """تحديث سمعة العميل أو المستخدم"""
        current_time = int(time.time())
        score_change = self.suspicious_patterns.get(action, 0)
        
        # تحديث سمعة IP
        if identifier in self.suspicious_ips:
            self.suspicious_ips[identifier]["score"] = max(
                -100, min(100, self.suspicious_ips[identifier]["score"] + score_change)
            )
        else:
            self.suspicious_ips[identifier] = {
                "score": score_change,
                "last_seen": current_time
            }
        
        self.suspicious_ips[identifier]["last_seen"] = current_time
        
        # تحديث سمعة المستخدم إذا كان مسجل الدخول
        if user_id:
            if user_id in self.user_reputation:
                self.user_reputation[user_id]["score"] = max(
                    0, min(200, self.user_reputation[user_id]["score"] + score_change)
                )
            else:
                self.user_reputation[user_id] = {
                    "score": 100 + score_change,
                    "last_activity": current_time
                }
            
            self.user_reputation[user_id]["last_activity"] = current_time
        
        # حفظ في Redis إذا متاح
        if self.redis_client:
            try:
                self.redis_client.hset(
                    f"reputation:ip:{identifier}", 
                    mapping={
                        "score": self.suspicious_ips[identifier]["score"],
                        "last_seen": current_time
                    }
                )
                self.redis_client.expire(f"reputation:ip:{identifier}", 86400)  # 24 ساعة
                
                if user_id:
                    self.redis_client.hset(
                        f"reputation:user:{user_id}",
                        mapping={
                            "score": self.user_reputation[user_id]["score"],
                            "last_activity": current_time
                        }
                    )
                    self.redis_client.expire(f"reputation:user:{user_id}", 604800)  # 7 أيام
            except:
                pass
    
    def get_dynamic_limits(self, identifier, base_per_minute, base_per_hour, user_id=None):
        """حساب حدود ديناميكية بناءً على السمعة"""
        # الحصول على نقاط السمعة
        ip_score = self.suspicious_ips.get(identifier, {}).get("score", 0)
        user_score = 100  # افتراضي للمستخدمين غير مسجلي الدخول
        
        if user_id:
            user_score = self.user_reputation.get(user_id, {}).get("score", 100)
        
        # حساب المضاعف بناءً على السمعة
        if ip_score < -50 or user_score < 20:
            # سمعة سيئة جداً - حدود صارمة
            multiplier = 0.2
        elif ip_score < -20 or user_score < 50:
            # سمعة سيئة - حدود منخفضة
            multiplier = 0.5
        elif ip_score > 20 and user_score > 150:
            # سمعة ممتازة - حدود مرتفعة
            multiplier = 2.0
        elif ip_score > 10 and user_score > 120:
            # سمعة جيدة - حدود أعلى قليلاً
            multiplier = 1.5
        else:
            # سمعة طبيعية - حدود افتراضية
            multiplier = 1.0
        
        return {
            'per_minute': max(1, int(base_per_minute * multiplier)),
            'per_hour': max(5, int(base_per_hour * multiplier)),
            'multiplier': multiplier
        }
    
    def check_rate_limit(self, identifier, limit_per_minute, limit_per_hour):
        """فحص Rate Limit الأساسي (للتوافق مع الكود القديم)"""
        current_time = int(time.time())
        
        if self.redis_client:
            return self._check_rate_limit_redis(identifier, limit_per_minute, limit_per_hour, current_time)
        else:
            return self._check_rate_limit_memory(identifier, limit_per_minute, limit_per_hour, current_time)
    
    def _check_rate_limit_redis(self, identifier, limit_per_minute, limit_per_hour, current_time):
        """فحص Rate Limit باستخدام Redis"""
        try:
            pipe = self.redis_client.pipeline()
            
            # مفاتيح للدقيقة والساعة
            minute_key = f"rate_limit:{identifier}:minute:{current_time // 60}"
            hour_key = f"rate_limit:{identifier}:hour:{current_time // 3600}"
            
            # زيادة العدادات
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # انتهاء صلاحية بعد دقيقتين
            pipe.incr(hour_key)
            pipe.expire(hour_key, 7200)  # انتهاء صلاحية بعد ساعتين
            
            results = pipe.execute()
            minute_count = results[0]
            hour_count = results[2]
            
            # فحص الحدود
            if minute_count > limit_per_minute:
                return False, f"Rate limit exceeded: {minute_count}/{limit_per_minute} per minute"
            
            if hour_count > limit_per_hour:
                return False, f"Rate limit exceeded: {hour_count}/{limit_per_hour} per hour"
            
            return True, None
            
        except Exception as e:
            self.app.logger.error(f"Redis rate limit error: {e}")
            # استخدام الذاكرة كبديل
            return self._check_rate_limit_memory(identifier, limit_per_minute, limit_per_hour, current_time)
    
    def _check_rate_limit_memory(self, identifier, limit_per_minute, limit_per_hour, current_time):
        """فحص Rate Limit باستخدام الذاكرة"""
        with self.lock:
            minute_window = current_time // 60
            hour_window = current_time // 3600
            
            # تنظيف البيانات القديمة
            self._cleanup_old_data(current_time)
            
            # إضافة الطلب الحالي
            self.memory_store[identifier]['minute'].append(minute_window)
            self.memory_store[identifier]['hour'].append(hour_window)
            
            # عد الطلبات في النافذة الزمنية الحالية
            minute_count = sum(1 for t in self.memory_store[identifier]['minute'] if t == minute_window)
            hour_count = sum(1 for t in self.memory_store[identifier]['hour'] if t == hour_window)
            
            # فحص الحدود
            if minute_count > limit_per_minute:
                return False, f"Rate limit exceeded: {minute_count}/{limit_per_minute} per minute"
            
            if hour_count > limit_per_hour:
                return False, f"Rate limit exceeded: {hour_count}/{limit_per_hour} per hour"
            
            return True, None
    
    def check_advanced_rate_limit(self, identifier, base_per_minute, base_per_hour, 
                                  endpoint, user_id=None):
        """فحص معدل متقدم مع تحليل سلوكي"""
        current_time = int(time.time())
        
        # الحصول على حدود ديناميكية
        limits = self.get_dynamic_limits(identifier, base_per_minute, base_per_hour, user_id)
        
        # فحص التردد السريع (أقل من ثانية واحدة)
        if self.redis_client:
            last_request_key = f"last_request:{identifier}"
            last_request = self.redis_client.get(last_request_key)
            if last_request and (current_time - int(last_request)) < 1:
                self.update_reputation(identifier, 'rapid_requests', user_id)
                return False, "Requests too frequent", limits['multiplier']
            
            self.redis_client.setex(last_request_key, 5, current_time)
        
        # فحص Rate Limit العادي
        if self.redis_client:
            allowed, error_msg = self._check_rate_limit_redis_advanced(
                identifier, limits['per_minute'], limits['per_hour'], current_time, endpoint
            )
        else:
            allowed, error_msg = self._check_rate_limit_memory_advanced(
                identifier, limits['per_minute'], limits['per_hour'], current_time, endpoint
            )
        
        if not allowed:
            self.update_reputation(identifier, 'rapid_requests', user_id)
        else:
            self.update_reputation(identifier, 'normal_browsing', user_id)
        
        return allowed, error_msg, limits['multiplier']
    
    def _check_rate_limit_redis_advanced(self, identifier, limit_per_minute, 
                                        limit_per_hour, current_time, endpoint):
        """فحص Rate Limit متقدم باستخدام Redis"""
        try:
            pipe = self.redis_client.pipeline()
            
            # مفاتيح مختلفة للـ endpoints المختلفة
            minute_key = f"rate_limit:{identifier}:{endpoint}:minute:{current_time // 60}"
            hour_key = f"rate_limit:{identifier}:{endpoint}:hour:{current_time // 3600}"
            global_minute_key = f"rate_limit:{identifier}:global:minute:{current_time // 60}"
            global_hour_key = f"rate_limit:{identifier}:global:hour:{current_time // 3600}"
            
            # زيادة العدادات
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 7200)
            pipe.incr(global_minute_key)
            pipe.expire(global_minute_key, 120)
            pipe.incr(global_hour_key)
            pipe.expire(global_hour_key, 7200)
            
            results = pipe.execute()
            endpoint_minute_count = results[0]
            endpoint_hour_count = results[2]
            global_minute_count = results[4]
            global_hour_count = results[6]
            
            # فحص حدود الـ endpoint المحدد
            if endpoint_minute_count > limit_per_minute:
                return False, f"Endpoint rate limit exceeded: {endpoint_minute_count}/{limit_per_minute} per minute"
            
            if endpoint_hour_count > limit_per_hour:
                return False, f"Endpoint rate limit exceeded: {endpoint_hour_count}/{limit_per_hour} per hour"
            
            # فحص الحدود العامة (لمنع إساءة الاستخدام العام)
            if global_minute_count > limit_per_minute * 3:
                return False, f"Global rate limit exceeded: {global_minute_count} per minute"
            
            if global_hour_count > limit_per_hour * 3:
                return False, f"Global rate limit exceeded: {global_hour_count} per hour"
            
            return True, None
            
        except Exception as e:
            self.app.logger.error(f"Redis advanced rate limit error: {e}")
            return self._check_rate_limit_memory_advanced(
                identifier, limit_per_minute, limit_per_hour, current_time, endpoint
            )
    
    def _check_rate_limit_memory_advanced(self, identifier, limit_per_minute, 
                                         limit_per_hour, current_time, endpoint):
        """فحص Rate Limit متقدم باستخدام الذاكرة"""
        with self.lock:
            minute_window = current_time // 60
            hour_window = current_time // 3600
            
            # تنظيف البيانات القديمة
            self._cleanup_old_data(current_time)
            
            # مفاتيح مختلفة للـ endpoints
            endpoint_key = f"{identifier}:{endpoint}"
            
            # إضافة الطلب الحالي
            if endpoint_key not in self.memory_store:
                self.memory_store[endpoint_key] = defaultdict(deque)
            
            self.memory_store[endpoint_key]['minute'].append(minute_window)
            self.memory_store[endpoint_key]['hour'].append(hour_window)
            
            # عد الطلبات في النافذة الزمنية الحالية
            minute_count = sum(1 for t in self.memory_store[endpoint_key]['minute'] 
                             if t == minute_window)
            hour_count = sum(1 for t in self.memory_store[endpoint_key]['hour'] 
                           if t == hour_window)
            
            # فحص الحدود
            if minute_count > limit_per_minute:
                return False, f"Rate limit exceeded: {minute_count}/{limit_per_minute} per minute"
            
            if hour_count > limit_per_hour:
                return False, f"Rate limit exceeded: {hour_count}/{limit_per_hour} per hour"
            
            return True, None
    
    def _cleanup_old_data(self, current_time):
        """تنظيف البيانات القديمة من الذاكرة"""
        minute_threshold = (current_time // 60) - 2
        hour_threshold = (current_time // 3600) - 2
        reputation_threshold = current_time - 86400  # 24 ساعة
        
        # تنظيف بيانات Rate Limiting
        for key in list(self.memory_store.keys()):
            minute_queue = self.memory_store[key]['minute']
            while minute_queue and minute_queue[0] < minute_threshold:
                minute_queue.popleft()
            
            hour_queue = self.memory_store[key]['hour']
            while hour_queue and hour_queue[0] < hour_threshold:
                hour_queue.popleft()
            
            if not minute_queue and not hour_queue:
                del self.memory_store[key]
        
        # تنظيف بيانات السمعة القديمة
        for ip in list(self.suspicious_ips.keys()):
            if self.suspicious_ips[ip]["last_seen"] < reputation_threshold:
                del self.suspicious_ips[ip]
        
        for user_id in list(self.user_reputation.keys()):
            if self.user_reputation[user_id]["last_activity"] < reputation_threshold:
                del self.user_reputation[user_id]
    
    def is_temporarily_blocked(self, identifier):
        """فحص ما إذا كان IP محظور مؤقتاً"""
        if self.redis_client:
            block_key = f"temp_block:{identifier}"
            return self.redis_client.exists(block_key)
        else:
            # في الذاكرة، نعتمد على النقاط فقط
            return self.suspicious_ips.get(identifier, {}).get("score", 0) < -75
    
    def temporary_block(self, identifier, duration_minutes=15):
        """حظر مؤقت للـ IP"""
        if self.redis_client:
            block_key = f"temp_block:{identifier}"
            self.redis_client.setex(block_key, duration_minutes * 60, "blocked")
            self.app.logger.warning(f"Temporarily blocked IP {identifier} for {duration_minutes} minutes")


# إنشاء instance من SmartRateLimiter
smart_limiter = SmartRateLimiter()

def advanced_rate_limit(per_minute=10, per_hour=100, skip_trusted=True, block_on_abuse=True):
    """ديكوريتر للـ Rate Limiting المتقدم مع تحليل سلوكي"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # فحص المصادر الموثوقة
            if skip_trusted and smart_limiter.is_trusted_source(request):
                return f(*args, **kwargs)
            
            # فحص الـ endpoints المستثناة
            if any(request.path.startswith(endpoint) for endpoint in EXEMPT_ENDPOINTS):
                return f(*args, **kwargs)
            
            # الحصول على معرف العميل ومعرف المستخدم
            client_fingerprint = smart_limiter.get_client_fingerprint(request)
            user_id = current_user.id if current_user.is_authenticated else None
            endpoint = request.endpoint or request.path.split('/')[-1]
            
            # فحص الحظر المؤقت
            if smart_limiter.is_temporarily_blocked(client_fingerprint):
                app.logger.warning(f"Access denied for temporarily blocked client: {get_remote_address()}")
                
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({
                        'error': 'Temporarily blocked',
                        'message': 'Your access has been temporarily restricted due to suspicious activity.',
                        'retry_after': 900  # 15 دقيقة
                    }), 429
                
                flash('تم حظر وصولك مؤقتاً بسبب نشاط مشبوه. يرجى المحاولة بعد 15 دقيقة.', 'error')
                return render_template('429.html'), 429
            
            # فحص Rate Limit المتقدم
            allowed, error_msg, reputation_multiplier = smart_limiter.check_advanced_rate_limit(
                client_fingerprint, per_minute, per_hour, endpoint, user_id
            )
            
            if not allowed:
                app.logger.warning(f"Rate limit exceeded for {get_remote_address()}: {error_msg}")
                
                # في حالة تجاوز الحد عدة مرات، تطبيق حظر مؤقت
                if block_on_abuse and reputation_multiplier < 0.5:
                    smart_limiter.temporary_block(client_fingerprint, 15)
                
                # تحديد مدة الانتظار بناءً على السمعة
                retry_after = int(60 / max(0.1, reputation_multiplier))
                
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests. Please try again later.',
                        'retry_after': retry_after,
                        'reputation': f"{reputation_multiplier:.1f}x"
                    }), 429
                
                flash(f'تم تجاوز الحد المسموح من الطلبات. يرجى المحاولة بعد {retry_after} ثانية.', 'error')
                return render_template('429.html'), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def smart_rate_limit(per_minute=10, per_hour=100, skip_trusted=True):
    """ديكوريتر للـ Rate Limiting الذكي"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # فحص المصادر الموثوقة
            if skip_trusted and smart_limiter.is_trusted_source(request):
                return f(*args, **kwargs)
            
            # فحص الـ endpoints المستثناة
            if any(request.path.startswith(endpoint) for endpoint in EXEMPT_ENDPOINTS):
                return f(*args, **kwargs)
            
            # الحصول على معرف العميل
            client_id = smart_limiter.get_client_identifier(request)
            
            # فحص Rate Limit
            allowed, error_msg = smart_limiter.check_rate_limit(
                client_id, per_minute, per_hour
            )
            
            if not allowed:
                app.logger.warning(f"Rate limit exceeded for {get_remote_address()}: {error_msg}")
                
                # إرجاع استجابة JSON للـ API endpoints
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': 'Too many requests. Please try again later.',
                        'retry_after': 60
                    }), 429
                
                # إرجاع صفحة HTML للمستخدمين العاديين
                flash('تم تجاوز الحد المسموح من الطلبات. يرجى المحاولة بعد قليل.', 'error')
                return render_template('429.html'), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_adaptive_limits(endpoint):
    """الحصول على حدود تكيفية حسب الـ endpoint"""
    limits = {
        'login': {'per_minute': 5, 'per_hour': 20},
        'register': {'per_minute': 3, 'per_hour': 10},
        'verify-email': {'per_minute': 10, 'per_hour': 30},
        'resend-verification': {'per_minute': 2, 'per_hour': 5},
        'setup-admin': {'per_minute': 2, 'per_hour': 5},
        'reset-admin-password': {'per_minute': 3, 'per_hour': 10},
        'new-order': {'per_minute': 5, 'per_hour': 50},
        'default': {'per_minute': 30, 'per_hour': 200}
    }
    
    for key, limit in limits.items():
        if key in endpoint:
            return limit
    
    return limits['default']

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

# إعداد Rate Limiter التقليدي (كبديل)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'memory://'),
    strategy="moving-window"
)

# تهيئة Smart Rate Limiter
smart_limiter.init_app(app)

# تهيئة نظام التليجرام
telegram_system.init_app(app)

# إعدادات reCAPTCHA
app.config['RECAPTCHA_SITE_KEY'] = os.environ.get('RECAPTCHA_SITE_KEY', '')
app.config['RECAPTCHA_SECRET_KEY'] = os.environ.get('RECAPTCHA_SECRET_KEY', '')
app.config['CAPTCHA_SECRET'] = os.environ.get('CAPTCHA_SECRET', 'default-secret-key-change-this')

# نظام تتبع الجلسات المشبوهة
suspicious_sessions = defaultdict(lambda: {
    'attempts': 0,
    'last_attempt': 0,
    'suspicious_score': 0,
    'blocked_until': 0
})

def track_suspicious_session(client_ip, action_type, severity=1):
    current_time = int(time.time())
    
    # تجاهل المصادر الموثوقة من التتبع القاسي
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            app.logger.info(f"Ignoring suspicious activity from trusted IP {client_ip}: {action_type}")
            return
    except:
        pass
    
    session_data = suspicious_sessions[client_ip]
    
    # زيادة عدد المحاولات
    session_data['attempts'] += 1
    session_data['last_attempt'] = current_time
    session_data['suspicious_score'] += (severity * 0.7)  # تخفيف شدة العقوبة
    
    # تطبيق حظر تدريجي أكثر تساهلاً
    if session_data['suspicious_score'] >= 25:  # زيادة العتبة من 15 إلى 25
        session_data['blocked_until'] = current_time + 1800  # 30 دقيقة
        app.logger.warning(f"IP {client_ip} blocked for 30 minutes due to suspicious activity")
    elif session_data['suspicious_score'] >= 15:  # زيادة العتبة من 8 إلى 15
        session_data['blocked_until'] = current_time + 300  # 5 دقائق
        app.logger.warning(f"IP {client_ip} blocked for 5 minutes due to suspicious activity")
    
    # تقليل النقاط تدريجياً
    time_since_last = current_time - session_data.get('last_decay', current_time)
    if time_since_last > 300:  # كل 5 دقائق
        session_data['suspicious_score'] = max(0, session_data['suspicious_score'] - 2)
        session_data['last_decay'] = current_time
    
    app.logger.info(f"Suspicious activity tracked for {client_ip}: {action_type} (Score: {session_data['suspicious_score']:.1f})")

def is_session_blocked(client_ip):
    """فحص ما إذا كانت الجلسة محظورة مع استثناءات للمصادر الموثوقة"""
    current_time = int(time.time())
    session_data = suspicious_sessions[client_ip]
    
    # استثناء للـ localhost والشبكات الخاصة
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            return False, 0
    except:
        pass
    
    if session_data['blocked_until'] > current_time:
        return True, session_data['blocked_until'] - current_time
    
    return False, 0

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
    
    # حقول الملف الشخصي الجديدة مع default values آمنة
    whatsapp = db.Column(db.String(20), default='')
    preferred_platform = db.Column(db.String(10), default='')
    preferred_payment = db.Column(db.String(50), default='')
    ea_email = db.Column(db.String(100), default='')
    telegram_id = db.Column(db.String(50), default='')
    telegram_username = db.Column(db.String(50), default='')
    last_profile_update = db.Column(db.DateTime)
    
    # خاصية محسوبة بدلاً من column لتجنب مشاكل قاعدة البيانات
    @property
    def profile_completed(self):
        """حساب حالة اكتمال الملف الشخصي ديناميكياً"""
        required_fields = [self.whatsapp, self.preferred_platform, self.preferred_payment]
        return all(field and field.strip() for field in required_fields)
    
    def get_profile_completion_data(self):
        """إرجاع بيانات تفصيلية عن اكتمال الملف الشخصي"""
        steps = {
            'whatsapp': bool(self.whatsapp and self.whatsapp.strip()),
            'platform': bool(self.preferred_platform and self.preferred_platform.strip()),
            'payment': bool(self.preferred_payment and self.preferred_payment.strip()),
            'ea_email': bool(self.ea_email and self.ea_email.strip()),
            'telegram': bool(self.telegram_id and self.telegram_id.strip()),
        }
        
        completed_count = sum(1 for completed in steps.values() if completed)
        total_count = len(steps)
        percentage = round((completed_count / total_count) * 100)
        
        return {
            'steps': steps,
            'completed_count': completed_count,
            'total_count': total_count,
            'percentage': percentage,
            'is_completed': self.profile_completed
        }

class Order(db.Model):
    __tablename__ = 'orders'  # Explicit table name
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    coins_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # حقول إضافية للطلبات مع default values آمنة
    ea_email = db.Column(db.String(100), default='')
    ea_password = db.Column(db.String(200), default='')  # مشفرة
    backup_codes = db.Column(db.Text, default='')  # مشفرة أيضاً
    transfer_type = db.Column(db.String(20), default='normal')  # normal, instant
    notes = db.Column(db.Text, default='')
    price = db.Column(db.Float, default=0.0)
    phone_number = db.Column(db.String(20), default='')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@app.context_processor
def inject_datetime():
    """إضافة دوال التاريخ لجميع القوالب"""
    return {
        'moment': lambda: datetime,
        'now': datetime.now(),
        'datetime': datetime
    }

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
# السطر الذي يسبق الكتلة مباشرة:
        return True  # Don't block registration if email fails

#  تحديث دالة verify_recaptcha_advanced 
def verify_recaptcha_advanced(token, request):
    if not app.config['RECAPTCHA_SECRET_KEY']:
        app.logger.warning("reCAPTCHA not configured - allowing request to pass")
        return {'success': True, 'penalty': 0}
    
    if not token:
        app.logger.warning("No reCAPTCHA token provided")
        return {'success': False, 'penalty': 4}
    
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': app.config['RECAPTCHA_SECRET_KEY'],
                'response': token,
                'remoteip': get_remote_address()
            },
            timeout=10
        )
        result = response.json()
        
        success = result.get('success', False)
        score = result.get('score', 0)
        action = result.get('action', 'unknown')
        hostname = result.get('hostname', '')
        challenge_ts = result.get('challenge_ts', '')
        
        app.logger.info(f"reCAPTCHA result - Success: {success}, Score: {score}, Action: {action}")
        
        penalty_score = 0
        
        if not success:
            penalty_score = 5
            app.logger.warning(f"reCAPTCHA failed - Errors: {result.get('error-codes', [])}")
            return {'success': False, 'penalty': penalty_score}
        
        # تحليل النقاط مع معايير متوازنة
        if score < 0.1:
            penalty_score = 5  # مشبوه جداً
        elif score < 0.3:
            penalty_score = 3  # مشبوه
        elif score < 0.5:
            penalty_score = 2  # حذر
        elif score < 0.7:
            penalty_score = 1  # حذر قليل
        else:
            penalty_score = 0  # آمن
        
        # فحص Action consistency مخفف
        expected_actions = ['login', 'register', 'submit']
        if action not in expected_actions and action != 'unknown':
            penalty_score += 1
            app.logger.warning(f"Unexpected reCAPTCHA action: {action}")
        
        # فحص الـ hostname مخفف
        expected_hostnames = ['senioraa.onrender.com', 'localhost', '127.0.0.1']
        if hostname and not any(host in hostname for host in expected_hostnames):
            penalty_score += 1
            app.logger.warning(f"Unexpected hostname in reCAPTCHA: {hostname}")
        
        # فحص التوقيت مخفف
        if challenge_ts:
            try:
                from datetime import datetime
                import dateutil.parser
                challenge_time = dateutil.parser.parse(challenge_ts)
                current_time = datetime.utcnow()
                time_diff = (current_time - challenge_time).total_seconds()
                
                if time_diff > 600:  # أكثر من 10 دقائق
                    penalty_score += 1
                    app.logger.warning(f"Old reCAPTCHA token used: {time_diff}s old")
            except:
                penalty_score += 0  # تجاهل الأخطاء
        
        # العتبة الجديدة المتوازنة
        final_success = penalty_score < 4
        
        app.logger.info(f"reCAPTCHA advanced verification - Final: {final_success}, Penalty: {penalty_score}")
        
        return {'success': final_success, 'penalty': penalty_score}
            
    except Exception as e:
        app.logger.error(f"reCAPTCHA verification error: {e}")
        return {'success': True, 'penalty': 0}

# السطر الذي يلي الكتلة مباشرة:
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
# السطر الذي يسبق الكتلة مباشرة:
    return hashlib.md5((timestamp + secret).encode()).hexdigest(), timestamp

# تحديث دالة verify_time_token
def verify_time_token_advanced(token, timestamp, form_data):
    """التحقق المتقدم من الرمز المؤقت مع تحليل سلوكي"""
    try:
        current_time = int(time.time())
        form_time = int(timestamp)
        time_diff = current_time - form_time
        
        # تحليل وقت ملء النموذج
        if time_diff < 2:  # أقل من ثانيتين = مشبوه جداً
            app.logger.warning(f"Form submitted too quickly: {time_diff}s")
            return False
        
        if time_diff > 3600:  # أكثر من ساعة = منتهي الصلاحية
            app.logger.warning(f"Form token expired: {time_diff}s old")
            return False
        
        # فحص التوقيت المناسب للبيانات المُدخلة
        email = form_data.get('email', '')
        password = form_data.get('password', '')
        
        # تقدير الوقت المطلوب لملء النموذج
        estimated_time = 0
        if email:
            estimated_time += len(email) * 0.1  # 100ms لكل حرف
        if password:
            estimated_time += len(password) * 0.15  # 150ms لكل حرف
        
        estimated_time += 3  # وقت إضافي للقراءة والتفكير
        
        if time_diff < estimated_time:
            app.logger.warning(f"Form filled faster than humanly possible: {time_diff}s vs estimated {estimated_time}s")
            return False
        
        # التحقق من صحة الرمز
        secret = app.config['CAPTCHA_SECRET']
        expected_token = hashlib.md5((timestamp + secret).encode()).hexdigest()
        
        if token != expected_token:
            app.logger.warning("Invalid time token signature")
            return False
        
        return True
        
    except Exception as e:
        app.logger.error(f"Time token verification error: {e}")
        return False

# السطر الذي يلي الكتلة مباشرة:
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
    
# السطر الذي يسبق الكتلة مباشرة:
    return False

# تحديث دالة comprehensive_captcha_check
def comprehensive_captcha_check(request, form_data):
    client_ip = get_remote_address()
    
    # فحص الـ endpoints المستثناة
    if any(request.path.startswith(endpoint) for endpoint in EXEMPT_ENDPOINTS):
        return True
    
    # تحديد مستوى الثقة
    trust_level = get_trust_level(request)
    
    # المصادر عالية الثقة تمر بفحوصات مخففة
    if trust_level == 'high':
        app.logger.info(f"High trust request from {client_ip} - applying relaxed checks")
        
        # فحص Honeypot فقط للمصادر عالية الثقة
        if not check_honeypot(form_data):
            track_suspicious_session(client_ip, 'honeypot_hit', 3)  # عقوبة مخففة
            app.logger.warning(f"Honeypot check failed for trusted IP: {client_ip}")
            return False
        
        # فحص reCAPTCHA مخفف للمصادر الموثوقة
        recaptcha_token = form_data.get('g-recaptcha-response', '')
        if recaptcha_token:
            recaptcha_result = verify_recaptcha_advanced(recaptcha_token, request)
            if not recaptcha_result['success'] and recaptcha_result['penalty'] > 4:
                app.logger.warning(f"reCAPTCHA failed for trusted IP {client_ip} with high penalty: {recaptcha_result['penalty']}")
                return False
        
        return True
    
    # المصادر متوسطة الثقة
    elif trust_level == 'medium':
        app.logger.info(f"Medium trust request from {client_ip} - applying moderate checks")
        
        # فحص الحظر المؤقت
        is_blocked, remaining_time = is_session_blocked(client_ip)
        if is_blocked:
            app.logger.warning(f"Request from blocked session {client_ip}")
            return False
        
        # فحص Honeypot
        if not check_honeypot(form_data):
            track_suspicious_session(client_ip, 'honeypot_hit', 5)
            app.logger.warning(f"Honeypot check failed for IP: {client_ip}")
            return False
        
        # فحص Time Token مخفف
        time_token = form_data.get('time_token', '')
        timestamp = form_data.get('timestamp', '')
        
        if not verify_time_token(time_token, timestamp):
            track_suspicious_session(client_ip, 'invalid_time_token', 2)
            app.logger.warning(f"Time token verification failed for IP: {client_ip}")
            return False
        
        # فحص reCAPTCHA
        recaptcha_token = form_data.get('g-recaptcha-response', '')
        if recaptcha_token:
            recaptcha_result = verify_recaptcha_advanced(recaptcha_token, request)
            if not recaptcha_result['success']:
                track_suspicious_session(client_ip, 'recaptcha_failed', recaptcha_result['penalty'])
                app.logger.warning(f"reCAPTCHA verification failed for IP: {client_ip}")
                return False
        else:
            track_suspicious_session(client_ip, 'missing_recaptcha', 2)
            app.logger.warning(f"No reCAPTCHA token provided from {client_ip}")
            return False
        
        return True
    
    # المصادر منخفضة الثقة - فحص كامل
    else:
        app.logger.info(f"Low trust request from {client_ip} - applying full checks")
        
        # فحص الحظر المؤقت
        is_blocked, remaining_time = is_session_blocked(client_ip)
        if is_blocked:
            app.logger.warning(f"Request from blocked session {client_ip}")
            return False
        
        # فحص VPN/Proxy مخفف
        if not detect_vpn_proxy(request):
            track_suspicious_session(client_ip, 'vpn_proxy_detected', 4)  # عقوبة مخففة
            app.logger.warning(f"VPN/Proxy detected from {client_ip}")
            return False
        
        # فحص Browser Automation مخفف
        if not detect_automation(request):
            track_suspicious_session(client_ip, 'automation_detected', 5)  # عقوبة مخففة
            app.logger.warning(f"Browser automation detected from {client_ip}")
            return False
        
        # فحص سلوك البوت الأساسي
        if is_bot_behavior(request):
            track_suspicious_session(client_ip, 'bot_behavior', 2)
            app.logger.warning(f"Bot behavior detected from {client_ip}")
            return False
        
        # فحص Honeypot
        if not check_honeypot(form_data):
            track_suspicious_session(client_ip, 'honeypot_hit', 8)
            app.logger.warning(f"Honeypot check failed for IP: {client_ip}")
            return False
        
        # فحص Time Token
        time_token = form_data.get('time_token', '')
        timestamp = form_data.get('timestamp', '')
        
        if not verify_time_token_advanced(time_token, timestamp, form_data):
            track_suspicious_session(client_ip, 'invalid_time_token', 3)
            app.logger.warning(f"Advanced time token verification failed for IP: {client_ip}")
            return False
        
        # فحص reCAPTCHA
        recaptcha_token = form_data.get('g-recaptcha-response', '')
        if recaptcha_token:
            recaptcha_result = verify_recaptcha_advanced(recaptcha_token, request)
            if not recaptcha_result['success']:
                track_suspicious_session(client_ip, 'recaptcha_failed', recaptcha_result['penalty'])
                app.logger.warning(f"Advanced reCAPTCHA verification failed for IP: {client_ip}")
                return False
        else:
            track_suspicious_session(client_ip, 'missing_recaptcha', 3)
            app.logger.warning(f"No reCAPTCHA token provided from {client_ip}")
            return False
        
        # فحص التحليل السلوكي مخفف
        behavioral_score = advanced_behavioral_analysis(form_data, request)
        if behavioral_score > 7:  # عتبة أعلى
            track_suspicious_session(client_ip, 'suspicious_behavior', behavioral_score)
            app.logger.warning(f"Suspicious behavioral analysis for IP: {client_ip}, score: {behavioral_score}")
            return False
        
        return True

# السطر الذي يلي الكتلة مباشرة:
def generate_device_fingerprint_advanced(request):
    """إنشاء بصمة جهاز متقدمة للكشف عن التلاعب"""
    ip = get_remote_address()
    
    # جمع بيانات أكثر تفصيلاً
    advanced_data = {
        'user_agent': request.headers.get('User-Agent', '')[:200],
        'accept': request.headers.get('Accept', '')[:100],
        'accept_language': request.headers.get('Accept-Language', '')[:50],
        'accept_encoding': request.headers.get('Accept-Encoding', '')[:50],
        'connection': request.headers.get('Connection', '')[:20],
        'upgrade_insecure_requests': request.headers.get('Upgrade-Insecure-Requests', ''),
        'sec_fetch_site': request.headers.get('Sec-Fetch-Site', ''),
        'sec_fetch_mode': request.headers.get('Sec-Fetch-Mode', ''),
        'sec_fetch_user': request.headers.get('Sec-Fetch-User', ''),
        'sec_fetch_dest': request.headers.get('Sec-Fetch-Dest', ''),
        'cache_control': request.headers.get('Cache-Control', '')[:50],
        'pragma': request.headers.get('Pragma', ''),
        'dnt': request.headers.get('DNT', ''),
        'te': request.headers.get('TE', ''),
        'sec_ch_ua': request.headers.get('Sec-CH-UA', '')[:100],
        'sec_ch_ua_mobile': request.headers.get('Sec-CH-UA-Mobile', ''),
        'sec_ch_ua_platform': request.headers.get('Sec-CH-UA-Platform', ''),
        'viewport': request.headers.get('Viewport-Width', '')
    }
    
    # تحليل التناقضات في البيانات
    inconsistency_score = 0
    
    # فحص User-Agent vs Sec-CH-UA
    ua = advanced_data['user_agent'].lower()
    sec_ua = advanced_data['sec_ch_ua'].lower()
    
    if 'chrome' in ua and 'chrome' not in sec_ua and sec_ua:
        inconsistency_score += 3
    elif 'firefox' in ua and 'chrome' in sec_ua:
        inconsistency_score += 3
    
    # فحص Mobile indicators
    is_mobile_ua = any(mobile in ua for mobile in ['mobile', 'android', 'iphone'])
    sec_mobile = advanced_data['sec_ch_ua_mobile'] == '?1'
    
    if is_mobile_ua != sec_mobile and advanced_data['sec_ch_ua_mobile']:
        inconsistency_score += 2
    
    # فحص Platform consistency
    platform = advanced_data['sec_ch_ua_platform'].lower()
    if 'windows' in ua and 'android' in platform:
        inconsistency_score += 3
    elif 'mac' in ua and 'windows' in platform:
        inconsistency_score += 3
    
    # فحص Headers المفقودة المشبوهة
    modern_headers = ['sec_fetch_site', 'sec_fetch_mode', 'sec_ch_ua']
    missing_modern = sum(1 for h in modern_headers if not advanced_data[h])
    
    if missing_modern >= 2 and 'chrome' in ua:
        inconsistency_score += 2
    
    # حساب hash البصمة
    fingerprint_string = '|'.join(str(v) for v in advanced_data.values())
    fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]
    
    advanced_data['inconsistency_score'] = inconsistency_score
    
    return fingerprint_hash, advanced_data

##   إضافة دالة detect_automation
def detect_automation(request):
    """كشف أدوات التشغيل الآلي المتقدم"""
    automation_score = 0
    client_ip = get_remote_address()
    
    # فحص WebDriver properties (يتم إضافتها في JavaScript)
    automation_indicators = request.form.get('automation_check', '')
    if automation_indicators:
        indicators = json.loads(automation_indicators) if automation_indicators else {}
        
        # فحص وجود WebDriver
        if indicators.get('webdriver', False):
            automation_score += 5
            app.logger.warning(f"WebDriver detected from {client_ip}")
        
        # فحص أدوات التطوير
        if indicators.get('devtools', False):
            automation_score += 3
        
        # فحص الـ plugins المشبوهة
        if indicators.get('suspicious_plugins', 0) > 0:
            automation_score += 2
        
        # فحص سلوك المتصفح غير الطبيعي
        if indicators.get('screen_inconsistency', False):
            automation_score += 4
        
        # فحص عدم وجود events طبيعية
        if indicators.get('no_mouse_movement', False):
            automation_score += 3
    
    # فحص headers مشبوهة للـ automation
    user_agent = request.headers.get('User-Agent', '').lower()
    automation_keywords = [
        'headless', 'phantomjs', 'selenium', 'webdriver', 
        'chrome-lighthouse', 'chromedriver', 'geckodriver',
        'puppeteer', 'playwright'
    ]
    
    for keyword in automation_keywords:
        if keyword in user_agent:
            automation_score += 4
            app.logger.warning(f"Automation keyword '{keyword}' in UA from {client_ip}")
    
    # فحص عدم وجود referrer طبيعي
    referrer = request.headers.get('Referer', '')
    if not referrer and request.method == 'POST':
        automation_score += 2
    
    app.logger.info(f"Automation detection score for {client_ip}: {automation_score}")
    
# السطر السابق:
    return automation_score < 8  # السماح إذا كان أقل من 8 نقاط

def is_trusted_request(request):
    client_ip = get_remote_address()
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # IPs موثوقة
    trusted_ips = ['127.0.0.1', 'localhost']
    if any(ip in client_ip for ip in trusted_ips):
        return True
    
    # User-Agents موثوقة (متصفحات حقيقية)
    trusted_browsers = [
        'chrome/', 'firefox/', 'safari/', 'edge/', 'opera/',
        'miuibrowser/', 'samsungbrowser/', 'yabrowser/'
    ]
    
    if any(browser in user_agent for browser in trusted_browsers):
        # فحص إضافي للمتصفحات الحقيقية
        required_headers = ['accept', 'accept-language', 'accept-encoding']
        missing_headers = sum(1 for h in required_headers if not request.headers.get(h.replace('-', '_').title()))
        
        if missing_headers == 0:
            return True
    
    return False

def get_trust_level(request):
    if is_trusted_request(request):
        return 'high'
    
    client_ip = get_remote_address()
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            return 'medium'
    except:
        pass
    
    return 'low'

#  إضافة دالة detect_vpn_proxy جديدة في ملف app.py
def detect_vpn_proxy(request):
    """كشف VPN والـ Proxy المتقدم"""
    client_ip = get_remote_address()
    vpn_score = 0
    
    # قائمة مؤشرات VPN/Proxy
    vpn_indicators = []
    
    # فحص headers مشبوهة للـ proxy
    proxy_headers = [
        'HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'HTTP_X_CLUSTER_CLIENT_IP',
        'HTTP_CLIENT_IP', 'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED',
        'HTTP_VIA', 'HTTP_X_FORWARDED_PROTO'
    ]
    
    for header in proxy_headers:
        if request.environ.get(header):
            vpn_score += 1
            vpn_indicators.append(f"proxy_header_{header}")
    
    # فحص User-Agent patterns للـ VPN clients
    user_agent = request.headers.get('User-Agent', '').lower()
    vpn_patterns = [
        'openvpn', 'nordvpn', 'expressvpn', 'cyberghost', 'protonvpn',
        'surfshark', 'tunnelbear', 'hotspot shield', 'windscribe'
    ]
    
    for pattern in vpn_patterns:
        if pattern in user_agent:
            vpn_score += 3
            vpn_indicators.append(f"vpn_ua_{pattern}")
    
    # فحص timezone inconsistency
    timezone_header = request.headers.get('X-Timezone', '')
    accept_language = request.headers.get('Accept-Language', '')
    
    if timezone_header and accept_language:
        # تحليل بسيط للتناقض الجغرافي
        if ('us' in accept_language.lower() and 'europe' in timezone_header.lower()) or \
           ('gb' in accept_language.lower() and 'america' in timezone_header.lower()):
            vpn_score += 2
            vpn_indicators.append("timezone_mismatch")
    
    # فحص DNS leaks (إذا توفرت معلومات)
    x_real_ip = request.headers.get('X-Real-IP', '')
    x_forwarded_for = request.headers.get('X-Forwarded-For', '')
    
    if x_real_ip and x_forwarded_for and x_real_ip != x_forwarded_for:
        vpn_score += 2
        vpn_indicators.append("ip_mismatch")
    
    # فحص connection patterns
    connection = request.headers.get('Connection', '').lower()
    if 'keep-alive' not in connection and connection:
        vpn_score += 1
        vpn_indicators.append("unusual_connection")
    
    app.logger.info(f"VPN/Proxy detection for {client_ip}: score = {vpn_score}, indicators = {vpn_indicators}")
    
    return vpn_score < 6  # السماح إذا كان أقل من 6 نقاط

# السطر التالي:
def is_suspicious_fingerprint(fingerprint_data):
    """فحص بصمة الجهاز للعلامات المشبوهة"""
    suspicious_indicators = 0
    
    # فحص User-Agent
    ua = fingerprint_data.get('user_agent', '').lower()
    if not ua or len(ua) < 20:
        suspicious_indicators += 1
    
    # فحص Accept headers
    accept = fingerprint_data.get('accept', '')
    if not accept or 'text/html' not in accept:
        suspicious_indicators += 1
    
    # فحص Accept-Language
    accept_lang = fingerprint_data.get('accept_language', '')
    if not accept_lang:
        suspicious_indicators += 1
    
    # فحص Sec-Fetch headers (علامة على متصفح حديث)
    sec_fetch_site = fingerprint_data.get('sec_fetch_site', '')
    sec_fetch_mode = fingerprint_data.get('sec_fetch_mode', '')
    if not sec_fetch_site and not sec_fetch_mode:
        suspicious_indicators += 1
    
    # إذا كان هناك 3 أو أكثر من العلامات المشبوهة
    return suspicious_indicators >= 3

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

@app.route('/admin/security-stats')
@login_required
@advanced_rate_limit(per_minute=10, per_hour=50)
def security_stats():
    """إحصائيات الأمان للمدير"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # إحصائيات Rate Limiting
        total_ips = len(smart_limiter.suspicious_ips)
        blocked_ips = sum(1 for ip_data in smart_limiter.suspicious_ips.values() 
                         if ip_data['score'] < -50)
        trusted_ips = sum(1 for ip_data in smart_limiter.suspicious_ips.values() 
                         if ip_data['score'] > 50)
        
        # إحصائيات المستخدمين
        total_users = User.query.count()
        verified_users = User.query.filter_by(is_verified=True).count()
        
        # إحصائيات الطلبات الأخيرة
        recent_time = datetime.utcnow() - timedelta(hours=1)
        recent_registrations = User.query.filter(User.created_at >= recent_time).count()
        
        return jsonify({
            'rate_limiting': {
                'total_tracked_ips': total_ips,
                'blocked_ips': blocked_ips,
                'trusted_ips': trusted_ips,
                'suspicious_ratio': round(blocked_ips / max(1, total_ips) * 100, 2)
            },
            'users': {
                'total_users': total_users,
                'verified_users': verified_users,
                'verification_rate': round(verified_users / max(1, total_users) * 100, 2),
                'recent_registrations': recent_registrations
            },
            'system': {
                'redis_connected': smart_limiter.redis_client is not None,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        app.logger.error(f"Security stats error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/advanced-security-stats')
@login_required
@advanced_rate_limit(per_minute=5, per_hour=20)
def advanced_security_stats():
    """ إحصائيات أمان متقدمة للمدير"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        current_time = int(time.time())
        
        # إحصائيات محاولات تغيير كلمة المرور
        recent_time = datetime.utcnow() - timedelta(hours=24)
        
        # تحليل الأنشطة المشبوهة
        high_risk_activities = {
            'honeypot_hits': sum(1 for data in suspicious_sessions.values() 
                               if 'honeypot' in str(data)),
            'automation_detected': sum(1 for data in suspicious_sessions.values() 
                                     if data.get('suspicious_score', 0) > 10),
            'failed_password_attempts': sum(1 for data in suspicious_sessions.values() 
                                          if 'password' in str(data)),
            'vpn_proxy_detected': sum(1 for data in suspicious_sessions.values() 
                                    if 'vpn' in str(data))
        }
        
        # إحصائيات المستخدمين
        user_stats = {
            'total_users': User.query.count(),
            'verified_users': User.query.filter_by(is_verified=True).count(),
            'admin_users': User.query.filter_by(is_admin=True).count(),
            'recent_registrations': User.query.filter(User.created_at >= recent_time).count()
        }
        
        # إحصائيات الطلبات  
        order_stats = {
            'total_orders': Order.query.count(),
            'pending_orders': Order.query.filter_by(status='pending').count(),
            'completed_orders': Order.query.filter_by(status='completed').count(),
            'recent_orders': Order.query.filter(Order.created_at >= recent_time).count()
        }
        
        # تحليل الأمان العام
        security_score = calculate_security_score(high_risk_activities, user_stats)
        
        return jsonify({
            'security_activities': high_risk_activities,
            'user_statistics': user_stats,
            'order_statistics': order_stats,
            'security_score': security_score,
            'recommendations': generate_security_recommendations(high_risk_activities),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Advanced security stats error: {e}")
        return jsonify({'error': str(e)}), 500

def calculate_security_score(activities, user_stats):
    """حساب نقاط الأمان العامة"""
    base_score = 100
    
    # خصم النقاط حسب الأنشطة المشبوهة
    base_score -= activities.get('honeypot_hits', 0) * 5
    base_score -= activities.get('automation_detected', 0) * 10
    base_score -= activities.get('failed_password_attempts', 0) * 3
    base_score -= activities.get('vpn_proxy_detected', 0) * 2
    
    # مكافآت للمؤشرات الإيجابية
    verification_rate = user_stats.get('verified_users', 0) / max(1, user_stats.get('total_users', 1))
    if verification_rate > 0.8:
        base_score += 10
    
    return max(0, min(100, base_score))

def generate_security_recommendations(activities):
    """توليد توصيات أمنية"""
    recommendations = []
    
    if activities.get('honeypot_hits', 0) > 5:
        recommendations.append(" تم اكتشاف عدد عالي من محاولات البوتات - فكر في تشديد الحماية")
    
    if activities.get('automation_detected', 0) > 3:
        recommendations.append(" تم اكتشاف أدوات أتمتة - راجع إعدادات reCAPTCHA")
    
    if activities.get('failed_password_attempts', 0) > 10:
        recommendations.append(" محاولات كلمة مرور مشبوهة - فعل التنبيهات")
    
    if not recommendations:
        recommendations.append(" النظام آمن حالياً - استمر في المراقبة")
    
    return recommendations

@app.route('/admin/quick-stats')
@login_required
def quick_security_stats():
    """إحصائيات أمان سريعة"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # إحصائيات الحظر الحالي
        current_time = int(time.time())
        active_blocks = sum(1 for data in suspicious_sessions.values() 
                          if data['blocked_until'] > current_time)
        
        # إحصائيات النشاط المشبوه
        high_risk_ips = sum(1 for data in suspicious_sessions.values() 
                          if data['suspicious_score'] >= 5)
        
        return jsonify({
            'active_blocks': active_blocks,
            'high_risk_ips': high_risk_ips,
            'total_tracked_sessions': len(suspicious_sessions),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/security-actions', methods=['POST'])
@login_required
@advanced_rate_limit(per_minute=5, per_hour=20)
def security_actions():
    """إجراءات أمنية للمدير"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        action = request.json.get('action')
        target = request.json.get('target')
        
        if action == 'unblock_ip':
            if smart_limiter.redis_client:
                smart_limiter.redis_client.delete(f"temp_block:{target}")
            if target in smart_limiter.suspicious_ips:
                smart_limiter.suspicious_ips[target]['score'] = 0
            app.logger.info(f"Admin {current_user.email} unblocked IP {target}")
            return jsonify({'success': True, 'message': 'IP unblocked successfully'})
        
        elif action == 'reset_reputation':
            if target in smart_limiter.suspicious_ips:
                smart_limiter.suspicious_ips[target]['score'] = 0
            if smart_limiter.redis_client:
                smart_limiter.redis_client.delete(f"reputation:ip:{target}")
            app.logger.info(f"Admin {current_user.email} reset reputation for {target}")
            return jsonify({'success': True, 'message': 'Reputation reset successfully'})
        
        elif action == 'cleanup_old_data':
            smart_limiter._cleanup_old_data(int(time.time()))
            app.logger.info(f"Admin {current_user.email} triggered data cleanup")
            return jsonify({'success': True, 'message': 'Old data cleaned successfully'})
        
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    except Exception as e:
        app.logger.error(f"Security action error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/order/<int:order_id>/details')
@login_required
@advanced_rate_limit(per_minute=30, per_hour=200)
def get_order_details(order_id):
    """الحصول على تفاصيل طلب محدد"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        order = Order.query.get_or_404(order_id)
        
        order_details = {
            'id': order.id,
            'platform': order.platform,
            'coins_amount': order.coins_amount,
            'price': order.price,
            'transfer_type': order.transfer_type or 'normal',
            'payment_method': order.payment_method,
            'phone_number': order.phone_number,
            'ea_email': order.ea_email,
            'notes': order.notes,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat() if order.updated_at else None,
            'user_email': order.user.email,
            'user_telegram_linked': bool(order.user.telegram_id)
        }
        
        return jsonify({
            'success': True,
            'order': order_details
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching order details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/export/orders')
@login_required
@advanced_rate_limit(per_minute=2, per_hour=10)
def export_orders():
    """تصدير الطلبات إلى CSV"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        import csv
        import io
        from flask import make_response
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # رؤوس الأعمدة
        writer.writerow([
            'رقم الطلب', 'البريد الإلكتروني', 'المنصة', 'كمية الكوينز', 
            'السعر', 'طريقة الدفع', 'نوع التحويل', 'الحالة', 
            'رقم الواتساب', 'تاريخ الإنشاء'
        ])
        
        # بيانات الطلبات
        orders = Order.query.join(User).all()
        for order in orders:
            writer.writerow([
                order.id,
                order.user.email,
                order.platform,
                order.coins_amount,
                order.price or 0,
                order.payment_method,
                order.transfer_type or 'normal',
                order.status,
                order.phone_number or '',
                order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # إعداد الاستجابة
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        app.logger.info(f"Orders exported by admin: {current_user.email}")
        return response
        
    except Exception as e:
        app.logger.error(f"Error exporting orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/export/all')
@login_required
@advanced_rate_limit(per_minute=1, per_hour=5)
def export_all_data():
    """تصدير جميع البيانات إلى ZIP"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        import zipfile
        import io
        import csv
        from flask import make_response
        
        # إنشاء ملف ZIP في الذاكرة
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # تصدير الطلبات
            orders_csv = io.StringIO()
            orders_writer = csv.writer(orders_csv)
            orders_writer.writerow([
                'رقم الطلب', 'البريد الإلكتروني', 'المنصة', 'كمية الكوينز', 
                'السعر', 'طريقة الدفع', 'نوع التحويل', 'الحالة', 
                'رقم الواتساب', 'تاريخ الإنشاء'
            ])
            
            orders = Order.query.join(User).all()
            for order in orders:
                orders_writer.writerow([
                    order.id, order.user.email, order.platform,
                    order.coins_amount, order.price or 0, order.payment_method,
                    order.transfer_type or 'normal', order.status,
                    order.phone_number or '', order.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            zip_file.writestr('orders.csv', orders_csv.getvalue().encode('utf-8-sig'))
            
            # تصدير المستخدمين
            users_csv = io.StringIO()
            users_writer = csv.writer(users_csv)
            users_writer.writerow([
                'البريد الإلكتروني', 'مفعل', 'مدير', 'رقم الواتساب',
                'المنصة المفضلة', 'طريقة الدفع المفضلة', 'بريد EA',
                'معرف التليجرام', 'تاريخ التسجيل'
            ])
            
            users = User.query.all()
            for user in users:
                users_writer.writerow([
                    user.email, user.is_verified, user.is_admin,
                    user.whatsapp or '', user.preferred_platform or '',
                    user.preferred_payment or '', user.ea_email or '',
                    user.telegram_id or '', user.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            zip_file.writestr('users.csv', users_csv.getvalue().encode('utf-8-sig'))
            
            # إضافة ملف إحصائيات
            stats = calculate_admin_statistics()
            stats_content = f"""تقرير إحصائيات النظام
تاريخ التصدير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

إحصائيات المستخدمين:
- إجمالي المستخدمين: {stats.get('users', {}).get('total', 0)}
- المستخدمين المفعلين: {stats.get('users', {}).get('verified', 0)}
- معدل التفعيل: {stats.get('users', {}).get('verification_rate', 0):.1f}%
- مربوطين بالتليجرام: {stats.get('users', {}).get('telegram_linked', 0)}

إحصائيات الطلبات:
- إجمالي الطلبات: {stats.get('orders', {}).get('total', 0)}
- الطلبات المكتملة: {stats.get('orders', {}).get('completed', 0)}
- معدل الإنجاز: {stats.get('orders', {}).get('completion_rate', 0):.1f}%

الإيرادات:
- إجمالي الإيرادات: {stats.get('revenue', {}).get('total', 0):,.2f} جنيه
- متوسط قيمة الطلب: {stats.get('revenue', {}).get('avg_order', 0):,.2f} جنيه
"""
            zip_file.writestr('statistics.txt', stats_content.encode('utf-8'))
        
        zip_buffer.seek(0)
        
        response = make_response(zip_buffer.getvalue())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename=complete_data_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        
        app.logger.info(f"Complete data export by admin: {current_user.email}")
        return response
        
    except Exception as e:
        app.logger.error(f"Error exporting all data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/bulk-notification', methods=['POST'])
@login_required
@advanced_rate_limit(per_minute=1, per_hour=3)
def send_bulk_notification():
    """إرسال إشعار جماعي لجميع المستخدمين المربوطين بالتليجرام"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        if not telegram_system.is_configured():
            return jsonify({'error': 'Telegram system not configured'}), 503
        
        # الحصول على جميع المستخدمين المربوطين بالتليجرام
        users_with_telegram = User.query.filter(User.telegram_id.isnot(None)).all()
        
        if not users_with_telegram:
            return jsonify({'error': 'No users with Telegram linked'}), 400
        
        # تنسيق الرسالة
        formatted_message = f"""
📢 <b>إشعار من إدارة شهد السنيورة</b>

{message}

🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}

شكراً لاختيارك شهد السنيورة! 🎮
        """
        
        # إرسال الرسائل
        sent_count = 0
        failed_count = 0
        
        for user in users_with_telegram:
            success = telegram_system.send_message(user.telegram_id, formatted_message.strip())
            if success:
                sent_count += 1
            else:
                failed_count += 1
        
        app.logger.info(f"Bulk notification sent by {current_user.email}: {sent_count} sent, {failed_count} failed")
        
        return jsonify({
            'success': True,
            'message': f'تم إرسال الإشعار بنجاح',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_users': len(users_with_telegram)
        })
        
    except Exception as e:
        app.logger.error(f"Error sending bulk notification: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/logs')
@login_required
@advanced_rate_limit(per_minute=10, per_hour=50)
def view_system_logs():
    """عرض سجلات النظام"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        import os
        
        logs_content = ""
        log_file_path = "logs/app.log"
        
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8') as f:
                # قراءة آخر 1000 سطر
                lines = f.readlines()
                logs_content = ''.join(lines[-1000:])
        else:
            logs_content = "ملف السجلات غير موجود"
        
        # إنشاء صفحة HTML لعرض السجلات
        html_content = f"""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سجلات النظام</title>
    <style>
        body {{
            font-family: 'Courier New', monospace;
            background: #1a1a1a;
            color: #f0f0f0;
            padding: 20px;
            margin: 0;
        }}
        .log-container {{
            background: #2d2d2d;
            border-radius: 10px;
            padding: 20px;
            white-space: pre-wrap;
            font-size: 12px;
            line-height: 1.4;
            max-height: 80vh;
            overflow-y: auto;
        }}
        .log-header {{
            background: #4a5568;
            color: white;
            padding: 15px;
            border-radius: 10px 10px 0 0;
            margin: -20px -20px 20px -20px;
        }}
        .error {{ color: #ff6b6b; }}
        .warning {{ color: #ffa500; }}
        .info {{ color: #4dabf7; }}
        .success {{ color: #51cf66; }}
    </style>
</head>
<body>
    <div class="log-header">
        <h2>سجلات النظام - شهد السنيورة</h2>
        <p>آخر 1000 سطر - تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="log-container">{logs_content}</div>
    <script>
        // تمرير تلقائي لأسفل
        document.querySelector('.log-container').scrollTop = 
            document.querySelector('.log-container').scrollHeight;
        
        // تحديث تلقائي كل 30 ثانية
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
        """
        
        from flask import make_response
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        
        return response
        
    except Exception as e:
        app.logger.error(f"Error viewing system logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/repair-database', methods=['POST'])
@login_required
@advanced_rate_limit(per_minute=1, per_hour=3)
def repair_database_endpoint():
    """إصلاح قاعدة البيانات (للطوارئ فقط)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # إصلاح قاعدة البيانات
        repair_success = force_database_repair()
        
        if repair_success:
            app.logger.info(f"Database repair initiated by admin: {current_user.email}")
            return jsonify({
                'success': True,
                'message': 'تم إصلاح قاعدة البيانات بنجاح'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'فشل في إصلاح قاعدة البيانات'
            }), 500
            
    except Exception as e:
        app.logger.error(f"Database repair error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/backup', methods=['POST'])
@login_required
@advanced_rate_limit(per_minute=1, per_hour=2)
def create_database_backup():
    """إنشاء نسخة احتياطية من قاعدة البيانات"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        import json
        import os
        
        backup_data = {
            'backup_info': {
                'created_at': datetime.now().isoformat(),
                'created_by': current_user.email,
                'version': '1.0'
            },
            'users': [],
            'orders': []
        }
        
        # نسخ احتياطية للمستخدمين (بدون كلمات المرور)
        users = User.query.all()
        for user in users:
            backup_data['users'].append({
                'id': user.id,
                'email': user.email,
                'is_verified': user.is_verified,
                'is_admin': user.is_admin,
                'whatsapp': user.whatsapp,
                'preferred_platform': user.preferred_platform,
                'preferred_payment': user.preferred_payment,
                'ea_email': user.ea_email,
                'telegram_id': user.telegram_id,
                'telegram_username': user.telegram_username,
                'profile_completed': user.profile_completed,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_profile_update': user.last_profile_update.isoformat() if user.last_profile_update else None
            })
        
        # نسخ احتياطية للطلبات
        orders = Order.query.all()
        for order in orders:
            backup_data['orders'].append({
                'id': order.id,
                'user_id': order.user_id,
                'platform': order.platform,
                'payment_method': order.payment_method,
                'coins_amount': order.coins_amount,
                'status': order.status,
                'ea_email': order.ea_email,
                'transfer_type': order.transfer_type,
                'notes': order.notes,
                'price': order.price,
                'phone_number': order.phone_number,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None
            })
        
        # حفظ النسخة الاحتياطية
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_dir = "backups"
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backup_path = os.path.join(backup_dir, backup_filename)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        app.logger.info(f"Database backup created by {current_user.email}: {backup_filename}")
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء النسخة الاحتياطية بنجاح',
            'filename': backup_filename,
            'users_count': len(backup_data['users']),
            'orders_count': len(backup_data['orders'])
        })
        
    except Exception as e:
        app.logger.error(f"Error creating database backup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/telegram-test', methods=['POST'])
@login_required
@advanced_rate_limit(per_minute=2, per_hour=10)
def test_telegram_system():
    """اختبار نظام التليجرام (للمطورين)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        test_type = request.json.get('test_type', 'config')
        
        if test_type == 'config':
            # فحص إعدادات التليجرام
            return jsonify({
                'success': True,
                'telegram_configured': telegram_system.is_configured(),
                'bot_token_exists': bool(telegram_system.bot_token),
                'bot_username': telegram_system.bot_username,
                'webhook_url': telegram_system.webhook_url
            })
            
        elif test_type == 'webhook':
            # إعداد webhook
            if telegram_system.is_configured():
                result = telegram_system.setup_webhook()
                return jsonify({
                    'success': result,
                    'message': 'Webhook setup successfully' if result else 'Failed to setup webhook'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Telegram not configured'
                })
                
        elif test_type == 'notification':
            # اختبار إرسال إشعار
            if current_user.telegram_id:
                test_message = f"""
🧪 <b>رسالة اختبار</b>

✅ نظام التليجرام يعمل بشكل صحيح!

🕒 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 المرسل: {current_user.email}

🎮 شهد السنيورة - نظام الإشعارات
                """
                
                result = telegram_system.send_message(current_user.telegram_id, test_message.strip())
                return jsonify({
                    'success': result,
                    'message': 'Test notification sent' if result else 'Failed to send notification'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Admin Telegram not linked'
                })
                
        else:
            return jsonify({'error': 'Invalid test type'}), 400
            
    except Exception as e:
        app.logger.error(f"Telegram test error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/reset-blocks', methods=['POST'])
@login_required
def reset_all_blocks():
    """إعادة تعيين جميع عمليات الحظر - للطوارئ"""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # مسح جميع الحظوريات
        suspicious_sessions.clear()
        smart_limiter.suspicious_ips.clear()
        
        # مسح من Redis إذا متاح
        if smart_limiter.redis_client:
            for key in smart_limiter.redis_client.scan_iter("temp_block:*"):
                smart_limiter.redis_client.delete(key)
        
        app.logger.info(f"Admin {current_user.email} reset all blocks")
        return jsonify({'success': True, 'message': 'All blocks cleared successfully'})
        
    except Exception as e:
        app.logger.error(f"Reset blocks error: {e}")
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

def log_password_change_attempt(user_email, ip_address, success=True, reason=""):
    """📌 تسجيل محاولات تغيير كلمة المرور للمراجعة الأمنية"""
    status = "نجح" if success else "فشل"
    log_message = f"محاولة تغيير كلمة المرور - المستخدم: {user_email}, IP: {ip_address}, الحالة: {status}"
    
    if reason:
        log_message += f", السبب: {reason}"
    
    if success:
        app.logger.info(log_message)
    else:
        app.logger.warning(log_message)
        
        # إضافة تتبع للمحاولات المشبوهة
        track_suspicious_session(ip_address, 'failed_password_change', 2)

@app.route('/reset-admin-password', methods=['GET', 'POST'])
@login_required
def validate_password_strength(password):
    """ التحقق من قوة كلمة المرور مع معايير متقدمة"""
    errors = []
    score = 0
    
    # الطول الأساسي
    if len(password) < 8:
        errors.append("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        return False, errors, 0
    elif len(password) >= 12:
        score += 2
    else:
        score += 1
    
    # فحص الأحرف الكبيرة
    if any(c.isupper() for c in password):
        score += 1
    else:
        errors.append("يجب أن تحتوي على حرف كبير واحد على الأقل")
    
    # فحص الأحرف الصغيرة  
    if any(c.islower() for c in password):
        score += 1
    else:
        errors.append("يجب أن تحتوي على حرف صغير واحد على الأقل")
    
    # فحص الأرقام
    if any(c.isdigit() for c in password):
        score += 1
    else:
        errors.append("يجب أن تحتوي على رقم واحد على الأقل")
    
    # فحص الرموز الخاصة
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if any(c in special_chars for c in password):
        score += 2
    else:
        errors.append("يُنصح بإضافة رمز خاص (!@#$%^&*)")
    
    # فحص التكرار
    if len(set(password)) < len(password) * 0.7:
        errors.append("تجنب تكرار الأحرف كثيراً")
        score -= 1
    
    # كلمات مرور شائعة
    common_passwords = [
        "password", "123456", "admin123", "qwerty", 
        "password123", "admin", "administrator"
    ]
    if password.lower() in common_passwords:
        errors.append("كلمة المرور شائعة جداً، اختر كلمة أقوى")
        return False, errors, 0
    
    # تقييم النتيجة النهائية
    is_strong = score >= 5 and len(errors) <= 1
    
    return is_strong, errors, min(100, score * 15)

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
            
            # التحقق من كلمة المرور الحالية مع تسجيل المحاولات
            client_ip = get_remote_address()
            
            if not check_password_hash(current_user.password_hash, current_password):
                log_password_change_attempt(current_user.email, client_ip, False, "كلمة المرور الحالية خاطئة")
                flash('كلمة المرور الحالية غير صحيحة', 'error')
                return render_template('reset_admin_password.html')
            
            # التحقق المتقدم من قوة كلمة المرور الجديدة
            is_strong, password_errors, strength_score = validate_password_strength(new_password)
            
            if not is_strong:
                flash(f'كلمة المرور ضعيفة (النقاط: {strength_score}/100). المشاكل: {", ".join(password_errors)}', 'error')
                return render_template('reset_admin_password.html')
            
            # تحذير إذا كانت كلمة المرور متوسطة القوة
            if strength_score < 80:
                flash(f'تحذير: قوة كلمة المرور متوسطة ({strength_score}/100). يُنصح بتحسينها.', 'warning')
            
            if new_password != confirm_password:
                flash('كلمات المرور غير متطابقة', 'error')
                return render_template('reset_admin_password.html')
            
            # تحديث كلمة المرور
            current_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # تسجيل تفصيلي أكثر للأمان
            app.logger.info(f"Admin password reset for user: {current_user.email} from IP: {get_remote_address()}")
            
            # تحديث timestamp آخر تعديل للملف الشخصي  
            current_user.last_profile_update = datetime.utcnow()
            
            # إضافة تحديث سمعة المستخدم إيجابياً
            client_fingerprint = smart_limiter.get_client_fingerprint(request)
            smart_limiter.update_reputation(client_fingerprint, 'successful_action', current_user.id)
            flash('تم تغيير كلمة المرور بنجاح!', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error resetting admin password: {e}")
            flash('حدث خطأ أثناء تغيير كلمة المرور', 'error')
    
    return render_template('reset_admin_password.html')

@app.route('/register', methods=['GET', 'POST'])
@advanced_rate_limit(per_minute=5, per_hour=15, block_on_abuse=True)
def register():
    if request.method == 'GET':
        # إنشاء time token للنموذج
        time_token, timestamp = generate_time_token()
        return render_template('register.html', time_token=time_token, timestamp=timestamp)
    
    if request.method == 'POST':
        client_fingerprint = smart_limiter.get_client_fingerprint(request)
        
        try:
            # فحص Captcha الشامل
            if not comprehensive_captcha_check(request, request.form):
                smart_limiter.update_reputation(client_fingerprint, 'honeypot_hit')
                flash('فشل في التحقق من الأمان. يرجى المحاولة مرة أخرى.', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            email = request.form['email'].lower().strip()
            password = request.form['password']
            
            # Validate email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
                flash('البريد الإلكتروني غير صالح', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            # Check if email is from trusted domain
            if not is_valid_email(email):
                smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
                flash('يجب استخدام بريد إلكتروني من Gmail أو Hotmail أو iCloud أو Yahoo', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            # Check password length
            if len(password) < 6:
                smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
                flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('register.html', time_token=time_token, timestamp=timestamp)
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
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
                
                # تحديث السمعة إيجابياً للتسجيل الناجح
                smart_limiter.update_reputation(client_fingerprint, 'successful_action')
                
                flash('تم إرسال كود التفعيل إلى بريدك الإلكتروني', 'success')
                return redirect(url_for('verify_email'))
            else:
                flash('خطأ في إرسال البريد الإلكتروني، حاول مرة أخرى', 'error')
                
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
            flash('حدث خطأ أثناء التسجيل، حاول مرة أخرى', 'error')
        
        # في حالة الخطأ، إنشاء tokens جديدة
        time_token, timestamp = generate_time_token()
        return render_template('register.html', time_token=time_token, timestamp=timestamp)

def advanced_form_analysis(form_data, client_ip):
    """تحليل متقدم لبيانات النموذج للكشف عن السلوك المشبوه"""
    suspicious_score = 0
    
    # 1. تحليل البريد الإلكتروني
    email = form_data.get('email', '').lower()
    if email:
        # فحص النطاقات المشبوهة
        suspicious_domains = [
            'tempmail', '10minutemail', 'guerrillamail', 'mailinator',
            'yopmail', 'temp-mail', 'throwaway', 'dispostable'
        ]
        
        if any(domain in email for domain in suspicious_domains):
            suspicious_score += 3
            app.logger.warning(f"Suspicious email domain from {client_ip}: {email}")
        
        # فحص أنماط البريد المشبوهة
        if '+' in email.split('@')[0]:  # plus addressing
            suspicious_score += 1
        
        if email.count('.') > 3:  # نقاط كثيرة
            suspicious_score += 1
        
        if any(char.isdigit() for char in email) and email.count('1') > 3:
            suspicious_score += 1  # أرقام كثيرة متكررة
    
    # 2. تحليل كلمة المرور
    password = form_data.get('password', '')
    if password:
        # كلمات مرور شائعة للبوتات
        common_bot_passwords = [
            '123456', 'password', 'test123', 'admin123', 'qwerty',
            '111111', '000000', 'test', 'admin', 'user123'
        ]
        
        if password in common_bot_passwords:
            suspicious_score += 2
        
        # أنماط مشبوهة
        if password.isdigit() and len(password) == 6:  # أرقام فقط
            suspicious_score += 1
        
        if password == password.lower() and len(password) < 8:  # أحرف صغيرة فقط وقصيرة
            suspicious_score += 1
    
    # 3. تحليل توقيت الإدخال
    timestamp = form_data.get('timestamp', '')
    if timestamp:
        try:
            form_time = int(timestamp)
            current_time = int(time.time())
            filling_time = current_time - form_time
            
            # وقت قصير جداً (أقل من 5 ثوان) = بوت محتمل
            if filling_time < 5:
                suspicious_score += 2
            # وقت طويل جداً (أكثر من 30 دقيقة) = مشبوه
            elif filling_time > 1800:
                suspicious_score += 1
        except:
            suspicious_score += 1
    
    # 4. فحص تسلسل الحقول
    # إذا تم ملء جميع الحقول بنفس الترتيب دائماً = مشبوه
    fields_order = list(form_data.keys())
    expected_order = ['email', 'password', 'time_token', 'timestamp']
    
    if fields_order[:4] == expected_order:
        suspicious_score += 1  # ترتيب مثالي = مشبوه
    
    app.logger.info(f"Form analysis for {client_ip}: suspicious_score = {suspicious_score}")
    
# السطر الذي يسبق الكتلة مباشرة:
    return suspicious_score < 5  # السماح إذا كان أقل من 5 نقاط مشبوهة

#  إضافة نظام IP Reputation في ملف app.py
class IPReputationSystem:
    def __init__(self):
        self.ip_history = defaultdict(lambda: {
            'attempts': 0,
            'successful_logins': 0,
            'failed_logins': 0,
            'registrations': 0,
            'last_activity': 0,
            'reputation_score': 100,
            'countries': set(),
            'user_agents': set()
        })
        self.lock = Lock()
    
    def update_ip_activity(self, ip, activity_type, success=True):
        """تحديث نشاط IP"""
        with self.lock:
            current_time = int(time.time())
            data = self.ip_history[ip]
            
            data['attempts'] += 1
            data['last_activity'] = current_time
            
            if activity_type == 'login':
                if success:
                    data['successful_logins'] += 1
                    data['reputation_score'] = min(150, data['reputation_score'] + 5)
                else:
                    data['failed_logins'] += 1
                    data['reputation_score'] = max(0, data['reputation_score'] - 10)
            
            elif activity_type == 'register':
                data['registrations'] += 1
                if success:
                    data['reputation_score'] = min(150, data['reputation_score'] + 10)
                else:
                    data['reputation_score'] = max(0, data['reputation_score'] - 15)
            
            # تحليل patterns مشبوهة
            if data['failed_logins'] > 5:
                data['reputation_score'] = max(0, data['reputation_score'] - 20)
            
            if data['registrations'] > 3:
                data['reputation_score'] = max(0, data['reputation_score'] - 15)
    
    def get_ip_reputation(self, ip):
        """الحصول على سمعة IP"""
        return self.ip_history[ip]['reputation_score']
    
    def is_ip_suspicious(self, ip):
        """فحص ما إذا كان IP مشبوه"""
        data = self.ip_history[ip]
        
        # IP جديد تماماً
        if data['attempts'] == 0:
            return False
        
        # سمعة منخفضة
        if data['reputation_score'] < 30:
            return True
        
        # نسبة فشل عالية
        total_attempts = data['successful_logins'] + data['failed_logins']
        if total_attempts > 3 and (data['failed_logins'] / total_attempts) > 0.7:
            return True
        
        # تسجيلات كثيرة
        if data['registrations'] > 2:
            return True
        
        return False
    
    def cleanup_old_data(self):
        """تنظيف البيانات القديمة"""
        current_time = int(time.time())
        threshold = current_time - (7 * 24 * 3600)  # أسبوع
        
        old_ips = [ip for ip, data in self.ip_history.items() 
                  if data['last_activity'] < threshold]
        
        for ip in old_ips:
            del self.ip_history[ip]

# إنشاء instance من نظام السمعة
ip_reputation = IPReputationSystem()


# السطر الذي يلي الكتلة مباشرة:
@app.route('/verify-email', methods=['GET', 'POST'])
@advanced_rate_limit(per_minute=10, per_hour=30)
def verify_email():
    if 'user_email' not in session:
        flash('يجب التسجيل أولاً', 'error')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        client_fingerprint = smart_limiter.get_client_fingerprint(request)
        
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
                smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
                flash('كود التفعيل غير صحيح', 'error')
                return render_template('verify_email.html')
            
            if datetime.utcnow() > user.code_expiry:
                smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
                flash('كود التفعيل منتهي الصلاحية، يرجى طلب كود جديد', 'error')
                return render_template('verify_email.html')
            
            # تفعيل المستخدم
            user.is_verified = True
            user.verification_code = None
            user.code_expiry = None
            db.session.commit()
            
            # تحديث السمعة إيجابياً لتفعيل الحساب
            smart_limiter.update_reputation(client_fingerprint, 'account_verified')
            
            session.pop('user_email', None)
            flash('تم تفعيل حسابك بنجاح! يمكنك الآن تسجيل الدخول', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            app.logger.error(f"Verification error: {e}")
            smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
            flash('حدث خطأ أثناء التفعيل، حاول مرة أخرى', 'error')
    
    return render_template('verify_email.html')

@app.route('/login', methods=['GET', 'POST'])
@advanced_rate_limit(per_minute=8, per_hour=30, block_on_abuse=True)
def login():
    if request.method == 'GET':
        # إنشاء time token للنموذج
        time_token, timestamp = generate_time_token()
        return render_template('login.html', time_token=time_token, timestamp=timestamp)
    
    if request.method == 'POST':
        client_fingerprint = smart_limiter.get_client_fingerprint(request)
        
        try:
            # فحص Captcha الشامل
            if not comprehensive_captcha_check(request, request.form):
                smart_limiter.update_reputation(client_fingerprint, 'honeypot_hit')
                flash('فشل في التحقق من الأمان. يرجى المحاولة مرة أخرى.', 'error')
                time_token, timestamp = generate_time_token()
                return render_template('login.html', time_token=time_token, timestamp=timestamp)
            
            email = request.form['email'].lower().strip()
            password = request.form['password']
            
            user = User.query.filter_by(email=email).first()
            
            if user and check_password_hash(user.password_hash, password):
                if user.is_verified:
                    login_user(user)
                    
                    # تحديث السمعة إيجابياً لتسجيل الدخول الناجح
                    smart_limiter.update_reputation(client_fingerprint, 'successful_action', user.id)
                    
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
                # تحديث السمعة سلبياً لفشل تسجيل الدخول
                smart_limiter.update_reputation(client_fingerprint, 'failed_login')
                flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'error')
                
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            smart_limiter.update_reputation(client_fingerprint, 'failed_login')
            flash('حدث خطأ أثناء تسجيل الدخول، حاول مرة أخرى', 'error')
        
        # في حالة الخطأ، إنشاء tokens جديدة
        time_token, timestamp = generate_time_token()
        return render_template('login.html', time_token=time_token, timestamp=timestamp)

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
@advanced_rate_limit(per_minute=5, per_hour=30)
def new_order():
    # فحص اكتمال الملف الشخصي الأساسي
    if not current_user.whatsapp or not current_user.preferred_platform or not current_user.preferred_payment:
        flash('يجب إكمال الملف الشخصي أولاً قبل تقديم طلب', 'warning')
        return redirect(url_for('profile'))
    
    if request.method == 'GET':
        platforms_data = [
            {
                'id': 'PS',
                'name': 'PlayStation',
                'icon': 'fab fa-playstation',
                'color': '#003087',
                'description': 'PlayStation 4 & 5'
            },
            {
                'id': 'Xbox',
                'name': 'Xbox',
                'icon': 'fab fa-xbox',
                'color': '#107C10',
                'description': 'Xbox One & Series X/S'
            },
            {
                'id': 'PC',
                'name': 'PC',
                'icon': 'fas fa-desktop',
                'color': '#FF6B00',
                'description': 'Origin & Steam'
            }
        ]
        
        payment_methods_data = [
            {
                'id': 'vodafone',
                'name': 'فودافون كاش',
                'icon': 'fas fa-mobile-alt',
                'color': '#E60000',
                'description': 'تحويل فوري'
            },
            {
                'id': 'etisalat',
                'name': 'اتصالات كاش',
                'icon': 'fas fa-mobile-alt',
                'color': '#8CC63F',
                'description': 'تحويل فوري'
            },
            {
                'id': 'orange',
                'name': 'أورنج كاش',
                'icon': 'fas fa-mobile-alt',
                'color': '#FF7900',
                'description': 'تحويل فوري'
            },
            {
                'id': 'instapay',
                'name': 'إنستا باي',
                'icon': 'fas fa-university',
                'color': '#1E88E5',
                'description': 'بنك إلى بنك'
            },
            {
                'id': 'wallet',
                'name': 'محفظة بنكية',
                'icon': 'fas fa-wallet',
                'color': '#6B73FF',
                'description': 'جميع البنوك'
            }
        ]
        
        return render_template('new_order.html', 
                             platforms=platforms_data,
                             payment_methods=payment_methods_data,
                             user=current_user)
    
    if request.method == 'POST':
        client_fingerprint = smart_limiter.get_client_fingerprint(request)
        
        try:
            # جمع بيانات النموذج
            platform = request.form.get('platform', '').strip()
            coins_amount = int(request.form.get('coins_amount', 0))
            payment_method = request.form.get('payment_method', '').strip()
            transfer_type = request.form.get('transfer_type', 'normal').strip()
            
            # بيانات EA (اختيارية)
            ea_email = request.form.get('ea_email', '').strip()
            ea_password = request.form.get('ea_password', '').strip()
            backup_codes = request.form.get('backup_codes', '').strip()
            
            # معلومات إضافية
            phone_number = request.form.get('phone_number', current_user.whatsapp or '').strip()
            notes = request.form.get('notes', '').strip()
            
            # التحقق من البيانات الأساسية
            if not all([platform, coins_amount, payment_method]):
                flash('جميع الحقول الأساسية مطلوبة', 'error')
                return redirect(url_for('new_order'))
            
            if coins_amount < 300000:
                flash('الحد الأدنى للكوينز هو 300,000', 'error')
                return redirect(url_for('new_order'))
            
            # حساب السعر
            price_info, price_error = calculate_price(platform, coins_amount, transfer_type)
            if price_error:
                flash(price_error, 'error')
                return redirect(url_for('new_order'))
            
            # إنشاء الطلب
            order = Order(
                user_id=current_user.id,
                platform=platform,
                coins_amount=coins_amount,
                payment_method=payment_method,
                transfer_type=transfer_type,
                price=price_info['total_price'],
                phone_number=phone_number,
                notes=notes
            )
            
            # إضافة بيانات EA إذا توفرت (مع التشفير)
            if ea_email:
                order.ea_email = ea_email
                
            if ea_password:
                # تشفير كلمة مرور EA
                order.ea_password = generate_password_hash(ea_password)
                
            if backup_codes:
                # تشفير أكواد الاحتياط
                order.backup_codes = generate_password_hash(backup_codes)
            
            db.session.add(order)
            db.session.commit()
            
            smart_limiter.update_reputation(client_fingerprint, 'successful_action', current_user.id)
            
            # إرسال إشعار تليجرام للمستخدم
            if current_user.telegram_id:
                order_data = {
                    'id': order.id,
                    'platform': platform,
                    'coins_amount': coins_amount,
                    'transfer_type': transfer_type,
                    'price': price_info['total_price'],
                    'payment_method': payment_method,
                    'phone_number': phone_number
                }
                
                telegram_system.send_order_notification(current_user.telegram_id, order_data)
                app.logger.info(f"Telegram notification sent for order {order.id}")
            
            flash(f'تم إرسال طلبك بنجاح! السعر المتوقع: {price_info["total_price"]} جنيه', 'success')
            return redirect(url_for('dashboard'))
            
        except ValueError:
            flash('كمية الكوينز يجب أن تكون رقماً صالحاً', 'error')
            return redirect(url_for('new_order'))
        except Exception as e:
            app.logger.error(f"New order error: {e}")
            smart_limiter.update_reputation(client_fingerprint, 'invalid_form', current_user.id)
            flash('حدث خطأ أثناء إرسال الطلب، حاول مرة أخرى', 'error')
            return redirect(url_for('new_order'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
@advanced_rate_limit(per_minute=20, per_hour=100)
def profile():
    if request.method == 'GET':
        return render_template('profile.html', user=current_user)
    
    if request.method == 'POST':
        client_fingerprint = smart_limiter.get_client_fingerprint(request)
        
        try:
            # فحص AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                field = request.form.get('field')
                value = request.form.get(field, '').strip()
                
                # تحديث الحقل المحدد
                if hasattr(current_user, field):
                    setattr(current_user, field, value)
                    current_user.last_profile_update = datetime.utcnow()
                    
                # لا حاجة لحفظ profile_completed لأنه property محسوب تلقائياً
                # current_user.profile_completed محسوب ديناميكياً الآن
                    
                    db.session.commit()
                    
                    smart_limiter.update_reputation(client_fingerprint, 'successful_action', current_user.id)
                    
                    return jsonify({
                        'success': True,
                        'message': 'تم حفظ البيانات بنجاح',
                        'profile_completed': current_user.profile_completed
                    })
                else:
                    return jsonify({'success': False, 'message': 'حقل غير صالح'}), 400
            
            # معالجة النموذج العادي
            else:
                current_user.whatsapp = request.form.get('whatsapp', '').strip()
                current_user.preferred_platform = request.form.get('preferred_platform', '').strip()
                current_user.preferred_payment = request.form.get('preferred_payment', '').strip()
                current_user.ea_email = request.form.get('ea_email', '').strip()
                current_user.last_profile_update = datetime.utcnow()
                
                # فحص اكتمال الملف الشخصي
                current_user.profile_completed = check_profile_completion(current_user)
                
                db.session.commit()
                
                smart_limiter.update_reputation(client_fingerprint, 'successful_action', current_user.id)
                
                flash('تم تحديث الملف الشخصي بنجاح!', 'success')
                return redirect(url_for('profile'))
                
        except Exception as e:
            app.logger.error(f"Profile update error: {e}")
            smart_limiter.update_reputation(client_fingerprint, 'invalid_form', current_user.id)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'حدث خطأ أثناء الحفظ'}), 500
            else:
                flash('حدث خطأ أثناء التحديث، حاول مرة أخرى', 'error')
                return render_template('profile.html', user=current_user)

@app.route('/profile/telegram-link')
@login_required  
@advanced_rate_limit(per_minute=5, per_hour=20)
def generate_telegram_link():
    """توليد رابط ربط التليجرام"""
    try:
        if not telegram_system.is_configured():
            return jsonify({
                'success': False,
                'message': 'خدمة التليجرام غير متاحة حالياً'
            }), 503
        
        # توليد رابط مع معرف المستخدم المشفر
        import base64
        encoded_user_id = base64.b64encode(str(current_user.id).encode()).decode()
        
        telegram_link = f"https://t.me/{telegram_system.bot_username}?start={encoded_user_id}"
        
        return jsonify({
            'success': True,
            'telegram_link': telegram_link,
            'bot_username': telegram_system.bot_username,
            'is_linked': bool(current_user.telegram_id),
            'instructions': [
                'اضغط على الرابط أدناه',
                'اضغط "Start" في التليجرام', 
                'أرسل أي رسالة للبوت',
                'سيتم الربط تلقائياً'
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Error generating Telegram link: {e}")
        return jsonify({
            'success': False,
            'message': 'خطأ في توليد رابط التليجرام'
        }), 500

@app.route('/profile/completion-status')
@login_required
def profile_completion_status():
    """إرجاع حالة اكتمال الملف الشخصي"""
    try:
        steps = {
            'whatsapp': bool(current_user.whatsapp and current_user.whatsapp.strip()),
            'platform': bool(current_user.preferred_platform and current_user.preferred_platform.strip()),
            'payment': bool(current_user.preferred_payment and current_user.preferred_payment.strip()),
            'ea_email': bool(current_user.ea_email and current_user.ea_email.strip()),
            'telegram': bool(current_user.telegram_id and current_user.telegram_id.strip()),
            'profile': current_user.profile_completed or False
        }
        
        completed_count = sum(1 for completed in steps.values() if completed)
        total_count = len(steps)
        percentage = round((completed_count / total_count) * 100)
        
        return jsonify({
            'success': True,
            'steps': steps,
            'completed_count': completed_count,
            'total_count': total_count,
            'percentage': percentage,
            'profile_completed': current_user.profile_completed
        })
        
    except Exception as e:
        app.logger.error(f"Profile completion status error: {e}")
        return jsonify({'success': False, 'message': 'خطأ في تحميل البيانات'}), 500

@app.route('/resend-verification', methods=['POST'])
@advanced_rate_limit(per_minute=2, per_hour=5, block_on_abuse=True)
def resend_verification():
    if 'user_email' not in session:
        flash('يجب التسجيل أولاً', 'error')
        return redirect(url_for('register'))
    
    client_fingerprint = smart_limiter.get_client_fingerprint(request)
    
    try:
        user = User.query.filter_by(email=session['user_email']).first()
        
        if not user:
            smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
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
            smart_limiter.update_reputation(client_fingerprint, 'successful_action')
            flash('تم إرسال كود تفعيل جديد إلى بريدك الإلكتروني', 'success')
        else:
            smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
            flash('خطأ في إرسال البريد الإلكتروني', 'error')
            
    except Exception as e:
        app.logger.error(f"Resend verification error: {e}")
        smart_limiter.update_reputation(client_fingerprint, 'invalid_form')
        flash('حدث خطأ، حاول مرة أخرى', 'error')
    
    return redirect(url_for('verify_email'))

def calculate_price(platform, coins_amount, transfer_type='normal'):
    """حساب سعر الطلب بناءً على المنصة والكمية ونوع التحويل"""
    
    # أسعار الكوينز لكل منصة (لكل مليون كوين)
    base_prices = {
        'PS': 850,      # PlayStation
        'Xbox': 850,    # Xbox (نفس PlayStation)
        'PC': 950       # PC أغلى قليلاً
    }
    
    # معاملات نوع التحويل
    transfer_multipliers = {
        'normal': 1.0,    # عادي
        'instant': 1.15   # فوري (زيادة 15%)
    }
    
    # تخفيضات الكمية
    quantity_discounts = [
        (10000000, 0.95),   # 10+ مليون: خصم 5%
        (25000000, 0.90),   # 25+ مليون: خصم 10%
        (50000000, 0.85),   # 50+ مليون: خصم 15%
        (100000000, 0.80)   # 100+ مليون: خصم 20%
    ]
    
    # الحد الأدنى
    if coins_amount < 300000:
        return None, "الحد الأدنى 300,000 كوين"
    
    # السعر الأساسي
    base_price = base_prices.get(platform, base_prices['PS'])
    millions = coins_amount / 1000000
    total_price = base_price * millions
    
    # تطبيق تخفيض الكمية
    discount_rate = 1.0
    for threshold, rate in quantity_discounts:
        if coins_amount >= threshold:
            discount_rate = rate
            break
    
    total_price *= discount_rate
    
    # تطبيق معامل نوع التحويل
    transfer_rate = transfer_multipliers.get(transfer_type, 1.0)
    total_price *= transfer_rate
    
    # حساب المعلومات الإضافية
    price_info = {
        'total_price': round(total_price, 2),
        'base_price_per_million': base_price,
        'millions': round(millions, 2),
        'discount_rate': discount_rate,
        'discount_percent': round((1 - discount_rate) * 100, 1) if discount_rate < 1 else 0,
        'transfer_type': transfer_type,
        'transfer_fee': round(total_price * (transfer_rate - 1), 2) if transfer_rate > 1 else 0
    }
    
    return price_info, None

@app.route('/telegram-webhook', methods=['POST'])
@advanced_rate_limit(per_minute=100, per_hour=1000, skip_trusted=True)
def telegram_webhook():
    """معالج webhook للتليجرام"""
    try:
        update_data = request.get_json()
        
        if not update_data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        # معالجة التحديث
        result = telegram_system.process_telegram_update(update_data)
        
        if result:
            app.logger.info(f"Telegram update processed: {result.get('action', 'unknown')}")
            
            # إذا كان المستخدم يريد ربط حسابه
            if result.get('action') == 'start' and result.get('website_user_id'):
                # ربط حساب التليجرام مع حساب الموقع
                link_telegram_account(result.get('website_user_id'), result.get('user_id'), result.get('username'))
            
            return jsonify({'status': 'ok'}), 200
        else:
            return jsonify({'status': 'ignored'}), 200
            
    except Exception as e:
        app.logger.error(f"Telegram webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def link_telegram_account(website_user_id: str, telegram_user_id: str, telegram_username: str = None):
    """ربط حساب التليجرام مع حساب الموقع"""
    try:
        user = User.query.get(int(website_user_id))
        
        if user:
            user.telegram_id = telegram_user_id
            user.telegram_username = telegram_username
            user.last_profile_update = datetime.utcnow()
            
            # تحديث حالة اكتمال الملف الشخصي
            user.profile_completed = check_profile_completion(user)
            
            db.session.commit()
            
            # إرسال رسالة تأكيد
            success_message = f"""
✅ <b>تم ربط حسابك بنجاح!</b>

🎉 مرحباً {user.email}!

سيتم إرسال إشعارات فورية عن:
• طلباتك الجديدة 📋
• تحديثات الحالة 🔄  
• العروض الخاصة 🎁

شكراً لاختيارك شهد السنيورة! 🚀
            """
            
            telegram_system.send_message(telegram_user_id, success_message.strip())
            
            app.logger.info(f"Telegram account linked: User {website_user_id} -> Telegram {telegram_user_id}")
            return True
        else:
            app.logger.warning(f"User not found for linking: {website_user_id}")
            return False
            
    except Exception as e:
        app.logger.error(f"Error linking Telegram account: {e}")
        return False

@app.route('/api/calculate-price', methods=['POST'])
@login_required
@advanced_rate_limit(per_minute=30, per_hour=200)
def api_calculate_price():
    """API لحساب السعر ديناميكياً"""
    try:
        data = request.get_json()
        
        platform = data.get('platform')
        coins_amount = int(data.get('coins_amount', 0))
        transfer_type = data.get('transfer_type', 'normal')
        
        if not platform or coins_amount <= 0:
            return jsonify({
                'success': False,
                'message': 'بيانات غير صالحة'
            }), 400
        
        price_info, error = calculate_price(platform, coins_amount, transfer_type)
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'price_info': price_info
        })
        
    except Exception as e:
        app.logger.error(f"Price calculation error: {e}")
        return jsonify({
            'success': False,
            'message': 'خطأ في حساب السعر'
        }), 500

@app.route('/admin')
@login_required
@advanced_rate_limit(per_minute=30, per_hour=200)
def admin_dashboard():
    try:
        if not current_user.is_admin:
            flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
            return redirect(url_for('dashboard'))
        
        # الحصول على المعاملات
        page = request.args.get('page', 1, type=int)
        per_page = 10
        status_filter = request.args.get('status', 'all')
        date_filter = request.args.get('date', 'all')
        search_query = request.args.get('search', '')
        
        # إحصائيات شاملة
        stats = calculate_admin_statistics()
        
        # فلترة الطلبات
        orders_query = Order.query
        
        if status_filter != 'all':
            orders_query = orders_query.filter(Order.status == status_filter)
            
        if date_filter != 'all':
            if date_filter == 'today':
                today = datetime.utcnow().date()
                orders_query = orders_query.filter(
                    db.func.date(Order.created_at) == today
                )
            elif date_filter == 'week':
                week_ago = datetime.utcnow() - timedelta(days=7)
                orders_query = orders_query.filter(Order.created_at >= week_ago)
            elif date_filter == 'month':
                month_ago = datetime.utcnow() - timedelta(days=30)
                orders_query = orders_query.filter(Order.created_at >= month_ago)
        
        if search_query:
            orders_query = orders_query.join(User).filter(
                db.or_(
                    User.email.contains(search_query),
                    Order.platform.contains(search_query),
                    Order.payment_method.contains(search_query)
                )
            )
        
        # ترتيب وتقسيم الصفحات
        orders = orders_query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # المستخدمين مع إحصائيات
        users = User.query.all()
        users_stats = calculate_users_statistics(users)
        
        # إحصائيات الأمان
        security_stats = calculate_security_statistics()
        
        # بيانات الرسوم البيانية
        charts_data = generate_charts_data()
        
        return render_template('admin_dashboard.html',
                             orders=orders,
                             users=users,
                             stats=stats,
                             users_stats=users_stats,
                             security_stats=security_stats,
                             charts_data=charts_data,
                             status_filter=status_filter,
                             date_filter=date_filter,
                             search_query=search_query)
                             
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {e}")
        flash('حدث خطأ في تحميل البيانات', 'error')
        return render_template('admin_dashboard.html', 
                             orders=[], users=[], stats={}, 
                             users_stats={}, security_stats={}, charts_data={})

def calculate_admin_statistics():
    """حساب الإحصائيات الشاملة للإدارة"""
    try:
        now = datetime.utcnow()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # إحصائيات المستخدمين
        total_users = User.query.count()
        verified_users = User.query.filter_by(is_verified=True).count()
        new_users_today = User.query.filter(
            db.func.date(User.created_at) == today
        ).count()
        new_users_week = User.query.filter(User.created_at >= week_ago).count()
        telegram_linked = User.query.filter(User.telegram_id.isnot(None)).count()
        
        # إحصائيات الطلبات
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        completed_orders = Order.query.filter_by(status='completed').count()
        cancelled_orders = Order.query.filter_by(status='cancelled').count()
        orders_today = Order.query.filter(
            db.func.date(Order.created_at) == today
        ).count()
        orders_week = Order.query.filter(Order.created_at >= week_ago).count()
        
        # إحصائيات مالية
        total_revenue = db.session.query(db.func.sum(Order.price)).filter(
            Order.status == 'completed'
        ).scalar() or 0
        revenue_week = db.session.query(db.func.sum(Order.price)).filter(
            Order.status == 'completed',
            Order.created_at >= week_ago
        ).scalar() or 0
        revenue_month = db.session.query(db.func.sum(Order.price)).filter(
            Order.status == 'completed',
            Order.created_at >= month_ago
        ).scalar() or 0
        
        # متوسط قيمة الطلب
        avg_order_value = db.session.query(db.func.avg(Order.price)).filter(
            Order.status == 'completed'
        ).scalar() or 0
        
        # إحصائيات المنصات
        platform_stats = db.session.query(
            Order.platform,
            db.func.count(Order.id).label('count')
        ).group_by(Order.platform).all()
        
        # معدل التحويل
        completion_rate = (completed_orders / max(1, total_orders)) * 100
        
        return {
            'users': {
                'total': total_users,
                'verified': verified_users,
                'verification_rate': (verified_users / max(1, total_users)) * 100,
                'new_today': new_users_today,
                'new_week': new_users_week,
                'telegram_linked': telegram_linked,
                'telegram_rate': (telegram_linked / max(1, total_users)) * 100
            },
            'orders': {
                'total': total_orders,
                'pending': pending_orders,
                'completed': completed_orders,
                'cancelled': cancelled_orders,
                'today': orders_today,
                'week': orders_week,
                'completion_rate': completion_rate
            },
            'revenue': {
                'total': round(total_revenue, 2),
                'week': round(revenue_week, 2),
                'month': round(revenue_month, 2),
                'avg_order': round(avg_order_value, 2)
            },
            'platforms': {p.platform: p.count for p in platform_stats}
        }
        
    except Exception as e:
        app.logger.error(f"Error calculating admin statistics: {e}")
        return {}

def calculate_users_statistics(users):
    """حساب إحصائيات المستخدمين التفصيلية"""
    try:
        now = datetime.utcnow()
        
        # تصنيف المستخدمين حسب النشاط
        active_users = []
        inactive_users = []
        
        for user in users:
            user_orders = Order.query.filter_by(user_id=user.id).count()
            last_order = Order.query.filter_by(user_id=user.id).order_by(
                Order.created_at.desc()
            ).first()
            
            days_since_last_order = None
            if last_order:
                days_since_last_order = (now - last_order.created_at).days
            
            user_data = {
                'user': user,
                'orders_count': user_orders,
                'last_order_date': last_order.created_at if last_order else None,
                'days_since_last_order': days_since_last_order
            }
            
            if user_orders > 0 and (not days_since_last_order or days_since_last_order <= 30):
                active_users.append(user_data)
            else:
                inactive_users.append(user_data)
        
        return {
            'active_users': active_users,
            'inactive_users': inactive_users,
            'activity_rate': (len(active_users) / max(1, len(users))) * 100
        }
        
    except Exception as e:
        app.logger.error(f"Error calculating users statistics: {e}")
        return {'active_users': [], 'inactive_users': [], 'activity_rate': 0}

def calculate_security_statistics():
    """حساب إحصائيات الأمان"""
    try:
        current_time = int(time.time())
        
        # إحصائيات الحظر والسمعة
        total_tracked_ips = len(smart_limiter.suspicious_ips)
        blocked_ips = sum(1 for data in smart_limiter.suspicious_ips.values() 
                         if data.get('score', 0) < -50)
        trusted_ips = sum(1 for data in smart_limiter.suspicious_ips.values() 
                         if data.get('score', 0) > 50)
        
        # إحصائيات الجلسات المشبوهة
        active_blocks = sum(1 for data in suspicious_sessions.values() 
                          if data.get('blocked_until', 0) > current_time)
        high_risk_sessions = sum(1 for data in suspicious_sessions.values() 
                               if data.get('suspicious_score', 0) >= 10)
        
        # حساب نقاط الأمان العامة
        security_score = calculate_overall_security_score(
            total_tracked_ips, blocked_ips, active_blocks, high_risk_sessions
        )
        
        return {
            'tracked_ips': total_tracked_ips,
            'blocked_ips': blocked_ips,
            'trusted_ips': trusted_ips,
            'active_blocks': active_blocks,
            'high_risk_sessions': high_risk_sessions,
            'security_score': security_score,
            'threat_level': get_threat_level(security_score)
        }
        
    except Exception as e:
        app.logger.error(f"Error calculating security statistics: {e}")
        return {}

def calculate_overall_security_score(tracked_ips, blocked_ips, active_blocks, high_risk):
    """حساب نقاط الأمان العامة"""
    base_score = 100
    
    if tracked_ips > 0:
        blocked_ratio = (blocked_ips / tracked_ips) * 100
        if blocked_ratio > 20:
            base_score -= 30
        elif blocked_ratio > 10:
            base_score -= 15
        elif blocked_ratio > 5:
            base_score -= 5
    
    base_score -= min(30, active_blocks * 5)
    base_score -= min(20, high_risk * 3)
    
    return max(0, min(100, base_score))

def get_threat_level(security_score):
    """تحديد مستوى التهديد"""
    if security_score >= 90:
        return {'level': 'low', 'text': 'منخفض', 'color': 'success'}
    elif security_score >= 70:
        return {'level': 'medium', 'text': 'متوسط', 'color': 'warning'}
    elif security_score >= 50:
        return {'level': 'high', 'text': 'عالي', 'color': 'danger'}
    else:
        return {'level': 'critical', 'text': 'حرج', 'color': 'danger'}

def generate_charts_data():
    """توليد بيانات الرسوم البيانية"""
    try:
        now = datetime.utcnow()
        
        # بيانات آخر 7 أيام
        days_data = []
        for i in range(7):
            date = (now - timedelta(days=i)).date()
            orders_count = Order.query.filter(
                db.func.date(Order.created_at) == date
            ).count()
            users_count = User.query.filter(
                db.func.date(User.created_at) == date
            ).count()
            
            days_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'orders': orders_count,
                'users': users_count
            })
        
        days_data.reverse()  # ترتيب من الأقدم للأحدث
        
        # توزيع حالات الطلبات
        status_distribution = db.session.query(
            Order.status,
            db.func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        
        # توزيع المنصات
        platform_distribution = db.session.query(
            Order.platform,
            db.func.count(Order.id).label('count')
        ).group_by(Order.platform).all()
        
        return {
            'daily_activity': days_data,
            'status_distribution': [{'status': s.status, 'count': s.count} for s in status_distribution],
            'platform_distribution': [{'platform': p.platform, 'count': p.count} for p in platform_distribution]
        }
        
    except Exception as e:
        app.logger.error(f"Error generating charts data: {e}")
        return {}

@app.route('/admin/order/<int:order_id>/update', methods=['POST'])
@login_required
def update_order_status(order_id):
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403
        
        new_status = request.json.get('status')
        
        order = Order.query.get_or_404(order_id)
        old_status = order.status
        order.status = new_status
        db.session.commit()
        
        # إرسال إشعار تليجرام للمستخدم عن تغيير الحالة
        if order.user.telegram_id and old_status != new_status:
            telegram_system.send_status_update(
                order.user.telegram_id, 
                order_id, 
                old_status, 
                new_status
            )
            app.logger.info(f"Status update notification sent for order {order_id}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update order error: {e}")
        return jsonify({'error': 'Server error'}), 500

def init_database():
    """Initialize database and create default admin user"""
    try:
        # إنشاء الجداول الأساسية
        db.create_all()
        print("Database tables created successfully")
        
        # إصلاح طارئ لقاعدة البيانات
        try:
            emergency_fix_success = emergency_fix_database()
            if not emergency_fix_success:
                print("⚠️ Emergency repair had issues, trying standard update...")
        except Exception as e:
            print(f"⚠️ Emergency repair failed: {e}")
        
        # تحديث الجداول الموجودة بطريقة آمنة
        try:
            if 'postgresql' in str(db.engine.url):
                update_existing_tables()  # PostgreSQL version
            else:
                update_existing_tables_sqlite()  # SQLite version
        except Exception as e:
            print(f"Warning: Table update failed: {e}")
            db.session.rollback()
        
        # تحسين قاعدة البيانات
        try:
            optimize_database()
        except Exception as e:
            print(f"Warning: Database optimization failed: {e}")
            db.session.rollback()
        
        # تنظيف البيانات القديمة
        try:
            cleanup_old_verification_codes()
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")
            db.session.rollback()
        
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

def update_existing_tables():
    """تحديث الجداول الموجودة لإضافة الحقول الجديدة - PostgreSQL Compatible"""
    try:
        with app.app_context():
            # إضافة الحقول الجديدة إذا لم تكن موجودة - PostgreSQL compatible
            new_columns = [
                ('users', 'whatsapp', 'VARCHAR(20)'),
                ('users', 'preferred_platform', 'VARCHAR(10)'),
                ('users', 'preferred_payment', 'VARCHAR(50)'),
                ('users', 'ea_email', 'VARCHAR(100)'),
                ('users', 'telegram_id', 'VARCHAR(50)'),
                ('users', 'telegram_username', 'VARCHAR(50)'),
                ('users', 'profile_completed', 'BOOLEAN DEFAULT FALSE'),  # تصحيح PostgreSQL
                ('users', 'last_profile_update', 'TIMESTAMP'),
                ('orders', 'ea_email', 'VARCHAR(100)'),
                ('orders', 'ea_password', 'VARCHAR(200)'),
                ('orders', 'backup_codes', 'TEXT'),
                ('orders', 'transfer_type', "VARCHAR(20) DEFAULT 'normal'"),  # تصحيح PostgreSQL
                ('orders', 'notes', 'TEXT'),
                ('orders', 'price', 'DECIMAL(10,2)'),
                ('orders', 'phone_number', 'VARCHAR(20)'),
                ('orders', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]
            
            for table, column, column_type in new_columns:
                try:
                    # فحص وجود العمود أولاً
                    check_query = text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = :table_name 
                        AND column_name = :column_name
                    """)
                    
                    result = db.session.execute(check_query, {
                        'table_name': table,
                        'column_name': column
                    }).fetchone()
                    
                    if not result:
                        # إضافة العمود إذا لم يكن موجوداً
                        alter_query = text(f'ALTER TABLE {table} ADD COLUMN {column} {column_type}')
                        db.session.execute(alter_query)
                        db.session.commit()
                        print(f"Added column {column} to {table}")
                    else:
                        print(f"Column {column} already exists in {table}")
                        
                except Exception as e:
                    db.session.rollback()
                    error_msg = str(e).lower()
                    if "already exists" in error_msg or "duplicate column" in error_msg:
                        print(f"Column {column} already exists in {table}")
                    else:
                        print(f"Error adding column {column} to {table}: {e}")
                        # محاولة إضافة العمود بطريقة مختلفة للمشاكل المعروفة
                        if "profile_completed" in column and "boolean" in error_msg:
                            try:
                                # محاولة إضافة بدون default أولاً
                                alter_query_simple = text(f'ALTER TABLE {table} ADD COLUMN {column} BOOLEAN')
                                db.session.execute(alter_query_simple)
                                # إضافة default بعدين
                                default_query = text(f'ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT FALSE')
                                db.session.execute(default_query)
                                db.session.commit()
                                print(f"Added column {column} to {table} (fixed boolean issue)")
                            except Exception as fix_error:
                                print(f"Failed to fix {column}: {fix_error}")
                                db.session.rollback()
                        elif "transfer_type" in column and "cannot use column reference" in error_msg:
                            try:
                                # محاولة إضافة بدون default أولاً
                                alter_query_simple = text(f'ALTER TABLE {table} ADD COLUMN {column} VARCHAR(20)')
                                db.session.execute(alter_query_simple)
                                # إضافة default بعدين
                                default_query = text(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT 'normal'")
                                db.session.execute(default_query)
                                db.session.commit()
                                print(f"Added column {column} to {table} (fixed default issue)")
                            except Exception as fix_error:
                                print(f"Failed to fix {column}: {fix_error}")
                                db.session.rollback()
            
            print("Database tables updated successfully")
            
    except Exception as e:
        print(f"Database update error: {e}")
        db.session.rollback()

def safe_column_exists(table_name, column_name):
    """فحص آمن لوجود عمود في الجدول"""
    try:
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name 
            AND column_name = :column_name
        """)
        
        result = db.session.execute(check_query, {
            'table_name': table_name,
            'column_name': column_name
        }).fetchone()
        
        return result is not None
        
    except Exception as e:
        print(f"Error checking column existence: {e}")
        return False

def emergency_fix_database():
    """إصلاح طارئ لقاعدة البيانات لحل المشاكل الحرجة"""
    try:
        print("🚨 Starting emergency database repair...")
        
        # إصلاح profile_completed column
        try:
            # فحص إذا العمود موجود
            check_profile = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'profile_completed'
            """)
            result = db.session.execute(check_profile).fetchone()
            
            if not result:
                # إضافة العمود بالطريقة الصحيحة
                add_profile = text('ALTER TABLE users ADD COLUMN profile_completed BOOLEAN')
                db.session.execute(add_profile)
                
                set_default = text('ALTER TABLE users ALTER COLUMN profile_completed SET DEFAULT FALSE')
                db.session.execute(set_default)
                
                # تحديث القيم الموجودة
                update_existing = text('UPDATE users SET profile_completed = FALSE WHERE profile_completed IS NULL')
                db.session.execute(update_existing)
                
                db.session.commit()
                print("✅ Fixed profile_completed column")
            else:
                print("✅ profile_completed column already exists")
                
        except Exception as e:
            print(f"❌ Error fixing profile_completed: {e}")
            db.session.rollback()
        
        # إصلاح transfer_type column
        try:
            check_transfer = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders' 
                AND column_name = 'transfer_type'
            """)
            result = db.session.execute(check_transfer).fetchone()
            
            if not result:
                # إضافة العمود بالطريقة الصحيحة
                add_transfer = text('ALTER TABLE orders ADD COLUMN transfer_type VARCHAR(20)')
                db.session.execute(add_transfer)
                
                set_default = text("ALTER TABLE orders ALTER COLUMN transfer_type SET DEFAULT 'normal'")
                db.session.execute(set_default)
                
                # تحديث القيم الموجودة
                update_existing = text("UPDATE orders SET transfer_type = 'normal' WHERE transfer_type IS NULL")
                db.session.execute(update_existing)
                
                db.session.commit()
                print("✅ Fixed transfer_type column")
            else:
                print("✅ transfer_type column already exists")
                
        except Exception as e:
            print(f"❌ Error fixing transfer_type: {e}")
            db.session.rollback()
        
        print("🎉 Emergency repair completed successfully!")
        return True
        
    except Exception as e:
        print(f"💥 Emergency repair failed: {e}")
        db.session.rollback()
        return False

def safe_migration():
    """Migration آمن يتجنب مشاكل SQLAlchemy مع الـ columns المفقودة"""
    try:
        print("🔄 Starting safe database migration...")
        
        # فحص حالة قاعدة البيانات أولاً
        try:
            # استخدام raw SQL للفحص
            result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()
            existing_tables = [row[0] for row in result]
            
            if 'users' not in existing_tables or 'orders' not in existing_tables:
                print("❌ Core tables missing, creating basic structure...")
                db.create_all()
                print("✅ Basic tables created")
        except Exception as e:
            print(f"⚠️ Table check failed: {e}")
            # إنشاء الجداول الأساسية كـ fallback
            try:
                db.create_all()
                print("✅ Fallback table creation completed")
            except Exception as create_error:
                print(f"❌ Failed to create tables: {create_error}")
                return False
        
        # إضافة columns مفقودة واحد واحد مع معالجة أخطاء PostgreSQL
        missing_columns = []
        
        # فحص columns في users table
        try:
            users_check = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users'
            """)).fetchall()
            users_columns = [row[0] for row in users_check]
        except Exception as e:
            print(f"❌ Cannot check users columns: {e}")
            users_columns = []
        
        required_user_columns = {
            'whatsapp': 'VARCHAR(20)',
            'preferred_platform': 'VARCHAR(10)', 
            'preferred_payment': 'VARCHAR(50)',
            'ea_email': 'VARCHAR(100)',
            'telegram_id': 'VARCHAR(50)',
            'telegram_username': 'VARCHAR(50)',
            'last_profile_update': 'TIMESTAMP'
        }
        
        for col_name, col_type in required_user_columns.items():
            if col_name not in users_columns:
                missing_columns.append(('users', col_name, col_type, ''))
        
        # فحص columns في orders table
        try:
            orders_check = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'orders'
            """)).fetchall()
            orders_columns = [row[0] for row in orders_check]
        except Exception as e:
            print(f"❌ Cannot check orders columns: {e}")
            orders_columns = []
        
        required_order_columns = {
            'ea_email': 'VARCHAR(100)',
            'ea_password': 'VARCHAR(200)',
            'backup_codes': 'TEXT',
            'transfer_type': 'VARCHAR(20)',
            'notes': 'TEXT',
            'price': 'DECIMAL(10,2)',
            'phone_number': 'VARCHAR(20)',
            'updated_at': 'TIMESTAMP'
        }
        
        for col_name, col_type in required_order_columns.items():
            if col_name not in orders_columns:
                default_val = "'normal'" if col_name == 'transfer_type' else "''" if 'VARCHAR' in col_type or col_type == 'TEXT' else '0.0' if 'DECIMAL' in col_type else 'NULL'
                missing_columns.append(('orders', col_name, col_type, default_val))
        
        # إضافة الـ columns المفقودة
        for table, column, column_type, default_value in missing_columns:
            try:
                # إضافة العمود بدون DEFAULT أولاً
                add_query = text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type}')
                db.session.execute(add_query)
                
                # إضافة DEFAULT value منفصل إذا لزم الأمر
                if default_value and default_value != 'NULL':
                    if column == 'transfer_type':
                        update_query = text(f"UPDATE {table} SET {column} = 'normal' WHERE {column} IS NULL")
                    else:
                        update_query = text(f"UPDATE {table} SET {column} = {default_value} WHERE {column} IS NULL")
                    db.session.execute(update_query)
                
                db.session.commit()
                print(f"✅ Added column {column} to {table}")
                
            except Exception as e:
                print(f"⚠️ Error adding {column} to {table}: {e}")
                db.session.rollback()
        
        print("🎉 Safe migration completed!")
        return True
        
    except Exception as e:
        print(f"💥 Migration failed: {e}")
        db.session.rollback()
        return False

def force_database_repair():
    """إصلاح إجباري لقاعدة البيانات في حالة الأخطاء الحرجة"""
    try:
        print("Starting database repair...")
        
        # إنهاء جميع الـ transactions المعلقة
        db.session.rollback()
        db.session.close()
        
        # إعادة إنشاء الاتصال
        db.session.remove()
        
        # فحص وإضافة الأعمدة المفقودة واحداً تلو الآخر
        repair_columns = [
            ('users', 'whatsapp', 'VARCHAR(20)'),
            ('users', 'preferred_platform', 'VARCHAR(10)'),
            ('users', 'preferred_payment', 'VARCHAR(50)'),
            ('users', 'ea_email', 'VARCHAR(100)'),
            ('users', 'telegram_id', 'VARCHAR(50)'),
            ('users', 'telegram_username', 'VARCHAR(50)'),
            ('users', 'profile_completed', 'BOOLEAN DEFAULT FALSE'),
            ('users', 'last_profile_update', 'TIMESTAMP'),
            ('orders', 'ea_email', 'VARCHAR(100)'),
            ('orders', 'ea_password', 'VARCHAR(200)'),
            ('orders', 'backup_codes', 'TEXT'),
            ('orders', 'transfer_type', 'VARCHAR(20) DEFAULT \'normal\''),
            ('orders', 'notes', 'TEXT'),
            ('orders', 'price', 'DECIMAL(10,2)'),
            ('orders', 'phone_number', 'VARCHAR(20)'),
            ('orders', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        ]
        
        success_count = 0
        for table, column, column_type in repair_columns:
            if safe_add_column(table, column, column_type):
                success_count += 1
        
        print(f"Database repair completed: {success_count}/{len(repair_columns)} columns processed")
        return True
        
    except Exception as e:
        print(f"Database repair failed: {e}")
        return False

def update_existing_tables_sqlite():
    """تحديث الجداول الموجودة لإضافة الحقول الجديدة - SQLite"""
    try:
        with app.app_context():
            # إضافة الحقول الجديدة إذا لم تكن موجودة لـ SQLite
            new_columns = [
                ('users', 'whatsapp', 'TEXT'),
                ('users', 'preferred_platform', 'TEXT'),
                ('users', 'preferred_payment', 'TEXT'),
                ('users', 'ea_email', 'TEXT'),
                ('users', 'telegram_id', 'TEXT'),
                ('users', 'telegram_username', 'TEXT'),
                ('users', 'profile_completed', 'BOOLEAN DEFAULT 0'),
                ('users', 'last_profile_update', 'TIMESTAMP'),
                ('orders', 'ea_email', 'TEXT'),
                ('orders', 'ea_password', 'TEXT'),
                ('orders', 'backup_codes', 'TEXT'),
                ('orders', 'transfer_type', 'TEXT DEFAULT "normal"'),
                ('orders', 'notes', 'TEXT'),
                ('orders', 'price', 'REAL'),
                ('orders', 'phone_number', 'TEXT'),
                ('orders', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            ]
            
            for table, column, column_type in new_columns:
                try:
                    # محاولة إضافة العمود
                    alter_query = text(f'ALTER TABLE {table} ADD COLUMN {column} {column_type}')
                    db.session.execute(alter_query)
                    db.session.commit()
                    print(f"Added column {column} to {table}")
                except Exception as e:
                    db.session.rollback()
                    error_msg = str(e).lower()
                    if "already exists" in error_msg or "duplicate column" in error_msg:
                        print(f"Column {column} already exists in {table}")
                    else:
                        print(f"Error adding column {column} to {table}: {e}")
            
            print("SQLite tables updated successfully")
            
    except Exception as e:
        print(f"SQLite update error: {e}")
        db.session.rollback()

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
        db.session.rollback()

def cleanup_old_verification_codes():
    """تنظيف رموز التفعيل المنتهية الصلاحية"""
    try:
        with app.app_context():
            # فحص وجود الأعمدة المطلوبة أولاً
            if not safe_column_exists('users', 'code_expiry'):
                print("Column code_expiry does not exist, skipping cleanup")
                return
                
            expired_time = datetime.utcnow() - timedelta(hours=24)
            
            # استعلام آمن يتعامل مع الأعمدة الموجودة فقط
            try:
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
                db.session.rollback()
                # إذا فشل الاستعلام، استخدم SQL مباشر
                try:
                    cleanup_query = text("""
                        UPDATE users 
                        SET verification_code = NULL, code_expiry = NULL 
                        WHERE code_expiry < :expired_time 
                        AND is_verified = false
                    """)
                    
                    result = db.session.execute(cleanup_query, {'expired_time': expired_time})
                    db.session.commit()
                    print(f"Cleaned up verification codes using direct SQL")
                    
                except Exception as sql_error:
                    print(f"SQL cleanup also failed: {sql_error}")
                    db.session.rollback()
                
    except Exception as e:
        print(f"Cleanup error: {e}")
        db.session.rollback()

@app.before_request
def before_request():
    """معالج محسن مع تساهل للمصادر الموثوقة"""
    # تجاهل الملفات الثابتة والـ endpoints المستثناة
    if (request.path.startswith('/static/') or 
        any(request.path.startswith(endpoint) for endpoint in EXEMPT_ENDPOINTS)):
        return
    
    client_ip = get_remote_address()
    
    # فحص ما إذا كان مصدر موثوق
    is_trusted_ip = False
    try:
        ip_obj = ipaddress.ip_address(client_ip)
        if ip_obj.is_private or ip_obj.is_loopback:
            is_trusted_ip = True
    except:
        pass
    
    # 1. فحص الحظر المؤقت (إلا للمصادر الموثوقة)
    if not is_trusted_ip:
        is_blocked, remaining_time = is_session_blocked(client_ip)
        if is_blocked:
            app.logger.warning(f"Blocked request from {client_ip}, remaining time: {remaining_time}s")
            return jsonify({
                'error': 'Access temporarily restricted',
                'retry_after': remaining_time
            }), 429
    
    # 2. فحص User-Agent المشبوه (مخفف للمصادر الموثوقة)
    user_agent = request.headers.get('User-Agent', '')
    
    if not is_trusted_ip:
        # قائمة مخففة من User-Agents المشبوهة
        highly_suspicious_agents = [
            'python-requests', 'curl', 'wget', 'scrapy', 'selenium'
        ]
        
        if any(agent in user_agent.lower() for agent in highly_suspicious_agents):
            if not smart_limiter.is_trusted_source(request):
                track_suspicious_session(client_ip, 'suspicious_user_agent', 1)  # تخفيف العقوبة
                app.logger.warning(f"Suspicious user agent from {client_ip}: {user_agent}")
    
    # 3. فحص الطلبات السريعة (مخفف)
    if not is_trusted_ip:
        session_key = f"last_request_time:{client_ip}"
        last_request_time = session.get(session_key, 0)
        current_time = time.time()
        
        if current_time - last_request_time < 0.1:  # أقل من 0.1 ثانية
            track_suspicious_session(client_ip, 'rapid_requests', 1)
        
        session[session_key] = current_time
    
    # 4. فحص طلبات 404 المتكررة (للجميع)
    if request.endpoint is None:  # 404 error
        if not is_trusted_ip:
            track_suspicious_session(client_ip, '404_requests', 0.5)  # تخفيف العقوبة
        app.logger.info(f"404 request from {client_ip}: {request.path}")

@app.after_request
def after_request(response):
    """معالج بعد كل طلب لتنظيف البيانات"""
    # تنظيف دوري للبيانات القديمة (كل 100 طلب تقريباً)
    if random.randint(1, 100) == 1:
        smart_limiter._cleanup_old_data(int(time.time()))
    
    return response

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
    try:
        # تنفيذ migration آمن أولاً
        safe_migration()
        
        # ثم تنفيذ باقي الإعدادات
        init_database()
        
    except Exception as e:
        app.logger.error(f"Database initialization error: {e}")
        print(f"Database initialization error: {e}")
    
    # إعداد webhook للتليجرام في production
    if not app.debug and telegram_system.is_configured():
        try:
            webhook_setup = telegram_system.setup_webhook()
            if webhook_setup:
                app.logger.info("Telegram webhook configured successfully")
            else:
                app.logger.warning("Failed to configure Telegram webhook")
        except Exception as e:
            app.logger.error(f"Error setting up Telegram webhook: {e}")

if __name__ == '__main__':
    app.run(debug=True)
