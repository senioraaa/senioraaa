// نظام فحص وتطبيق التحديثات التلقائية
class AutoUpdateSystem {
    constructor() {
        this.updateConfig = {
            checkInterval: 3600000, // ساعة واحدة
            sources: {
                github: 'https://api.github.com/repos/senioraaa/senioraaa',
                gamesPrices: 'https://api.shahd-senior.com/prices',
                security: 'https://api.shahd-senior.com/security-updates',
                content: 'https://api.shahd-senior.com/content-updates'
            },
            autoApply: {
                security: true,
                prices: true,
                content: false,
                code: false
            },
            backupBeforeUpdate: true,
            rollbackOnFailure: true
        };
        
        this.updateQueue = [];
        this.updateHistory = [];
        this.isUpdating = false;
        
        this.init();
    }
    
    // تهيئة نظام التحديثات
    init() {
        this.startUpdateScheduler();
        this.setupUpdateListeners();
        this.loadUpdateHistory();
    }
    
    // بدء مجدول التحديثات
    startUpdateScheduler() {
        // فحص التحديثات بشكل دوري
        setInterval(() => {
            this.checkForUpdates();
        }, this.updateConfig.checkInterval);
        
        // فحص فوري عند البدء
        setTimeout(() => {
            this.checkForUpdates();
        }, 5000);
        
        console.log('✅ تم بدء نظام التحديثات التلقائية');
    }
    
    // فحص التحديثات المتاحة
    async checkForUpdates() {
        if (this.isUpdating) {
            console.log('⏳ عملية تحديث قيد التشغيل، الانتظار...');
            return;
        }
        
        try {
            console.log('🔍 فحص التحديثات المتاحة...');
            
            // فحص تحديثات الأمان
            const securityUpdates = await this.checkSecurityUpdates();
            
            // فحص تحديثات الأسعار
            const priceUpdates = await this.checkPriceUpdates();
            
            // فحص تحديثات المحتوى
            const contentUpdates = await this.checkContentUpdates();
            
            // فحص تحديثات الكود
            const codeUpdates = await this.checkCodeUpdates();
            
            // جمع جميع التحديثات
            const allUpdates = [
                ...securityUpdates,
                ...priceUpdates,
                ...contentUpdates,
                ...codeUpdates
            ];
            
            if (allUpdates.length > 0) {
                console.log(`📦 تم العثور على ${allUpdates.length} تحديث`);
                
                // إضافة للقائمة
                this.updateQueue.push(...allUpdates);
                
                // تطبيق التحديثات التلقائية
                await this.processUpdateQueue();
            } else {
                console.log('✅ لا توجد تحديثات جديدة');
            }
            
        } catch (error) {
            console.error('❌ خطأ في فحص التحديثات:', error);
        }
    }
    
    // فحص تحديثات الأمان
    async checkSecurityUpdates() {
        try {
            const response = await fetch(this.updateConfig.sources.security);
            const data = await response.json();
            
            const updates = data.updates || [];
            
            return updates.map(update => ({
                id: update.id,
                type: 'security',
                version: update.version,
                description: update.description,
                severity: update.severity,
                files: update.files,
                autoApply: this.updateConfig.autoApply.security,
                priority: this.getSeverityPriority(update.severity)
            }));
            
        } catch (error) {
            console.error('❌ خطأ في فحص تحديثات الأمان:', error);
            return [];
        }
    }
    
    // فحص تحديثات الأسعار
    async checkPriceUpdates() {
        try {
            const response = await fetch(this.updateConfig.sources.gamesPrices);
            const data = await response.json();
            
            const currentPrices = await this.getCurrentPrices();
            const updates = [];
            
            for (const game of data.games) {
                const currentGame = currentPrices.find(g => g.id === game.id);
                
                if (currentGame && this.hasPriceChanged(currentGame, game)) {
                    updates.push({
                        id: `price_${game.id}_${Date.now()}`,
                        type: 'price',
                        gameId: game.id,
                        gameName: game.name,
                        oldPrices: currentGame.prices,
                        newPrices: game.prices,
                        autoApply: this.updateConfig.autoApply.prices,
                        priority: 2
                    });
                }
            }
            
            return updates;
            
        } catch (error) {
            console.error('❌ خطأ في فحص تحديثات الأسعار:', error);
            return [];
        }
    }
    
    // فحص تحديثات المحتوى
    async checkContentUpdates() {
        try {
            const response = await fetch(this.updateConfig.sources.content);
            const data = await response.json();
            
            const updates = data.updates || [];
            
            return updates.map(update => ({
                id: update.id,
                type: 'content',
                contentType: update.contentType,
                description: update.description,
                files: update.files,
                changes: update.changes,
                autoApply: this.updateConfig.autoApply.content,
                priority: 3
            }));
            
        } catch (error) {
            console.error('❌ خطأ في فحص تحديثات المحتوى:', error);
            return [];
        }
    }
    
    // فحص تحديثات الكود
    async checkCodeUpdates() {
        try {
            const response = await fetch(`${this.updateConfig.sources.github}/releases/latest`);
            const data = await response.json();
            
            const currentVersion = await this.getCurrentVersion();
            
            if (data.tag_name !== currentVersion) {
                return [{
                    id: `code_${data.tag_name}`,
                    type: 'code',
                    version: data.tag_name,
                    description: data.body,
                    downloadUrl: data.zipball_url,
                    assets: data.assets,
                    autoApply: this.updateConfig.autoApply.code,
                    priority: 1
                }];
            }
            
            return [];
            
        } catch (error) {
            console.error('❌ خطأ في فحص تحديثات الكود:', error);
            return [];
        }
    }
    
    // معالجة قائمة التحديثات
    async processUpdateQueue() {
        if (this.updateQueue.length === 0) {
            return;
        }
        
        // ترتيب التحديثات حسب الأولوية
        this.updateQueue.sort((a, b) => a.priority - b.priority);
        
        for (const update of this.updateQueue) {
            if (update.autoApply) {
                await this.applyUpdate(update);
            } else {
                await this.notifyPendingUpdate(update);
            }
        }
        
        // تنظيف القائمة
        this.updateQueue = [];
    }
    
    // تطبيق التحديث
    async applyUpdate(update) {
        this.isUpdating = true;
        
        try {
            console.log(`🔄 بدء تطبيق التحديث: ${update.id}`);
            
            // إنشاء نسخة احتياطية
            if (this.updateConfig.backupBeforeUpdate) {
                await this.createPreUpdateBackup(update);
            }
            
            // تطبيق التحديث حسب النوع
            let result;
            switch (update.type) {
                case 'security':
                    result = await this.applySecurityUpdate(update);
                    break;
                case 'price':
                    result = await this.applyPriceUpdate(update);
                    break;
                case 'content':
                    result = await this.applyContentUpdate(update);
                    break;
                case 'code':
                    result = await this.applyCodeUpdate(update);
                    break;
                default:
                    throw new Error(`نوع تحديث غير مدعوم: ${update.type}`);
            }
            
            if (result.success) {
                // تسجيل النجاح
                update.status = 'applied';
                update.appliedAt = new Date();
                
                this.updateHistory.push(update);
                
                console.log(`✅ تم تطبيق التحديث: ${update.id}`);
                
                // إرسال إشعار نجاح
                await this.sendUpdateNotification(update, 'success');
                
            } else {
                throw new Error(result.error);
            }
            
        } catch (error) {
            console.error(`❌ خطأ في تطبيق التحديث: ${update.id}`, error);
            
            // محاولة التراجع
            if (this.updateConfig.rollbackOnFailure) {
                await this.rollbackUpdate(update);
            }
            
            // تسجيل الفشل
            update.status = 'failed';
            update.error = error.message;
            update.failedAt = new Date();
            
            this.updateHistory.push(update);
            
            // إرسال إشعار خطأ
            await this.sendUpdateNotification(update, 'error');
            
        } finally {
            this.isUpdating = false;
        }
    }
    
    // تطبيق تحديث الأسعار
    async applyPriceUpdate(update) {
        try {
            // تحديث أسعار اللعبة
            const gameData = await this.getGameData(update.gameId);
            
            if (gameData) {
                gameData.prices = update.newPrices;
                await this.updateGameData(update.gameId, gameData);
                
                console.log(`💰 تم تحديث أسعار ${update.gameName}`);
                
                return { success: true };
            } else {
                throw new Error('لم يتم العثور على بيانات اللعبة');
            }
            
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    // تطبيق تحديث الأمان
    async applySecurityUpdate(update) {
        try {
            for (const file of update.files) {
                await this.updateSecurityFile(file);
            }
            
            console.log(`🔒 تم تطبيق تحديث الأمان: ${update.description}`);
            
            return { success: true };
            
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    // تطبيق تحديث المحتوى
    async applyContentUpdate(update) {
        try {
            for (const file of update.files) {
                await this.updateContentFile(file);
            }
            
            console.log(`📄 تم تطبيق تحديث المحتوى: ${update.description}`);
            
            return { success: true };
            
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    // تطبيق تحديث الكود
    async applyCodeUpdate(update) {
        try {
            // تحميل الإصدار الجديد
            const codeBundle = await this.downloadCodeUpdate(update.downloadUrl);
            
            // تطبيق التحديث
            await this.installCodeUpdate(codeBundle);
            
            // تحديث رقم الإصدار
            await this.updateVersion(update.version);
            
            console.log(`🆕 تم تطبيق تحديث الكود: ${update.version}`);
            
            return { success: true };
            
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    // إنشاء نسخة احتياطية قبل التحديث
    async createPreUpdateBackup(update) {
        try {
            const backupName = `pre_update_${update.id}_${Date.now()}`;
            
            // إنشاء نسخة احتياطية
            if (typeof backupManager !== 'undefined') {
                await backupManager.createBackup(backupName, 'pre-update');
            }
            
            console.log(`💾 تم إنشاء نسخة احتياطية قبل التحديث: ${backupName}`);
            
            return backupName;
            
        } catch (error) {
            console.error('❌ خطأ في إنشاء النسخة الاحتياطية:', error);
            throw error;
        }
    }
    
    // التراجع عن التحديث
    async rollbackUpdate(update) {
        try {
            console.log(`🔄 بدء التراجع عن التحديث: ${update.id}`);
            
            const backupName = `pre_update_${update.id}`;
            
            if (typeof backupManager !== 'undefined') {
                await backupManager.restoreBackup(backupName);
            }
            
            console.log(`✅ تم التراجع عن التحديث: ${update.id}`);
            
        } catch (error) {
            console.error(`❌ خطأ في التراجع عن التحديث: ${update.id}`, error);
        }
    }
    
    // إرسال إشعار التحديث
    async sendUpdateNotification(update, status) {
        let message = '';
        
        if (status === 'success') {
            message = `✅ تم تطبيق التحديث بنجاح\n\n`;
            message += `🆔 المعرف: ${update.id}\n`;
            message += `📄 النوع: ${update.type}\n`;
            message += `📝 الوصف: ${update.description || 'غير متاح'}\n`;
            message += `⏰ وقت التطبيق: ${update.appliedAt}`;
        } else if (status === 'error') {
            message = `❌ فشل في تطبيق التحديث\n\n`;
            message += `🆔 المعرف: ${update.id}\n`;
            message += `📄 النوع: ${update.type}\n`;
            message += `🚨 الخطأ: ${update.error}\n`;
            message += `⏰ وقت الفشل: ${update.failedAt}`;
        }
        
        // إرسال الإشعار
        await this.sendNotification(message, status);
    }
    
    // إرسال إشعار التحديث المعلق
    async notifyPendingUpdate(update) {
        const message = `🔔 تحديث جديد متاح\n\n`;
        const details = `🆔 المعرف: ${update.id}\n`;
        const type = `📄 النوع: ${update.type}\n`;
        const description = `📝 الوصف: ${update.description || 'غير متاح'}\n`;
        const action = `⚡ يتطلب تطبيق يدوي`;
        
        const fullMessage = message + details + type + description + action;
        
        await this.sendNotification(fullMessage, 'info');
    }
    
    // الحصول على أولوية الخطورة
    getSeverityPriority(severity) {
        const priorities = {
            'critical': 1,
            'high': 2,
            'medium': 3,
            'low': 4
        };
        
        return priorities[severity] || 4;
    }
    
    // فحص تغيير الأسعار
    hasPriceChanged(current, updated) {
        return JSON.stringify(current.prices) !== JSON.stringify(updated.prices);
    }
    
    // الحصول على تقرير التحديثات
    getUpdateReport() {
        return {
            totalUpdates: this.updateHistory.length,
            successfulUpdates: this.updateHistory.filter(u => u.status === 'applied').length,
            failedUpdates: this.updateHistory.filter(u => u.status === 'failed').length,
            pendingUpdates: this.updateQueue.length,
            lastUpdate: this.updateHistory[this.updateHistory.length - 1],
            nextCheck: new Date(Date.now() + this.updateConfig.checkInterval)
        };
    }
    
    // إيقاف نظام التحديثات
    stopUpdateSystem() {
        this.isUpdating = false;
        console.log('🛑 تم إيقاف نظام التحديثات التلقائية');
    }
}

// تشغيل نظام التحديثات التلقائية
const autoUpdateSystem = new AutoUpdateSystem();

// تصدير للاستخدام العام
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutoUpdateSystem;
}
    
