// اختبارات التكامل
class IntegrationTests {
    constructor() {
        this.testResults = [];
    }
    
    // اختبار تكامل الواتساب
    async testWhatsAppIntegration() {
        console.log('🧪 اختبار تكامل الواتساب...');
        
        try {
            const testOrder = {
                id: 'INT-TEST-001',
                gameName: 'FC 25',
                platform: 'PS5',
                accountType: 'primary',
                price: 60,
                customerPhone: '01234567890',
                timestamp: new Date().toISOString()
            };
            
            // اختبار تنسيق الرسالة
            const message = formatOrderMessage(testOrder);
            this.assert(message.length > 0, 'رسالة الواتساب تم تنسيقها');
            
            // اختبار رابط الواتساب
            const whatsappUrl = generateWhatsAppURL(message);
            this.assert(whatsappUrl.includes('wa.me'), 'رابط الواتساب صحيح');
            
            this.logResult('تكامل الواتساب', true);
        } catch (error) {
            this.logResult('تكامل الواتساب', false, error);
        }
    }
    
    // اختبار تكامل تليجرام
    async testTelegramIntegration() {
        console.log('🧪 اختبار تكامل تليجرام...');
        
        try {
            const testOrder = {
                id: 'INT-TEST-002',
                gameName: 'FC 25',
                platform: 'PS5',
                price: 60
            };
            
            // اختبار تنسيق رسالة تليجرام
            const message = formatTelegramMessage(testOrder);
            this.assert(message.includes('طلب جديد'), 'رسالة تليجرام تم تنسيقها');
            
            // اختبار إرسال الرسالة (محاكاة)
            const result = await this.simulateTelegramSend(message);
            this.assert(result.success, 'إرسال رسالة تليجرام نجح');
            
            this.logResult('تكامل تليجرام', true);
        } catch (error) {
            this.logResult('تكامل تليجرام', false, error);
        }
    }
    
    // اختبار تكامل نظام الطلبات
    async testOrderSystemIntegration() {
        console.log('🧪 اختبار تكامل نظام الطلبات...');
        
        try {
            const gameData = {
                gameId: 'fc25',
                gameName: 'FC 25',
                platform: 'ps5',
                accountType: 'primary',
                price: 60
            };
            
            const customerData = {
                phone: '01234567890',
                name: 'عميل تجريبي',
                paymentMethod: 'vodafone'
            };
            
            // إنشاء طلب
            const order = await this.createTestOrder(gameData, customerData);
            this.assert(order.id, 'تم إنشاء الطلب بنجاح');
            
            // اختبار حفظ الطلب
            const savedOrder = await this.getOrderById(order.id);
            this.assert(savedOrder, 'تم حفظ الطلب بنجاح');
            
            // اختبار تحديث حالة الطلب
            const updated = await this.updateOrderStatus(order.id, 'completed');
            this.assert(updated, 'تم تحديث حالة الطلب');
            
            this.logResult('تكامل نظام الطلبات', true);
        } catch (error) {
            this.logResult('تكامل نظام الطلبات', false, error);
        }
    }
    
    // اختبار تكامل طرق الدفع
    async testPaymentIntegration() {
        console.log('🧪 اختبار تكامل طرق الدفع...');
        
        try {
            const paymentData = {
                method: 'vodafone',
                amount: 60,
                currency: 'EGP',
                customerPhone: '01234567890'
            };
            
            // اختبار تحضير بيانات الدفع
            const prepared = await this.preparePaymentData(paymentData);
            this.assert(prepared.method === 'vodafone', 'طريقة الدفع صحيحة');
            
            // اختبار محاكاة الدفع
            const result = await this.simulatePayment(prepared);
            this.assert(result.success, 'عملية الدفع نجحت');
            
            this.logResult('تكامل طرق الدفع', true);
        } catch (error) {
            this.logResult('تكامل طرق الدفع', false, error);
        }
    }
    
    // اختبار تكامل قاعدة البيانات
    async testDatabaseIntegration() {
        console.log('🧪 اختبار تكامل قاعدة البيانات...');
        
        try {
            // اختبار حفظ البيانات
            const testData = {
                key: 'test-integration',
                value: 'test-value',
                timestamp: Date.now()
            };
            
            await this.saveData(testData);
            
            // اختبار استرجاع البيانات
            const retrieved = await this.getData('test-integration');
            this.assert(retrieved.value === 'test-value', 'تم استرجاع البيانات بنجاح');
            
            // اختبار تحديث البيانات
            testData.value = 'updated-value';
            await this.updateData(testData);
            
            const updated = await this.getData('test-integration');
            this.assert(updated.value === 'updated-value', 'تم تحديث البيانات');
            
            // اختبار حذف البيانات
            await this.deleteData('test-integration');
            const deleted = await this.getData('test-integration');
            this.assert(!deleted, 'تم حذف البيانات');
            
            this.logResult('تكامل قاعدة البيانات', true);
        } catch (error) {
            this.logResult('تكامل قاعدة البيانات', false, error);
        }
    }
    
    // وظائف مساعدة للاختبار
    async simulateTelegramSend(message) {
        // محاكاة إرسال رسالة تليجرام
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({ success: true, message: 'تم الإرسال' });
            }, 1000);
        });
    }
    
    async createTestOrder(gameData, customerData) {
        // محاكاة إنشاء طلب
        return {
            id: this.generateOrderId(),
            ...gameData,
            ...customerData,
            status: 'pending',
            timestamp: new Date().toISOString()
        };
    }
    
    async getOrderById(id) {
        // محاكاة استرجاع طلب
        const orders = JSON.parse(localStorage.getItem('orders') || '[]');
        return orders.find(o => o.id === id);
    }
    
    async updateOrderStatus(id, status) {
        // محاكاة تحديث حالة الطلب
        const orders = JSON.parse(localStorage.getItem('orders') || '[]');
        const order = orders.find(o => o.id === id);
        if (order) {
            order.status = status;
            localStorage.setItem('orders', JSON.stringify(orders));
            return true;
        }
        return false;
    }
    
    async preparePaymentData(data) {
        // محاكاة تحضير بيانات الدفع
        return {
            ...data,
            prepared: true,
            timestamp: Date.now()
        };
    }
    
    async simulatePayment(data) {
        // محاكاة عملية الدفع
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({ success: true, transactionId: 'TX-' + Date.now() });
            }, 2000);
        });
    }
    
    async saveData(data) {
        // محاكاة حفظ البيانات
        localStorage.setItem(data.key, JSON.stringify(data));
    }
    
    async getData(key) {
        // محاكاة استرجاع البيانات
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    }
    
    async updateData(data) {
        // محاكاة تحديث البيانات
        localStorage.setItem(data.key, JSON.stringify(data));
    }
    
    async deleteData(key) {
        // محاكاة حذف البيانات
        localStorage.removeItem(key);
    }
    
    generateOrderId() {
        return 'SH-' + Date.now().toString(36).toUpperCase();
    }
    
    assert(condition, message) {
        if (!condition) {
            throw new Error(message);
        }
    }
    
    logResult(testName, passed, error = null) {
        this.testResults.push({
            name: testName,
            passed: passed,
            error: error,
            timestamp: new Date().toISOString()
        });
        
        if (passed) {
            console.log(`✅ ${testName} - نجح`);
        } else {
            console.error(`❌ ${testName} - فشل`, error);
        }
    }
    
    // تشغيل جميع اختبارات التكامل
    async runAllTests() {
        console.log('🚀 بدء تشغيل اختبارات التكامل...');
        
        await this.testWhatsAppIntegration();
        await this.testTelegramIntegration();
        await this.testOrderSystemIntegration();
        await this.testPaymentIntegration();
        await this.testDatabaseIntegration();
        
        this.generateReport();
    }
    
    generateReport() {
        const passed = this.testResults.filter(r => r.passed).length;
        const failed = this.testResults.filter(r => !r.passed).length;
        
        console.log('\n📊 تقرير اختبارات التكامل:');
        console.log(`✅ اختبارات ناجحة: ${passed}`);
        console.log(`❌ اختبارات فاشلة: ${failed}`);
        console.log(`📈 نسبة النجاح: ${((passed / (passed + failed)) * 100).toFixed(2)}%`);
        
        return {
            passed: passed,
            failed: failed,
            total: passed + failed,
            results: this.testResults
        };
    }
}

// إنشاء نسخة من اختبارات التكامل
const integrationTests = new IntegrationTests();
