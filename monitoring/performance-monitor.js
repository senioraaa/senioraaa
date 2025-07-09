// نظام مراقبة الأداء المتقدم
class PerformanceMonitor {
    constructor() {
        this.metrics = {
            responseTime: [],
            uptime: 0,
            cpuUsage: [],
            memoryUsage: [],
            diskUsage: [],
            networkTraffic: [],
            errorRate: [],
            userSessions: []
        };
        
        this.thresholds = {
            responseTime: 2000,    // 2 ثانية
            cpuUsage: 80,          // 80%
            memoryUsage: 85,       // 85%
            diskUsage: 90,         // 90%
            errorRate: 5,          // 5%
            uptime: 99.9           // 99.9%
        };
        
        this.alerts = {
            active: [],
            history: [],
            recipients: [
                'admin@shahd-senior.com',
                '@shahd_senior_bot'
            ]
        };
        
        this.monitoringInterval = 60000; // دقيقة واحدة
        this.isMonitoring = false;
        
        this.init();
    }
    
    // تهيئة نظام المراقبة
    init() {
        this.startMonitoring();
        this.setupHealthChecks();
        this.setupAlertSystem();
        this.setupReporting();
    }
    
    // بدء المراقبة
    startMonitoring() {
        if (this.isMonitoring) {
            console.log('⚠️ نظام المراقبة يعمل بالفعل');
            return;
        }
        
        this.isMonitoring = true;
        
        // مراقبة مستمرة
        this.monitoringTimer = setInterval(() => {
            this.collectMetrics();
        }, this.monitoringInterval);
        
        // مراقبة وقت التشغيل
        this.uptimeTimer = setInterval(() => {
            this.updateUptime();
        }, 1000);
        
        console.log('✅ تم بدء نظام مراقبة الأداء');
    }
    
    // جمع المقاييس
    async collectMetrics() {
        try {
            // جمع مقاييس الأداء
            const metrics = await this.gatherSystemMetrics();
            
            // تحديث البيانات
            this.updateMetrics(metrics);
            
            // فحص العتبات
            await this.checkThresholds(metrics);
            
            // حفظ البيانات
            this.saveMetrics(metrics);
            
        } catch (error) {
            console.error('❌ خطأ في جمع المقاييس:', error);
        }
    }
    
    // جمع مقاييس النظام
    async gatherSystemMetrics() {
        const metrics = {
            timestamp: new Date(),
            responseTime: await this.measureResponseTime(),
            cpuUsage: await this.getCPUUsage(),
            memoryUsage: await this.getMemoryUsage(),
            diskUsage: await this.getDiskUsage(),
            networkTraffic: await this.getNetworkTraffic(),
            errorRate: await this.getErrorRate(),
            userSessions: await this.getUserSessions(),
            customMetrics: await this.getCustomMetrics()
        };
        
        return metrics;
    }
    
    // قياس وقت الاستجابة
    async measureResponseTime() {
        try {
            const startTime = performance.now();
            
            // اختبار الاستجابة للصفحة الرئيسية
            const response = await fetch(window.location.origin, {
                method: 'GET',
                cache: 'no-cache'
            });
            
            const endTime = performance.now();
            const responseTime = endTime - startTime;
            
            return {
                value: responseTime,
                status: response.status,
                ok: response.ok
            };
            
        } catch (error) {
            console.error('❌ خطأ في قياس وقت الاستجابة:', error);
            return {
                value: -1,
                status: 0,
                ok: false,
                error: error.message
            };
        }
    }
    
    // الحصول على استخدام المعالج
    async getCPUUsage() {
        try {
            // محاكاة قياس استخدام المعالج
            const cpuUsage = Math.random() * 100;
            
            return {
                value: cpuUsage,
                cores: navigator.hardwareConcurrency || 1,
                timestamp: new Date()
            };
            
        } catch (error) {
            console.error('❌ خطأ في قياس استخدام المعالج:', error);
            return { value: -1, error: error.message };
        }
    }
    
    // الحصول على استخدام الذاكرة
    async getMemoryUsage() {
        try {
            if (performance.memory) {
                const memory = performance.memory;
                
                return {
                    used: memory.usedJSHeapSize,
                    total: memory.totalJSHeapSize,
                    limit: memory.jsHeapSizeLimit,
                    percentage: (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100
                };
            } else {
                // تقدير استخدام الذاكرة
                return {
                    used: 0,
                    total: 0,
                    limit: 0,
                    percentage: Math.random() * 100
                };
            }
            
        } catch (error) {
            console.error('❌ خطأ في قياس استخدام الذاكرة:', error);
            return { percentage: -1, error: error.message };
        }
    }
    
    // الحصول على استخدام القرص
    async getDiskUsage() {
        try {
            // محاكاة قياس استخدام القرص
            const diskUsage = Math.random() * 100;
            
            return {
                percentage: diskUsage,
                total: '50GB',
                used: `${(diskUsage / 100 * 50).toFixed(1)}GB`,
                free: `${(50 - diskUsage / 100 * 50).toFixed(1)}GB`
            };
            
        } catch (error) {
            console.error('❌ خطأ في قياس استخدام القرص:', error);
            return { percentage: -1, error: error.message };
        }
    }
    
    // الحصول على حركة المرور
    async getNetworkTraffic() {
        try {
            if (navigator.connection) {
                const connection = navigator.connection;
                
                return {
                    effectiveType: connection.effectiveType,
                    downlink: connection.downlink,
                    rtt: connection.rtt,
                    saveData: connection.saveData
                };
            } else {
                return {
                    effectiveType: 'unknown',
                    downlink: -1,
                    rtt: -1,
                    saveData: false
                };
            }
            
        } catch (error) {
            console.error('❌ خطأ في قياس حركة المرور:', error);
            return { error: error.message };
        }
    }
    
    // الحصول على معدل الأخطاء
    async getErrorRate() {
        try {
            const totalRequests = this.getTotalRequests();
            const errorRequests = this.getErrorRequests();
            
            const errorRate = totalRequests > 0 ? (errorRequests / totalRequests) * 100 : 0;
            
            return {
                rate: errorRate,
                totalRequests: totalRequests,
                errorRequests: errorRequests,
                successRate: 100 - errorRate
            };
            
        } catch (error) {
            console.error('❌ خطأ في قياس معدل الأخطاء:', error);
            return { rate: -1, error: error.message };
        }
    }
    
    // الحصول على جلسات المستخدمين
    async getUserSessions() {
        try {
            // محاكاة جلسات المستخدمين
            const activeSessions = Math.floor(Math.random() * 100);
            
            return {
                active: activeSessions,
                total: activeSessions + Math.floor(Math.random() * 50),
                avgDuration: Math.floor(Math.random() * 600) + 60, // 1-10 دقائق
                bounceRate: Math.random() * 50 + 20 // 20-70%
            };
            
        } catch (error) {
            console.error('❌ خطأ في قياس جلسات المستخدمين:', error);
            return { active: -1, error: error.message };
        }
    }
    
    // الحصول على مقاييس مخصصة
    async getCustomMetrics() {
        try {
            return {
                ordersPerMinute: Math.floor(Math.random() * 10),
                conversionRate: Math.random() * 5 + 1,
                averageOrderValue: Math.random() * 50 + 30,
                whatsappClicks: Math.floor(Math.random() * 50),
                telegramNotifications: Math.floor(Math.random() * 20),
                gamePriceUpdates: Math.floor(Math.random() * 5)
            };
            
        } catch (error) {
            console.error('❌ خطأ في قياس المقاييس المخصصة:', error);
            return { error: error.message };
        }
    }
    
    // تحديث المقاييس
    updateMetrics(newMetrics) {
        // تحديث وقت الاستجابة
        this.metrics.responseTime.push(newMetrics.responseTime);
        if (this.metrics.responseTime.length > 100) {
            this.metrics.responseTime.shift();
        }
        
        // تحديث استخدام المعالج
        this.metrics.cpuUsage.push(newMetrics.cpuUsage);
        if (this.metrics.cpuUsage.length > 100) {
            this.metrics.cpuUsage.shift();
        }
        
        // تحديث استخدام الذاكرة
        this.metrics.memoryUsage.push(newMetrics.memoryUsage);
        if (this.metrics.memoryUsage.length > 100) {
            this.metrics.memoryUsage.shift();
        }
        
        // تحديث باقي المقاييس
        Object.keys(newMetrics).forEach(key => {
            if (Array.isArray(this.metrics[key])) {
                this.metrics[key].push(newMetrics[key]);
                if (this.metrics[key].length > 100) {
                    this.metrics[key].shift();
                }
            }
        });
    }
    
    // فحص العتبات
    async checkThresholds(metrics) {
        const alerts = [];
        
        // فحص وقت الاستجابة
        if (metrics.responseTime.value > this.thresholds.responseTime) {
            alerts.push({
                type: 'response_time',
                severity: 'warning',
                message: `وقت الاستجابة عالي: ${metrics.responseTime.value.toFixed(2)}ms`,
                threshold: this.thresholds.responseTime,
                value: metrics.responseTime.value
            });
        }
        
        // فحص استخدام المعالج
        if (metrics.cpuUsage.value > this.thresholds.cpuUsage) {
            alerts.push({
                type: 'cpu_usage',
                severity: 'critical',
                message: `استخدام المعالج عالي: ${metrics.cpuUsage.value.toFixed(1)}%`,
                threshold: this.thresholds.cpuUsage,
                value: metrics.cpuUsage.value
            });
        }
        
        // فحص استخدام الذاكرة
        if (metrics.memoryUsage.percentage > this.thresholds.memoryUsage) {
            alerts.push({
                type: 'memory_usage',
                severity: 'warning',
                message: `استخدام الذاكرة عالي: ${metrics.memoryUsage.percentage.toFixed(1)}%`,
                threshold: this.thresholds.memoryUsage,
                value: metrics.memoryUsage.percentage
            });
        }
        
        // فحص معدل الأخطاء
        if (metrics.errorRate.rate > this.thresholds.errorRate) {
            alerts.push({
                type: 'error_rate',
                severity: 'critical',
                message: `معدل الأخطاء عالي: ${metrics.errorRate.rate.toFixed(1)}%`,
                threshold: this.thresholds.errorRate,
                value: metrics.errorRate.rate
            });
        }
        
        // إرسال التنبيهات
        for (const alert of alerts) {
            await this.sendAlert(alert);
        }
    }
    
    // إرسال تنبيه
    async sendAlert(alert) {
        // التحقق من عدم إرسال تنبيه مكرر
        const existingAlert = this.alerts.active.find(a => a.type === alert.type);
        if (existingAlert) {
            return;
        }
        
        // إضافة التنبيه للقائمة النشطة
        alert.timestamp = new Date();
        alert.id = Date.now().toString();
        this.alerts.active.push(alert);
        
        // إنشاء رسالة التنبيه
        const message = `🚨 تنبيه أداء: ${alert.message}\n\n`;
        const details = `🔍 التفاصيل:\n`;
        const thresholdInfo = `📊 العتبة: ${alert.threshold}\n`;
        const valueInfo = `📈 القيمة الحالية: ${alert.value}\n`;
        const timeInfo = `⏰ الوقت: ${alert.timestamp.toLocaleString('ar-EG')}`;
        
        const fullMessage = message + details + thresholdInfo + valueInfo + timeInfo;
        
        // إرسال التنبيه
        await this.sendNotification(fullMessage, alert.severity);
        
        // إضافة للتاريخ
        this.alerts.history.push(alert);
        
        console.log(`🚨 تم إرسال تنبيه: ${alert.message}`);
    }
    
    // إرسال إشعار
    async sendNotification(message, severity = 'info') {
        try {
            // إرسال بريد إلكتروني
            await this.sendEmail(message, severity);
            
            // إرسال تليجرام
            await this.sendTelegram(message, severity);
            
        } catch (error) {
            console.error('❌ خطأ في إرسال الإشعار:', error);
        }
    }
    
    // تحديث وقت التشغيل
    updateUptime() {
        this.metrics.uptime += 1;
    }
    
    // الحصول على تقرير الأداء
    getPerformanceReport() {
        const now = new Date();
        const report = {
            timestamp: now,
            uptime: this.formatUptime(this.metrics.uptime),
            averageResponseTime: this.calculateAverage(this.metrics.responseTime.map(r => r.value)),
            averageCPUUsage: this.calculateAverage(this.metrics.cpuUsage.map(c => c.value)),
            averageMemoryUsage: this.calculateAverage(this.metrics.memoryUsage.map(m => m.percentage)),
            currentErrorRate: this.metrics.errorRate[this.metrics.errorRate.length - 1]?.rate || 0,
            activeAlerts: this.alerts.active.length,
            totalAlerts: this.alerts.history.length,
            healthStatus: this.getHealthStatus()
        };
        
        return report;
    }
    
    // تنسيق وقت التشغيل
    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        return `${days}d ${hours}h ${minutes}m ${secs}s`;
    }
    
    // حساب المتوسط
    calculateAverage(values) {
        if (values.length === 0) return 0;
        const sum = values.reduce((acc, val) => acc + val, 0);
        return sum / values.length;
    }
    
    // الحصول على حالة الصحة
    getHealthStatus() {
        const activeAlerts = this.alerts.active;
        const criticalAlerts = activeAlerts.filter(a => a.severity === 'critical');
        const warningAlerts = activeAlerts.filter(a => a.severity === 'warning');
        
        if (criticalAlerts.length > 0) {
            return 'critical';
        } else if (warningAlerts.length > 0) {
            return 'warning';
        } else {
            return 'healthy';
        }
    }
    
    // إيقاف المراقبة
    stopMonitoring() {
        if (this.monitoringTimer) {
            clearInterval(this.monitoringTimer);
        }
        
        if (this.uptimeTimer) {
            clearInterval(this.uptimeTimer);
        }
        
        this.isMonitoring = false;
        console.log('🛑 تم إيقاف نظام مراقبة الأداء');
    }
}

// تشغيل نظام مراقبة الأداء
const performanceMonitor = new PerformanceMonitor();

// تصدير للاستخدام العام
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceMonitor;
}
    
