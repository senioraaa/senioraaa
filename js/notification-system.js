      // نظام الإشعارات المتقدم class NotificationSystem { constructor() { this.whatsApp = window.whatsAppIntegration;
      this.telegram = window.telegramBot; this.notifications = []; this.isEnabled = true; this.init(); } // تهيئة النظام
      init() { this.loadNotifications(); this.setupEventListeners(); console.log('✅ تم تهيئة نظام الإشعارات'); } //
      تحميل الإشعارات المحفوظة loadNotifications() { const saved = localStorage.getItem('notifications'); if (saved) {
      this.notifications = JSON.parse(saved); } } // حفظ الإشعارات saveNotifications() {
      localStorage.setItem('notifications', JSON.stringify(this.notifications)); } // إعداد مستمعي الأحداث
      setupEventListeners() { // إشعار عند طلب جديد document.addEventListener('newOrder', (event) => {
      this.handleNewOrder(event.detail); }); // إشعار عند تغيير حالة الطلب
      document.addEventListener('orderStatusChanged', (event) => { this.handleOrderStatusChange(event.detail); }); //
      إشعار عند مشكلة document.addEventListener('orderProblem', (event) => { this.handleOrderProblem(event.detail); });
      } // معالجة الطلب الجديد async handleNewOrder(orderData) { const notification = { id:
      this.generateNotificationId(), type: 'new_order', orderId: orderData.orderId, title: 'طلب جديد', message: `طلب
      جديد: ${orderData.gameName} - ${orderData.platform}`, timestamp: new Date().toISOString(), read: false, priority:
      'high' }; // إضافة الإشعار this.addNotification(notification); // إرسال إشعارات await
      this.sendNotifications(orderData, 'new_order'); // تشغيل صوت الإشعار this.playNotificationSound(); // إظهار إشعار
      المتصفح this.showBrowserNotification(notification); } // معالجة تغيير حالة الطلب async
      handleOrderStatusChange(data) { const notification = { id: this.generateNotificationId(), type: 'status_change',
      orderId: data.orderId, title: 'تغيير حالة الطلب', message: `تم تغيير حالة الطلب ${data.orderId} إلى
      ${data.newStatus}`, timestamp: new Date().toISOString(), read: false, priority: 'medium' };
      this.addNotification(notification); // إرسال إشعار حسب الحالة switch (data.newStatus) { case 'confirmed': await
      this.telegram.sendOrderConfirmation(data.orderData); break; case 'delivered': await
      this.telegram.sendDeliveryNotification(data.orderData); break; case 'cancelled': await
      this.sendCancellationNotification(data.orderData); break; } } // معالجة مشكلة الطلب async handleOrderProblem(data)
      { const notification = { id: this.generateNotificationId(), type: 'problem', orderId: data.orderId, title: 'مشكلة
      في الطلب', message: `مشكلة في الطلب ${data.orderId}: ${data.problem}`, timestamp: new Date().toISOString(), read:
      false, priority: 'urgent' }; this.addNotification(notification); // إرسال إشعار المشكلة await
      this.telegram.sendProblemNotification(data.orderData, data.problem); // إرسال رسالة واتساب للعميل await
      this.sendCustomerProblemNotification(data.orderData, data.problem); // تشغيل صوت إنذار
      this.playUrgentNotificationSound(); } // إضافة إشعار جديد addNotification(notification) {
      this.notifications.unshift(notification); // الاحتفاظ بآخر 100 إشعار فقط if (this.notifications.length >
