class MonitoringSystem {
    constructor() {
        this.config = {
            checkInterval: 60000, // دقيقة واحدة
            alertThresholds: {
                responseTime: 2000, // 2 ثانية
                errorRate: 5, // 5%
                cpuUsage: 80, // 80%
                memoryUsage: 85, // 85%
                diskUsage: 90 // 90%
            },
            endpoints: [
                'https://shahd-senior.com',
                'https://shahd-senior.com/fc25.html',
                'https://shahd-senior.com/api/health'
            ],
            notifications: {
                telegram: {
                    botToken: process.env.TELEGRAM_BOT_TOKEN,
                    chatId: process.env.TELEGRAM_CHAT_ID
                },
                email: {
                    smtp: 'smtp.gmail.com',
                    port: 587,
                    user: process.env.EMAIL_USER,
                    pass: process.env.EMAIL_PASS,
                    to: 'admin@shahd-senior.com'
                }
            }
        };
        
        this.metrics = {
            uptime: 0,
            responseTime: [],
            errorCount: 0,
            requestCount: 0,
            lastCheck: null
        };
        
        this.alerts = [];
        this.isRunning = false;
    }
    
    async start() {
        console.log('🔍 بدء نظام المراقبة...');
        
        this.isRunning = true;
        
        // مراقبة دورية
        this.monitoringInterval = setInterval(() => {
            this.performHealthChecks();
        }, this.config.checkInterval);
        
        // مراقبة الأداء
        this.performanceInterval = setInterval(() => {
            this.monitorPerformance();
        }, 300000); // كل 5 دقائق
        
        // مراقبة الأخطاء
        this.errorInterval = setInterval(() => {
            this.checkErrorLogs();
        }, 600000); // كل 10 دقائق
        
        console.log('✅ نظام المراقبة يعمل');
    }
    
    async performHealthChecks() {
        console.log('🏥 إجراء فحوصات الصحة...');
        
        for (const endpoint of this.config.endpoints) {
            try {
                const startTime = Date.now();
                const response = await this.makeRequest(endpoint);
                const responseTime = Date.now() - startTime;
                
                // تسجيل الاستجابة
                this.recordResponse(endpoint, responseTime, response.status);
                
                // فحص الأداء
                if (responseTime > this.config.alertThresholds.responseTime) {
                    await this.sendAlert('performance', {
                        endpoint: endpoint,
                        responseTime: responseTime,
                        threshold: this.config.alertThresholds.responseTime
                    });
                }
                
                // فحص الحالة
                if (response.status !== 200) {
                    await this.sendAlert('availability', {
                        endpoint: endpoint,
                        status: response.status,
                        message: response.statusText
                    });
                }
                
            } catch (error) {
                await this.sendAlert('error', {
                    endpoint: endpoint,
                    error: error.message
                });
            }
        }
        
        this.metrics.lastCheck = new Date();
    }
    
    async monitorPerformance() {
        console.log('📊 مراقبة الأداء...');
        
        try {
            // فحص استخدام الموارد
            const systemStats = await this.getSystemStats();
            
            // فحص CPU
            if (systemStats.cpuUsage > this.config.alertThresholds.cpuUsage) {
                await this.sendAlert('resource', {
                    type: 'CPU',
                    usage: systemStats.cpuUsage,
                    threshold: this.config.alertThresholds.cpuUsage
                });
            }
            
            // فحص الذاكرة
            if (systemStats.memoryUsage > this.config.alertThresholds.memoryUsage) {
                await this.sendAlert('resource', {
                    type: 'Memory',
                    usage: systemStats.memoryUsage,
                    threshold: this.config.alertThresholds.memoryUsage
                });
            }
            
            // فحص التخزين
            if (systemStats.diskUsage > this.config.alertThresholds.diskUsage) {
                await this.sendAlert('resource', {
                    type: 'Disk',
                    usage: systemStats.diskUsage,
                    threshold: this.config.alertThresholds.diskUsage
                });
            }
            
        } catch (error) {
            console.error('❌ خطأ في مراقبة الأداء:', error);
        }
    }
    
    async checkErrorLogs() {
        console.log('🔍 فحص سجلات الأخطاء...');
        
        try {
            // قراءة سجلات الأخطاء
            const errorLogs = await this.readErrorLogs();
            
            // تحليل الأخطاء
            const recentErrors = errorLogs.filter(log => {
                const logTime = new Date(log.timestamp);
                const tenMinutesAgo = new Date(Date.now() - 10 * 60 * 1000);
                return logTime > tenMinutesAgo;
            });
            
            // حساب معدل الأخطاء
            const errorRate = (recentErrors.length / this.metrics.requestCount) * 100;
            
            if (errorRate > this.config.alertThresholds.errorRate) {
                await this.sendAlert('error_rate', {
                    errorRate: errorRate,
                    threshold: this.config.alertThresholds.errorRate,
                    recentErrors: recentErrors.length
                });
            }
            
        } catch (error) {
            console.error('❌ خطأ في فحص سجلات الأخطاء:', error);
        }
    }
    
    async sendAlert(type, data) {
        console.log(`🚨 إرسال تنبيه: ${type}`);
        
        const alert = {
            id: this.generateId(),
            type: type,
            data: data,
            timestamp: new Date(),
            severity: this.getAlertSeverity(type),
            resolved: false
        };
        
        this.alerts.push(alert);
        
        // إرسال عبر تليجرام
        await this.sendTelegramAlert(alert);
        
        // إرسال عبر البريد الإلكتروني للتنبيهات الحرجة
        if (alert.severity === 'critical') {
            await this.sendEmailAlert(alert);
        }
        
        // تسجيل في سجل التنبيهات
        await this.logAlert(alert);
    }
    
    async sendTelegramAlert(alert) {
        const message = this.formatAlertMessage(alert);
        
        try {
            const url = `https://api.telegram.org/bot${this.config.notifications.telegram.botToken}/sendMessage`;
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: this.config.notifications.telegram.chatId,
                    text: message,
                    parse_mode: 'HTML'
                })
            });
            
            if (response.ok) {
                console.log('✅ تم إرسال التنبيه عبر تليجرام');
            }
            
        } catch (error) {
            console.error('❌ فشل إرسال التنبيه عبر تليجرام:', error);
        }
    }
    
    formatAlertMessage(alert) {
        const severityEmoji = {
            'low': '🟡',
            'medium': '🟠',
            'high': '🔴',
            'critical': '🚨'
        };
        
        let message = `${severityEmoji[alert.severity]} تنبيه: ${alert.type}\n\n`;
        message += `⏰ الوقت: ${alert.timestamp.toLocaleString('ar-EG')}\n`;
        message += `🔍 التفاصيل:\n`;
        
        switch (alert.type) {
            case 'performance':
                message += `🌐 الموقع: ${alert.data.endpoint}\n`;
                message += `⏱️ وقت الاستجابة: ${alert.data.responseTime}ms\n`;
                message += `⚠️ الحد المسموح: ${alert.data.threshold}ms\n`;
                break;
                
            case 'availability':
                message += `🌐 الموقع: ${alert.data.endpoint}\n`;
                message += `📊 الحالة: ${alert.data.status}\n`;
                message += `📝 الرسالة: ${alert.data.message}\n`;
                break;
                
            case 'resource':
                message += `💻 النوع: ${alert.data.type}\n`;
                message += `📊 الاستخدام: ${alert.data.usage}%\n`;
                message += `⚠️ الحد المسموح: ${alert.data.threshold}%\n`;
                break;
                
            case 'error':
                message += `🌐 الموقع: ${alert.data.endpoint}\n`;
                message += `❌ الخطأ: ${alert.data.error}\n`;
                break;
                
            case 'error_rate':
                message += `📊 معدل الأخطاء: ${alert.data.errorRate.toFixed(2)}%\n`;
                message += `⚠️ الحد المسموح: ${alert.data.threshold}%\n`;
                message += `🔢 الأخطاء الحديثة: ${alert.data.recentErrors}\n`;
                break;
        }
        
        message += `\n🔗 زيارة الموقع`;
        
        return message;
    }
    
    async getSystemStats() {
        // محاكاة إحصائيات النظام
        // في التطبيق الحقيقي، ستستخدم APIs مثل /proc/stat, /proc/meminfo, etc.
        
        return {
            cpuUsage: Math.random() * 100,
            memoryUsage: Math.random() * 100,
            diskUsage: Math.random() * 100,
            loadAverage: Math.random() * 4,
            uptime: Date.now() - this.startTime
        };
    }
    
    async readErrorLogs() {
        // محاكاة قراءة سجلات الأخطاء
        // في التطبيق الحقيقي، ستقرأ من ملفات السجل الفعلية
        
        return [
            {
                timestamp: new Date(Date.now() - 5 * 60 * 1000),
                level: 'error',
                message: 'Database connection failed',
                stack: 'Error: Connection timeout...'
            },
            {
                timestamp: new Date(Date.now() - 8 * 60 * 1000),
                level: 'warning',
                message: 'Slow query detected',
                query: 'SELECT * FROM orders...'
            }
        ];
    }
    
    recordResponse(endpoint, responseTime, status) {
        this.metrics.requestCount++;
        this.metrics.responseTime.push(responseTime);
        
        // الاحتفاظ بآخر 100 قياس فقط
        if (this.metrics.responseTime.length > 100) {
            this.metrics.responseTime.shift();
        }
        
        if (status !== 200) {
            this.metrics.errorCount++;
        }
    }
    
    getAlertSeverity(type) {
        const severityMap = {
            'performance': 'medium',
            'availability': 'high',
            'resource': 'high',
            'error': 'medium',
            'error_rate': 'high'
        };
        
        return severityMap[type] || 'low';
    }
    
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
    
    async makeRequest(url) {
        const response = await fetch(url);
        return {
            status: response.status,
            statusText: response.statusText,
            headers: response.headers
        };
    }
    
    async logAlert(alert) {
        // تسجيل التنبيه في سجل مخصص
        console.log(`📝 تسجيل التنبيه: ${alert.id}`);
    }
    
    stop() {
        console.log('⏹️ إيقاف نظام المراقبة...');
        
        this.isRunning = false;
        
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
        
        if (this.performanceInterval) {
            clearInterval(this.performanceInterval);
        }
        
        if (this.errorInterval) {
            clearInterval(this.errorInterval);
        }
        
        console.log('✅ تم إيقاف نظام المراقبة');
    }
    
    getMetrics() {
        const avgResponseTime = this.metrics.responseTime.length > 0 
            ? this.metrics.responseTime.reduce((sum, time) => sum + time, 0) / this.metrics.responseTime.length
            : 0;
            
        const errorRate = this.metrics.requestCount > 0 
            ? (this.metrics.errorCount / this.metrics.requestCount) * 100
            : 0;
            
        return {
            uptime: this.metrics.uptime,
            avgResponseTime: avgResponseTime,
            errorRate: errorRate,
            totalRequests: this.metrics.requestCount,
            totalErrors: this.metrics.errorCount,
            activeAlerts: this.alerts.filter(alert => !alert.resolved).length,
            lastCheck: this.metrics.lastCheck
        };
    }
}

// تشغيل نظام المراقبة
const monitoringSystem = new MonitoringSystem();
// monitoringSystem.start();

module.exports = MonitoringSystem;
    
