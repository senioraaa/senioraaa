// WhatsApp Integration
const WHATSAPP_NUMBER = '201234567890'; // رقم الواتساب
const WHATSAPP_API_URL = 'https://api.whatsapp.com/send';

// Send WhatsApp Message
function sendWhatsAppMessage(orderData) {
    const message = formatWhatsAppMessage(orderData);
    const whatsappUrl = `${WHATSAPP_API_URL}?phone=${WHATSAPP_NUMBER}&text=${encodeURIComponent(message)}`;
    
    // Open WhatsApp in new window
    window.open(whatsappUrl, '_blank');
    
    // Track event
    trackEvent('whatsapp_message_sent', {
        platform: orderData.platform,
        type: orderData.type,
        price: orderData.price
    });
}

// Format WhatsApp Message
function formatWhatsAppMessage(orderData) {
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
    
    const message = `
🎮 *طلب جديد من منصة شهد السنيورة*

*تفاصيل الطلب:*
🎯 اللعبة: ${orderData.game}
📱 المنصة: ${orderData.platform}
💎 نوع الحساب: ${typeNames[orderData.type]}
💰 السعر: ${orderData.price} جنيه

*معلومات العميل:*
📞 رقم الهاتف: ${orderData.phone}
💳 طريقة الدفع: ${paymentMethods[orderData.paymentMethod]}
🔢 رقم المحفظة: ${orderData.paymentNumber}

*معلومات الطلب:*
⏰ وقت الطلب: ${getCurrentTime()}
🆔 رقم الطلب: ${generateOrderId()}

*ملاحظات:*
- يرجى التأكد من صحة البيانات
- سيتم التسليم خلال 15 ساعة
- الضمان 6 شهور حسب الشروط

شكراً لثقتكم في منصة شهد السنيورة! 🙏
    `.trim();
    
    return message;
}

// Quick WhatsApp Contact
function quickWhatsAppContact(message = '') {
    const defaultMessage = message || 'مرحباً، أريد الاستفسار عن الألعاب المتاحة';
    const whatsappUrl = `${WHATSAPP_API_URL}?phone=${WHATSAPP_NUMBER}&text=${encodeURIComponent(defaultMessage)}`;
    
    window.open(whatsappUrl, '_blank');
    
    trackEvent('quick_whatsapp_contact');
}

// WhatsApp Support
function whatsAppSupport(orderData = null) {
    let message = 'مرحباً، أحتاج إلى مساعدة من فريق الدعم الفني';
    
    if (orderData) {
        message = `
مرحباً، أحتاج إلى مساعدة بخصوص طلبي:

🎮 اللعبة: ${orderData.game}
📱 المنصة: ${orderData.platform}
💎 نوع الحساب: ${orderData.type}
📞 رقم الهاتف: ${orderData.phone}

يرجى التواصل معي للمساعدة.
        `.trim();
    }
    
    const whatsappUrl = `${WHATSAPP_API_URL}?phone=${WHATSAPP_NUMBER}&text=${encodeURIComponent(message)}`;
    window.open(whatsappUrl, '_blank');
    
    trackEvent('whatsapp_support_request');
}

// WhatsApp FAQ
function whatsAppFAQ(question = '') {
    const faqMessages = {
        'primary-secondary': 'مرحباً، أريد معرفة الفرق بين حساب Primary و Secondary',
        'delivery-time': 'مرحباً، أريد معرفة مدة التسليم',
        'warranty': 'مرحباً، أريد معرفة تفاصيل الضمان',
        'payment': 'مرحباً، أريد معرفة طرق الدفع المتاحة',
        'activation': 'مرحباً، أحتاج مساعدة في تفعيل الحساب'
    };
    
    const message = faqMessages[question] || 'مرحباً، لدي استفسار حول خدماتكم';
    const whatsappUrl = `${WHATSAPP_API_URL}?phone=${WHATSAPP_NUMBER}&text=${encodeURIComponent(message)}`;
    
    window.open(whatsappUrl, '_blank');
    
    trackEvent('whatsapp_faq', { question: question });
}

// WhatsApp Business API (Advanced)
class WhatsAppBusinessAPI {
    constructor(apiKey, phoneNumberId) {
        this.apiKey = apiKey;
        this.phoneNumberId = phoneNumberId;
        this.apiUrl = 'https://graph.facebook.com/v18.0';
    }
    
    async sendMessage(to, message) {
        const response = await fetch(`${this.apiUrl}/${this.phoneNumberId}/messages`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                messaging_product: 'whatsapp',
                to: to,
                type: 'text',
                text: {
                    body: message
                }
            })
        });
        
        return response.json();
    }
    
    async sendTemplate(to, templateName, languageCode = 'ar') {
        const response = await fetch(`${this.apiUrl}/${this.phoneNumberId}/messages`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                messaging_product: 'whatsapp',
                to: to,
                type: 'template',
                template: {
                    name: templateName,
                    language: {
                        code: languageCode
                    }
                }
            })
        });
        
        return response.json();
    }
}

// WhatsApp Chat Widget
function createWhatsAppWidget() {
    const widget = document.createElement('div');
    widget.innerHTML = `


        
;
    
    document.body.appendChild(widget);
    
    // Add click event
    widget.addEventListener('click', function() {
        quickWhatsAppContact();
    });
}

// Initialize WhatsApp Widget
document.addEventListener('DOMContentLoaded', function() {
    createWhatsAppWidget();
});

// WhatsApp Share
function shareToWhatsApp(text, url = '') {
    const shareText = url ? `${text} ${url}` : text;
    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
    
    window.open(whatsappUrl, '_blank');
    
    trackEvent('whatsapp_share', { text: text });
}

// WhatsApp Group Links
const WHATSAPP_GROUPS = {
    customers: 'https://chat.whatsapp.com/XXXXXXXXX',
    support: 'https://chat.whatsapp.com/XXXXXXXXX',
    updates: 'https://chat.whatsapp.com/XXXXXXXXX'
};

function joinWhatsAppGroup(groupType) {
    const groupLink = WHATSAPP_GROUPS[groupType];
    if (groupLink) {
        window.open(groupLink, '_blank');
        trackEvent('whatsapp_group_join', { group: groupType });
    }
}

// WhatsApp Status Updates
function sendStatusUpdate(message) {
    // This would typically be handled by a backend service
    // For now, we'll just log it
    console.log('Status update:', message);
    
    // In a real implementation, this would send to WhatsApp Business API
    // to update the business's status
}

// WhatsApp Broadcast List
function addToWhatsAppBroadcast(phoneNumber) {
    // This would typically be handled by a backend service
    // Store the phone number for broadcast messages
    let broadcastList = JSON.parse(localStorage.getItem('whatsapp_broadcast')) || [];
    
    if (!broadcastList.includes(phoneNumber)) {
        broadcastList.push(phoneNumber);
        localStorage.setItem('whatsapp_broadcast', JSON.stringify(broadcastList));
        
        trackEvent('whatsapp_broadcast_subscribe', { phone: phoneNumber });
    }
}

// WhatsApp Auto-Reply Templates
const AUTO_REPLY_TEMPLATES = {
    welcome: 'مرحباً بك في منصة شهد السنيورة! 🎮\n\nنحن متخصصون في بيع الألعاب الرقمية بأفضل الأسعار.\n\nكيف يمكنني مساعدتك اليوم؟',
    
    business_hours: 'شكراً لتواصلك معنا! 🙏\n\nنحن نعمل من الساعة 9 صباحاً حتى 12 منتصف الليل.\n\nسيتم الرد على رسالتك في أقرب وقت ممكن.',
    
    order_confirmation: 'شكراً لطلبك! ✅\n\nتم استلام طلبك وسيتم معالجته خلال 15 ساعة.\n\nرقم الطلب: {order_id}\n\nسنتواصل معك قريباً!',
    
    delivery_update: 'تحديث حالة الطلب 📦\n\nرقم الطلب: {order_id}\n\nالحالة: {status}\n\nالتفاصيل: {details}'
};

function getAutoReplyTemplate(templateName, variables = {}) {
    let template = AUTO_REPLY_TEMPLATES[templateName];
    
    if (template) {
        // Replace variables in template
        Object.keys(variables).forEach(key => {
            template = template.replace(`{${key}}`, variables[key]);
        });
        
        return template;
    }
    
    return '';
}

// Export functions for global use
window.whatsAppUtils = {
    sendWhatsAppMessage,
    quickWhatsAppContact,
    whatsAppSupport,
    whatsAppFAQ,
    shareToWhatsApp,
    joinWhatsAppGroup,
    addToWhatsAppBroadcast,
    getAutoReplyTemplate
};
    
