import os
from datetime import datetime

# إعدادات التليجرام
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'YOUR_CHAT_ID_HERE')

# إعدادات الواتساب
WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '201234567890')

# إعدادات الموقع
SITE_NAME = "منصة شهد السنيورة"
SITE_URL = "https://senioraa.onrender.com"
SITE_DESCRIPTION = "أرخص أسعار الألعاب الرقمية في مصر"

# إعدادات البريد الإلكتروني
EMAIL_INFO = os.environ.get('EMAIL_INFO', 'info@senioraa.com')
EMAIL_SUPPORT = os.environ.get('EMAIL_SUPPORT', 'support@senioraa.com')
EMAIL_LEGAL = os.environ.get('EMAIL_LEGAL', 'legal@senioraa.com')

# إعدادات الألعاب
SUPPORTED_GAMES = {
    'fc25': {
        'name': 'EA Sports FC 25',
        'description': 'أحدث إصدار من لعبة كرة القدم الشهيرة',
        'platforms': ['PS4', 'PS5', 'Xbox', 'PC'],
        'account_types': ['primary', 'secondary', 'full'],
        'release_date': '2024-09-29'
    }
}

# إعدادات المنصات
SUPPORTED_PLATFORMS = {
    'ps4': {
        'name': 'PlayStation 4',
        'icon': '🎮',
        'color': '#003087'
    },
    'ps5': {
        'name': 'PlayStation 5',
        'icon': '🎮',
        'color': '#00439C'
    },
    'xbox': {
        'name': 'Xbox Series X/S & Xbox One',
        'icon': '🎮',
        'color': '#107C10'
    },
    'pc': {
        'name': 'PC (Steam/Epic Games)',
        'icon': '💻',
        'color': '#171A21'
    }
}

# إعدادات أنواع الحسابات
ACCOUNT_TYPES = {
    'primary': {
        'name': 'Primary',
        'name_ar': 'أساسي',
        'description': 'تفعيل أساسي - العب من حسابك الشخصي',
        'color': '#4CAF50',
        'icon': '🟢',
        'features': [
            'تفعيل الحساب كأساسي',
            'اللعب من حسابك الشخصي',
            'الألعاب متاحة لكل المستخدمين',
            'ضمان أطول'
        ]
    },
    'secondary': {
        'name': 'Secondary',
        'name_ar': 'ثانوي',
        'description': 'تسجيل دخول مؤقت - سعر أرخص',
        'color': '#FF9800',
        'icon': '🟡',
        'features': [
            'تسجيل دخول مؤقت',
            'تحميل اللعبة',
            'العودة لحسابك الشخصي',
            'قيود أكثر في الاستخدام'
        ]
    },
    'full': {
        'name': 'Full',
        'name_ar': 'كامل',
        'description': 'حساب كامل قابل للتعديل',
        'color': '#2196F3',
        'icon': '🔵',
        'features': [
            'حساب كامل',
            'قابل للتعديل',
            'مرونة كاملة',
            'أفضل قيمة'
        ]
    }
}

# إعدادات طرق الدفع
PAYMENT_METHODS = {
    'vodafone_cash': {
        'name': 'فودافون كاش',
        'name_en': 'Vodafone Cash',
        'icon': '📱',
        'color': '#E60000'
    },
    'orange_money': {
        'name': 'أورانج موني',
        'name_en': 'Orange Money',
        'icon': '🟠',
        'color': '#FF6600'
    },
    'etisalat_cash': {
        'name': 'إتصالات كاش',
        'name_en': 'Etisalat Cash',
        'icon': '🟢',
        'color': '#00B04F'
    },
    'bank_transfer': {
        'name': 'تحويل بنكي',
        'name_en': 'Bank Transfer',
        'icon': '🏦',
        'color': '#2196F3'
    },
    'credit_card': {
        'name': 'بطاقة ائتمان',
        'name_en': 'Credit Card',
        'icon': '💳',
        'color': '#4CAF50'
    }
}

# إعدادات الأسعار الافتراضية
DEFAULT_PRICES = {
    'fc25': {
        'ps4': {
            'primary': 50,
            'secondary': 30,
            'full': 80
        },
        'ps5': {
            'primary': 60,
            'secondary': 40,
            'full': 100
        },
        'xbox': {
            'primary': 55,
            'secondary': 35,
            'full': 90
        },
        'pc': {
            'primary': 45,
            'secondary': 25,
            'full': 70
        }
    }
}

# إعدادات العملة
CURRENCY = {
    'symbol': 'جنيه',
    'symbol_en': 'EGP',
    'code': 'EGP'
}

# إعدادات الضمان
WARRANTY_PERIOD = 6  # بالأشهر
DELIVERY_TIME = 15  # بالساعات
RESPONSE_TIME = 15  # بالدقائق

# إعدادات وقت العمل
WORKING_HOURS = {
    'saturday_to_thursday': {
        'start': '09:00',
        'end': '00:00'
    },
    'friday': {
        'start': '14:00',
        'end': '00:00'
    },
    'emergency': '24/7'
}

# إعدادات الموقع الجغرافي
SUPPORTED_REGIONS = {
    'egypt': {
        'name': 'مصر',
        'name_en': 'Egypt',
        'flag': '🇪🇬',
        'currency': 'EGP',
        'phone_code': '+20'
    },
    'saudi': {
        'name': 'السعودية',
        'name_en': 'Saudi Arabia',
        'flag': '🇸🇦',
        'currency': 'SAR',
        'phone_code': '+966'
    },
    'uae': {
        'name': 'الإمارات',
        'name_en': 'UAE',
        'flag': '🇦🇪',
        'currency': 'AED',
        'phone_code': '+971'
    }
}

# إعدادات الإشعارات
NOTIFICATION_SETTINGS = {
    'new_order': True,
    'price_update': True,
    'customer_message': True,
    'daily_report': True,
    'error_alerts': True
}

# إعدادات التحليلات
ANALYTICS_SETTINGS = {
    'google_analytics_id': os.environ.get('GOOGLE_ANALYTICS_ID', ''),
    'facebook_pixel_id': os.environ.get('FACEBOOK_PIXEL_ID', ''),
    'track_orders': True,
    'track_prices': True,
    'track_visitors': True
}

# إعدادات الأمان
SECURITY_SETTINGS = {
    'max_login_attempts': 5,
    'session_timeout': 3600,  # ثانية
    'password_min_length': 8,
    'enable_2fa': False
}

# إعدادات قاعدة البيانات
DATABASE_CONFIG = {
    'type': 'json',  # json أو sqlite
    'json_file': 'data/prices.json',
    'sqlite_file': 'data/database.db'
}

# إعدادات الملفات
FILE_SETTINGS = {
    'upload_folder': 'uploads',
    'max_file_size': 5 * 1024 * 1024,  # 5 ميجابايت
    'allowed_extensions': ['jpg', 'jpeg', 'png', 'gif', 'pdf']
}

# إعدادات التطوير
DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'
DEVELOPMENT_MODE = os.environ.get('DEVELOPMENT', 'False').lower() == 'true'

# إعدادات الإنتاج
PRODUCTION_SETTINGS = {
    'use_ssl': True,
    'enable_caching': True,
    'compress_responses': True,
    'log_level': 'INFO'
}

# إعدادات النسخ الاحتياطي
BACKUP_SETTINGS = {
    'enabled': True,
    'frequency': 'daily',  # daily, weekly, monthly
    'keep_backups': 7,  # عدد النسخ المحفوظة
    'backup_folder': 'backups'
}

# إعدادات الصيانة
MAINTENANCE_MODE = os.environ.get('MAINTENANCE_MODE', 'False').lower() == 'true'
MAINTENANCE_MESSAGE = "الموقع تحت الصيانة حالياً. سنعود قريباً!"

# إعدادات الإحصائيات
STATS_SETTINGS = {
    'track_daily_orders': True,
    'track_monthly_revenue': True,
    'track_popular_games': True,
    'track_popular_platforms': True
}

# إعدادات الخصومات
DISCOUNT_SETTINGS = {
    'new_customer_discount': 10,  # نسبة مئوية
    'bulk_order_discount': 15,   # للطلبات الكبيرة
    'loyal_customer_discount': 20,  # للعملاء المخلصين
    'referral_bonus': 50  # بالجنيه للإحالة
}

# إعدادات الرسائل
MESSAGE_TEMPLATES = {
    'order_confirmation': """
مرحباً بك في منصة شهد السنيورة! 🎮

طلب جديد:
🎯 اللعبة: {game}
📱 المنصة: {platform}
💎 نوع الحساب: {account_type}
💰 السعر: {price} جنيه
📞 طريقة الدفع: {payment_method}
⏰ وقت الطلب: {timestamp}

سيتم التواصل معك خلال 15 دقيقة لتأكيد الطلب! 🚀
    """,
    
    'welcome_message': """
مرحباً بك في منصة شهد السنيورة! 🎮

نحن متخصصون في بيع الألعاب الرقمية بأرخص الأسعار في مصر.

🎯 خدماتنا:
• حسابات Primary و Secondary و Full
• جميع المنصات (PS4, PS5, Xbox, PC)
• ضمان 6 أشهر
• تسليم خلال 15 ساعة
• دعم فني مجاني

📱 للطلب: {whatsapp_number}
🌐 الموقع: {site_url}
    """
}

# إعدادات اللغة
LANGUAGE_SETTINGS = {
    'default_language': 'ar',
    'supported_languages': ['ar', 'en'],
    'rtl_languages': ['ar']
}

# إعدادات التوقيت
TIMEZONE = 'Africa/Cairo'
DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# إعدادات الأداء
PERFORMANCE_SETTINGS = {
    'cache_timeout': 300,  # ثانية
    'page_size': 20,  # عدد العناصر في الصفحة
    'max_requests_per_minute': 60
}

# إعدادات السيو
SEO_SETTINGS = {
    'site_title': 'منصة شهد السنيورة - أرخص أسعار الألعاب الرقمية في مصر',
    'meta_description': 'احصل على FC 25 وجميع الألعاب الرقمية بأرخص الأسعار مع ضمان 6 أشهر وتسليم خلال 15 ساعة',
    'keywords': 'fc 25, ألعاب رقمية, بلايستيشن, xbox, pc, حسابات أساسية, egypt gaming'
}

# دالة للحصول على إعدادات البيئة
def get_env_setting(key, default=None):
    """الحصول على إعدادات البيئة مع قيمة افتراضية"""
    return os.environ.get(key, default)

# دالة للتحقق من صحة الإعدادات
def validate_settings():
    """التحقق من صحة الإعدادات الأساسية"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        errors.append("TELEGRAM_BOT_TOKEN غير محدد")
    
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == 'YOUR_CHAT_ID_HERE':
        errors.append("TELEGRAM_CHAT_ID غير محدد")
    
    if not WHATSAPP_NUMBER:
        errors.append("WHATSAPP_NUMBER غير محدد")
    
    return errors

# دالة للحصول على معلومات النظام
def get_system_info():
    """الحصول على معلومات النظام"""
    return {
        'site_name': SITE_NAME,
        'site_url': SITE_URL,
        'version': '2.0',
        'last_updated': datetime.now().strftime(DATETIME_FORMAT),
        'debug_mode': DEBUG_MODE,
        'maintenance_mode': MAINTENANCE_MODE
    }

# طباعة معلومات الإعدادات عند التشغيل
if __name__ == "__main__":
    print("🔧 فحص إعدادات النظام...")
    
    # التحقق من صحة الإعدادات
    validation_errors = validate_settings()
    if validation_errors:
        print("❌ أخطاء في الإعدادات:")
        for error in validation_errors:
            print(f"  - {error}")
    else:
        print("✅ جميع الإعدادات صحيحة")
    
    # عرض معلومات النظام
    system_info = get_system_info()
    print("\n📊 معلومات النظام:")
    for key, value in system_info.items():
        print(f"  {key}: {value}")
    
    print(f"\n🎮 الألعاب المدعومة: {len(SUPPORTED_GAMES)}")
    print(f"📱 المنصات المدعومة: {len(SUPPORTED_PLATFORMS)}")
    print(f"💳 طرق الدفع المدعومة: {len(PAYMENT_METHODS)}")
    print(f"🌍 المناطق المدعومة: {len(SUPPORTED_REGIONS)}")
