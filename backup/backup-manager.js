// نظام إدارة النسخ الاحتياطي الشامل
class BackupManager {
    constructor() {
        this.backupConfig = {
            retention: {
                daily: 7,     // الاحتفاظ بـ 7 نسخ يومية
                weekly: 4,    // الاحتفاظ بـ 4 نسخ أسبوعية
                monthly: 12   // الاحتفاظ بـ 12 نسخة شهرية
            },
            destinations: {
                local: 'backups/',
                cloud: {
                    provider: 'google-drive',
                    bucket: 'shahd-senior-backups',
                    accessKey: 'YOUR_ACCESS_KEY',
                    secretKey: 'YOUR_SECRET_KEY'
                }
            },
            compression: {
                enabled: true,
                level: 6,
                format: 'zip'
            },
            encryption: {
                enabled: true,
                algorithm: 'AES-256',
                key: 'YOUR_ENCRYPTION_KEY'
            }
        };
        
        this.backupQueue = [];
        this.backupHistory = [];
        this.isBackupRunning = false;
        
        this.init();
    }
    
    // تهيئة نظام النسخ الاحتياطي
    init() {
        this.loadBackupHistory();
        this.scheduleBackups();
        this.startBackupProcessor();
        this.setupBackupMonitoring();
    }
    
    // جدولة النسخ الاحتياطي
    scheduleBackups() {
        // نسخ يومية في الساعة 3:00 صباحاً
        this.scheduleDailyBackup('03:00');
        
        // نسخ أسبوعية يوم الأحد في الساعة 2:00 صباحاً
        this.scheduleWeeklyBackup('sunday', '02:00');
        
        // نسخ شهرية في أول يوم من كل شهر
        this.scheduleMonthlyBackup(1, '01:00');
    }
    
    // جدولة النسخ اليومية
    scheduleDailyBackup(time) {
        const [hours, minutes] = time.split(':');
        const now = new Date();
        const scheduledTime = new Date(now);
        scheduledTime.setHours(parseInt(hours), parseInt(minutes), 0, 0);
        
        // إذا كان الوقت قد مر اليوم، اجعله غداً
        if (scheduledTime <= now) {
            scheduledTime.setDate(scheduledTime.getDate() + 1);
        }
        
        const timeUntilBackup = scheduledTime - now;
        
        setTimeout(() => {
            this.createDailyBackup();
            // إعادة جدولة للغد
            this.scheduleDailyBackup(time);
        }, timeUntilBackup);
        
        console.log(`📅 تم جدولة النسخ اليومية في الساعة ${time}`);
    }
    
    // إنشاء نسخة احتياطية يومية
    async createDailyBackup() {
        try {
            const timestamp = new Date().toISOString().split('T')[0];
            const backupName = `daily_backup_${timestamp}`;
            
            await this.createBackup(backupName, 'daily');
            
            // تنظيف النسخ اليومية القديمة
            await this.cleanupOldBackups('daily');
            
        } catch (error) {
            console.error('❌ خطأ في إنشاء النسخة اليومية:', error);
        }
    }
    
    // إنشاء نسخة احتياطية شاملة
    async createBackup(backupName, type = 'manual') {
        if (this.isBackupRunning) {
            console.log('⏳ نسخة احتياطية قيد التشغيل، الانتظار...');
            return;
        }
        
        this.isBackupRunning = true;
        
        try {
            console.log(`🚀 بدء إنشاء نسخة احتياطية: ${backupName}`);
            
            const backup = {
                name: backupName,
                type: type,
                startTime: new Date(),
                status: 'running',
                components: {
                    database: false,
                    files: false,
                    configs: false,
                    uploads: false
                }
            };
            
            // إنشاء مجلد النسخة الاحتياطية
            const backupPath = await this.createBackupDirectory(backupName);
            
            // نسخ قاعدة البيانات
            await this.backupDatabase(backupPath);
            backup.components.database = true;
            
            // نسخ الملفات الأساسية
            await this.backupSourceFiles(backupPath);
            backup.components.files = true;
            
            // نسخ الإعدادات
            await this.backupConfigs(backupPath);
            backup.components.configs = true;
            
            // نسخ الملفات المرفوعة
            await this.backupUploads(backupPath);
            backup.components.uploads = true;
            
            // ضغط النسخة الاحتياطية
            const compressedPath = await this.compressBackup(backupPath);
            
            // تشفير النسخة الاحتياطية
            if (this.backupConfig.encryption.enabled) {
                await this.encryptBackup(compressedPath);
            }
            
            // رفع للتخزين السحابي
            await this.uploadToCloud(compressedPath);
            
            // تحديث حالة النسخة الاحتياطية
            backup.status = 'completed';
            backup.endTime = new Date();
            backup.size = await this.getBackupSize(compressedPath);
            backup.path = compressedPath;
            
            // إضافة للتاريخ
            this.backupHistory.push(backup);
            this.saveBackupHistory();
            
            console.log(`✅ تم إنشاء النسخة الاحتياطية: ${backupName}`);
            
            // إرسال إشعار نجاح
            await this.sendBackupNotification(backup, 'success');
            
            return backup;
            
        } catch (error) {
            console.error(`❌ خطأ في إنشاء النسخة الاحتياطية: ${backupName}`, error);
            
            // إرسال إشعار خطأ
            await this.sendBackupNotification({ name: backupName, error: error.message }, 'error');
            
            throw error;
            
        } finally {
            this.isBackupRunning = false;
        }
    }
    
    // نسخ قاعدة البيانات
    async backupDatabase(backupPath) {
        try {
            console.log('💾 نسخ قاعدة البيانات...');
            
            // تصدير بيانات الألعاب
            const gamesData = await this.exportGamesData();
            await this.saveToFile(`${backupPath}/games.json`, JSON.stringify(gamesData, null, 2));
            
            // تصدير بيانات الطلبات
            const ordersData = await this.exportOrdersData();
            await this.saveToFile(`${backupPath}/orders.json`, JSON.stringify(ordersData, null, 2));
            
            // تصدير بيانات العملاء
            const customersData = await this.exportCustomersData();
            await this.saveToFile(`${backupPath}/customers.json`, JSON.stringify(customersData, null, 2));
            
            // تصدير الإعدادات
            const settingsData = await this.exportSettingsData();
            await this.saveToFile(`${backupPath}/settings.json`, JSON.stringify(settingsData, null, 2));
            
            console.log('✅ تم نسخ قاعدة البيانات');
            
        } catch (error) {
            console.error('❌ خطأ في نسخ قاعدة البيانات:', error);
            throw error;
        }
    }
    
    // نسخ الملفات الأساسية
    async backupSourceFiles(backupPath) {
        try {
            console.log('📁 نسخ الملفات الأساسية...');
            
            const sourceFiles = [
                'index.html',
                'fc25.html',
                'faq.html',
                'terms.html',
                'contact.html',
                'css/',
                'js/',
                'images/',
                'data/'
            ];
            
            for (const file of sourceFiles) {
                await this.copyFile(file, `${backupPath}/source/${file}`);
            }
            
            console.log('✅ تم نسخ الملفات الأساسية');
            
        } catch (error) {
            console.error('❌ خطأ في نسخ الملفات الأساسية:', error);
            throw error;
        }
    }
    
    // نسخ الإعدادات
    async backupConfigs(backupPath) {
        try {
            console.log('⚙️ نسخ الإعدادات...');
            
            const configs = {
                maintenance: this.backupConfig,
                security: await this.getSecurityConfig(),
                performance: await this.getPerformanceConfig(),
                notifications: await this.getNotificationConfig()
            };
            
            await this.saveToFile(`${backupPath}/configs.json`, JSON.stringify(configs, null, 2));
            
            console.log('✅ تم نسخ الإعدادات');
            
        } catch (error) {
            console.error('❌ خطأ في نسخ الإعدادات:', error);
            throw error;
        }
    }
    
    // ضغط النسخة الاحتياطية
    async compressBackup(backupPath) {
        try {
            console.log('📦 ضغط النسخة الاحتياطية...');
            
            const compressedPath = `${backupPath}.${this.backupConfig.compression.format}`;
            
            // هنا يتم تطبيق ضغط المجلد
            await this.zipDirectory(backupPath, compressedPath);
            
            // حذف المجلد الأصلي
            await this.deleteDirectory(backupPath);
            
            console.log('✅ تم ضغط النسخة الاحتياطية');
            
            return compressedPath;
            
        } catch (error) {
            console.error('❌ خطأ في ضغط النسخة الاحتياطية:', error);
            throw error;
        }
    }
    
    // تشفير النسخة الاحتياطية
    async encryptBackup(filePath) {
        try {
            console.log('🔐 تشفير النسخة الاحتياطية...');
            
            const encryptedPath = `${filePath}.encrypted`;
            
            // هنا يتم تطبيق التشفير
            await this.encryptFile(filePath, encryptedPath, this.backupConfig.encryption.key);
            
            // حذف الملف غير المشفر
            await this.deleteFile(filePath);
            
            console.log('✅ تم تشفير النسخة الاحتياطية');
            
            return encryptedPath;
            
        } catch (error) {
            console.error('❌ خطأ في تشفير النسخة الاحتياطية:', error);
            throw error;
        }
    }
    
    // رفع للتخزين السحابي
    async uploadToCloud(filePath) {
        try {
            console.log('☁️ رفع للتخزين السحابي...');
            
            const cloudConfig = this.backupConfig.destinations.cloud;
            const fileName = filePath.split('/').pop();
            
            // هنا يتم تطبيق الرفع للتخزين السحابي
            const uploadResult = await this.uploadFile(filePath, `${cloudConfig.bucket}/${fileName}`);
            
            if (uploadResult.success) {
                console.log('✅ تم رفع النسخة الاحتياطية للتخزين السحابي');
                return uploadResult.url;
            } else {
                throw new Error('فشل في رفع النسخة الاحتياطية');
            }
            
        } catch (error) {
            console.error('❌ خطأ في رفع النسخة الاحتياطية:', error);
            throw error;
        }
    }
    
    // تنظيف النسخ القديمة
    async cleanupOldBackups(type) {
        try {
            const retention = this.backupConfig.retention[type];
            const oldBackups = this.backupHistory
                .filter(backup => backup.type === type)
                .sort((a, b) => new Date(b.startTime) - new Date(a.startTime))
                .slice(retention);
            
            for (const backup of oldBackups) {
                await this.deleteBackup(backup);
                console.log(`🗑️ تم حذف النسخة الاحتياطية القديمة: ${backup.name}`);
            }
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف النسخ القديمة:', error);
        }
    }
    
    // استعادة نسخة احتياطية
    async restoreBackup(backupName) {
        try {
            console.log(`🔄 بدء استعادة النسخة الاحتياطية: ${backupName}`);
            
            const backup = this.backupHistory.find(b => b.name === backupName);
            if (!backup) {
                throw new Error('النسخة الاحتياطية غير موجودة');
            }
            
            // تحميل النسخة الاحتياطية
            const backupPath = await this.downloadBackup(backup);
            
            // فك التشفير
            if (this.backupConfig.encryption.enabled) {
                await this.decryptBackup(backupPath);
            }
            
            // فك الضغط
            const extractedPath = await this.extractBackup(backupPath);
            
            // استعادة قاعدة البيانات
            await this.restoreDatabase(extractedPath);
            
            // استعادة الملفات
            await this.restoreFiles(extractedPath);
            
            // استعادة الإعدادات
            await this.restoreConfigs(extractedPath);
            
            console.log(`✅ تم استعادة النسخة الاحتياطية: ${backupName}`);
            
        } catch (error) {
            console.error(`❌ خطأ في استعادة النسخة الاحتياطية: ${backupName}`, error);
            throw error;
        }
    }
    
    // إرسال إشعار النسخ الاحتياطي
    async sendBackupNotification(backup, status) {
        let message = '';
        
        if (status === 'success') {
            message = `✅ تم إنشاء النسخة الاحتياطية بنجاح\n\n`;
            message += `📄 اسم النسخة: ${backup.name}\n`;
            message += `📊 الحجم: ${backup.size || 'غير محدد'}\n`;
            message += `⏰ وقت الإنشاء: ${backup.startTime}\n`;
            message += `⏱️ وقت الانتهاء: ${backup.endTime}\n`;
        } else {
            message = `❌ فشل في إنشاء النسخة الاحتياطية\n\n`;
            message += `📄 اسم النسخة: ${backup.name}\n`;
            message += `🚨 الخطأ: ${backup.error}\n`;
        }
        
        // إرسال الإشعار
        await this.sendNotification(message, status);
    }
    
    // الحصول على تقرير النسخ الاحتياطي
    getBackupReport() {
        return {
            totalBackups: this.backupHistory.length,
            successfulBackups: this.backupHistory.filter(b => b.status === 'completed').length,
            failedBackups: this.backupHistory.filter(b => b.status === 'failed').length,
            lastBackup: this.backupHistory[this.backupHistory.length - 1],
            totalSize: this.backupHistory.reduce((total, backup) => total + (backup.size || 0), 0),
            nextScheduledBackup: this.getNextScheduledBackup()
        };
    }
}

// تشغيل نظام النسخ الاحتياطي
const backupManager = new BackupManager();

// تصدير للاستخدام العام
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BackupManager;
}
    
