import os
import logging
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix

# إعداد اللوجر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'senior_aaa_secret_key_2024'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# المتغيرات البيئية (نحتفظ بها للمتغيرات الأخرى فقط)
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://senioraaa.onrender.com')

# ملف حفظ الأسعار
PRICES_FILE = 'prices_data.json'

# بيانات الأسعار المؤقتة
DEFAULT_PRICES = {
    "fc25": {
        "ps4": {
            "Primary": 85,
            "Secondary": 70,
            "Full": 120
        },
        "ps5": {
            "Primary": 90,
            "Secondary": 75,
            "Full": 125
        },
        "xbox": {
            "Primary": 85,
            "Secondary": 70,
            "Full": 120
        },
        "pc": {
            "Primary": 80,
            "Secondary": 65,
            "Full": 115
        }
    }
}

def load_prices():
    """تحميل الأسعار من الملف"""
    try:
        if os.path.exists(PRICES_FILE):
            with open(PRICES_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info("✅ تم تحميل الأسعار من الملف")
                return data
        else:
            logger.info("📝 إنشاء ملف أسعار جديد")
            save_prices(DEFAULT_PRICES)
            return DEFAULT_PRICES.copy()
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الأسعار: {e}")
        return DEFAULT_PRICES.copy()

def save_prices(prices_data):
    """حفظ الأسعار في الملف"""
    try:
        with open(PRICES_FILE, 'w', encoding='utf-8') as file:
            json.dump(prices_data, file, ensure_ascii=False, indent=4)
        logger.info("✅ تم حفظ الأسعار في الملف")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الأسعار: {e}")
        return False

# تحميل الأسعار عند بدء التشغيل
PRICES_DATA = load_prices()

def update_price(platform, account_type, new_price):
    """تحديث السعر في JSON فقط - بدون تليجرام"""
    global PRICES_DATA
    try:
        if platform.lower() in PRICES_DATA['fc25'] and account_type in PRICES_DATA['fc25'][platform.lower()]:
            old_price = PRICES_DATA['fc25'][platform.lower()][account_type]
            PRICES_DATA['fc25'][platform.lower()][account_type] = int(new_price)
            
            # حفظ التحديث في الملف فقط
            if save_prices(PRICES_DATA):
                logger.info(f"✅ تم تحديث السعر: {platform} {account_type} من {old_price} إلى {new_price}")
                return True
        return False
    except Exception as e:
        logger.error(f"خطأ في تحديث السعر: {e}")
        return False

# Routes المنصة الرئيسية
@app.route('/')
def home():
    """الصفحة الرئيسية للمنصة"""
    try:
        # إعادة تحميل الأسعار لضمان التحديث
        global PRICES_DATA
        PRICES_DATA = load_prices()
        return render_template('index.html', prices=PRICES_DATA)
    except Exception as e:
        logger.error(f"خطأ في تحميل الصفحة الرئيسية: {e}")
        return jsonify({
            'status': 'active',
            'message': 'منصة شهد السنيورة - أرخص أسعار FC 25 في مصر! ✅'
        })

@app.route('/api/prices')
def api_prices():
    """API للأسعار - يعيد الأسعار المحدثة"""
    global PRICES_DATA
    PRICES_DATA = load_prices()  # تأكد من أحدث الأسعار
    return jsonify(PRICES_DATA)

@app.route('/api/update_price', methods=['POST'])
def api_update_price():
    """API لتحديث الأسعار من JSON فقط"""
    try:
        data = request.get_json()
        platform = data.get('platform', '').lower()
        account_type = data.get('account_type', '')
        new_price = int(data.get('price', 0))
        
        if update_price(platform, account_type, new_price):
            return jsonify({
                'success': True,
                'message': 'تم تحديث السعر بنجاح في JSON',
                'updated_price': {
                    'platform': platform,
                    'account_type': account_type,
                    'price': new_price
                },
                'all_prices': PRICES_DATA
            })
        else:
            return jsonify({
                'success': False,
                'message': 'فشل في تحديث السعر'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ: {str(e)}'
        }), 500

@app.route('/admin')
def admin():
    """لوحة الإدارة الجديدة - JSON فقط"""
    # إعادة تحميل الأسعار للتأكد من أحدث البيانات
    global PRICES_DATA
    PRICES_DATA = load_prices()
    
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة إدارة الأسعار - JSON فقط</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
                min-height: 100vh;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 3px solid #667eea;
            }}
            .header h1 {{
                color: #667eea;
                margin: 0;
                font-size: 2.2rem;
            }}
            .platform-section {{
                background: linear-gradient(45deg, #28a745, #20a039);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .platform-section h3 {{
                margin: 0 0 15px 0;
                text-align: center;
                font-size: 1.4rem;
            }}
            .price-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 10px 0;
                padding: 10px;
                background: rgba(255,255,255,0.2);
                border-radius: 8px;
            }}
            .price-label {{
                font-weight: bold;
                font-size: 1.1rem;
            }}
            .price-input {{
                width: 100px;
                padding: 8px;
                border: none;
                border-radius: 5px;
                text-align: center;
                font-size: 1rem;
                font-weight: bold;
            }}
            .update-btn {{
                background: #007bff;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
            }}
            .update-btn:hover {{
                background: #0056b3;
                transform: translateY(-1px);
            }}
            .success-msg {{
                background: #d4edda;
                color: #155724;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                border: 1px solid #c3e6cb;
            }}
            .error-msg {{
                background: #f8d7da;
                color: #721c24;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                border: 1px solid #f5c6cb;
            }}
            .json-info {{
                background: #e7f3ff;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                text-align: center;
                border-left: 4px solid #007bff;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎮 لوحة إدارة الأسعار</h1>
                <p style="margin: 10px 0; color: #666;">نظام JSON مبسط - بدون تليجرام</p>
            </div>
            
            <div class="json-info">
                <h4 style="margin: 0; color: #007bff;">📁 حفظ مباشر في ملف JSON</h4>
                <p style="margin: 5px 0;">جميع التحديثات تحفظ مباشرة في <strong>prices_data.json</strong></p>
            </div>
            
            <div id="message-area"></div>
            
            <div class="platform-section">
                <h3>🎮 PlayStation 4</h3>
                <div class="price-row">
                    <span class="price-label">Primary:</span>
                    <input type="number" class="price-input" id="ps4_Primary" value="{PRICES_DATA['fc25']['ps4']['Primary']}">
                    <button class="update-btn" onclick="updatePrice('ps4', 'Primary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Secondary:</span>
                    <input type="number" class="price-input" id="ps4_Secondary" value="{PRICES_DATA['fc25']['ps4']['Secondary']}">
                    <button class="update-btn" onclick="updatePrice('ps4', 'Secondary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Full:</span>
                    <input type="number" class="price-input" id="ps4_Full" value="{PRICES_DATA['fc25']['ps4']['Full']}">
                    <button class="update-btn" onclick="updatePrice('ps4', 'Full')">تحديث</button>
                </div>
            </div>
            
            <div class="platform-section">
                <h3>🎮 PlayStation 5</h3>
                <div class="price-row">
                    <span class="price-label">Primary:</span>
                    <input type="number" class="price-input" id="ps5_Primary" value="{PRICES_DATA['fc25']['ps5']['Primary']}">
                    <button class="update-btn" onclick="updatePrice('ps5', 'Primary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Secondary:</span>
                    <input type="number" class="price-input" id="ps5_Secondary" value="{PRICES_DATA['fc25']['ps5']['Secondary']}">
                    <button class="update-btn" onclick="updatePrice('ps5', 'Secondary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Full:</span>
                    <input type="number" class="price-input" id="ps5_Full" value="{PRICES_DATA['fc25']['ps5']['Full']}">
                    <button class="update-btn" onclick="updatePrice('ps5', 'Full')">تحديث</button>
                </div>
            </div>
            
            <div class="platform-section">
                <h3>🎮 Xbox Series</h3>
                <div class="price-row">
                    <span class="price-label">Primary:</span>
                    <input type="number" class="price-input" id="xbox_Primary" value="{PRICES_DATA['fc25']['xbox']['Primary']}">
                    <button class="update-btn" onclick="updatePrice('xbox', 'Primary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Secondary:</span>
                    <input type="number" class="price-input" id="xbox_Secondary" value="{PRICES_DATA['fc25']['xbox']['Secondary']}">
                    <button class="update-btn" onclick="updatePrice('xbox', 'Secondary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Full:</span>
                    <input type="number" class="price-input" id="xbox_Full" value="{PRICES_DATA['fc25']['xbox']['Full']}">
                    <button class="update-btn" onclick="updatePrice('xbox', 'Full')">تحديث</button>
                </div>
            </div>
            
            <div class="platform-section">
                <h3>💻 PC</h3>
                <div class="price-row">
                    <span class="price-label">Primary:</span>
                    <input type="number" class="price-input" id="pc_Primary" value="{PRICES_DATA['fc25']['pc']['Primary']}">
                    <button class="update-btn" onclick="updatePrice('pc', 'Primary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Secondary:</span>
                    <input type="number" class="price-input" id="pc_Secondary" value="{PRICES_DATA['fc25']['pc']['Secondary']}">
                    <button class="update-btn" onclick="updatePrice('pc', 'Secondary')">تحديث</button>
                </div>
                <div class="price-row">
                    <span class="price-label">Full:</span>
                    <input type="number" class="price-input" id="pc_Full" value="{PRICES_DATA['fc25']['pc']['Full']}">
                    <button class="update-btn" onclick="updatePrice('pc', 'Full')">تحديث</button>
                </div>
            </div>
        </div>
        
        <script>
            function updatePrice(platform, accountType) {{
                const inputId = platform + '_' + accountType;
                const newPrice = document.getElementById(inputId).value;
                const messageArea = document.getElementById('message-area');
                
                if (!newPrice || newPrice <= 0) {{
                    showMessage('يرجى إدخال سعر صحيح', 'error');
                    return;
                }}
                
                fetch('/api/update_price', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        platform: platform,
                        account_type: accountType,
                        price: parseInt(newPrice)
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        showMessage(`✅ تم تحديث ${{platform.toUpperCase()}} ${{accountType}} إلى ${{newPrice}} جنيه`, 'success');
                        // تحديث API prices
                        window.location.reload();
                    }} else {{
                        showMessage('❌ ' + data.message, 'error');
                    }}
                }})
                .catch(error => {{
                    showMessage('❌ خطأ في الاتصال: ' + error, 'error');
                }});
            }}
            
            function showMessage(message, type) {{
                const messageArea = document.getElementById('message-area');
                const className = type === 'success' ? 'success-msg' : 'error-msg';
                messageArea.innerHTML = `<div class="${{className}}">${{message}}</div>`;
                setTimeout(() => {{
                    messageArea.innerHTML = '';
                }}, 3000);
            }}
        </script>
    </body>
    </html>
    """
    return html

@app.route('/order')
def order_page():
    """صفحة الطلب"""
    return redirect("https://wa.me/201094591331?text=مرحباً، أريد طلب FC 25")

@app.route('/faq')
def faq_page():
    """صفحة الأسئلة الشائعة"""
    return jsonify({
        'faq': [
            {'q': 'ما هو الفرق بين Primary و Secondary؟', 'a': 'Primary يتم تفعيله كحساب أساسي، Secondary للتحميل فقط'},
            {'q': 'كم مدة الضمان؟', 'a': 'سنة كاملة مع عدم مخالفة الشروط'},
            {'q': 'متى يتم التسليم؟', 'a': 'خلال 15 ساعة كحد أقصى'},
            {'q': 'هل يمكن تغيير بيانات الحساب؟', 'a': 'ممنوع نهائياً تغيير أي بيانات'},
            {'q': 'كيف يتم تحديث الأسعار؟', 'a': 'يتم التحديث من لوحة الإدارة مع الحفظ المباشر في JSON'}
        ]
    })

@app.route('/status')  
def status_page():
    """صفحة حالة النظام"""
    return jsonify({
        'status': 'active',
        'system': 'JSON Price Management',
        'telegram': 'disabled',
        'prices_file': 'active',
        'website': WEBHOOK_URL,
        'message': 'نظام إدارة الأسعار نشط ✅'
    })

if __name__ == '__main__':
    logger.info("🚀 بدء تشغيل منصة شهد السنيورة مع نظام JSON")
    
    # إنشاء ملف الأسعار إذا لم يكن موجوداً
    if not os.path.exists(PRICES_FILE):
        save_prices(DEFAULT_PRICES)
        logger.info("📝 تم إنشاء ملف الأسعار الافتراضي")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
