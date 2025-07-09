# telegram_bot.py
import os
import requests
import json
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramBot:
    def __init__(self):
        # محاولة الحصول على التوكن من متغيرات البيئة أولاً، ثم من config
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN') or TELEGRAM_BOT_TOKEN
        self.chat_id = os.getenv('CHAT_ID') or TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message, parse_mode="HTML"):
        """إرسال رسالة للتليجرام"""
        if not self.bot_token or not self.chat_id:
            return {"status": "error", "message": "لم يتم تكوين التوكن أو Chat ID"}
            
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                return {"status": "success", "message": "تم إرسال الرسالة بنجاح"}
            else:
                return {"status": "error", "message": f"خطأ في الإرسال: {response.text}"}
                
        except Exception as e:
            return {"status": "error", "message": f"خطأ في الاتصال: {str(e)}"}
    
    def send_order_notification(self, order_data):
        """إرسال إشعار طلب جديد"""
        try:
            message = f"""
🚨 <b>طلب جديد!</b>

🎮 <b>اللعبة:</b> {order_data.get('game', 'FC 25')}
📱 <b>المنصة:</b> {order_data.get('platform', 'غير محدد')}
💎 <b>نوع الحساب:</b> {order_data.get('account_type', 'غير محدد')}
💰 <b>السعر:</b> {order_data.get('price', 0)} جنيه
💳 <b>طريقة الدفع:</b> {order_data.get('payment_method', 'غير محدد')}
📞 <b>رقم العميل:</b> {order_data.get('customer_phone', order_data.get('phone', 'غير محدد'))}
🎯 <b>رقم الدفع:</b> {order_data.get('payment_number', 'غير محدد')}
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 <b>رقم الطلب:</b> #{order_data.get('order_id', 'غير محدد')}

#طلب_جديد #FC25
            """
            
            return self.send_message(message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في تجهيز الرسالة: {str(e)}"}
    
    def send_new_order_notification(self, order_data):
        """إرسال إشعار طلب جديد - متوافق مع النظام القديم"""
        return self.send_order_notification(order_data)
    
    def send_test_message(self, custom_message):
        """إرسال رسالة تجريبية"""
        try:
            test_message = f"""
🧪 <b>رسالة تجريبية</b>

📝 <b>المحتوى:</b> {custom_message}
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 <b>الحالة:</b> اختبار نظام الإشعارات
            """
            
            return self.send_message(test_message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في الرسالة التجريبية: {str(e)}"}
    
    def send_price_update_notification(self, game=None, platform=None, account_type=None, old_price=None, new_price=None, admin_name=None):
        """إرسال إشعار تحديث السعر"""
        try:
            if admin_name and not game:
                # النمط المبسط
                message = f"""
💰 <b>تم تحديث الأسعار</b>

👤 <b>بواسطة:</b> {admin_name}
⏰ <b>وقت التحديث:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

تم تحديث أسعار FC 25 لجميع المنصات.

#تحديث_الاسعار #ادارة
                """
            else:
                # النمط المفصل
                message = f"""
💰 <b>تحديث سعر</b>

🎮 <b>اللعبة:</b> {game or 'FC 25'}
📱 <b>المنصة:</b> {platform or 'غير محدد'}
💎 <b>نوع الحساب:</b> {account_type or 'غير محدد'}
💸 <b>السعر السابق:</b> {old_price or 0} جنيه
💵 <b>السعر الجديد:</b> {new_price or 0} جنيه
📊 <b>الفرق:</b> {(new_price or 0) - (old_price or 0)} جنيه
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#تحديث_الاسعار #ادارة
                """
            
            return self.send_message(message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في إشعار تحديث السعر: {str(e)}"}
    
    def send_daily_report(self, stats):
        """إرسال تقرير يومي"""
        try:
            message = f"""
📊 <b>التقرير اليومي</b>

📈 <b>الطلبات اليوم:</b> {stats.get('orders_today', 0)}
💰 <b>الإيرادات اليوم:</b> {stats.get('revenue_today', 0)} جنيه
🎮 <b>أشهر منصة:</b> {stats.get('popular_platform', 'غير محدد')}
💎 <b>أشهر نوع حساب:</b> {stats.get('popular_account_type', 'غير محدد')}
⏰ <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d')}

📋 <b>تفاصيل إضافية:</b>
- PS4: {stats.get('ps4_orders', 0)} طلبات
- PS5: {stats.get('ps5_orders', 0)} طلبات
- Xbox: {stats.get('xbox_orders', 0)} طلبات
- PC: {stats.get('pc_orders', 0)} طلبات

#تقرير_يومي #احصائيات
            """
            
            return self.send_message(message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في التقرير اليومي: {str(e)}"}
    
    def send_error_notification(self, error_message, context=""):
        """إرسال إشعار خطأ"""
        try:
            message = f"""
⚠️ <b>تحذير نظام</b>

🔴 <b>الخطأ:</b> {error_message}
📍 <b>السياق:</b> {context}
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔧 <b>الحالة:</b> يتطلب مراجعة

#خطأ_نظام #تحذير
            """
            
            return self.send_message(message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في إشعار الخطأ: {str(e)}"}
    
    def send_customer_message(self, customer_name, customer_phone, subject, message):
        """إرسال رسالة عميل"""
        try:
            telegram_message = f"""
📧 <b>رسالة من عميل</b>

👤 <b>الاسم:</b> {customer_name}
📱 <b>الهاتف:</b> {customer_phone}
📋 <b>الموضوع:</b> {subject}
💬 <b>الرسالة:</b> {message}
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔗 <b>رد سريع:</b> https://wa.me/{customer_phone.replace('+', '').replace(' ', '')}

#رسالة_عميل #دعم_فني
            """
            
            return self.send_message(telegram_message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في رسالة العميل: {str(e)}"}
    
    def send_admin_login_notification(self, admin_name, ip_address="غير محدد"):
        """إرسال إشعار تسجيل دخول المدير"""
        try:
            message = f"""
🔐 <b>تسجيل دخول مدير</b>

👤 <b>المدير:</b> {admin_name}
🌐 <b>عنوان IP:</b> {ip_address}
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#تسجيل_دخول #امان
            """
            
            return self.send_message(message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في إشعار تسجيل الدخول: {str(e)}"}
    
    def send_backup_notification(self, backup_status, backup_size="غير محدد"):
        """إرسال إشعار النسخ الاحتياطي"""
        try:
            status_emoji = "✅" if backup_status == "success" else "❌"
            status_text = "نجح" if backup_status == "success" else "فشل"
            
            message = f"""
💾 <b>النسخ الاحتياطي</b>

{status_emoji} <b>الحالة:</b> {status_text}
📦 <b>حجم النسخة:</b> {backup_size}
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#نسخ_احتياطي #صيانة
            """
            
            return self.send_message(message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في إشعار النسخ الاحتياطي: {str(e)}"}
    
    def check_bot_status(self):
        """فحص حالة البوت"""
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url)
            
            if response.status_code == 200:
                bot_info = response.json()
                return {
                    "status": "success",
                    "bot_info": bot_info.get('result', {}),
                    "message": "البوت يعمل بشكل طبيعي"
                }
            else:
                return {
                    "status": "error",
                    "message": f"خطأ في الاتصال بالبوت: {response.text}"
                }
                
        except Exception as e:
            return {"status": "error", "message": f"خطأ في فحص البوت: {str(e)}"}
    
    def get_chat_info(self):
        """الحصول على معلومات المحادثة"""
        try:
            url = f"{self.api_url}/getChat"
            data = {"chat_id": self.chat_id}
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                chat_info = response.json()
                return {
                    "status": "success",
                    "chat_info": chat_info.get('result', {}),
                    "message": "تم الحصول على معلومات المحادثة"
                }
            else:
                return {
                    "status": "error",
                    "message": f"خطأ في الحصول على معلومات المحادثة: {response.text}"
                }
                
        except Exception as e:
            return {"status": "error", "message": f"خطأ في معلومات المحادثة: {str(e)}"}
    
    def init_app(self, app):
        """تهيئة النظام مع Flask app"""
        app.telegram_bot = self
        app.telegram_system = self  # للتوافق مع النظام القديم
        return self

# إنشاء كلاس مرادف للتوافق مع النظام القديم
class TelegramSystem(TelegramBot):
    pass

# إنشاء instances
telegram_bot = TelegramBot()
telegram_system = TelegramBot()  # للتوافق مع النظام القديم

# وظائف مساعدة للاستخدام السريع
def send_order_notification(order_data):
    """وظيفة سريعة لإرسال إشعار طلب"""
    return telegram_bot.send_order_notification(order_data)

def send_new_order_notification(order_data):
    """وظيفة سريعة لإرسال إشعار طلب جديد - متوافق مع النظام القديم"""
    return telegram_bot.send_new_order_notification(order_data)

def send_test_message(message):
    """وظيفة سريعة لإرسال رسالة تجريبية"""
    return telegram_bot.send_test_message(message)

def send_price_update(game=None, platform=None, account_type=None, old_price=None, new_price=None, admin_name=None):
    """وظيفة سريعة لإرسال إشعار تحديث السعر"""
    return telegram_bot.send_price_update_notification(game, platform, account_type, old_price, new_price, admin_name)

def send_price_update_notification(admin_name):
    """وظيفة سريعة لإرسال إشعار تحديث السعر - متوافق مع النظام القديم"""
    return telegram_bot.send_price_update_notification(admin_name=admin_name)

def send_customer_message(name, phone, subject, message):
    """وظيفة سريعة لإرسال رسالة عميل"""
    return telegram_bot.send_customer_message(name, phone, subject, message)

def send_daily_report(stats):
    """وظيفة سريعة لإرسال تقرير يومي"""
    return telegram_bot.send_daily_report(stats)

def send_error_notification(error_message, context=""):
    """وظيفة سريعة لإرسال إشعار خطأ"""
    return telegram_bot.send_error_notification(error_message, context)

def send_admin_login_notification(admin_name, ip_address="غير محدد"):
    """وظيفة سريعة لإرسال إشعار تسجيل دخول المدير"""
    return telegram_bot.send_admin_login_notification(admin_name, ip_address)

def send_backup_notification(backup_status, backup_size="غير محدد"):
    """وظيفة سريعة لإرسال إشعار النسخ الاحتياطي"""
    return telegram_bot.send_backup_notification(backup_status, backup_size)

def check_bot_status():
    """وظيفة سريعة لفحص حالة البوت"""
    return telegram_bot.check_bot_status()

def get_chat_info():
    """وظيفة سريعة للحصول على معلومات المحادثة"""
    return telegram_bot.get_chat_info()

# مثال على الاستخدام
if __name__ == "__main__":
    # اختبار البوت
    print("🧪 اختبار بوت التليجرام...")
    
    # فحص حالة البوت
    status = check_bot_status()
    print(f"حالة البوت: {status}")
    
    # إرسال رسالة تجريبية
    test_result = send_test_message("مرحباً! هذه رسالة تجريبية من منصة شهد السنيورة 🎮")
    print(f"نتيجة الرسالة التجريبية: {test_result}")
    
    # مثال على طلب وهمي
    sample_order = {
        "game": "FC 25",
        "platform": "PS5",
        "account_type": "Primary",
        "price": 60,
        "payment_method": "فودافون كاش",
        "customer_phone": "01234567890",
        "phone": "01234567890",  # للتوافق مع النظام القديم
        "payment_number": "01234567890",
        "order_id": "ORD001"
    }
    
    order_result = send_order_notification(sample_order)
    print(f"نتيجة إشعار الطلب: {order_result}")
    
    # مثال على تحديث السعر
    price_update_result = send_price_update("FC 25", "PS5", "Primary", 50, 60)
    print(f"نتيجة إشعار تحديث السعر: {price_update_result}")
    
    # مثال على تحديث السعر - النمط المبسط
    simple_price_update = send_price_update_notification("Admin")
    print(f"نتيجة إشعار تحديث السعر المبسط: {simple_price_update}")
    
    # مثال على رسالة عميل
    customer_msg_result = send_customer_message(
        "أحمد محمد", 
        "01234567890", 
        "استفسار عن FC 25", 
        "مرحباً، أريد معرفة أسعار FC 25 لجميع المنصات"
    )
    print(f"نتيجة رسالة العميل: {customer_msg_result}")
    
    # مثال على إحصائيات يومية
    daily_stats = {
        "orders_today": 15,
        "revenue_today": 900,
        "popular_platform": "PS5",
        "popular_account_type": "Primary",
        "ps4_orders": 3,
        "ps5_orders": 8,
        "xbox_orders": 2,
        "pc_orders": 2
    }
    
    report_result = send_daily_report(daily_stats)
    print(f"نتيجة التقرير اليومي: {report_result}")
    
    # مثال على إشعار خطأ
    error_result = send_error_notification("خطأ في الاتصال بقاعدة البيانات", "دالة معالجة الطلبات")
    print(f"نتيجة إشعار الخطأ: {error_result}")
    
    # مثال على إشعار تسجيل دخول المدير
    login_result = send_admin_login_notification("شهد السنيورة", "192.168.1.100")
    print(f"نتيجة إشعار تسجيل الدخول: {login_result}")
    
    # مثال على إشعار النسخ الاحتياطي
    backup_result = send_backup_notification("success", "2.5 MB")
    print(f"نتيجة إشعار النسخ الاحتياطي: {backup_result}")
