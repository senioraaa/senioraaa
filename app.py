from flask import Flask, render_template, request, jsonify, abort
import json, os, secrets, time, re, hashlib
from datetime import datetime, timedelta
import logging
from functools import wraps
from collections import defaultdict
import urllib.parse

# إعداد التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# إعداد الـ Logging للأمان
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# متغيرات الحماية العامة
blocked_ips = {}
request_counts = defaultdict(list)
failed_attempts = {}
prices_cache = {}
last_prices_update = 0

# إعدادات الواتساب
WHATSAPP_NUMBER = "+201094591331"  # غير الرقم هنا
BUSINESS_NAME = "Senior Gaming Store"

# Rate Limiting محسن بدون CSRF
def rate_limit(max_requests=10, window=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            current_time = time.time()
            
            # فحص IP محظور
            if client_ip in blocked_ips:
                block_time, duration = blocked_ips[client_ip]
                if current_time - block_time < duration:
                    logger.warning(f"🚨 IP محظور: {client_ip}")
                    abort(429)
                else:
                    del blocked_ips[client_ip]
            
            # تنظيف الطلبات القديمة
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip]
                if current_time - req_time < window
            ]
            
            # فحص عدد الطلبات
            if len(request_counts[client_ip]) >= max_requests:
                # حظر مؤقت
                blocked_ips[client_ip] = (current_time, 300)  # 5 دقائق
                logger.warning(f"🚨 Rate limit exceeded - IP blocked: {client_ip}")
                abort(429)
            
            # إضافة الطلب الحالي
            request_counts[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# حماية إضافية من Spam
def anti_spam_check(ip_address, user_agent):
    """فحص إضافي ضد الـ spam والـ bots"""
    current_time = time.time()
    
    # فحص User Agent
    suspicious_agents = ['bot', 'crawler', 'spider', 'scraper']
    if any(agent in user_agent.lower() for agent in suspicious_agents):
        logger.warning(f"🚨 Suspicious user agent from IP: {ip_address}")
        return False
    
    # فحص التكرار السريع
    key = f"{ip_address}_{user_agent}"
    if key not in failed_attempts:
        failed_attempts[key] = []
    
    # تنظيف المحاولات القديمة
    failed_attempts[key] = [
        t for t in failed_attempts[key] 
        if current_time - t < 60  # آخر دقيقة
    ]
    
    # إذا أكتر من 3 محاولات في دقيقة واحدة
    if len(failed_attempts[key]) >= 3:
        blocked_ips[ip_address] = (current_time, 900)  # حظر 15 دقيقة
        logger.warning(f"🚨 Anti-spam triggered - IP blocked: {ip_address}")
        return False
    
    failed_attempts[key].append(current_time)
    return True

# تحميل الأسعار من JSON مع Cache
def load_prices():
    global prices_cache, last_prices_update
    
    try:
        if os.path.exists('prices.json'):
            file_time = os.path.getmtime('prices.json')
            if file_time > last_prices_update:
                with open('prices.json', 'r', encoding='utf-8') as f:
                    prices_cache = json.load(f)
                last_prices_update = file_time
                logger.info("🔄 تم تحديث الأسعار من ملف JSON")
        
        if not prices_cache:
            create_default_prices()
            
        return prices_cache
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الأسعار: {e}")
        return get_default_prices()

# إنشاء ملف أسعار افتراضي
def create_default_prices():
    global prices_cache
    default_prices = get_default_prices()
    
    try:
        with open('prices.json', 'w', encoding='utf-8') as f:
            json.dump(default_prices, f, ensure_ascii=False, indent=2)
        logger.info("✅ تم إنشاء ملف الأسعار الافتراضي")
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء ملف الأسعار: {e}")
    
    prices_cache = default_prices
    return default_prices

# الأسعار الافتراضية - مع لوجوهات احترافية
def get_default_prices():
    return {
        "games": {
            "FC25_EN_Standard": {
                "name": "FC 25 - Standard Edition (English) 🇺🇸",
                "platforms": {
                    "PS5": {
                        "name": "PlayStation 5",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 3300},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 1600},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1100}
                        }
                    },
                    "PS4": {
                        "name": "PlayStation 4",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 3300},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 1150},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1100}
                        }
                    }
                }
            },
            "FC25_EN_Ultimate": {
                "name": "FC 25 - Ultimate Edition (English) 🇺🇸",
                "platforms": {
                    "PS5": {
                        "name": "PlayStation 5",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 4500},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 1000},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1060}
                        }
                    },
                    "PS4": {
                        "name": "PlayStation 4",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 4500},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 1000},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1050}
                        }
                    }
                }
            },
            "FC25_AR_Standard": {
                "name": "FC 25 - Standard Edition (Arabic) 🇸🇦",
                "platforms": {
                    "PS5": {
                        "name": "PlayStation 5",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 3500},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 1090},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1200}
                        }
                    },
                    "PS4": {
                        "name": "PlayStation 4",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 3500},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 1250},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1200}
                        }
                    }
                }
            },
            "FC25_AR_Ultimate": {
                "name": "FC 25 - Ultimate Edition (Arabic) 🇸🇦",
                "platforms": {
                    "PS5": {
                        "name": "PlayStation 5",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 5000},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 300},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 500}
                        }
                    },
                    "PS4": {
                        "name": "PlayStation 4",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8.985 2.596v17.548l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v10.735l3.794-1.139V4.688c0-.69.318-1.151.818-.991.636.181.818.991.818.991v8.596l3.794-.567V8.688c0-.69.304-1.151.794-.991.636.181.794.991.794.991v7.735L24 17.135V1.135L8.985 2.596z" fill="#003087"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 5000},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 600},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1470}
                        }
                    }
                }
            },
            "FC25_XBOX_Standard": {
                "name": "FC 25 - Xbox Standard Edition 🎮",
                "platforms": {
                    "Xbox": {
                        "name": "Xbox Series X/S & Xbox One",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M4.102 21.033C6.211 22.881 8.977 24 12 24c3.026 0 5.789-1.119 7.902-2.967.409-.359.358-.763-.127-.763-.127 0-.254.033-.381.084C17.635 21.12 14.975 21.6 12 21.6c-2.975 0-5.635-.48-7.394-1.246-.127-.051-.254-.084-.381-.084-.484 0-.535.404-.127.763zM12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.568 8.16c-.604-.825-.377-1.899.168-2.49.545-.591 1.44-.612 2.007-.047.567.565.544 1.462-.047 2.007-.591.545-1.665.772-2.49.168-.412-.302-.638-.638-.638-.638zm-11.136 0s-.226.336-.638.638c-.825.604-1.899.377-2.49-.168-.591-.545-.612-1.44-.047-2.007.565-.567 1.462-.544 2.007.047.545.591.772 1.665.168 2.49zM12 3.6c2.355 0 4.515.958 6.061 2.504C16.65 7.35 15.075 8.4 12 8.4S7.35 7.35 5.939 6.104C7.485 4.558 9.645 3.6 12 3.6z" fill="#107C10"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 3500},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 2850},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 2300}
                        }
                    }
                }
            },
            "FC25_XBOX_Ultimate": {
                "name": "FC 25 - Xbox Ultimate Edition 🎮",
                "platforms": {
                    "Xbox": {
                        "name": "Xbox Series X/S & Xbox One",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M4.102 21.033C6.211 22.881 8.977 24 12 24c3.026 0 5.789-1.119 7.902-2.967.409-.359.358-.763-.127-.763-.127 0-.254.033-.381.084C17.635 21.12 14.975 21.6 12 21.6c-2.975 0-5.635-.48-7.394-1.246-.127-.051-.254-.084-.381-.084-.484 0-.535.404-.127.763zM12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.568 8.16c-.604-.825-.377-1.899.168-2.49.545-.591 1.44-.612 2.007-.047.567.565.544 1.462-.047 2.007-.591.545-1.665.772-2.49.168-.412-.302-.638-.638-.638-.638zm-11.136 0s-.226.336-.638.638c-.825.604-1.899.377-2.49-.168-.591-.545-.612-1.44-.047-2.007.565-.567 1.462-.544 2.007.047.545.591.772 1.665.168 2.49zM12 3.6c2.355 0 4.515.958 6.061 2.504C16.65 7.35 15.075 8.4 12 8.4S7.35 7.35 5.939 6.104C7.485 4.558 9.645 3.6 12 3.6z" fill="#107C10"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 4500},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 3800},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 3200}
                        }
                    }
                }
            },
            "FC25_PC_Standard": {
                "name": "FC 25 - PC Standard Edition 🖥️",
                "platforms": {
                    "PC": {
                        "name": "PC (EA Desktop)",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M20 3H4c-1.103 0-2 .897-2 2v10c0 1.103.897 2 2 2h7v2H8v2h8v-2h-3v-2h7c1.103 0 2-.897 2-2V5c0-1.103-.897-2-2-2zM4 5h16l.002 10H4V5z" fill="#0078D4"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 2700},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 2200},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 1800}
                        }
                    }
                }
            },
            "FC25_PC_Ultimate": {
                "name": "FC 25 - PC Ultimate Edition 🖥️",
                "platforms": {
                    "PC": {
                        "name": "PC (EA Desktop)",
                        "icon": '''<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M20 3H4c-1.103 0-2 .897-2 2v10c0 1.103.897 2 2 2h7v2H8v2h8v-2h-3v-2h7c1.103 0 2-.897 2-2V5c0-1.103-.897-2-2-2zM4 5h16l.002 10H4V5z" fill="#0078D4"/>
                        </svg>''',
                        "accounts": {
                            "Full": {"name": "Full - حساب كامل", "price": 3600},
                            "Primary": {"name": "Primary - تفعيل أساسي", "price": 3000},
                            "Secondary": {"name": "Secondary - تسجيل دخول مؤقت", "price": 2500}
                        }
                    }
                }
            }
        },
        "settings": {
            "currency": "جنيه مصري",
            "warranty": "1 سنة",
            "delivery_time": "15 ساعة كحد أقصى",
            "whatsapp_number": "+201094591331"
        }
    }



# Headers أمنية قوية
@app.after_request
def security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://wa.me"
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

# تنظيف المدخلات
def sanitize_input(text, max_length=100):
    if not text:
        return None
    
    text = str(text).strip()
    
    if len(text) > max_length:
        return None
    
    text = re.sub(r'[<>"\';\\&]', '', text)
    text = re.sub(r'(script|javascript|vbscript|onload|onerror)', '', text, flags=re.IGNORECASE)
    
    return text

# الصفحة الرئيسية
@app.route('/')
@rate_limit(max_requests=25, window=60)
def index():
    try:
        prices = load_prices()
        
        logger.info("✅ تم تحميل الصفحة الرئيسية بنجاح")
        
        return render_template('index.html', prices=prices)
    except Exception as e:
        logger.error(f"❌ خطأ في الصفحة الرئيسية: {e}")
        abort(500)

# إنشاء رابط واتساب مباشر - بدون CSRF
@app.route('/whatsapp', methods=['POST'])
@rate_limit(max_requests=8, window=60)
def create_whatsapp_link():
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    try:
        # فحص Anti-spam
        if not anti_spam_check(client_ip, user_agent):
            return jsonify({'error': 'تم تجاوز الحد المسموح - يرجى المحاولة لاحقاً'}), 429
        
        # فحص الـ Referer للتأكد من المصدر
        referer = request.headers.get('Referer', '')
        if not referer or 'senioraa.onrender.com' not in referer:
            logger.warning(f"🚨 محاولة وصول مباشر من IP: {client_ip}")
            return jsonify({'error': 'طلب غير صالح'}), 400
        
        # تنظيف البيانات
        game_type = sanitize_input(request.form.get('game_type'))
        platform = sanitize_input(request.form.get('platform'))
        account_type = sanitize_input(request.form.get('account_type'))
        
        if not all([game_type, platform, account_type]):
            return jsonify({'error': 'يرجى اختيار جميع الخيارات أولاً'}), 400
        
        # تحميل الأسعار والتحقق
        prices = load_prices()
        
        if (game_type not in prices.get('games', {}) or
            platform not in prices['games'][game_type].get('platforms', {}) or
            account_type not in prices['games'][game_type]['platforms'][platform].get('accounts', {})):
            logger.warning(f"🚨 اختيار منتج غير صحيح من IP: {client_ip}")
            return jsonify({'error': 'اختيار المنتج غير صحيح'}), 400
        
        # بيانات المنتج
        game_name = prices['games'][game_type]['name']
        platform_name = prices['games'][game_type]['platforms'][platform]['name']
        account_name = prices['games'][game_type]['platforms'][platform]['accounts'][account_type]['name']
        price = prices['games'][game_type]['platforms'][platform]['accounts'][account_type]['price']
        currency = prices.get('settings', {}).get('currency', 'جنيه')
        
        # إنشاء ID مرجعي (للتتبع فقط - لا يُحفظ)
        timestamp = str(int(time.time()))
        reference_id = hashlib.md5(f"{timestamp}{client_ip}{game_type}{platform}".encode()).hexdigest()[:8].upper()
        
        # إنشاء رسالة الواتساب
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        message = f"""🎮 *استفسار من {BUSINESS_NAME}*

🆔 *المرجع:* {reference_id}

🎯 *المطلوب:*
• اللعبة: {game_name}
• المنصة: {platform_name}
• نوع الحساب: {account_name}
• السعر: {price} {currency}

⏰ *وقت الاستفسار:* {current_time}

👋 *السلام عليكم، أريد الاستفسار عن هذا المنتج*

شكراً 🌟"""
        
        # ترميز الرسالة للـ URL
        encoded_message = urllib.parse.quote(message)
        
        # رقم الواتساب من الإعدادات
        whatsapp_number = prices.get('settings', {}).get('whatsapp_number', WHATSAPP_NUMBER)
        clean_number = whatsapp_number.replace('+', '').replace('-', '').replace(' ', '')
        
        # إنشاء رابط الواتساب
        whatsapp_url = f"https://wa.me/{clean_number}?text={encoded_message}"
        
        logger.info(f"✅ فتح واتساب: {reference_id} - {platform} {account_type} - {price} {currency} - IP: {client_ip}")
        
        return jsonify({
            'success': True,
            'reference_id': reference_id,
            'whatsapp_url': whatsapp_url,
            'price': price,
            'currency': currency,
            'message': 'سيتم فتح الواتساب الآن...'
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء رابط الواتساب: {e}")
        return jsonify({'error': 'حدث خطأ في النظام - يرجى المحاولة مرة أخرى'}), 500

# API للحصول على الأسعار
@app.route('/api/prices')
@rate_limit(max_requests=15, window=60)
def get_prices():
    try:
        prices = load_prices()
        return jsonify(prices)
    except Exception as e:
        logger.error(f"❌ خطأ في API الأسعار: {e}")
        return jsonify({'error': 'خطأ في النظام'}), 500

# Health check
@app.route('/health')
@app.route('/ping')
def health_check():
    try:
        # فحص الأسعار فقط
        prices = load_prices()
        
        return {
            'status': 'healthy',
            'prices': 'ok' if prices else 'error',
            'timestamp': datetime.now().isoformat()
        }, 200
    except Exception as e:
        logger.error(f"❌ خطأ في Health Check: {e}")
        return {'status': 'error', 'message': str(e)}, 500

# Robots.txt
@app.route('/robots.txt')
def robots():
    return '''User-agent: *
Disallow: /admin/
Disallow: /api/
Crawl-delay: 10''', 200, {'Content-Type': 'text/plain'}

# معالجات الأخطاء
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'طلب غير صحيح'}), 400

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(429)
def too_many_requests(error):
    return render_template('429.html'), 429

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ خطأ داخلي: {error}")
    return render_template('500.html'), 500

# تشغيل التطبيق
if __name__ == '__main__':
    load_prices()
    logger.info("🚀 تم تشغيل التطبيق بنجاح - واتساب مباشر (بدون CSRF)")
    
    app.run(
        debug=False, 
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 5000))
    )
else:
    # تشغيل تلقائي عند استخدام gunicorn
    load_prices()
    logger.info("🚀 تم تشغيل التطبيق عبر gunicorn - واتساب مباشر (بدون CSRF)")
