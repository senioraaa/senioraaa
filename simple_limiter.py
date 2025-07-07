# ملف: simple_limiter.py
# نظام Rate Limiting المبسط لحماية التطبيق من الطلبات المفرطة

import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, g
import logging

# إعداد نظام السجلات
logger = logging.getLogger(__name__)

class SimpleLimiter:
    """
    نظام Rate Limiting مبسط يستخدم الذاكرة المحلية
    يحدد عدد الطلبات المسموحة لكل عنوان IP في فترة زمنية محددة
    """

    def __init__(self):
        # قاموس لتخزين طلبات كل عنوان IP
        self.requests = defaultdict(deque)
        # قاموس لتخزين وقت آخر تنظيف للطلبات القديمة
        self.last_cleanup = defaultdict(float)

    def is_allowed(self, key, limit=100, window=3600):
        """
        فحص ما إذا كان الطلب مسموح أم لا

        Args:
            key (str): مفتاح التعريف (عادة عنوان IP)
            limit (int): عدد الطلبات المسموحة (افتراضي: 100)
            window (int): النافذة الزمنية بالثواني (افتراضي: 3600 = ساعة واحدة)

        Returns:
            bool: True إذا كان الطلب مسموح، False إذا تم تجاوز الحد
        """
        current_time = time.time()

        # تنظيف الطلبات القديمة كل 5 دقائق
        if current_time - self.last_cleanup[key] > 300:
            self._cleanup_old_requests(key, current_time, window)
            self.last_cleanup[key] = current_time

        # إضافة الطلب الحالي
        self.requests[key].append(current_time)

        # فحص عدد الطلبات في النافزة الزمنية
        valid_requests = [req_time for req_time in self.requests[key] 
                         if current_time - req_time <= window]

        # تحديث قائمة الطلبات
        self.requests[key] = deque(valid_requests)

        return len(valid_requests) <= limit

    def _cleanup_old_requests(self, key, current_time, window):
        """
        تنظيف الطلبات القديمة التي تجاوزت النافذة الزمنية
        """
        if key in self.requests:
            valid_requests = [req_time for req_time in self.requests[key] 
                             if current_time - req_time <= window]
            self.requests[key] = deque(valid_requests)

    def get_remaining_requests(self, key, limit=100, window=3600):
        """
        الحصول على عدد الطلبات المتبقية

        Returns:
            int: عدد الطلبات المتبقية
        """
        current_time = time.time()
        valid_requests = [req_time for req_time in self.requests[key] 
                         if current_time - req_time <= window]
        return max(0, limit - len(valid_requests))

    def get_reset_time(self, key, window=3600):
        """
        الحصول على وقت إعادة تعيين العداد

        Returns:
            float: وقت إعادة التعيين (timestamp)
        """
        if key not in self.requests or not self.requests[key]:
            return time.time()

        oldest_request = min(self.requests[key])
        return oldest_request + window

# إنشاء مثيل عام من نظام Rate Limiting
limiter = SimpleLimiter()

def rate_limit(limit=100, window=3600, key_func=None):
    """
    ديكوريتر لتطبيق Rate Limiting على الدوال

    Args:
        limit (int): عدد الطلبات المسموحة
        window (int): النافذة الزمنية بالثواني
        key_func (function): دالة لتحديد مفتاح التعريف
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # تحديد مفتاح التعريف
            if key_func:
                key = key_func()
            else:
                key = get_client_ip()

            # فحص الحد المسموح
            if not limiter.is_allowed(key, limit, window):
                logger.warning(f"Rate limit exceeded for IP: {key}")

                # إرجاع رسالة خطأ مع معلومات إضافية
                reset_time = limiter.get_reset_time(key, window)
                return jsonify({
                    'error': 'تم تجاوز الحد المسموح من الطلبات',
                    'message': f'يمكنك إرسال {limit} طلب كل {window} ثانية',
                    'retry_after': int(reset_time - time.time()),
                    'reset_time': int(reset_time)
                }), 429

            # إضافة معلومات Rate Limiting إلى الاستجابة
            g.rate_limit_remaining = limiter.get_remaining_requests(key, limit, window)
            g.rate_limit_reset = limiter.get_reset_time(key, window)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_client_ip():
    """
    الحصول على عنوان IP الحقيقي للعميل
    يأخذ في الاعتبار Proxy Headers
    """
    # فحص Headers المختلفة للحصول على IP الحقيقي
    if request.headers.get('X-Forwarded-For'):
        # أخذ أول IP في القائمة (IP الأصلي)
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    elif request.headers.get('X-Forwarded-Host'):
        ip = request.headers.get('X-Forwarded-Host')
    else:
        ip = request.remote_addr

    return ip or '127.0.0.1'

def add_rate_limit_headers(response):
    """
    إضافة Headers خاصة بـ Rate Limiting إلى الاستجابة
    """
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)

    if hasattr(g, 'rate_limit_reset'):
        response.headers['X-RateLimit-Reset'] = str(int(g.rate_limit_reset))

    return response

# إعدادات Rate Limiting المختلفة للاستخدامات المتنوعة
class RateLimitConfig:
    """
    إعدادات Rate Limiting المختلفة
    """
    # للطلبات العامة
    GENERAL = {'limit': 1000, 'window': 3600}  # 1000 طلب في الساعة

    # لتسجيل الدخول
    LOGIN = {'limit': 10, 'window': 900}  # 10 محاولات في 15 دقيقة

    # للتسجيل
    REGISTER = {'limit': 5, 'window': 3600}  # 5 تسجيلات في الساعة

    # لإرسال الرسائل
    MESSAGES = {'limit': 50, 'window': 3600}  # 50 رسالة في الساعة

    # للبحث
    SEARCH = {'limit': 100, 'window': 3600}  # 100 بحث في الساعة

    # لرفع الملفات
    UPLOAD = {'limit': 20, 'window': 3600}  # 20 رفع في الساعة

# دوال مساعدة للاستخدام السريع
def general_rate_limit():
    """Rate limiting للطلبات العامة"""
    return rate_limit(**RateLimitConfig.GENERAL)

def login_rate_limit():
    """Rate limiting لتسجيل الدخول"""
    return rate_limit(**RateLimitConfig.LOGIN)

def register_rate_limit():
    """Rate limiting للتسجيل"""
    return rate_limit(**RateLimitConfig.REGISTER)

def message_rate_limit():
    """Rate limiting للرسائل"""
    return rate_limit(**RateLimitConfig.MESSAGES)

def search_rate_limit():
    """Rate limiting للبحث"""
    return rate_limit(**RateLimitConfig.SEARCH)

def upload_rate_limit():
    """Rate limiting لرفع الملفات"""
    return rate_limit(**RateLimitConfig.UPLOAD)

# دالة لتنظيف البيانات القديمة دورياً
def cleanup_old_data():
    """
    تنظيف البيانات القديمة من الذاكرة
    يجب استدعاؤها دورياً لتجنب امتلاء الذاكرة
    """
    current_time = time.time()
    keys_to_remove = []

    for key in limiter.requests:
        # إزالة الطلبات الأقدم من 24 ساعة
        valid_requests = [req_time for req_time in limiter.requests[key] 
                         if current_time - req_time <= 86400]

        if valid_requests:
            limiter.requests[key] = deque(valid_requests)
        else:
            keys_to_remove.append(key)

    # إزالة المفاتيح الفارغة
    for key in keys_to_remove:
        del limiter.requests[key]
        if key in limiter.last_cleanup:
            del limiter.last_cleanup[key]

    logger.info(f"تم تنظيف {len(keys_to_remove)} مفتاح من بيانات Rate Limiting")
