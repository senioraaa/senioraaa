      // نظام إدارة الطلبات class OrderSystem { constructor() { this.orders = []; this.currentOrderId =
      this.generateOrderId(); this.whatsApp = window.whatsAppIntegration; this.telegram = null; // سيتم تهيئته لاحقاً }
      // إنشاء رقم طلب فريد generateOrderId() { const timestamp = Date.now(); const random = Math.floor(Math.random() *
      1000); return `ORD-${timestamp}-${random}`; } // إنشاء طلب جديد createOrder(formData) { const orderData = {
      orderId: this.generateOrderId(), gameName: formData.gameName || 'EA Sports FC 25', platform: formData.platform,
      accountType: formData.accountType, price: this.calculatePrice(formData.platform, formData.accountType),
      paymentMethod: formData.paymentMethod, customerPhone: formData.customerPhone, customerEmail:
      formData.customerEmail, customerAddress: formData.customerAddress, notes: formData.notes, orderTime: new
      Date().toLocaleString('ar-EG', { timeZone: 'Africa/Cairo', year: 'numeric', month: 'long', day: 'numeric', hour:
      '2-digit', minute: '2-digit' }), status: 'pending', createdAt: new Date().toISOString(), lastUpdated: new
      Date().toISOString() }; return orderData; } // حساب السعر calculatePrice(platform, accountType) { const prices = {
      'ps4': { 'primary': 50, 'secondary': 30, 'full': 80 }, 'ps5': { 'primary': 60, 'secondary': 40, 'full': 100 },
      'xbox': { 'primary': 55, 'secondary': 35, 'full': 90 }, 'pc': { 'primary': 45, 'secondary': 25, 'full': 70 } };
      return prices[platform]?.[accountType] || 0; } // معالجة الطلب وإرساله async processOrder(formData) { try { //
      إنشاء الطلب const orderData = this.createOrder(formData); // التحقق من صحة البيانات if
      (!this.validateOrder(orderData)) { throw new Error('بيانات الطلب غير صحيحة'); } // حفظ الطلب
      this.saveOrder(orderData); // إرسال للواتساب const whatsappSent = this.whatsApp.sendOrder(orderData); if
      (whatsappSent) { // إرسال إشعار تليجرام await this.sendTelegramNotification(orderData); // تسجيل الطلب
      this.logOrder(orderData); // إرجاع معلومات الطلب return { success: true, orderId: orderData.orderId, message: 'تم
      إرسال الطلب بنجاح', orderData: orderData }; } else { throw new Error('فشل في إرسال الطلب للواتساب'); } } catch
      (error) { console.error('خطأ في معالجة الطلب:', error); return { success: false, error: error.message }; } } //
      التحقق من صحة الطلب validateOrder(orderData) { // التحقق من البيانات الأساسية if (!orderData.platform ||
      !orderData.accountType) { return false; } // التحقق من رقم الهاتف if
      (!this.whatsApp.validateWhatsAppNumber(orderData.customerPhone)) { return false; } // التحقق من السعر if
      (!orderData.price || orderData.price <= 0) { return false; } return true; } // حفظ الطلب saveOrder(orderData) {
      this.orders.push(orderData); // حفظ في localStorage let savedOrders = JSON.parse(localStorage.getItem('allOrders')
      || '[]'); savedOrders.push(orderData); localStorage.setItem('allOrders', JSON.stringify(savedOrders)); // حفظ آخر
      طلب localStorage.setItem('lastOrder', JSON.stringify(orderData)); } // استرجاع جميع الطلبات getAllOrders() {
      return JSON.parse(localStorage.getItem('allOrders') || '[]'); } // البحث عن طلب بالرقم findOrderById(orderId) {
      const orders = this.getAllOrders(); return orders.find(order => order.orderId === orderId); } // تحديث حالة الطلب
      updateOrderStatus(orderId, newStatus) { let orders = this.getAllOrders(); const orderIndex =
      orders.findIndex(order => order.orderId === orderId); if (orderIndex !== -1) { orders[orderIndex].status =
      newStatus; orders[orderIndex].lastUpdated = new Date().toISOString(); localStorage.setItem('allOrders',
      JSON.stringify(orders)); return true; } return false; } // تسجيل الطلب في وحدة التحكم logOrder(orderData) {
      console.log('طلب جديد:', { orderId: orderData.orderId, game: orderData.gameName, platform: orderData.platform,
      accountType: orderData.accountType, price: orderData.price, customer: orderData.customerPhone, time:
      orderData.orderTime }); } // إرسال إشعار تليجرام async sendTelegramNotification(orderData) { if
      (window.telegramBot) { try { await window.telegramBot.sendOrderNotification(orderData); } catch (error) {
      console.error('خطأ في إرسال إشعار التليجرام:', error); } } } // إحصائيات الطلبات getOrderStatistics() { const
      orders = this.getAllOrders(); const stats = { total: orders.length, pending: orders.filter(order => order.status
      === 'pending').length, confirmed: orders.filter(order => order.status === 'confirmed').length, delivered:
      orders.filter(order => order.status === 'delivered').length, cancelled: orders.filter(order => order.status ===
      'cancelled').length, totalRevenue: orders.reduce((sum, order) => sum + (order.price || 0), 0) }; return stats; }
      // تصدير الطلبات إلى CSV exportOrdersToCSV() { const orders = this.getAllOrders(); const csvContent =
      this.convertOrdersToCSV(orders); this.downloadCSV(csvContent, 'orders.csv'); } // تحويل الطلبات إلى CSV
      convertOrdersToCSV(orders) { const headers = ['رقم الطلب', 'اللعبة', 'المنصة', 'نوع الحساب', 'السعر', 'رقم
      العميل', 'وقت الطلب', 'الحالة']; const csvRows = [headers.join(',')]; orders.forEach(order => { const row = [
      order.orderId, order.gameName, order.platform, order.accountType, order.price, order.customerPhone,
      order.orderTime, order.status ]; csvRows.push(row.join(',')); }); return csvRows.join('\n'); } // تحميل ملف CSV
      downloadCSV(content, filename) { const blob = new Blob([content], { type: 'text/csv' }); const url =
      window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename;
      a.click(); window.URL.revokeObjectURL(url); } } // تهيئة نظام الطلبات window.orderSystem = new OrderSystem();
