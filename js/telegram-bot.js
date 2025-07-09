      // بوت تليجرام للإشعارات class TelegramBot { constructor() { this.botToken = 'YOUR_BOT_TOKEN_HERE'; // ضع التوكن
      الخاص بك هنا this.chatId = 'YOUR_CHAT_ID_HERE'; // ضع معرف المحادثة هنا this.apiUrl =
      `https://api.telegram.org/bot${this.botToken}`; this.isEnabled = false; this.init(); } // تهيئة البوت async init()
      { try { // التحقق من صحة التوكن const isValid = await this.validateBot(); if (isValid) { this.isEnabled = true;
      console.log('✅ تم تهيئة بوت تليجرام بنجاح'); } else { console.warn('⚠️ فشل في تهيئة بوت تليجرام - تحقق من
      التوكن'); } } catch (error) { console.error('❌ خطأ في تهيئة بوت تليجرام:', error); } } // التحقق من صحة البوت
      async validateBot() { try { const response = await fetch(`${this.apiUrl}/getMe`); const data = await
      response.json(); return data.ok; } catch (error) { return false; } } // إرسال رسالة أساسية async sendMessage(text,
      chatId = this.chatId) { if (!this.isEnabled) { console.warn('⚠️ بوت تليجرام غير مفعل'); return false; } try {
      const response = await fetch(`${this.apiUrl}/sendMessage`, { method: 'POST', headers: { 'Content-Type':
      'application/json', }, body: JSON.stringify({ chat_id: chatId, text: text, parse_mode: 'HTML' }) }); const data =
      await response.json(); return data.ok; } catch (error) { console.error('خطأ في إرسال رسالة تليجرام:', error);
      return false; } } // إرسال إشعار طلب جديد async sendOrderNotification(orderData) { const message =
      this.formatOrderMessage(orderData); return await this.sendMessage(message); } // تنسيق رسالة الطلب
      formatOrderMessage(orderData) { const message = ` 🚨 طلب جديد - منصة شهد السنيورة

      📋 تفاصيل الطلب: ━━━━━━━━━━━━━━━━━━━━━━━━ 🆔 رقم الطلب: ${orderData.orderId} 🎮
      اللعبة: ${orderData.gameName} 📱 المنصة: ${orderData.platform.toUpperCase()} 💎
      نوع الحساب: ${orderData.accountType} 💰 السعر: ${orderData.price} جنيه 📞
      طريقة الدفع: ${orderData.paymentMethod} 👤 معلومات العميل: ━━━━━━━━━━━━━━━━━━━━━━━━ 📞
      رقم الهاتف: ${orderData.customerPhone} 📧 الإيميل: ${orderData.customerEmail || 'غير
      محدد'} ⏰ وقت الطلب: ${orderData.orderTime} 📊 الحالة: ${orderData.status} ${orderData.notes ? `📝
      ملاحظات: ${orderData.notes}` : ''} 🔔 الإجراءات المطلوبة: 1. تأكيد الطلب مع العميل 2. استلام الدفع
      3. تسليم الحساب خلال 15 ساعة ━━━━━━━━━━━━━━━━━━━━━━━━ 🌟 منصة شهد السنيورة `; return message.trim(); } //
      إرسال إشعار تأكيد الطلب async sendOrderConfirmation(orderData) { const message = ` ✅
      تأكيد الطلب - ${orderData.orderId}

      🎮 تم تأكيد الطلب بنجاح! 📞 العميل: ${orderData.customerPhone} 💰 المبلغ: ${orderData.price}
      جنيه ⏰ سيتم التسليم خلال 15 ساعة

      🔔 تذكير: تابع مع العميل لضمان الجودة `; return await this.sendMessage(message); } // إرسال إشعار تسليم
      الطلب async sendDeliveryNotification(orderData) { const message = ` 📦 تسليم الطلب - ${orderData.orderId}

      ✅ تم تسليم الطلب بنجاح! 🎮 اللعبة: ${orderData.gameName} 👤
      العميل: ${orderData.customerPhone} ⏰ وقت التسليم: ${new Date().toLocaleString('ar-EG')} 🛡️
      الضمان: ${this.getWarrantyPeriod(orderData.accountType)} 💬 تم إرسال تفاصيل الحساب عبر الواتساب `;
      return await this.sendMessage(message); } // إرسال إشعار مشكلة async sendProblemNotification(orderData,
      problemDescription) { const message = ` 🚨 مشكلة في الطلب - ${orderData.orderId}

      ❌ تم الإبلاغ عن مشكلة: ${problemDescription} 👤 العميل: ${orderData.customerPhone} 🎮
      اللعبة: ${orderData.gameName} 💎 نوع الحساب: ${orderData.accountType} ⚠️ يتطلب تدخل فوري! 🔧
      الإجراءات المطلوبة: 1. التواصل مع العميل فوراً 2. تشخيص المشكلة 3. تقديم حل أو استبدال 📞
      تواصل مع العميل الآن! `; return await this.sendMessage(message); } // إرسال الإحصائيات اليومية async
      sendDailyStats() { const stats = window.orderSystem.getOrderStatistics(); const message = ` 📊
      إحصائيات اليوم - منصة شهد السنيورة

      📈 الطلبات: ━━━━━━━━━━━━━━━━━━━━━━━━ 📋 إجمالي الطلبات: ${stats.total} ⏳
      في الانتظار: ${stats.pending} ✅ مؤكدة: ${stats.confirmed} 📦 تم التسليم: ${stats.delivered}
      ❌ ملغية: ${stats.cancelled} 💰 الإيرادات: ━━━━━━━━━━━━━━━━━━━━━━━━ 💵
      إجمالي الإيرادات: ${stats.totalRevenue} جنيه 📊 متوسط قيمة الطلب: ${stats.total > 0 ?
      Math.round(stats.totalRevenue / stats.total) : 0} جنيه 📅 التاريخ: ${new
      Date().toLocaleDateString('ar-EG')} `; return await this.sendMessage(message); } // الحصول على فترة الضمان
      getWarrantyPeriod(accountType) { const warranties = { 'primary': '6 أشهر', 'secondary': '3 أشهر', 'full': 'سنة
      كاملة' }; return warranties[accountType] || 'غير محدد'; } // إرسال رسالة مع أزرار async
      sendMessageWithButtons(text, buttons) { if (!this.isEnabled) return false; try { const response = await
      fetch(`${this.apiUrl}/sendMessage`, { method: 'POST', headers: { 'Content-Type': 'application/json', }, body:
      JSON.stringify({ chat_id: this.chatId, text: text, parse_mode: 'HTML', reply_markup: { inline_keyboard: buttons }
      }) }); const data = await response.json(); return data.ok; } catch (error) { console.error('خطأ في إرسال رسالة مع
      أزرار:', error); return false; } } // إرسال تذكير متابعة async sendFollowUpReminder(orderData) { const buttons = [
      [ { text: '✅ تأكيد الطلب', callback_data: `confirm_${orderData.orderId}` }, { text: '❌ إلغاء الطلب',
      callback_data: `cancel_${orderData.orderId}` } ], [ { text: '📞 اتصال بالعميل', url:
      `tel:${orderData.customerPhone}` } ] ]; const message = ` ⏰ تذكير متابعة - ${orderData.orderId}

      🔔 هذا الطلب بحاجة للمتابعة: 👤 العميل: ${orderData.customerPhone} 💰
      المبلغ: ${orderData.price} جنيه ⏰ مضى على الطلب: ${this.getTimeElapsed(orderData.createdAt)} 🚨
      الإجراء مطلوب فوراً! `; return await this.sendMessageWithButtons(message, buttons); } // حساب الوقت المنقضي
      getTimeElapsed(createdAt) { const now = new Date(); const created = new Date(createdAt); const diffMs = now -
      created; const diffHours = Math.floor(diffMs / (1000 * 60 * 60)); const diffMinutes = Math.floor((diffMs % (1000 *
      60 * 60)) / (1000 * 60)); if (diffHours > 0) { return `${diffHours} ساعة و ${diffMinutes} دقيقة`; } else { return
      `${diffMinutes} دقيقة`; } } // تفعيل/إلغاء تفعيل البوت toggleBot(enabled) { this.isEnabled = enabled;
      console.log(`🤖 بوت تليجرام ${enabled ? 'مفعل' : 'معطل'}`); } // إرسال رسالة اختبار async sendTestMessage() {
      const message = ` 🧪 رسالة اختبار - بوت تليجرام

      ✅ البوت يعمل بشكل صحيح! 🕒 الوقت: ${new Date().toLocaleString('ar-EG')} 🌟 منصة شهد السنيورة
      `; return await this.sendMessage(message); } } // تهيئة بوت تليجرام window.telegramBot = new TelegramBot();
    
