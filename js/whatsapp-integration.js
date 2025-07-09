      // تكامل الواتساب الكامل class WhatsAppIntegration { constructor() { this.phoneNumber = "+201234567890"; // رقم
      الواتساب this.baseUrl = "https://wa.me/"; this.currentOrder = null; } // إنشاء رسالة طلب منسقة
      createOrderMessage(orderData) { const message = ` 🎮 طلب جديد من منصة شهد السنيورة 📋 تفاصيل الطلب:
      ━━━━━━━━━━━━━━━━━━━━━━━━ 🎯 اللعبة: ${orderData.gameName} 📱 المنصة: ${orderData.platform} 💎 نوع الحساب:
      ${orderData.accountType} 💰 السعر: ${orderData.price} جنيه 📞 طريقة الدفع: ${orderData.paymentMethod} 👤 معلومات
      العميل: ━━━━━━━━━━━━━━━━━━━━━━━━ 📞 رقم الهاتف: ${orderData.customerPhone} 📧 الإيميل: ${orderData.customerEmail
      || 'غير محدد'} 📍 العنوان: ${orderData.customerAddress || 'غير محدد'} ⏰ معلومات الطلب: ━━━━━━━━━━━━━━━━━━━━━━━━
      🕒 وقت الطلب: ${orderData.orderTime} 🆔 رقم الطلب: ${orderData.orderId} 📊 حالة الطلب: في انتظار التأكيد 🔔
      ملاحظات: ━━━━━━━━━━━━━━━━━━━━━━━━ ${orderData.notes || 'لا توجد ملاحظات'} ✅ الخطوات التالية: 1. تأكيد الطلب 2.
      إرسال تفاصيل الدفع 3. تسليم الحساب خلال 15 ساعة 🚀 شكراً لاختياركم منصة شهد السنيورة! `; return message.trim(); }
      // إنشاء رسالة تأكيد الطلب createConfirmationMessage(orderData) { const message = ` ✅ تأكيد طلب رقم:
      ${orderData.orderId} 🎮 ${orderData.gameName} - ${orderData.platform} 💎 نوع الحساب: ${orderData.accountType} 💰
      المبلغ: ${orderData.price} جنيه 📞 طريقة الدفع: ${orderData.paymentMethod}
      ${this.getPaymentInstructions(orderData.paymentMethod)} ⏰ سيتم تسليم الحساب خلال 15 ساعة 🛡️ ضمان حسب نوع الحساب
      المختار 📞 للدعم الفني تواصل معنا على نفس الرقم `; return message.trim(); } // تعليمات الدفع
      getPaymentInstructions(paymentMethod) { const instructions = { 'vodafone-cash': ` 💳 فودافون كاش: - الرقم:
      01234567890 - الاسم: شهد السنيورة - أرسل صورة إيصال الدفع `, 'orange-money': ` 💳 أورانج موني: - الرقم:
      01234567890 - الاسم: شهد السنيورة - أرسل صورة إيصال الدفع `, 'etisalat-cash': ` 💳 اتصالات كاش: - الرقم:
      01234567890 - الاسم: شهد السنيورة - أرسل صورة إيصال الدفع `, 'bank-transfer': ` 💳 تحويل بنكي: - البنك: البنك
      الأهلي المصري - رقم الحساب: 123456789 - الاسم: شهد السنيورة - أرسل صورة إيصال التحويل ` }; return
      instructions[paymentMethod] || 'تعليمات الدفع غير محددة'; } // إرسال الطلب للواتساب sendOrder(orderData) {
      this.currentOrder = orderData; const message = this.createOrderMessage(orderData); const encodedMessage =
      encodeURIComponent(message); const whatsappUrl = `${this.baseUrl}${this.phoneNumber}?text=${encodedMessage}`; //
      حفظ الطلب في localStorage this.saveOrderToStorage(orderData); // فتح الواتساب window.open(whatsappUrl, '_blank');
      // إرسال إشعار للتليجرام this.sendTelegramNotification(orderData); return true; } // حفظ الطلب في التخزين المحلي
      saveOrderToStorage(orderData) { let orders = JSON.parse(localStorage.getItem('orders') || '[]');
      orders.push(orderData); localStorage.setItem('orders', JSON.stringify(orders)); localStorage.setItem('lastOrder',
      JSON.stringify(orderData)); } // استرجاع الطلبات من التخزين getOrdersFromStorage() { return
      JSON.parse(localStorage.getItem('orders') || '[]'); } // تحديث حالة الطلب updateOrderStatus(orderId, status) { let
      orders = this.getOrdersFromStorage(); const orderIndex = orders.findIndex(order => order.orderId === orderId); if
      (orderIndex !== -1) { orders[orderIndex].status = status; orders[orderIndex].lastUpdated = new
      Date().toISOString(); localStorage.setItem('orders', JSON.stringify(orders)); return true; } return false; } //
      إرسال إشعار تليجرام async sendTelegramNotification(orderData) { const telegramBot = new TelegramBot(); await
      telegramBot.sendOrderNotification(orderData); } // إنشاء رابط واتساب مخصص createCustomWhatsAppLink(phone, message)
      { const encodedMessage = encodeURIComponent(message); return `https://wa.me/${phone}?text=${encodedMessage}`; } //
      فحص صحة رقم الواتساب validateWhatsAppNumber(phoneNumber) { const regex = /^(\+201|01)[0-9]{9}$/; return
      regex.test(phoneNumber); } // إنشاء رسالة دعم فني createSupportMessage(issueType, orderData) { const message = `
      🛠️ طلب دعم فني 📋 تفاصيل المشكلة: ━━━━━━━━━━━━━━━━━━━━━━━━ 🔴 نوع المشكلة: ${issueType} 🆔 رقم الطلب:
      ${orderData.orderId} 🎮 اللعبة: ${orderData.gameName} 📱 المنصة: ${orderData.platform} 💎 نوع الحساب:
      ${orderData.accountType} ⏰ وقت الطلب الأصلي: ${orderData.orderTime} 📞 رقم العميل: ${orderData.customerPhone} 📝
      وصف المشكلة: [يرجى وصف المشكلة بالتفصيل] 🚨 حاجة لحل سريع! `; return message.trim(); } } // تهيئة تكامل الواتساب
      عند تحميل الصفحة window.whatsAppIntegration = new WhatsAppIntegration();
