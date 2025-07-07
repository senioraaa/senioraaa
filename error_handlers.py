# ملف: error_handlers.py
# معالجات الأخطاء الشاملة لمشروع شهد السنيورة

from flask import jsonify, request, render_template, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.exceptions import RequestEntityTooLarge
import logging
import traceback
from datetime import datetime, timezone
import sys

# إعداد نظام السجلات
logger = logging.getLogger(__name__)

class ErrorHandler:
    """
    فئة معالجة الأخطاء الرئيسية
    تحتوي على جميع معالجات الأخطاء المختلفة
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        تهيئة معالجات الأخطاء مع التطبيق
        """
        self.app = app
        self.register_error_handlers()

    def register_error_handlers(self):
        """
        تسجيل جميع معالجات الأخطاء
        """
        # أخطاء HTTP العامة
        self.app.errorhandler(400)(self.handle_bad_request)
        self.app.errorhandler(401)(self.handle_unauthorized)
        self.app.errorhandler(403)(self.handle_forbidden)
        self.app.errorhandler(404)(self.handle_not_found)
        self.app.errorhandler(405)(self.handle_method_not_allowed)
        self.app.errorhandler(413)(self.handle_request_entity_too_large)
        self.app.errorhandler(429)(self.handle_rate_limit_exceeded)
        self.app.errorhandler(500)(self.handle_internal_server_error)
        self.app.errorhandler(502)(self.handle_bad_gateway)
        self.app.errorhandler(503)(self.handle_service_unavailable)

        # أخطاء قاعدة البيانات
        self.app.errorhandler(SQLAlchemyError)(self.handle_database_error)
        self.app.errorhandler(IntegrityError)(self.handle_integrity_error)

        # أخطاء عامة
        self.app.errorhandler(Exception)(self.handle_generic_exception)

        # معالج الأخطاء غير المتوقعة
        self.app.errorhandler(HTTPException)(self.handle_http_exception)

    def is_api_request(self):
        """
        فحص ما إذا كان الطلب من API
        """
        return (
            request.path.startswith('/api/') or
            request.headers.get('Content-Type', '').startswith('application/json') or
            'application/json' in request.headers.get('Accept', '')
        )

    def log_error(self, error, error_type="ERROR", extra_info=None):
        """
        تسجيل الأخطاء في ملف السجلات
        """
        error_info = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error_type': error_type,
            'error_message': str(error),
            'request_method': request.method if request else 'N/A',
            'request_url': request.url if request else 'N/A',
            'request_ip': self.get_client_ip(),
            'user_agent': request.headers.get('User-Agent', 'N/A') if request else 'N/A',
        }

        if extra_info:
            error_info.update(extra_info)

        # تسجيل الخطأ
        logger.error(f"{error_type}: {error_info}")

        # في حالة الأخطاء الخطيرة، طباعة التفاصيل الكاملة
        if error_type in ['CRITICAL', 'DATABASE_ERROR', 'INTERNAL_ERROR']:
            logger.critical(f"تفاصيل الخطأ الكاملة: {traceback.format_exc()}")

    def get_client_ip(self):
        """
        الحصول على عنوان IP الحقيقي للعميل
        """
        if not request:
            return 'N/A'

        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr or 'N/A'

    def create_error_response(self, error_code, error_message, details=None, suggestions=None):
        """
        إنشاء استجابة خطأ موحدة
        """
        error_response = {
            'success': False,
            'error': {
                'code': error_code,
                'message': error_message,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        }

        if details:
            error_response['error']['details'] = details

        if suggestions:
            error_response['error']['suggestions'] = suggestions

        # إضافة معلومات إضافية في وضع التطوير
        if current_app.debug:
            error_response['error']['debug_info'] = {
                'request_method': request.method if request else 'N/A',
                'request_url': request.url if request else 'N/A',
                'client_ip': self.get_client_ip(),
            }

        return error_response

    # معالجات الأخطاء المحددة

    def handle_bad_request(self, error):
        """
        معالج خطأ 400 - طلب غير صحيح
        """
        self.log_error(error, "BAD_REQUEST")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                400,
                "طلب غير صحيح",
                "البيانات المرسلة غير صحيحة أو ناقصة",
                ["تحقق من صحة البيانات المرسلة", "راجع وثائق API"]
            )), 400

        return render_template('errors/400.html'), 400

    def handle_unauthorized(self, error):
        """
        معالج خطأ 401 - غير مصرح
        """
        self.log_error(error, "UNAUTHORIZED")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                401,
                "غير مصرح بالوصول",
                "يجب تسجيل الدخول للوصول إلى هذا المورد",
                ["قم بتسجيل الدخول", "تحقق من صحة رمز المصادقة"]
            )), 401

        return render_template('errors/401.html'), 401

    def handle_forbidden(self, error):
        """
        معالج خطأ 403 - ممنوع
        """
        self.log_error(error, "FORBIDDEN")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                403,
                "الوصول ممنوع",
                "ليس لديك صلاحية للوصول إلى هذا المورد",
                ["تحقق من صلاحياتك", "اتصل بالمدير للحصول على الصلاحيات"]
            )), 403

        return render_template('errors/403.html'), 403

    def handle_not_found(self, error):
        """
        معالج خطأ 404 - غير موجود
        """
        self.log_error(error, "NOT_FOUND")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                404,
                "المورد غير موجود",
                "الصفحة أو المورد المطلوب غير موجود",
                ["تحقق من صحة الرابط", "راجع قائمة الموارد المتاحة"]
            )), 404

        return render_template('errors/404.html'), 404

    def handle_method_not_allowed(self, error):
        """
        معالج خطأ 405 - طريقة غير مسموحة
        """
        self.log_error(error, "METHOD_NOT_ALLOWED")

        allowed_methods = error.valid_methods if hasattr(error, 'valid_methods') else []

        if self.is_api_request():
            return jsonify(self.create_error_response(
                405,
                "طريقة HTTP غير مسموحة",
                f"الطرق المسموحة: {', '.join(allowed_methods)}",
                [f"استخدم إحدى الطرق المسموحة: {', '.join(allowed_methods)}"]
            )), 405

        return render_template('errors/405.html', allowed_methods=allowed_methods), 405

    def handle_request_entity_too_large(self, error):
        """
        معالج خطأ 413 - حجم الطلب كبير جداً
        """
        self.log_error(error, "REQUEST_TOO_LARGE")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                413,
                "حجم الطلب كبير جداً",
                "الملف أو البيانات المرسلة تتجاوز الحد المسموح",
                ["قلل من حجم الملف", "اضغط الملف قبل الرفع"]
            )), 413

        return render_template('errors/413.html'), 413

    def handle_rate_limit_exceeded(self, error):
        """
        معالج خطأ 429 - تجاوز حد الطلبات
        """
        self.log_error(error, "RATE_LIMIT_EXCEEDED")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                429,
                "تم تجاوز حد الطلبات المسموح",
                "لقد أرسلت طلبات كثيرة في فترة قصيرة",
                ["انتظر قليلاً قبل إرسال طلب جديد", "قلل من عدد الطلبات"]
            )), 429

        return render_template('errors/429.html'), 429

    def handle_internal_server_error(self, error):
        """
        معالج خطأ 500 - خطأ داخلي في الخادم
        """
        self.log_error(error, "INTERNAL_ERROR", {
            'traceback': traceback.format_exc()
        })

        if self.is_api_request():
            return jsonify(self.create_error_response(
                500,
                "خطأ داخلي في الخادم",
                "حدث خطأ غير متوقع، يرجى المحاولة لاحقاً",
                ["أعد المحاولة بعد قليل", "اتصل بالدعم الفني إذا استمر الخطأ"]
            )), 500

        return render_template('errors/500.html'), 500

    def handle_bad_gateway(self, error):
        """
        معالج خطأ 502 - بوابة سيئة
        """
        self.log_error(error, "BAD_GATEWAY")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                502,
                "خطأ في البوابة",
                "الخادم غير متاح حالياً",
                ["أعد المحاولة بعد قليل"]
            )), 502

        return render_template('errors/502.html'), 502

    def handle_service_unavailable(self, error):
        """
        معالج خطأ 503 - الخدمة غير متاحة
        """
        self.log_error(error, "SERVICE_UNAVAILABLE")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                503,
                "الخدمة غير متاحة",
                "الخادم في وضع الصيانة أو محمل بشكل زائد",
                ["أعد المحاولة بعد قليل", "تحقق من حالة الخدمة"]
            )), 503

        return render_template('errors/503.html'), 503

    def handle_database_error(self, error):
        """
        معالج أخطاء قاعدة البيانات
        """
        self.log_error(error, "DATABASE_ERROR", {
            'error_type': type(error).__name__,
            'traceback': traceback.format_exc()
        })

        # محاولة التراجع عن المعاملة
        try:
            from models import db
            db.session.rollback()
        except:
            pass

        if self.is_api_request():
            return jsonify(self.create_error_response(
                500,
                "خطأ في قاعدة البيانات",
                "حدث خطأ أثناء الوصول إلى قاعدة البيانات",
                ["أعد المحاولة بعد قليل", "تحقق من صحة البيانات المرسلة"]
            )), 500

        return render_template('errors/database_error.html'), 500

    def handle_integrity_error(self, error):
        """
        معالج أخطاء تكامل البيانات
        """
        self.log_error(error, "INTEGRITY_ERROR")

        # محاولة التراجع عن المعاملة
        try:
            from models import db
            db.session.rollback()
        except:
            pass

        # تحديد نوع خطأ التكامل
        error_message = str(error.orig) if hasattr(error, 'orig') else str(error)

        if 'UNIQUE constraint failed' in error_message or 'duplicate key' in error_message.lower():
            message = "البيانات موجودة مسبقاً"
            details = "يوجد سجل بنفس البيانات المدخلة"
            suggestions = ["استخدم بيانات مختلفة", "تحقق من البيانات الموجودة"]
        elif 'FOREIGN KEY constraint failed' in error_message:
            message = "خطأ في الربط بين البيانات"
            details = "البيانات المرجعية غير موجودة"
            suggestions = ["تحقق من صحة المعرفات المرجعية"]
        else:
            message = "خطأ في تكامل البيانات"
            details = "البيانات المدخلة لا تتوافق مع قواعد قاعدة البيانات"
            suggestions = ["تحقق من صحة البيانات المدخلة"]

        if self.is_api_request():
            return jsonify(self.create_error_response(
                400,
                message,
                details,
                suggestions
            )), 400

        return render_template('errors/integrity_error.html', 
                             message=message, details=details), 400

    def handle_http_exception(self, error):
        """
        معالج الأخطاء HTTP العامة
        """
        self.log_error(error, "HTTP_EXCEPTION")

        if self.is_api_request():
            return jsonify(self.create_error_response(
                error.code,
                error.name,
                error.description,
                ["راجع وثائق API", "تحقق من صحة الطلب"]
            )), error.code

        # محاولة عرض قالب خطأ مخصص
        try:
            return render_template(f'errors/{error.code}.html'), error.code
        except:
            return render_template('errors/generic.html', error=error), error.code

    def handle_generic_exception(self, error):
        """
        معالج الأخطاء العامة غير المتوقعة
        """
        self.log_error(error, "GENERIC_EXCEPTION", {
            'error_type': type(error).__name__,
            'traceback': traceback.format_exc()
        })

        if self.is_api_request():
            return jsonify(self.create_error_response(
                500,
                "خطأ غير متوقع",
                "حدث خطأ غير متوقع، يرجى المحاولة لاحقاً",
                ["أعد المحاولة بعد قليل", "اتصل بالدعم الفني"]
            )), 500

        return render_template('errors/500.html'), 500

# دوال مساعدة للتعامل مع الأخطاء

def handle_validation_error(errors):
    """
    معالجة أخطاء التحقق من صحة البيانات
    """
    error_messages = []

    if isinstance(errors, dict):
        for field, messages in errors.items():
            if isinstance(messages, list):
                for message in messages:
                    error_messages.append(f"{field}: {message}")
            else:
                error_messages.append(f"{field}: {messages}")
    elif isinstance(errors, list):
        error_messages = errors
    else:
        error_messages = [str(errors)]

    return {
        'success': False,
        'error': {
            'code': 400,
            'message': 'خطأ في التحقق من صحة البيانات',
            'details': error_messages,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }

def handle_authentication_error(message="فشل في المصادقة"):
    """
    معالجة أخطاء المصادقة
    """
    return {
        'success': False,
        'error': {
            'code': 401,
            'message': message,
            'details': 'يجب تسجيل الدخول للوصول إلى هذا المورد',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }

def handle_authorization_error(message="ليس لديك صلاحية"):
    """
    معالجة أخطاء التصريح
    """
    return {
        'success': False,
        'error': {
            'code': 403,
            'message': message,
            'details': 'ليس لديك صلاحية للوصول إلى هذا المورد',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }

def handle_not_found_error(resource="المورد"):
    """
    معالجة أخطاء عدم الوجود
    """
    return {
        'success': False,
        'error': {
            'code': 404,
            'message': f'{resource} غير موجود',
            'details': f'لم يتم العثور على {resource} المطلوب',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }

def create_success_response(data=None, message="تم بنجاح", meta=None):
    """
    إنشاء استجابة نجاح موحدة
    """
    response = {
        'success': True,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }

    if data is not None:
        response['data'] = data

    if meta:
        response['meta'] = meta

    return response

# فئة للتعامل مع أخطاء مخصصة
class CustomError(Exception):
    """
    فئة أخطاء مخصصة للتطبيق
    """

    def __init__(self, message, code=500, details=None, suggestions=None):
        self.message = message
        self.code = code
        self.details = details
        self.suggestions = suggestions
        super().__init__(self.message)

    def to_dict(self):
        """
        تحويل الخطأ إلى قاموس
        """
        error_dict = {
            'code': self.code,
            'message': self.message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        if self.details:
            error_dict['details'] = self.details

        if self.suggestions:
            error_dict['suggestions'] = self.suggestions

        return error_dict

class ValidationError(CustomError):
    """
    خطأ التحقق من صحة البيانات
    """
    def __init__(self, message, field=None, details=None):
        super().__init__(message, 400, details)
        self.field = field

class AuthenticationError(CustomError):
    """
    خطأ المصادقة
    """
    def __init__(self, message="فشل في المصادقة"):
        super().__init__(message, 401)

class AuthorizationError(CustomError):
    """
    خطأ التصريح
    """
    def __init__(self, message="ليس لديك صلاحية"):
        super().__init__(message, 403)

class NotFoundError(CustomError):
    """
    خطأ عدم الوجود
    """
    def __init__(self, resource="المورد"):
        super().__init__(f'{resource} غير موجود', 404)

class RateLimitError(CustomError):
    """
    خطأ تجاوز حد الطلبات
    """
    def __init__(self, message="تم تجاوز حد الطلبات"):
        super().__init__(message, 429)

# دالة لتهيئة معالجات الأخطاء
def init_error_handlers(app):
    """
    تهيئة معالجات الأخطاء مع التطبيق
    """
    error_handler = ErrorHandler(app)

    # إضافة معالج للأخطاء المخصصة
    @app.errorhandler(CustomError)
    def handle_custom_error(error):
        if error_handler.is_api_request():
            return jsonify({
                'success': False,
                'error': error.to_dict()
            }), error.code

        return render_template('errors/custom.html', error=error), error.code

    return error_handler

# إعداد نظام السجلات للأخطاء
def setup_error_logging(app):
    """
    إعداد نظام السجلات للأخطاء
    """
    if not app.debug:
        # إعداد ملف السجلات
        import os
        from logging.handlers import RotatingFileHandler

        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/errors.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )

        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))

        file_handler.setLevel(logging.ERROR)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.ERROR)
        app.logger.info('تم تشغيل نظام تسجيل الأخطاء')
