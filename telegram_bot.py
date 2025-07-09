import requests
import json
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramBot:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message):
        """إرسال رسالة للتليجرام"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
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
📞 <b>رقم العميل:</b> {order_data.get('customer_phone', 'غير محدد')}
🎯 <b>رقم الدفع:</b> {order_data.get('payment_number', 'غير محدد')}
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 <b>رقم الطلب:</b> #{order_data.get('order_id', 'غير محدد')}
            """
            
            return self.send_message(message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في تجهيز الرسالة: {str(e)}"}
    
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
    
    def send_price_update_notification(self, game, platform, account_type, old_price, new_price):
        """إرسال إشعار تحديث السعر"""
        try:
            message = f"""
💰 <b>تحديث سعر</b>

🎮 <b>اللعبة:</b> {game}
📱 <b>المنصة:</b> {platform}
💎 <b>نوع الحساب:</b> {account_type}
💸 <b>السعر السابق:</b> {old_price} جنيه
💵 <b>السعر الجديد:</b> {new_price} جنيه
📊 <b>الفرق:</b> {new_price - old_price} جنيه
⏰ <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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
            """
            
            return self.send_message(telegram_message.strip())
            
        except Exception as e:
            return {"status": "error", "message": f"خطأ في رسالة العميل: {str(e)}"}
    
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

# إنشاء مثيل من البوت
telegram_bot = TelegramBot()

# وظائف مساعدة للاستخدام السريع
def send_order_notification(order_data):
    """وظيفة سريعة لإرسال إشعار طلب"""
    return telegram_bot.send_order_notification(order_data)

def send_test_message(message):
    """وظيفة سريعة لإرسال رسالة تجريبية"""
    return telegram_bot.send_test_message(message)

def send_price_update(game, platform, account_type, old_price, new_price):
    """وظيفة سريعة لإرسال إشعار تحديث السعر"""
    return telegram_bot.send_price_update_notification(game, platform, account_type, old_price, new_price)

def send_customer_message(name, phone, subject, message):
    """وظيفة سريعة لإرسال رسالة عميل"""
    return telegram_bot.send_customer_message(name, phone, subject, message)

def check_bot_status():
    """وظيفة سريعة لفحص حالة البوت"""
    return telegram_bot.check_bot_status()

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
        "payment_number": "01234567890",
        "order_id": "ORD001"
    }
    
    order_result = send_order_notification(sample_order)
    print(f"نتيجة إشعار الطلب: {order_result}")
