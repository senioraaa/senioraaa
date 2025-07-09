import psutil
import time
import json
import os
from datetime import datetime, timedelta
from config import *
import logging
import threading

# إعداد نظام السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/performance.log'),
        logging.StreamHandler()
    ]
)

class PerformanceMonitor:
    def __init__(self):
        self.monitoring = False
        self.stats_file = 'data/performance_stats.json'
        self.setup_monitoring()
    
    def setup_monitoring(self):
        """إعداد نظام المراقبة"""
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        if not os.path.exists(self.stats_file):
            self.save_stats([])
    
    def get_system_stats(self):
        """الحصول على إحصائيات النظام"""
        try:
            # إحصائيات CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # إحصائيات الذاكرة
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            
            # إحصائيات القرص
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used = disk.used / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB
            
            # إحصائيات الشبكة
            network = psutil.net_io_counters()
            
            # إحصائيات العمليات
            processes = len(psutil.pids())
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'percent': memory_percent,
                    'used_gb': round(memory_used, 2),
                    'total_gb': round(memory_total, 2)
                },
                'disk': {
                    'percent': disk_percent,
                    'used_gb': round(disk_used, 2),
                    'total_gb': round(disk_total, 2)
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'processes': processes
            }
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على إحصائيات النظام: {str(e)}")
            return None
    
    def save_stats(self, stats):
        """حفظ الإحصائيات"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"خطأ في حفظ الإحصائيات: {str(e)}")
    
    def load_stats(self):
        """تحميل الإحصائيات"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logging.error(f"خطأ في تحميل الإحصائيات: {str(e)}")
            return []
    
    def add_stat(self, stat):
        """إضافة إحصائية جديدة"""
        try:
            stats = self.load_stats()
            stats.append(stat)
            
            # الاحتفاظ بآخر 1000 إحصائية فقط
            if len(stats) > 1000:
                stats = stats[-1000:]
            
            self.save_stats(stats)
            
        except Exception as e:
            logging.error(f"خطأ في إضافة الإحصائية: {str(e)}")
    
    def get_current_stats(self):
        """الحصول على الإحصائيات الحالية"""
        return self.get_system_stats()
    
    def get_historical_stats(self, hours=24):
        """الحصول على الإحصائيات التاريخية"""
        try:
            stats = self.load_stats()
            
            # تصفية الإحصائيات حسب الوقت
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filtered_stats = []
            for stat in stats:
                stat_time = datetime.fromisoformat(stat['timestamp'])
                if stat_time >= cutoff_time:
                    filtered_stats.append(stat)
            
            return filtered_stats
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على الإحصائيات التاريخية: {str(e)}")
            return []
    
    def get_performance_summary(self):
        """الحصول على ملخص الأداء"""
        try:
            stats = self.get_historical_stats(24)
            
            if not stats:
                return {
                    'status': 'error',
                    'message': 'لا توجد إحصائيات متاحة'
                }
            
            # حساب المتوسطات
            cpu_values = [stat['cpu']['percent'] for stat in stats]
            memory_values = [stat['memory']['percent'] for stat in stats]
            disk_values = [stat['disk']['percent'] for stat in stats]
            
            avg_cpu = sum(cpu_values) / len(cpu_values)
            avg_memory = sum(memory_values) / len(memory_values)
            avg_disk = sum(disk_values) / len(disk_values)
            
            # حساب القيم القصوى والدنيا
            max_cpu = max(cpu_values)
            min_cpu = min(cpu_values)
            max_memory = max(memory_values)
            min_memory = min(memory_values)
            
            # تحديد حالة الأداء
            performance_status = 'جيد'
            if avg_cpu > 80 or avg_memory > 80:
                performance_status = 'سيء'
            elif avg_cpu > 60 or avg_memory > 60:
                performance_status = 'متوسط'
            
            return {
                'status': 'success',
                'summary': {
                    'performance_status': performance_status,
                    'avg_cpu': round(avg_cpu, 2),
                    'avg_memory': round(avg_memory, 2),
                    'avg_disk': round(avg_disk, 2),
                    'max_cpu': round(max_cpu, 2),
                    'min_cpu': round(min_cpu, 2),
                    'max_memory': round(max_memory, 2),
                    'min_memory': round(min_memory, 2),
                    'data_points': len(stats),
                    'last_updated': stats[-1]['timestamp'] if stats else None
                }
            }
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على ملخص الأداء: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def check_performance_alerts(self):
        """فحص تنبيهات الأداء"""
        try:
            current_stats = self.get_current_stats()
            
            if not current_stats:
                return []
            
            alerts = []
            
            # تنبيهات CPU
            if current_stats['cpu']['percent'] > 90:
                alerts.append({
                    'type': 'critical',
                    'message': f"استهلاك CPU عالي جداً: {current_stats['cpu']['percent']}%",
                    'timestamp': current_stats['timestamp']
                })
            elif current_stats['cpu']['percent'] > 80:
                alerts.append({
                    'type': 'warning',
                    'message': f"استهلاك CPU عالي: {current_stats['cpu']['percent']}%",
                    'timestamp': current_stats['timestamp']
                })
            
            # تنبيهات الذاكرة
            if current_stats['memory']['percent'] > 90:
                alerts.append({
                    'type': 'critical',
                    'message': f"استهلاك الذاكرة عالي جداً: {current_stats['memory']['percent']}%",
                    'timestamp': current_stats['timestamp']
                })
            elif current_stats['memory']['percent'] > 80:
                alerts.append({
                    'type': 'warning',
                    'message': f"استهلاك الذاكرة عالي: {current_stats['memory']['percent']}%",
                    'timestamp': current_stats['timestamp']
                })
            
            # تنبيهات القرص
            if current_stats['disk']['percent'] > 95:
                alerts.append({
                    'type': 'critical',
                    'message': f"مساحة القرص ممتلئة تقريباً: {current_stats['disk']['percent']}%",
                    'timestamp': current_stats['timestamp']
                })
            elif current_stats['disk']['percent'] > 85:
                alerts.append({
                    'type': 'warning',
                    'message': f"مساحة القرص منخفضة: {current_stats['disk']['percent']}%",
                    'timestamp': current_stats['timestamp']
                })
            
            return alerts
            
        except Exception as e:
            logging.error(f"خطأ في فحص تنبيهات الأداء: {str(e)}")
            return []
    
    def start_monitoring(self, interval=60):
        """بدء مراقبة الأداء"""
        self.monitoring = True
        
        def monitor():
            while self.monitoring:
                try:
                    stats = self.get_system_stats()
                    if stats:
                        self.add_stat(stats)
                        
                        # فحص التنبيهات
                        alerts = self.check_performance_alerts()
                        if alerts:
                            for alert in alerts:
                                logging.warning(f"تنبيه أداء: {alert['message']}")
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    logging.error(f"خطأ في مراقبة الأداء: {str(e)}")
                    time.sleep(interval)
        
        # تشغيل المراقبة في thread منفصل
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        logging.info(f"بدء مراقبة الأداء مع فترة {interval} ثانية")
    
    def stop_monitoring(self):
        """إيقاف مراقبة الأداء"""
        self.monitoring = False
        logging.info("تم إيقاف مراقبة الأداء")
    
    def cleanup_old_stats(self, days=7):
        """تنظيف الإحصائيات القديمة"""
        try:
            stats = self.load_stats()
            cutoff_time = datetime.now() - timedelta(days=days)
            
            cleaned_stats = []
            for stat in stats:
                stat_time = datetime.fromisoformat(stat['timestamp'])
                if stat_time >= cutoff_time:
                    cleaned_stats.append(stat)
            
            self.save_stats(cleaned_stats)
            
            removed_count = len(stats) - len(cleaned_stats)
            logging.info(f"تم تنظيف {removed_count} إحصائية قديمة")
            
            return {
                'status': 'success',
                'removed_count': removed_count,
                'remaining_count': len(cleaned_stats)
            }
            
        except Exception as e:
            logging.error(f"خطأ في تنظيف الإحصائيات القديمة: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

# إنشاء مثيل من نظام مراقبة الأداء
performance_monitor = PerformanceMonitor()

# وظائف للاستخدام السريع
def get_current_performance():
    """الحصول على الأداء الحالي"""
    return performance_monitor.get_current_stats()

def get_performance_summary():
    """الحصول على ملخص الأداء"""
    return performance_monitor.get_performance_summary()

def get_performance_alerts():
    """الحصول على تنبيهات الأداء"""
    return performance_monitor.check_performance_alerts()

def start_performance_monitoring():
    """بدء مراقبة الأداء"""
    performance_monitor.start_monitoring()

def stop_performance_monitoring():
    """إيقاف مراقبة الأداء"""
    performance_monitor.stop_monitoring()

# تشغيل النظام
if __name__ == "__main__":
    print("📊 بدء نظام مراقبة الأداء...")
    
    # عرض الإحصائيات الحالية
    current_stats = get_current_performance()
    print(f"الإحصائيات الحالية: {current_stats}")
    
    # عرض ملخص الأداء
    summary = get_performance_summary()
    print(f"ملخص الأداء: {summary}")
    
    # فحص التنبيهات
    alerts = get_performance_alerts()
    print(f"التنبيهات: {alerts}")
    
    # بدء المراقبة
    if PERFORMANCE_SETTINGS.get('auto_monitoring', True):
        start_performance_monitoring()
        
        try:
            while True:
                time.sleep(300)  # تقرير كل 5 دقائق
                summary = get_performance_summary()
                print(f"تقرير الأداء: {summary}")
        except KeyboardInterrupt:
            print("إيقاف نظام مراقبة الأداء...")
            stop_performance_monitoring()
    else:
        print("مراقبة الأداء التلقائية معطلة")
