// الوظائف الأساسية لموقع شهد السنيورة

// تحميل البيانات
let gamesData = {};
let currentOrder = {};

// تحميل بيانات الألعاب
async function loadGamesData() {
    try {
        const response = await fetch('data/games.json');
        gamesData = await response.json();
        console.log('تم تحميل بيانات الألعاب بنجاح');
    } catch (error) {
        console.error('خطأ في تحميل بيانات الألعاب:', error);
    }
}

// تحديث الأسعار حسب المنصة المختارة
function updatePrices(platform) {
    const fc25 = gamesData.games.find(game => game.id === 'fc25');
    if (!fc25) return;

    const prices = fc25.prices[platform];
    if (!prices) return;

    // تحديث الأسعار في الجدول
    const priceElements = {
        'primary': document.querySelector('.price-primary'),
        'secondary': document.querySelector('.price-secondary'),
        'full': document.querySelector('.price-full')
    };

    Object.keys(priceElements).forEach(type => {
        const element = priceElements[type];
        if (element) {
            element.textContent = `${prices[type].toLocaleString()} جنيه`;
        }
    });
}

// حساب السعر النهائي
function calculateFinalPrice(platform, accountType) {
    const fc25 = gamesData.games.find(game => game.id === 'fc25');
    if (!fc25) return 0;

    const price = fc25.prices[platform] ? fc25.prices[platform][accountType] : 0;
    return price;
}

// تجهيز بيانات الطلب
function prepareOrderData(platform, accountType) {
    const price = calculateFinalPrice(platform, accountType);
    const platformNames = {
        'ps4': 'PlayStation 4',
        'ps5': 'PlayStation 5',
        'xbox_one': 'Xbox One',
        'xbox_series': 'Xbox Series X/S',
        'pc': 'PC'
    };

    const accountTypeNames = {
        'primary': 'Primary (أساسي)',
        'secondary': 'Secondary (ثانوي)',
        'full': 'Full (كامل)'
    };

    return {
        game: 'FC 25',
        platform: platformNames[platform],
        accountType: accountTypeNames[accountType],
        price: price,
        timestamp: new Date().toLocaleString('ar-EG')
    };
}

// حفظ الطلب محلياً
function saveOrder(orderData) {
    const orders = JSON.parse(localStorage.getItem('orders') || '[]');
    const orderId = Date.now().toString();

    const newOrder = {
        id: orderId,
        ...orderData,
        status: 'pending'
    };

    orders.push(newOrder);
    localStorage.setItem('orders', JSON.stringify(orders));

    return orderId;
}

// إرسال إشعار للتليجرام
async function sendTelegramNotification(orderData) {
    const botToken = 'YOUR_BOT_TOKEN'; // يجب تعديل هذا
    const chatId = 'YOUR_CHAT_ID';     // يجب تعديل هذا

    const message = `
🔔 طلب جديد!
🎮 اللعبة: ${orderData.game}
📱 المنصة: ${orderData.platform}
💎 نوع الحساب: ${orderData.accountType}
💰 السعر: ${orderData.price.toLocaleString()} جنيه
📞 العميل: ${orderData.customerPhone || 'غير محدد'}
⏰ الوقت: ${orderData.timestamp}

يرجى التواصل مع العميل فوراً!
    `;

    try {
        const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: chatId,
                text: message,
                parse_mode: 'HTML'
            })
        });

        if (response.ok) {
            console.log('تم إرسال الإشعار للتليجرام بنجاح');
        } else {
            console.error('فشل في إرسال الإشعار للتليجرام');
        }
    } catch (error) {
        console.error('خطأ في إرسال الإشعار:', error);
    }
}

// إنشاء رسالة واتساب
function createWhatsAppMessage(orderData) {
    const message = `
مرحباً! أريد طلب:

🎮 اللعبة: ${orderData.game}
📱 المنصة: ${orderData.platform}
💎 نوع الحساب: ${orderData.accountType}
💰 السعر: ${orderData.price.toLocaleString()} جنيه

وقت الطلب: ${orderData.timestamp}

يرجى التواصل معي لتأكيد الطلب.
    `;

    return encodeURIComponent(message);
}

// فتح واتساب
function openWhatsApp(orderData) {
    const phoneNumber = '201234567890'; // يجب تعديل هذا
    const message = createWhatsAppMessage(orderData);
    const whatsappUrl = `https://wa.me/${phoneNumber}?text=${message}`;

    window.open(whatsappUrl, '_blank');
}

// معالج الطلب الرئيسي
async function processOrder(platform, accountType, customerInfo = {}) {
    try {
        // تجهيز بيانات الطلب
        const orderData = prepareOrderData(platform, accountType);
        orderData.customerPhone = customerInfo.phone || '';
        orderData.customerName = customerInfo.name || '';

        // حفظ الطلب
        const orderId = saveOrder(orderData);
        orderData.orderId = orderId;

        // إرسال الإشعار للتليجرام
        await sendTelegramNotification(orderData);

        // فتح واتساب
        openWhatsApp(orderData);

        // إظهار رسالة تأكيد
        showOrderConfirmation(orderId);

    } catch (error) {
        console.error('خطأ في معالجة الطلب:', error);
        alert('حدث خطأ في معالجة الطلب. يرجى المحاولة مرة أخرى.');
    }
}

// إظهار رسالة تأكيد الطلب
function showOrderConfirmation(orderId) {
    const confirmationMessage = `
        تم إنشاء طلبك بنجاح!
        رقم الطلب: ${orderId}

        سيتم التواصل معك خلال 15 دقيقة.
    `;

    alert(confirmationMessage);
}

// تهيئة الموقع عند التحميل
document.addEventListener('DOMContentLoaded', function () {
    loadGamesData();

    // إضافة أحداث النقر للأزرار
    document.querySelectorAll('.order-btn').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();

            const platform = this.dataset.platform;
            const accountType = this.dataset.accountType;

            if (platform && accountType) {
                processOrder(platform, accountType);
            }
        });
    });
});

// وظائف مساعدة
function formatPrice(price) {
    return price.toLocaleString('ar-EG') + ' جنيه';
}

function validatePhoneNumber(phone) {
    const phoneRegex = /^(01)[0-9]{9}$/;
    return phoneRegex.test(phone);
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// تصدير الوظائف للاستخدام في ملفات أخرى
window.ShahdSenior = {
    loadGamesData,
    updatePrices,
    calculateFinalPrice,
    processOrder,
    sendTelegramNotification,
    formatPrice,
    validatePhoneNumber,
    validateEmail
};
