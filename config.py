# ملف: config.py
# إعدادات التطبيق المنظمة لمشروع شهد السنيورة

import os
from datetime import timedelta
from urllib.parse import quote_plus

class Config:
    """
    الإعدادات الأساسية للتطبيق
    تحتوي على جميع الإعدادات المشتركة بين البيئات المختلفة
    """

    # ===== الإعدادات الأساسية =====

    # مفتاح التشفير السري - يجب تغييره في الإنتاج
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'shahd-senior-secret-key-2024-change-in-production'

    # اسم التطبيق
    APP_NAME = os.environ.get('APP_NAME') or 'شهد السنيورة'

    # إصدار التطبيق
    APP_VERSION = os.environ.get('APP_VERSION') or '1.0.0'

    # وصف التطبيق
    APP_DESCRIPTION = os.environ.get('APP_DESCRIPTION') or 'تطبيق شهد السنيورة للمراسلة'

    # ===== إعدادات قاعدة البيانات =====

    # رابط قاعدة البيانات الافتراضي (SQLite)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///shahd_senior.db'

    # تعطيل تتبع التعديلات لتوفير الذاكرة
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # إعدادات تجمع الاتصالات
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20
    }

    # تفعيل echo للاستعلامات في وضع التطوير
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'False').lower() == 'true'

    # ===== إعدادات الجلسات =====

    # مدة انتهاء الجلسة (30 يوم)
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get('SESSION_LIFETIME_DAYS', 30)))

    # إعدادات أمان الجلسة
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # ===== إعدادات الأمان =====

    # تفعيل CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # ساعة واحدة

    # إعدادات كلمات المرور
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_REQUIRE_UPPERCASE = os.environ.get('PASSWORD_REQUIRE_UPPERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_LOWERCASE = os.environ.get('PASSWORD_REQUIRE_LOWERCASE', 'True').lower() == 'true'
    PASSWORD_REQUIRE_NUMBERS = os.environ.get('PASSWORD_REQUIRE_NUMBERS', 'True').lower() == 'true'
    PASSWORD_REQUIRE_SYMBOLS = os.environ.get('PASSWORD_REQUIRE_SYMBOLS', 'False').lower() == 'true'

    # إعدادات Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '1000 per hour')

    # ===== إعدادات البريد الإلكتروني =====

    # إعدادات خادم SMTP
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'

    # بيانات اعتماد البريد الإلكتروني
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # البريد الافتراضي للمرسل
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@shahd-senior.com'

    # قائمة المديرين
    ADMINS = os.environ.get('ADMINS', '').split(',') if os.environ.get('ADMINS') else []

    # ===== إعدادات رفع الملفات =====

    # مجلد رفع الملفات
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.getcwd(), 'uploads')

    # الحد الأقصى لحجم الملف (16 ميجابايت)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    # أنواع الملفات المسموحة
    ALLOWED_EXTENSIONS = {
        'images': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
        'documents': {'pdf', 'doc', 'docx', 'txt', 'rtf'},
        'archives': {'zip', 'rar', '7z'},
        'audio': {'mp3', 'wav', 'ogg', 'm4a'},
        'video': {'mp4', 'avi', 'mov', 'wmv', 'flv'}
    }

    # الحد الأقصى لحجم الصور (5 ميجابايت)
    MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', 5 * 1024 * 1024))

    # جودة ضغط الصور
    IMAGE_QUALITY = int(os.environ.get('IMAGE_QUALITY', 85))

    # ===== إعدادات التخزين المؤقت =====

    # نوع التخزين المؤقت
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 دقائق

    # إعدادات Redis للتخزين المؤقت
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')

    # ===== إعدادات التوطين =====

    # اللغات المدعومة
    LANGUAGES = {
        'ar': 'العربية',
        'en': 'English'
    }

    # اللغة الافتراضية
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'ar')

    # المنطقة الزمنية
    TIMEZONE = os.environ.get('TIMEZONE', 'Asia/Riyadh')

    # ===== إعدادات الرسائل =====

    # الحد الأقصى لطول الرسالة
    MAX_MESSAGE_LENGTH = int(os.environ.get('MAX_MESSAGE_LENGTH', 1000))

    # الحد الأقصى لعدد الرسائل في الصفحة
    MESSAGES_PER_PAGE = int(os.environ.get('MESSAGES_PER_PAGE', 50))

    # مدة الاحتفاظ بالرسائل المحذوفة (أيام)
    DELETED_MESSAGES_RETENTION_DAYS = int(os.environ.get('DELETED_MESSAGES_RETENTION_DAYS', 30))

    # تفعيل إشعارات الرسائل
    ENABLE_MESSAGE_NOTIFICATIONS = os.environ.get('ENABLE_MESSAGE_NOTIFICATIONS', 'True').lower() == 'true'

    # ===== إعدادات المستخدمين =====

    # السماح بالتسجيل الجديد
    REGISTRATION_ENABLED = os.environ.get('REGISTRATION_ENABLED', 'True').lower() == 'true'

    # تفعيل التحقق من البريد الإلكتروني
    EMAIL_VERIFICATION_REQUIRED = os.environ.get('EMAIL_VERIFICATION_REQUIRED', 'True').lower() == 'true'

    # مدة صلاحية رمز التفعيل (ساعات)
    VERIFICATION_TOKEN_EXPIRY_HOURS = int(os.environ.get('VERIFICATION_TOKEN_EXPIRY_HOURS', 24))

    # الحد الأقصى لعدد المستخدمين في الصفحة
    USERS_PER_PAGE = int(os.environ.get('USERS_PER_PAGE', 20))

    # ===== إعدادات السجلات =====

    # مستوى السجلات
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # مجلد السجلات
    LOG_FOLDER = os.environ.get('LOG_FOLDER') or os.path.join(os.getcwd(), 'logs')

    # الحد الأقصى لحجم ملف السجل (10 ميجابايت)
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10 * 1024 * 1024))

    # عدد ملفات السجل المحفوظة
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))

    # ===== إعدادات الأداء =====

    # تفعيل ضغط الاستجابات
    COMPRESS_MIMETYPES = [
        'text/html', 'text/css', 'text/xml', 'text/javascript',
        'application/json', 'application/javascript'
    ]

    # مستوى الضغط
    COMPRESS_LEVEL = int(os.environ.get('COMPRESS_LEVEL', 6))

    # تفعيل التخزين المؤقت للملفات الثابتة
    SEND_FILE_MAX_AGE_DEFAULT = int(os.environ.get('SEND_FILE_MAX_AGE_DEFAULT', 31536000))  # سنة واحدة

    # ===== إعدادات الأمان المتقدمة =====

    # تفعيل HTTPS فقط
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'

    # إعدادات Content Security Policy
    CSP_DIRECTIVES = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data: https:",
        'font-src': "'self' https:",
        'connect-src': "'self'",
        'frame-ancestors': "'none'"
    }

    # تفعيل حماية XSS
    XSS_PROTECTION = True

    # تفعيل حماية Content Type
    CONTENT_TYPE_NOSNIFF = True

    # ===== إعدادات API =====

    # إصدار API
    API_VERSION = os.environ.get('API_VERSION', 'v1')

    # بادئة مسارات API
    API_PREFIX = f'/api/{API_VERSION}'

    # تفعيل وثائق API
    API_DOCS_ENABLED = os.environ.get('API_DOCS_ENABLED', 'True').lower() == 'true'

    # الحد الأقصى لعدد النتائج في API
    API_MAX_RESULTS = int(os.environ.get('API_MAX_RESULTS', 100))

    # ===== إعدادات المهام الخلفية =====

    # إعدادات Celery (إذا كان متاحاً)
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'

    # ===== إعدادات المراقبة =====

    # تفعيل مراقبة الأداء
    MONITORING_ENABLED = os.environ.get('MONITORING_ENABLED', 'False').lower() == 'true'

    # مفتاح Sentry (إذا كان متاحاً)
    SENTRY_DSN = os.environ.get('SENTRY_DSN')

    # ===== دوال مساعدة =====

    @staticmethod
    def init_app(app):
        """
        تهيئة التطبيق مع الإعدادات
        """
        # إنشاء المجلدات المطلوبة
        Config.create_required_directories()

        # تطبيق إعدادات الأمان
        Config.apply_security_settings(app)

    @staticmethod
    def create_required_directories():
        """
        إنشاء المجلدات المطلوبة للتطبيق
        """
        directories = [
            Config.UPLOAD_FOLDER,
            Config.LOG_FOLDER,
            os.path.join(Config.UPLOAD_FOLDER, 'images'),
            os.path.join(Config.UPLOAD_FOLDER, 'documents'),
            os.path.join(Config.UPLOAD_FOLDER, 'temp')
        ]

        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    @staticmethod
    def apply_security_settings(app):
        """
        تطبيق إعدادات الأمان على التطبيق
        """
        # إعداد Headers الأمان
        @app.after_request
        def set_security_headers(response):
            # حماية XSS
            if Config.XSS_PROTECTION:
                response.headers['X-XSS-Protection'] = '1; mode=block'

            # حماية Content Type
            if Config.CONTENT_TYPE_NOSNIFF:
                response.headers['X-Content-Type-Options'] = 'nosniff'

            # منع التضمين في إطارات
            response.headers['X-Frame-Options'] = 'DENY'

            # إعدادات HTTPS
            if Config.FORCE_HTTPS:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

            return response

    @staticmethod
    def get_database_uri():
        """
        الحصول على رابط قاعدة البيانات مع معالجة كلمات المرور الخاصة
        """
        database_url = os.environ.get('DATABASE_URL')
        if database_url and database_url.startswith('postgres://'):
            # تحويل postgres:// إلى postgresql:// للتوافق مع SQLAlchemy الحديث
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

        return database_url or Config.SQLALCHEMY_DATABASE_URI

    @staticmethod
    def is_email_configured():
        """
        فحص ما إذا كان البريد الإلكتروني مُعد
        """
        return bool(Config.MAIL_USERNAME and Config.MAIL_PASSWORD)

    @staticmethod
    def get_allowed_extensions():
        """
        الحصول على جميع أنواع الملفات المسموحة
        """
        all_extensions = set()
        for extensions in Config.ALLOWED_EXTENSIONS.values():
            all_extensions.update(extensions)
        return all_extensions

class DevelopmentConfig(Config):
    """
    إعدادات بيئة التطوير
    """
    DEBUG = True
    TESTING = False

    # تفعيل echo للاستعلامات
    SQLALCHEMY_ECHO = True

    # تعطيل CSRF في التطوير للاختبار
    WTF_CSRF_ENABLED = False

    # إعدادات البريد للتطوير (طباعة في وحدة التحكم)
    MAIL_SUPPRESS_SEND = True

    # تفعيل إعادة التحميل التلقائي
    TEMPLATES_AUTO_RELOAD = True

    # إعدادات أقل صرامة للتطوير
    SESSION_COOKIE_SECURE = False
    FORCE_HTTPS = False

    # مستوى سجلات مفصل
    LOG_LEVEL = 'DEBUG'

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # إعداد سجلات التطوير
        import logging
        logging.basicConfig(level=logging.DEBUG)

        print("🔧 تم تشغيل التطبيق في وضع التطوير")

class TestingConfig(Config):
    """
    إعدادات بيئة الاختبار
    """
    TESTING = True
    DEBUG = False

    # قاعدة بيانات في الذاكرة للاختبار
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # تعطيل CSRF للاختبار
    WTF_CSRF_ENABLED = False

    # تعطيل البريد الإلكتروني
    MAIL_SUPPRESS_SEND = True

    # إعدادات سريعة للاختبار
    PASSWORD_MIN_LENGTH = 4
    VERIFICATION_TOKEN_EXPIRY_HOURS = 1

    # تعطيل Rate Limiting
    RATELIMIT_ENABLED = False

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        print("🧪 تم تشغيل التطبيق في وضع الاختبار")

class ProductionConfig(Config):
    """
    إعدادات بيئة الإنتاج
    """
    DEBUG = False
    TESTING = False

    # إعدادات أمان صارمة
    SESSION_COOKIE_SECURE = True
    FORCE_HTTPS = True
    WTF_CSRF_ENABLED = True

    # تفعيل جميع إعدادات الأمان
    XSS_PROTECTION = True
    CONTENT_TYPE_NOSNIFF = True

    # إعدادات قاعدة البيانات محسنة للإنتاج
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': 3600,  # ساعة واحدة
        'pool_pre_ping': True,
        'pool_size': 20,
        'max_overflow': 40
    }

    # مستوى سجلات أقل تفصيلاً
    LOG_LEVEL = 'WARNING'

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # إعداد سجلات الإنتاج
        import logging
        from logging.handlers import RotatingFileHandler, SMTPHandler

        # إعداد ملف السجلات
        if not os.path.exists(cls.LOG_FOLDER):
            os.makedirs(cls.LOG_FOLDER)

        file_handler = RotatingFileHandler(
            os.path.join(cls.LOG_FOLDER, 'shahd_senior.log'),
            maxBytes=cls.LOG_MAX_SIZE,
            backupCount=cls.LOG_BACKUP_COUNT
        )

        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))

        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

        # إعداد إرسال الأخطاء بالبريد الإلكتروني
        if cls.is_email_configured() and cls.ADMINS:
            mail_handler = SMTPHandler(
                mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
                fromaddr=cls.MAIL_DEFAULT_SENDER,
                toaddrs=cls.ADMINS,
                subject='خطأ في تطبيق شهد السنيورة',
                credentials=(cls.MAIL_USERNAME, cls.MAIL_PASSWORD),
                secure=() if cls.MAIL_USE_TLS else None
            )

            mail_handler.setLevel(logging.ERROR)
            mail_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))

            app.logger.addHandler(mail_handler)

        app.logger.setLevel(logging.WARNING)
        print("🚀 تم تشغيل التطبيق في وضع الإنتاج")

class StagingConfig(ProductionConfig):
    """
    إعدادات بيئة التجريب (Staging)
    مشابهة للإنتاج لكن مع بعض التسهيلات للاختبار
    """
    DEBUG = False
    TESTING = False

    # إعدادات أقل صرامة من الإنتاج
    LOG_LEVEL = 'INFO'

    # السماح بوثائق API في التجريب
    API_DOCS_ENABLED = True

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        print("🎭 تم تشغيل التطبيق في وضع التجريب")

# قاموس الإعدادات المتاحة
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}

# دالة للحصول على الإعدادات حسب البيئة
def get_config(config_name=None):
    """
    الحصول على إعدادات البيئة المطلوبة

    Args:
        config_name (str): اسم البيئة (development, testing, production, staging)

    Returns:
        Config: فئة الإعدادات المناسبة
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    return config.get(config_name, config['default'])

# دالة للتحقق من صحة الإعدادات
def validate_config(config_class):
    """
    التحقق من صحة الإعدادات المطلوبة

    Args:
        config_class: فئة الإعدادات للتحقق منها

    Returns:
        list: قائمة بالأخطاء إن وجدت
    """
    errors = []

    # التحقق من المفتاح السري
    if not config_class.SECRET_KEY or config_class.SECRET_KEY == 'shahd-senior-secret-key-2024-change-in-production':
        if config_class.__name__ == 'ProductionConfig':
            errors.append("يجب تغيير SECRET_KEY في بيئة الإنتاج")

    # التحقق من إعدادات قاعدة البيانات
    if not config_class.SQLALCHEMY_DATABASE_URI:
        errors.append("يجب تحديد رابط قاعدة البيانات")

    # التحقق من إعدادات البريد الإلكتروني في الإنتاج
    if config_class.__name__ == 'ProductionConfig':
        if not config_class.is_email_configured():
            errors.append("يجب تكوين إعدادات البريد الإلكتروني في الإنتاج")

    # التحقق من وجود المجلدات المطلوبة
    required_dirs = [config_class.UPLOAD_FOLDER, config_class.LOG_FOLDER]
    for directory in required_dirs:
        parent_dir = os.path.dirname(directory)
        if not os.path.exists(parent_dir) and not os.access(parent_dir, os.W_OK):
            errors.append(f"لا يمكن إنشاء المجلد: {directory}")

    return errors

# دالة لطباعة ملخص الإعدادات
def print_config_summary(config_class):
    """
    طباعة ملخص الإعدادات الحالية
    """
    print(f"
📋 ملخص إعدادات {config_class.__name__}:")
    print(f"   🔧 وضع التطوير: {config_class.DEBUG}")
    print(f"   🧪 وضع الاختبار: {config_class.TESTING}")
    print(f"   🗄️  قاعدة البيانات: {config_class.get_database_uri()}")
    print(f"   📧 البريد مُعد: {config_class.is_email_configured()}")
    print(f"   📁 مجلد الرفع: {config_class.UPLOAD_FOLDER}")
    print(f"   📊 مستوى السجلات: {config_class.LOG_LEVEL}")
    print(f"   🔒 HTTPS إجباري: {getattr(config_class, 'FORCE_HTTPS', False)}")
    print(f"   ⏱️  مدة الجلسة: {config_class.PERMANENT_SESSION_LIFETIME}")
    print()
