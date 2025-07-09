// اختبارات الوحدة الشاملة
class UnitTests {
    constructor() {
        this.testResults = [];
        this.passedTests = 0;
        this.failedTests = 0;
    }
    
    // اختبار تحميل بيانات الألعاب
    testLoadGamesData() {
        console.log('🧪 اختبار تحميل بيانات الألعاب...');
        
        fetch('data/games.json')
            .then(response => response.json())
            .then(data => {
                this.assert(data.games, 'بيانات الألعاب موجودة');
                this.assert(data.games.fc25, 'لعبة FC 25 موجودة');
                this.assert(data.games.fc25.platforms, 'منصات اللعبة موجودة');
                this.assert(data.games.fc25.platforms.ps4, 'منصة PS4 موجودة');
                this.assert(data.games.fc25.platforms.ps5, 'منصة PS5 موجودة');
                this.logResult('تحميل بيانات الألعاب', true);
            })
            .catch(error => {
                this.logResult('تحميل بيانات الألعاب', false, error);
            });
    }
    
    // اختبار حساب الأسعار
    testPriceCalculation() {
        console.log('🧪 اختبار حساب الأسعار...');
        
        try {
            const testPrices = {
                ps4: { primary: 50, secondary: 30, full: 80 },
                ps5: { primary: 60, secondary: 40, full: 100 }
            };
            
            // اختبار حساب سعر PS4 Primary
            const ps4Primary = this.calculatePrice('ps4', 'primary', testPrices);
            this.assert(ps4Primary === 50, 'سعر PS4 Primary صحيح');
            
            // اختبار حساب سعر PS5 Full
            const ps5Full = this.calculatePrice('ps5', 'full', testPrices);
            this.assert(ps5Full === 100, 'سعر PS5 Full صحيح');
            
            this.logResult('حساب الأسعار', true);
        } catch (error) {
            this.logResult('حساب الأسعار', false, error);
        }
    }
    
    // اختبار تولید رقم الطلب
    testOrderIdGeneration() {
        console.log('🧪 اختبار تولید رقم الطلب...');
        
        try {
            const orderId1 = this.generateOrderId();
            const orderId2 = this.generateOrderId();
            
            this.assert(orderId1 !== orderId2, 'أرقام الطلبات فريدة');
            this.assert(orderId1.startsWith('SH-'), 'رقم الطلب يبدأ بـ SH-');
            this.assert(orderId1.length > 10, 'رقم الطلب بطول مناسب');
            
            this.logResult('تولید رقم الطلب', true);
        } catch (error) {
            this.logResult('تولید رقم الطلب', false, error);
        }
    }
    
    // اختبار حفظ الطلبات
    testOrderSaving() {
        console.log('🧪 اختبار حفظ الطلبات...');
        
        try {
            const testOrder = {
                id: 'TEST-001',
                gameName: 'FC 25',
                platform: 'PS5',
                price: 60,
                timestamp: new Date().toISOString()
            };
            
            // حفظ الطلب
            this.saveOrder(testOrder);
            
            // استرجاع الطلب
            const savedOrders = this.getOrders();
            const foundOrder = savedOrders.find(o => o.id === 'TEST-001');
            
            this.assert(foundOrder, 'الطلب تم حفظه بنجاح');
            this.assert(foundOrder.gameName === 'FC 25', 'بيانات الطلب صحيحة');
            
            this.logResult('حفظ الطلبات', true);
        } catch (error) {
            this.logResult('حفظ الطلبات', false, error);
        }
    }
    
    // اختبار تنسيق رسائل الواتساب
    testWhatsAppFormatting() {
        console.log('🧪 اختبار تنسيق رسائل الواتساب...');
        
        try {
            const testOrder = {
                id: 'TEST-001',
                gameName: 'FC 25',
                platform: 'PS5',
                accountType: 'primary',
                price: 60,
                customerPhone: '01234567890'
            };
            
            const message = this.formatWhatsAppMessage(testOrder);
            
            this.assert(message.includes('FC 25'), 'الرسالة تحتوي على اسم اللعبة');
            this.assert(message.includes('PS5'), 'الرسالة تحتوي على المنصة');
            this.assert(message.includes('60'), 'الرسالة تحتوي على السعر');
            
            this.logResult('تنسيق رسائل الواتساب', true);
        } catch (error) {
            this.logResult('تنسيق رسائل الواتساب', false, error);
        }
    }
    
    // وظائف مساعدة للاختبار
    calculatePrice(platform, type, prices) {
        return prices[platform][type];
    }
    
    generateOrderId() {
        const timestamp = Date.now().toString(36);
        const random = Math.random().toString(36).substr(2, 5);
        return `SH-${timestamp}-${random}`.toUpperCase();
    }
    
    saveOrder(order) {
        const orders = JSON.parse(localStorage.getItem('orders') || '[]');
        orders.push(order);
        localStorage.setItem('orders', JSON.stringify(orders));
    }
    
    getOrders() {
        return JSON.parse(localStorage.getItem('orders') || '[]');
    }
    
    formatWhatsAppMessage(order) {
        return `
🎮 طلب جديد من منصة شهد السنيورة
🎯 اللعبة: ${order.gameName}
📱 المنصة: ${order.platform}
💰 السعر: ${order.price} جنيه
🆔 رقم الطلب: ${order.id}
        `;
    }
    
    // وظائف الاختبار الأساسية
    assert(condition, message) {
        if (condition) {
            console.log(`✅ ${message}`);
            this.passedTests++;
        } else {
            console.error(`❌ ${message}`);
            this.failedTests++;
            throw new Error(`فشل الاختبار: ${message}`);
        }
    }
    
    logResult(testName, passed, error = null) {
        const result = {
            name: testName,
            passed: passed,
            error: error,
            timestamp: new Date().toISOString()
        };
        
        this.testResults.push(result);
        
        if (passed) {
            console.log(`✅ ${testName} - نجح`);
        } else {
            console.error(`❌ ${testName} - فشل`, error);
        }
    }
    
    // تشغيل جميع الاختبارات
    runAllTests() {
        console.log('🚀 بدء تشغيل جميع الاختبارات...');
        
        this.testLoadGamesData();
        this.testPriceCalculation();
        this.testOrderIdGeneration();
        this.testOrderSaving();
        this.testWhatsAppFormatting();
        
        setTimeout(() => {
            this.generateReport();
        }, 3000);
    }
    
    // تقرير النتائج
    generateReport() {
        console.log('\n📊 تقرير نتائج الاختبارات:');
        console.log(`✅ اختبارات ناجحة: ${this.passedTests}`);
        console.log(`❌ اختبارات فاشلة: ${this.failedTests}`);
        console.log(`📈 نسبة النجاح: ${((this.passedTests / (this.passedTests + this.failedTests)) * 100).toFixed(2)}%`);
        
        return {
            passed: this.passedTests,
            failed: this.failedTests,
            total: this.passedTests + this.failedTests,
            results: this.testResults
        };
    }
}

// إنشاء نسخة من نظام الاختبارات
const unitTests = new UnitTests();

// تشغيل الاختبارات عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    unitTests.runAllTests();
});
