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
from sqlalchemy import text # <--- هذا هو السطر الذي تم إضافته لإصلاح مشكلة Textual SQL expression

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
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
    
    # حقول الملف الشخصي الجديدة
    whatsapp = db.Column(db.String(20))
    preferred_platform = db.Column(db.String(10))
    preferred_payment = db.Column(db.String(50))
    ea_email = db.Column(db.String(100))
    telegram_id = db.Column(db.String(50))
    telegram_username = db.Column(db.String(50))
    profile_completed = db.Column(db.Boolean, default=False)
    last_profile_update = db.Column(db.DateTime)

class Order(db.Model):
    __tablename__ = 'orders'  # Explicit table name
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    platform = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    coins_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # حقول إضافية للطلبات
    ea_email = db.Column(db.String(100))
    ea_password = db.Column(db.String(200))  # مشفرة
    backup_codes = db.Column(db.Text)  # مشفرة أيضاً
    transfer_type = db.Column(db.String(20), default='normal')  # normal, instant
    notes = db.Column(db.Text)
    price = db.Column(db.Float)
    phone_number = db.Column(db.String(20))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
                    
                    # فحص اكتمال الملف الشخصي
                    current_user.profile_completed = check_profile_completion(current_user)
                    
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

def check_profile_completion(user):
    """فحص اكتمال الملف الشخصي"""
    required_fields = ['whatsapp', 'preferred_platform', 'preferred_payment']
    
    for field in required_fields:
        value = getattr(user, field, None)
        if not value or not value.strip():
            return False
    
    return True

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
        
        # تحديث الجداول الموجودة لإضافة الحقول الجديدة
        update_existing_tables()
        
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

def update_existing_tables():
    """تحديث الجداول الموجودة لإضافة الحقول الجديدة"""
    try:
        with app.app_context():
            # إضافة الحقول الجديدة إذا لم تكن موجودة
            new_columns = [
                ('users', 'whatsapp', 'VARCHAR(20)'),
                ('users', 'preferred_platform', 'VARCHAR(10)'),
                ('users', 'preferred_payment', 'VARCHAR(50)'),
                ('users', 'ea_email', 'VARCHAR(100)'),
                ('users', 'telegram_id', 'VARCHAR(50)'),
                ('users', 'telegram_username', 'VARCHAR(50)'),
                ('users', 'profile_completed', 'BOOLEAN DEFAULT FALSE'),
                ('users', 'last_profile_update', 'DATETIME'),
                ('orders', 'ea_email', 'VARCHAR(100)'),
                ('orders', 'ea_password', 'VARCHAR(200)'),
                ('orders', 'backup_codes', 'TEXT'),
                ('orders', 'transfer_type', 'VARCHAR(20) DEFAULT "normal"'),
                ('orders', 'notes', 'TEXT'),
                ('orders', 'price', 'FLOAT'),
                ('orders', 'phone_number', 'VARCHAR(20)'),
                ('orders', 'updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
            ]
            
            for table, column, column_type in new_columns:
                try:
                    db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {column_type}'))
                    print(f"Added column {column} to {table}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        pass  # العمود موجود بالفعل
                    else:
                        print(f"Error adding column {column}: {e}")
            
            db.session.commit()
            print("Database tables updated successfully")
            
    except Exception as e:
        print(f"Database update error: {e}")
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
    init_database()

if __name__ == '__main__':
    app.run(debug=True)
