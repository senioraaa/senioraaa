// Telegram Bot Integration
const TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'; // يجب استبداله بالتوكن الحقيقي
const TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID_HERE'; // يجب استبداله بـ Chat ID الحقيقي
const TELEGRAM_API_URL = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}`;

// Send Telegram Notification
async function sendTelegramNotification(orderData) {
    try {
        const message = formatTelegramMessage(orderData);
        
        const response = await fetch(`${TELEGRAM_API_URL}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML',
                disable_web_page_preview: true
            })
        });
        
        const result = await response.json();
        
        if (result.ok) {
            console.log('Telegram notification sent successfully');
            trackEvent('telegram_notification_sent', {
                order_id: orderData.id,
                platform: orderData.platform,
                type: orderData.type
            });
        } else {
            console.error('Telegram notification failed:', result.description);
        }
        
        return result;
    } catch (error) {
        console.error('Error sending Telegram notification:', error);
        return null;
    }
}

// Format Telegram Message
function formatTelegramMessage(orderData) {
    const paymentMethods = {
        vodafone: 'فودافون كاش',
        orange: 'أورانج موني',
        etisalat: 'إتصالات كاش'
    };
    
    const typeNames = {
        primary: 'Primary (أساسي)',
        secondary: 'Secondary (ثانوي)',
        full: 'Full (كامل)'
    };
    
    const orderId = generateOrderId();
    const currentTime = getCurrentTime();
    
    const message = `
🚨 طلب جديد من منصة شهد السنيورة

🎮 تفاصيل الطلب:
🎯 اللعبة: ${orderData.game}
📱 المنصة: ${orderData.platform}
💎 نوع الحساب: ${typeNames[orderData.type]}
💰 السعر: ${orderData.price} جنيه

👤 معلومات العميل:
📞 رقم الهاتف: ${orderData.phone}
💳 طريقة الدفع: ${paymentMethods[orderData.paymentMethod]}
🔢 رقم المحفظة: ${orderData.paymentNumber}

📋 معلومات الطلب:
🆔 رقم الطلب: ${orderId}
⏰ وقت الطلب: ${currentTime}
🌐 المصدر: موقع شهد السنيورة

⚡ حالة الطلب: جديد - في انتظار المعالجة
🎯 الأولوية: عادية
📊 رقم الطلب اليومي: ${getDailyOrderNumber()}

---
✅ يرجى معالجة الطلب خلال 15 ساعة
💬 للتواصل مع العميل: /contact_${orderId}
    `.trim();
    
    return message;
}

// Send Telegram Photo
async function sendTelegramPhoto(photoUrl, caption = '') {
    try {
        const response = await fetch(`${TELEGRAM_API_URL}/sendPhoto`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                photo: photoUrl,
                caption: caption,
                parse_mode: 'HTML'
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending Telegram photo:', error);
        return null;
    }
}

// Send Telegram Document
async function sendTelegramDocument(documentUrl, caption = '') {
    try {
        const response = await fetch(`${TELEGRAM_API_URL}/sendDocument`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                document: documentUrl,
                caption: caption,
                parse_mode: 'HTML'
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending Telegram document:', error);
        return null;
    }
}

// Send Order Status Update
async function sendOrderStatusUpdate(orderData, newStatus, details = '') {
    const statusMessages = {
        processing: '🔄 تتم معالجة الطلب',
        ready: '✅ الطلب جاهز للتسليم',
        delivered: '📦 تم تسليم الطلب',
        cancelled: '❌ تم إلغاء الطلب',
        refunded: '💰 تم استرداد المبلغ'
    };
    
    const message = `
🔔 تحديث حالة الطلب

🆔 رقم الطلب: ${orderData.id}
👤 العميل: ${orderData.phone}
🎮 المنتج: ${orderData.game} - ${orderData.platform}

📊 الحالة الجديدة: ${statusMessages[newStatus]}
📝 التفاصيل: ${details}
⏰ وقت التحديث: ${getCurrentTime()}

---
${newStatus === 'ready' ? '⚡ يرجى إشعار العميل بجاهزية الطلب' : ''}
${newStatus === 'delivered' ? '🎉 تم إنجاز الطلب بنجاح' : ''}
    `.trim();
    
    try {
        const response = await fetch(`${TELEGRAM_API_URL}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML',
                disable_web_page_preview: true
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending status update:', error);
        return null;
    }
}

// Send Daily Report
async function sendDailyReport() {
    const today = new Date().toISOString().split('T')[0];
    const orders = JSON.parse(localStorage.getItem('orders')) || [];
    const todayOrders = orders.filter(order => order.timestamp.startsWith(today));
    
    const totalOrders = todayOrders.length;
    const totalRevenue = todayOrders.reduce((sum, order) => sum + order.price, 0);
    const platformStats = {};
    const typeStats = {};
    
    todayOrders.forEach(order => {
        platformStats[order.platform] = (platformStats[order.platform] || 0) + 1;
        typeStats[order.type] = (typeStats[order.type] || 0) + 1;
    });
    
    const platformStatsText = Object.entries(platformStats)
        .map(([platform, count]) => `${platform}: ${count}`)
        .join('\n');
    
    const typeStatsText = Object.entries(typeStats)
        .map(([type, count]) => `${type}: ${count}`)
        .join('\n');
    
    const message = `
📊 تقرير يومي - منصة شهد السنيورة

📅 التاريخ: ${today}
📈 إجمالي الطلبات: ${totalOrders}
💰 إجمالي الإيرادات: ${totalRevenue} جنيه

📱 الطلبات حسب المنصة:
${platformStatsText || 'لا توجد طلبات'}

💎 الطلبات حسب نوع الحساب:
${typeStatsText || 'لا توجد طلبات'}

⏰ وقت التقرير: ${getCurrentTime()}

---
${totalOrders > 0 ? '🎉 يوم مثمر!' : '📈 نتطلع لمزيد من الطلبات'}
    `.trim();
    
    try {
        const response = await fetch(`${TELEGRAM_API_URL}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML',
                disable_web_page_preview: true
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending daily report:', error);
        return null;
    }
}

// Send Low Stock Alert
async function sendLowStockAlert(game, platform, currentStock) {
    const message = `
⚠️ تنبيه مخزون منخفض

🎮 اللعبة: ${game}
📱 المنصة: ${platform}
📊 المخزون الحالي: ${currentStock}

🔄 الإجراء المطلوب:
- تجديد المخزون
- إشعار المزودين
- تحديث الأسعار إذا لزم الأمر

⏰ وقت التنبيه: ${getCurrentTime()}

---
🚨 يرجى التحرك السريع لتجديد المخزون
    `.trim();
    
    try {
        const response = await fetch(`${TELEGRAM_API_URL}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML',
                disable_web_page_preview: true
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending low stock alert:', error);
        return null;
    }
}

// Send Error Alert
async function sendErrorAlert(errorType, errorMessage, errorDetails = '') {
    const message = `
🚨 تنبيه خطأ في النظام

🔴 نوع الخطأ: ${errorType}
📄 رسالة الخطأ: ${errorMessage}
📋 التفاصيل: ${errorDetails}

🌐 الصفحة: ${window.location.href}
🕒 وقت الخطأ: ${getCurrentTime()}
👤 المستخدم: ${navigator.userAgent}

---
⚡ يرجى التحقق من النظام فوراً
    `.trim();
    
    try {
        const response = await fetch(`${TELEGRAM_API_URL}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: message,
                parse_mode: 'HTML',
                disable_web_page_preview: true
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending error alert:', error);
        return null;
    }
}

// Get Daily Order Number
function getDailyOrderNumber() {
    const today = new Date().toISOString().split('T')[0];
    const orders = JSON.parse(localStorage.getItem('orders')) || [];
    const todayOrders = orders.filter(order => order.timestamp.startsWith(today));
    
    return todayOrders.length + 1;
}

// Setup Telegram Bot Commands
function setupTelegramCommands() {
    const commands = [
        { command: 'start', description: 'بدء التفاعل مع البوت' },
        { command: 'help', description: 'عرض قائمة الأوامر' },
        { command: 'orders', description: 'عرض الطلبات الحالية' },
        { command: 'stats', description: 'عرض الإحصائيات' },
        { command: 'report', description: 'إرسال تقرير يومي' },
        { command: 'settings', description: 'إعدادات البوت' }
    ];
    
    // This would typically be called from a backend service
    console.log('Telegram bot commands:', commands);
}

// Initialize Telegram Integration
function initializeTelegram() {
    // Set up error handling
    window.addEventListener('error', function(e) {
        sendErrorAlert('JavaScript Error', e.message, e.filename + ':' + e.lineno);
    });
    
    // Set up unhandled promise rejection handling
    window.addEventListener('unhandledrejection', function(e) {
        sendErrorAlert('Unhandled Promise Rejection', e.reason);
    });
    
    // Schedule daily report (would typically be handled by backend)
    // For demonstration purposes only
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    
    const msUntilMidnight = tomorrow.getTime() - now.getTime();
    
    setTimeout(() => {
        sendDailyReport();
        
        // Then schedule it to run every 24 hours
        setInterval(sendDailyReport, 24 * 60 * 60 * 1000);
    }, msUntilMidnight);
}

// Telegram Bot Webhook Handler (for backend implementation)
async function handleTelegramWebhook(update) {
    try {
        if (update.message) {
            const message = update.message;
            const chatId = message.chat.id;
            const text = message.text;
            
            if (text.startsWith('/')) {
                // Handle commands
                const command = text.split(' ')[0].replace('/', '');
                await handleTelegramCommand(command, chatId, message);
            } else {
                // Handle regular messages
                await handleTelegramMessage(text, chatId, message);
            }
        }
    } catch (error) {
        console.error('Error handling Telegram webhook:', error);
    }
}

// Handle Telegram Commands
async function handleTelegramCommand(command, chatId, message) {
    let response = '';
    
    switch (command) {
        case 'start':
            response = `
مرحباً! أنا بوت منصة شهد السنيورة 🎮

يمكنني مساعدتك في:
• تتبع الطلبات الجديدة
• عرض الإحصائيات
• إرسال التقارير اليومية
• إدارة المخزون

استخدم /help لعرض جميع الأوامر المتاحة.
            `;
            break;
            
        case 'help':
            response = `
📋 الأوامر المتاحة:

/start - بدء التفاعل مع البوت
/orders - عرض الطلبات الحالية  
/stats - عرض الإحصائيات
/report - إرسال تقرير يومي
/settings - إعدادات البوت

💡 نصائح:
• استخدم الأوامر في أي وقت
• ستتلقى إشعارات تلقائية عند وصول طلبات جديدة
• التقارير اليومية ترسل تلقائياً في منتصف الليل
            `;
            break;
            
        case 'orders':
            const orders = JSON.parse(localStorage.getItem('orders')) || [];
            const pendingOrders = orders.filter(order => order.status === 'pending');
            
            if (pendingOrders.length > 0) {
                response = `📋 الطلبات المعلقة (${pendingOrders.length}):\n\n`;
                pendingOrders.slice(0, 10).forEach((order, index) => {
                    response += `${index + 1}. ${order.game} - ${order.platform} (${order.price} جنيه)\n`;
                });
            } else {
                response = '✅ لا توجد طلبات معلقة حالياً';
            }
            break;
            
        default:
            response = 'أمر غير معروف. استخدم /help لعرض الأوامر المتاحة.';
    }
    
    await sendTelegramMessage(chatId, response);
}

// Send Telegram Message
async function sendTelegramMessage(chatId, text) {
    try {
        const response = await fetch(`${TELEGRAM_API_URL}/sendMessage`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: chatId,
                text: text,
                parse_mode: 'HTML',
                disable_web_page_preview: true
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error sending Telegram message:', error);
        return null;
    }
}

// Initialize Telegram when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeTelegram();
    setupTelegramCommands();
});

// Export functions for global use
window.telegramUtils = {
    sendTelegramNotification,
    sendOrderStatusUpdate,
    sendDailyReport,
    sendLowStockAlert,
    sendErrorAlert,
    handleTelegramWebhook
};
    
