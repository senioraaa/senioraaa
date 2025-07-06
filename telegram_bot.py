import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from flask import current_app

class TelegramNotificationSystem:
    """نظام إشعارات التليجرام المتقدم"""
    
    def __init__(self, app=None):
        self.app = app
        self.bot_token = None
        self.bot_username = None
        self.webhook_url = None
        self.base_url = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """تهيئة نظام التليجرام مع التطبيق"""
        self.app = app
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.bot_username = os.environ.get('BOT_USERNAME', 'YourBot_bot')
        self.webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL')
        
        if self.bot_token:
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
            app.logger.info("Telegram bot initialized successfully")
        else:
            app.logger.warning("Telegram bot token not configured")
    
    def is_configured(self) -> bool:
        """فحص ما إذا كان البوت مُعد بشكل صحيح"""
        return bool(self.bot_token and self.base_url)
    
    def send_message(self, chat_id: str, message: str, parse_mode: str = 'HTML') -> bool:
        """إرسال رسالة إلى مستخدم محدد"""
        if not self.is_configured():
            self.app.logger.warning("Telegram bot not configured, skipping message")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                self.app.logger.info(f"Message sent successfully to {chat_id}")
                return True
            else:
                self.app.logger.error(f"Failed to send message: {result}")
                return False
                
        except Exception as e:
            self.app.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_order_notification(self, user_telegram_id: str, order_data: Dict[str, Any]) -> bool:
        """إرسال إشعار عن طلب جديد"""
        if not user_telegram_id:
            return False
        
        # تنسيق رسالة الطلب
        message = self.format_order_message(order_data)
        return self.send_message(user_telegram_id, message)
    
    def send_status_update(self, user_telegram_id: str, order_id: int, 
                          old_status: str, new_status: str) -> bool:
        """إرسال تحديث حالة الطلب"""
        if not user_telegram_id:
            return False
        
        status_messages = {
            'pending': '⏳ قيد الانتظار',
            'processing': '⚙️ قيد المعالجة',
            'completed': '✅ مكتمل',
            'cancelled': '❌ ملغي'
        }
        
        old_status_text = status_messages.get(old_status, old_status)
        new_status_text = status_messages.get(new_status, new_status)
        
        message = f"""
🔔 <b>تحديث حالة الطلب #{order_id}</b>

📊 الحالة السابقة: {old_status_text}
🆕 الحالة الجديدة: {new_status_text}

🕒 وقت التحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}

شكراً لاختيارك شهد السنيورة! 🎮
        """
        
        return self.send_message(user_telegram_id, message.strip())
    
    def format_order_message(self, order_data: Dict[str, Any]) -> str:
        """تنسيق رسالة الطلب الجديد"""
        platform_icons = {
            'PS': '🎮 PlayStation',
            'Xbox': '🎯 Xbox',
            'PC': '💻 PC'
        }
        
        platform_text = platform_icons.get(order_data.get('platform', ''), order_data.get('platform', ''))
        coins_amount = order_data.get('coins_amount', 0)
        formatted_coins = f"{coins_amount:,}" if coins_amount else "غير محدد"
        
        transfer_type_text = "⚡ فوري" if order_data.get('transfer_type') == 'instant' else "🕒 عادي"
        price = order_data.get('price', 0)
        formatted_price = f"{price:,.2f}" if price else "يتم حسابه"
        
        message = f"""
🎉 <b>طلب جديد تم إرساله بنجاح!</b>

📋 <b>تفاصيل الطلب:</b>
🆔 رقم الطلب: #{order_data.get('id', 'جاري التوليد')}
🎮 المنصة: {platform_text}
💰 الكمية: {formatted_coins} كوين
⚡ نوع التحويل: {transfer_type_text}
💵 السعر المتوقع: {formatted_price} جنيه

📱 طريقة الدفع: {order_data.get('payment_method', 'غير محدد')}
📞 رقم الواتساب: {order_data.get('phone_number', 'غير محدد')}

🕒 وقت الطلب: {datetime.now().strftime('%Y-%m-%d %H:%M')}

سيتم التواصل معك قريباً لإتمام العملية! 
شكراً لاختيارك شهد السنيورة! 🚀
        """
        
        return message.strip()
    
    def setup_webhook(self) -> bool:
        """إعداد webhook للبوت"""
        if not self.is_configured() or not self.webhook_url:
            self.app.logger.warning("Cannot setup webhook: missing configuration")
            return False
        
        try:
            url = f"{self.base_url}/setWebhook"
            payload = {
                'url': self.webhook_url,
                'allowed_updates': ['message', 'callback_query']
            }
            
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                self.app.logger.info("Webhook setup successfully")
                return True
            else:
                self.app.logger.error(f"Failed to setup webhook: {result}")
                return False
                
        except Exception as e:
            self.app.logger.error(f"Error setting up webhook: {e}")
            return False
    
    def process_telegram_update(self, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """معالجة تحديثات التليجرام الواردة"""
        try:
            if 'message' in update_data:
                return self.process_message(update_data['message'])
            elif 'callback_query' in update_data:
                return self.process_callback_query(update_data['callback_query'])
            
            return None
            
        except Exception as e:
            self.app.logger.error(f"Error processing Telegram update: {e}")
            return None
    
    def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """معالجة الرسائل الواردة"""
        chat_id = str(message['chat']['id'])
        user_id = str(message['from']['id'])
        username = message['from'].get('username', '')
        text = message.get('text', '').strip()
        
        # معالجة أوامر البوت
        if text.startswith('/start'):
            return self.handle_start_command(chat_id, user_id, username, text)
        elif text == '/help':
            return self.handle_help_command(chat_id)
        elif text == '/status':
            return self.handle_status_command(chat_id, user_id)
        else:
            return self.handle_regular_message(chat_id, text)
    
    def handle_start_command(self, chat_id: str, user_id: str, username: str, text: str) -> Dict[str, Any]:
        """معالجة أمر /start"""
        # استخراج معرف المستخدم من الرابط إذا وُجد
        website_user_id = None
        if ' ' in text:
            try:
                import base64
                encoded_id = text.split(' ')[1]
                website_user_id = base64.b64decode(encoded_id).decode('utf-8')
            except:
                pass
        
        welcome_message = f"""
🎮 <b>مرحباً بك في بوت شهد السنيورة!</b>

أهلاً {username or 'صديقي'}! 👋

🔔 سيقوم هذا البوت بإرسال إشعارات فورية عن:
• الطلبات الجديدة 
• تحديثات حالة الطلبات
• العروض الخاصة والتخفيضات

📱 <b>الأوامر المتاحة:</b>
/help - عرض المساعدة
/status - حالة الربط مع حسابك

🔗 لربط حسابك، استخدم زر "ربط التليجرام" في موقعنا.

مرحباً بك في عائلة شهد السنيورة! 🚀
        """
        
        self.send_message(chat_id, welcome_message.strip())
        
        return {
            'action': 'start',
            'chat_id': chat_id,
            'user_id': user_id,
            'username': username,
            'website_user_id': website_user_id
        }
    
    def handle_help_command(self, chat_id: str) -> Dict[str, Any]:
        """معالجة أمر /help"""
        help_message = """
🤖 <b>مساعدة بوت شهد السنيورة</b>

📋 <b>الأوامر المتاحة:</b>
/start - بدء استخدام البوت
/help - عرض هذه المساعدة  
/status - فحص حالة الربط

🔔 <b>الإشعارات التلقائية:</b>
• إشعار فوري عند إرسال طلب جديد
• تحديثات حالة الطلب (قيد المعالجة، مكتمل، إلخ)
• تنبيهات العروض الخاصة

🔗 <b>كيفية الربط:</b>
1. سجل دخولك في موقع شهد السنيورة
2. اذهب للملف الشخصي  
3. اضغط على "ربط التليجرام"
4. أرسل أي رسالة لهذا البوت

💬 للدعم الفني، تواصل معنا عبر الموقع.
        """
        
        self.send_message(chat_id, help_message.strip())
        
        return {
            'action': 'help',
            'chat_id': chat_id
        }
    
    def handle_status_command(self, chat_id: str, user_id: str) -> Dict[str, Any]:
        """معالجة أمر /status"""
        # هنا يمكن فحص حالة الربط مع قاعدة البيانات
        status_message = f"""
📊 <b>حالة حسابك</b>

🆔 معرف التليجرام: <code>{user_id}</code>
💬 معرف المحادثة: <code>{chat_id}</code>

🔗 لربط حسابك مع الموقع:
1. اذهب إلى الملف الشخصي في الموقع
2. اضغط "ربط التليجرام"  
3. أرسل أي رسالة هنا

✅ البوت يعمل بشكل طبيعي
        """
        
        self.send_message(chat_id, status_message.strip())
        
        return {
            'action': 'status',
            'chat_id': chat_id,
            'user_id': user_id
        }
    
    def handle_regular_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """معالجة الرسائل العادية"""
        response_message = """
شكراً لرسالتك! 📝

🔗 إذا لم تقم بربط حسابك بعد:
• اذهب للملف الشخصي في الموقع
• اضغط "ربط التليجرام"
• ستتم المزامنة تلقائياً

💬 للمساعدة: /help
📊 لفحص الحالة: /status

سنتواصل معك قريباً! 🚀
        """
        
        self.send_message(chat_id, response_message.strip())
        
        return {
            'action': 'message',
            'chat_id': chat_id,
            'text': text
        }

# إنشاء instance عام
telegram_system = TelegramNotificationSystem()
