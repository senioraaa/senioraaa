import hashlib
import secrets
import time
import json
import os
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from config import *
import logging
import re

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/security.log'),
        logging.StreamHandler()
    ]
)

class SecurityManager:
    def __init__(self):
        self.blocked_ips = set()
        self.failed_attempts = {}
        self.suspicious_activities = []
        self.encryption_key = self.get_or_create_key()
        self.setup_security()
    
    def setup_security(self):
        """إعداد نظام الأمان"""
        os.makedirs('data/security', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # تحميل القوائم السوداء
        self.load_blocked_ips()
        self.load_failed_attempts()
    
    def get_or_create_key(self):
        """الحصول على مفتاح التشفير أو إنشاء واحد جديد"""
        key_file = 'data/security/encryption.key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt_data(self, data):
        """تشفير البيانات"""
        try:
            f = Fernet(self.encryption_key)
            if isinstance(data, str):
                data = data.encode()
            return f.encrypt(data)
        except Exception as e:
            logging.error(f"خطأ في تشفير البيانات: {str(e)}")
            return None
    
    def decrypt_data(self, encrypted_data):
        """فك تشفير البيانات"""
        try:
            f = Fernet(self.encryption_key)
            return f.decrypt(encrypted_data).decode()
        except Exception as e:
            logging.error(f"خطأ في فك تشفير البيانات: {str(e)}")
            return None
    
    def hash_password(self, password, salt=None):
        """تشفير كلمة المرور"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        
        return {
            'hash': password_hash.hex(),
            'salt': salt
        }
    
    def verify_password(self, password, stored_hash, salt):
        """التحقق من كلمة المرور"""
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        
        return password_hash.hex() == stored_hash
    
    def is_ip_blocked(self, ip_address):
        """التحقق من حظر IP"""
        return ip_address in self.blocked_ips
    
    def block_ip(self, ip_address, reason="محاولات تسجيل دخول متكررة"):
        """حظر IP معين"""
        self.blocked_ips.add(ip_address)
        self.save_blocked_ips()
        
        # تسجيل الحظر
        self.log_security_event({
            'type': 'ip_blocked',
            'ip': ip_address,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        logging.warning(f"تم حظر IP: {ip_address} - السبب: {reason}")
    
    def unblock_ip(self, ip_address):
        """إلغاء حظر IP"""
        if ip_address in self.blocked_ips:
            self.blocked_ips.remove(ip_address)
            self.save_blocked_ips()
            
            logging.info(f"تم إلغاء حظر IP: {ip_address}")
    
    def record_failed_attempt(self, ip_address, attempt_type="login"):
        """تسجيل محاولة فاشلة"""
        current_time = datetime.now()
        
        if ip_address not in self.failed_attempts:
            self.failed_attempts[ip_address] = []
        
        self.failed_attempts[ip_address].append({
            'type': attempt_type,
            'timestamp': current_time.isoformat()
        })
        
        # تنظيف المحاولات القديمة (أكثر من ساعة)
        cutoff_time = current_time - timedelta(hours=1)
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if datetime.fromisoformat(attempt['timestamp']) > cutoff_time
        ]
        
        # حظر IP في حالة تجاوز الحد الأقصى
        max_attempts = SECURITY_SETTINGS['max_login_attempts']
        if len(self.failed_attempts[ip_address]) >= max_attempts:
            self.block_ip(ip_address, f"تجاوز الحد الأقصى للمحاولات ({max_attempts})")
        
        self.save_failed_attempts()
    
    def is_suspicious_activity(self, activity_data):
        """فحص النشاط المشبوه"""
        suspicious_patterns = [
            r'union.*select',  # SQL injection
            r'',     # XSS
            r'\.\./',          # Path traversal
            r'eval\(',         # Code execution
            r'system\(',       # System commands
        ]
        
        for key, value in activity_data.items():
            if isinstance(value, str):
                for pattern in suspicious_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        return True
        
        return False
    
    def log_security_event(self, event_data):
        """تسجيل حدث أمني"""
        try:
            events_file = 'data/security/security_events.json'
            
            # تحميل الأحداث الموجودة
            if os.path.exists(events_file):
                with open(events_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            else:
                events = []
            
            # إضافة الحدث الجديد
            events.append(event_data)
            
            # الاحتفاظ بآخر 1000 حدث فقط
            if len(events) > 1000:
                events = events[-1000:]
            
            # حفظ الأحداث
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logging.error(f"خطأ في تسجيل الحدث الأمني: {str(e)}")
    
    def check_request_security(self, request_data):
        """فحص أمان الطلب"""
        try:
            # فحص النشاط المشبوه
            if self.is_suspicious_activity(request_data):
                self.log_security_event({
                    'type': 'suspicious_activity',
                    'data': request_data,
                    'timestamp': datetime.now().isoformat()
                })
                return {
                    'status': 'blocked',
                    'reason': 'نشاط مشبوه'
                }
            
            # فحص حظر IP
            client_ip = request_data.get('client_ip')
            if client_ip and self.is_ip_blocked(client_ip):
                return {
                    'status': 'blocked',
                    'reason': 'IP محظور'
                }
            
            return {
                'status': 'allowed'
            }
            
        except Exception as e:
            logging.error(f"خطأ في فحص أمان الطلب: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def generate_secure_token(self, length=32):
        """إنشاء رمز آمن"""
        return secrets.token_urlsafe(length)
    
    def validate_input(self, input_data, input_type="text"):
        """التحقق من صحة الإدخال"""
        if input_type == "email":
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(email_pattern, input_data) is not None
        
        elif input_type == "phone":
            phone_pattern = r'^[+]?[\d\s\-\(\)]{10,}$'
            return re.match(phone_pattern, input_data) is not None
        
        elif input_type == "password":
            # كلمة المرور يجب أن تكون 8 أحرف على الأقل
            min_length = SECURITY_SETTINGS['password_min_length']
            return len(input_data) >= min_length
        
        elif input_type == "text":
            # فحص النص العادي من المحتوى المشبوه
            return not self.is_suspicious_activity({'text': input_data})
        
        return True
    
    def get_security_report(self):
        """الحصول على تقرير الأمان"""
        try:
            events_file = 'data/security/security_events.json'
            
            if os.path.exists(events_file):
                with open(events_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
            else:
                events = []
            
            # تحليل الأحداث
            total_events = len(events)
            blocked_ips_count = len(self.blocked_ips)
            
            # إحصائيات الأحداث
            event_types = {}
            for event in events:
                event_type = event.get('type', 'unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # آخر الأحداث
            recent_events = events[-10:] if events else []
            
            return {
                'status': 'success',
                'report': {
                    'total_events': total_events,
                    'blocked_ips_count': blocked_ips_count,
                    'event_types': event_types,
                    'recent_events': recent_events,
                    'blocked_ips': list(self.blocked_ips),
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logging.error(f"خطأ في إنشاء تقرير الأمان: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def save_blocked_ips(self):
        """حفظ قائمة IPs المحظورة"""
        try:
            blocked_ips_file = 'data/security/blocked_ips.json'
            with open(blocked_ips_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.blocked_ips), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"خطأ في حفظ قائمة IPs المحظورة: {str(e)}")
    
    def load_blocked_ips(self):
        """تحميل قائمة IPs المحظورة"""
        try:
            blocked_ips_file = 'data/security/blocked_ips.json'
            if os.path.exists(blocked_ips_file):
                with open(blocked_ips_file, 'r', encoding='utf-8') as f:
                    self.blocked_ips = set(json.load(f))
        except Exception as e:
            logging.error(f"خطأ في تحميل قائمة IPs المحظورة: {str(e)}")
    
    def save_failed_attempts(self):
        """حفظ المحاولات الفاشلة"""
        try:
            failed_attempts_file = 'data/security/failed_attempts.json'
            with open(failed_attempts_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_attempts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"خطأ في حفظ المحاولات الفاشلة: {str(e)}")
    
    def load_failed_attempts(self):
        """تحميل المحاولات الفاشلة"""
        try:
            failed_attempts_file = 'data/security/failed_attempts.json'
            if os.path.exists(failed_attempts_file):
                with open(failed_attempts_file, 'r', encoding='utf-8') as f:
                    self.failed_attempts = json.load(f)
        except Exception as e:
            logging.error(f"خطأ في تحميل المحاولات الفاشلة: {str(e)}")
    
    def cleanup_old_data(self, days=30):
        """تنظيف البيانات القديمة"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # تنظيف المحاولات الفاشلة
            for ip in list(self.failed_attempts.keys()):
                self.failed_attempts[ip] = [
                    attempt for attempt in self.failed_attempts[ip]
                    if datetime.fromisoformat(attempt['timestamp']) > cutoff_time
                ]
                
                # حذف IP إذا لم تعد له محاولات
                if not self.failed_attempts[ip]:
                    del self.failed_attempts[ip]
            
            self.save_failed_attempts()
            
            # تنظيف أحداث الأمان
            events_file = 'data/security/security_events.json'
            if os.path.exists(events_file):
                with open(events_file, 'r', encoding='utf-8') as f:
                    events = json.load(f)
                
                cleaned_events = [
                    event for event in events
                    if datetime.fromisoformat(event['timestamp']) > cutoff_time
                ]
                
                with open(events_file, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_events, f, ensure_ascii=False, indent=2)
            
            logging.info(f"تم تنظيف البيانات الأمنية الأقدم من {days} يوم")
            
        except Exception as e:
            logging.error(f"خطأ في تنظيف البيانات القديمة: {str(e)}")

# إنشاء مثيل من نظام إدارة الأمان
security_manager = SecurityManager()

# وظائف للاستخدام السريع
def check_request_security(request_data):
    """فحص أمان الطلب"""
    return security_manager.check_request_security(request_data)

def block_ip(ip_address, reason="نشاط مشبوه"):
    """حظر IP"""
    security_manager.block_ip(ip_address, reason)

def record_failed_attempt(ip_address, attempt_type="login"):
    """تسجيل محاولة فاشلة"""
    security_manager.record_failed_attempt(ip_address, attempt_type)

def get_security_report():
    """الحصول على تقرير الأمان"""
    return security_manager.get_security_report()

def validate_input(input_data, input_type="text"):
    """التحقق من صحة الإدخال"""
    return security_manager.validate_input(input_data, input_type)

def generate_secure_token(length=32):
    """إنشاء رمز آمن"""
    return security_manager.generate_secure_token(length)

# تشغيل النظام
if __name__ == "__main__":
    print("🔒 بدء نظام إدارة الأمان...")
    
    # اختبار التحقق من الإدخال
    test_email = "test@example.com"
    print(f"اختبار إيميل '{test_email}': {validate_input(test_email, 'email')}")
    
    # اختبار إنشاء رمز آمن
    token = generate_secure_token()
    print(f"رمز آمن: {token}")
    
    # عرض تقرير الأمان
    report = get_security_report()
    print(f"تقرير الأمان: {report}")
    
    print("نظام إدارة الأمان جاهز للاستخدام")
