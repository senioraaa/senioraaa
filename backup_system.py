import os
import shutil
import json
import schedule
import time
from datetime import datetime, timedelta
from config import *
import zipfile
import logging

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backup.log'),
        logging.StreamHandler()
    ]
)

class BackupSystem:
    def __init__(self):
        self.backup_folder = BACKUP_SETTINGS['backup_folder']
        self.keep_backups = BACKUP_SETTINGS['keep_backups']
        self.setup_backup_folder()
    
    def setup_backup_folder(self):
        """إنشاء مجلد النسخ الاحتياطي"""
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)
            logging.info(f"تم إنشاء مجلد النسخ الاحتياطي: {self.backup_folder}")
    
    def create_backup(self, backup_type="manual"):
        """إنشاء نسخة احتياطية"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{backup_type}_{timestamp}.zip"
            backup_path = os.path.join(self.backup_folder, backup_name)
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # نسخ احتياطي للبيانات
                if os.path.exists('data'):
                    for root, dirs, files in os.walk('data'):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, '.')
                            zipf.write(file_path, arcname)
                
                # نسخ احتياطي للتكوين
                if os.path.exists('config.py'):
                    zipf.write('config.py')
                
                # نسخ احتياطي للملفات المهمة
                important_files = [
                    'app.py',
                    'telegram_bot.py',
                    'requirements.txt'
                ]
                
                for file in important_files:
                    if os.path.exists(file):
                        zipf.write(file)
                
                # نسخ احتياطي للقوالب
                if os.path.exists('templates'):
                    for root, dirs, files in os.walk('templates'):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, '.')
                            zipf.write(file_path, arcname)
                
                # نسخ احتياطي للملفات الثابتة
                if os.path.exists('static'):
                    for root, dirs, files in os.walk('static'):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, '.')
                            zipf.write(file_path, arcname)
            
            # إنشاء ملف معلومات النسخة الاحتياطية
            info_file = backup_path.replace('.zip', '_info.json')
            backup_info = {
                'backup_name': backup_name,
                'backup_type': backup_type,
                'timestamp': timestamp,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'size': os.path.getsize(backup_path),
                'files_count': len(zipf.namelist()) if 'zipf' in locals() else 0
            }
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            logging.info(f"تم إنشاء نسخة احتياطية: {backup_name}")
            self.cleanup_old_backups()
            
            return {
                'status': 'success',
                'backup_name': backup_name,
                'backup_path': backup_path,
                'info': backup_info
            }
            
        except Exception as e:
            logging.error(f"خطأ في إنشاء النسخة الاحتياطية: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def cleanup_old_backups(self):
        """حذف النسخ الاحتياطية القديمة"""
        try:
            backup_files = []
            for file in os.listdir(self.backup_folder):
                if file.startswith('backup_') and file.endswith('.zip'):
                    file_path = os.path.join(self.backup_folder, file)
                    backup_files.append((file, os.path.getmtime(file_path)))
            
            # ترتيب النسخ حسب التاريخ (الأحدث أولاً)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # حذف النسخ الزائدة
            if len(backup_files) > self.keep_backups:
                for file_name, _ in backup_files[self.keep_backups:]:
                    file_path = os.path.join(self.backup_folder, file_name)
                    info_file = file_path.replace('.zip', '_info.json')
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logging.info(f"تم حذف النسخة الاحتياطية القديمة: {file_name}")
                    
                    if os.path.exists(info_file):
                        os.remove(info_file)
            
        except Exception as e:
            logging.error(f"خطأ في تنظيف النسخ الاحتياطية: {str(e)}")
    
    def restore_backup(self, backup_name):
        """استعادة نسخة احتياطية"""
        try:
            backup_path = os.path.join(self.backup_folder, backup_name)
            
            if not os.path.exists(backup_path):
                return {
                    'status': 'error',
                    'message': 'النسخة الاحتياطية غير موجودة'
                }
            
            # إنشاء نسخة احتياطية من الحالة الحالية قبل الاستعادة
            current_backup = self.create_backup("pre_restore")
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall('.')
            
            logging.info(f"تم استعادة النسخة الاحتياطية: {backup_name}")
            
            return {
                'status': 'success',
                'message': 'تم استعادة النسخة الاحتياطية بنجاح',
                'current_backup': current_backup
            }
            
        except Exception as e:
            logging.error(f"خطأ في استعادة النسخة الاحتياطية: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_backup_list(self):
        """الحصول على قائمة النسخ الاحتياطية"""
        try:
            backups = []
            
            for file in os.listdir(self.backup_folder):
                if file.startswith('backup_') and file.endswith('.zip'):
                    file_path = os.path.join(self.backup_folder, file)
                    info_file = file_path.replace('.zip', '_info.json')
                    
                    backup_info = {
                        'name': file,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'date': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # قراءة معلومات إضافية إذا وجدت
                    if os.path.exists(info_file):
                        with open(info_file, 'r', encoding='utf-8') as f:
                            extra_info = json.load(f)
                            backup_info.update(extra_info)
                    
                    backups.append(backup_info)
            
            # ترتيب النسخ حسب التاريخ (الأحدث أولاً)
            backups.sort(key=lambda x: x['date'], reverse=True)
            
            return {
                'status': 'success',
                'backups': backups,
                'total_backups': len(backups)
            }
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على قائمة النسخ الاحتياطية: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_backup_info(self, backup_name):
        """الحصول على معلومات نسخة احتياطية معينة"""
        try:
            backup_path = os.path.join(self.backup_folder, backup_name)
            info_file = backup_path.replace('.zip', '_info.json')
            
            if not os.path.exists(backup_path):
                return {
                    'status': 'error',
                    'message': 'النسخة الاحتياطية غير موجودة'
                }
            
            info = {
                'name': backup_name,
                'path': backup_path,
                'size': os.path.getsize(backup_path),
                'date': datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    extra_info = json.load(f)
                    info.update(extra_info)
            
            # معلومات محتويات النسخة الاحتياطية
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                info['files'] = zipf.namelist()
                info['files_count'] = len(zipf.namelist())
            
            return {
                'status': 'success',
                'info': info
            }
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على معلومات النسخة الاحتياطية: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def schedule_backups(self):
        """جدولة النسخ الاحتياطية التلقائية"""
        frequency = BACKUP_SETTINGS['frequency']
        
        if frequency == 'daily':
            schedule.every().day.at("02:00").do(self.create_backup, "daily")
        elif frequency == 'weekly':
            schedule.every().week.do(self.create_backup, "weekly")
        elif frequency == 'monthly':
            schedule.every().month.do(self.create_backup, "monthly")
        
        logging.info(f"تم جدولة النسخ الاحتياطية: {frequency}")
    
    def run_backup_scheduler(self):
        """تشغيل جدولة النسخ الاحتياطية"""
        self.schedule_backups()
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # فحص كل دقيقة

# إنشاء مثيل من نظام النسخ الاحتياطي
backup_system = BackupSystem()

# وظائف للاستخدام السريع
def create_backup(backup_type="manual"):
    """إنشاء نسخة احتياطية"""
    return backup_system.create_backup(backup_type)

def restore_backup(backup_name):
    """استعادة نسخة احتياطية"""
    return backup_system.restore_backup(backup_name)

def get_backup_list():
    """الحصول على قائمة النسخ الاحتياطية"""
    return backup_system.get_backup_list()

def get_backup_info(backup_name):
    """الحصول على معلومات نسخة احتياطية"""
    return backup_system.get_backup_info(backup_name)

# تشغيل النظام
if __name__ == "__main__":
    print("🔄 بدء نظام النسخ الاحتياطي...")
    
    # إنشاء نسخة احتياطية تجريبية
    result = create_backup("test")
    print(f"نتيجة النسخة الاحتياطية: {result}")
    
    # عرض قائمة النسخ الاحتياطية
    backups = get_backup_list()
    print(f"النسخ الاحتياطية المتاحة: {backups}")
    
    # تشغيل الجدولة
    if BACKUP_SETTINGS['enabled']:
        backup_system.run_backup_scheduler()
    else:
        print("نظام النسخ الاحتياطي التلقائي معطل")
