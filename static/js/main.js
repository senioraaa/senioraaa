// وظائف الموقع الرئيسية
document.addEventListener('DOMContentLoaded', function() {
    console.log('موقع شهد السنيورة تم تحميله بنجاح!');
    
    // تحديث الأسعار في الوقت الفعلي
    updatePricesDisplay();
    
    // إضافة مستمعي الأحداث للأزرار
    setupEventListeners();
});

// إعداد مستمعي الأحداث
function setupEventListeners() {
    // أزرار الطلب
    const orderButtons = document.querySelectorAll('.order-btn');
    orderButtons.forEach(button => {
        button.addEventListener('click', handleOrderClick);
    });
    
    // أزرار تحديث الأسعار (في صفحة الإدارة)
    const updateButtons = document.querySelectorAll('.update-btn');
    updateButtons.forEach(button => {
        button.addEventListener('click', handlePriceUpdate);
    });
}

// التعامل مع النقر على زر الطلب
function handleOrderClick(event) {
    const button = event.target;
    const card = button.closest('.price-card');
    
    if (!card) return;
    
    // استخراج بيانات الطلب
    const orderData = {
        game: 'FC 25',
        platform: card.dataset.platform || 'PS5',
        account_type: card.dataset.accountType || 'Primary',
        price: card.querySelector('.price').textContent.replace(/[^0-9]/g, ''),
        timestamp: new Date().toISOString()
    };
    
    // عرض نموذج الطلب
    showOrderForm(orderData);
}

// عرض نموذج الطلب
function showOrderForm(orderData) {
    const modal = document.createElement('div');
    modal.className = 'order-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>🎮 تأكيد الطلب</h2>
                <span class="close-btn" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body">
                <div class="order-summary">
                    <h3>تفاصيل الطلب:</h3>
                    <p><strong>اللعبة:</strong> ${orderData.game}</p>
                    <p><strong>المنصة:</strong> ${orderData.platform}</p>
                    <p><strong>نوع الحساب:</strong> ${orderData.account_type}</p>
                    <p><strong>السعر:</strong> ${orderData.price} جنيه</p>
                </div>
                
                <div class="order-form">
                    <h3>بيانات الطلب:</h3>
                    <input type="text" id="customerPhone" placeholder="رقم الهاتف" required>
                    <select id="paymentMethod" required>
                        <option value="">اختر طريقة الدفع</option>
                        <option value="فودافون كاش">فودافون كاش</option>
                        <option value="أورانج موني">أورانج موني</option>
                        <option value="إتصالات كاش">إتصالات كاش</option>
                        <option value="تحويل بنكي">تحويل بنكي</option>
                    </select>
                    <input type="text" id="paymentNumber" placeholder="رقم الدفع/البطاقة">
                </div>
                
                <div class="modal-footer">
                    <button class="confirm-order-btn" onclick="confirmOrder(${JSON.stringify(orderData).replace(/"/g, '&quot;')})">
                        تأكيد الطلب والانتقال للواتساب
                    </button>
                    <button class="cancel-btn" onclick="closeModal()">إلغاء</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // إضافة الأنماط للمودال
    addModalStyles();
}

// تأكيد الطلب وإرسال للواتساب
function confirmOrder(orderData) {
    const customerPhone = document.getElementById('customerPhone').value;
    const paymentMethod = document.getElementById('paymentMethod').value;
    const paymentNumber = document.getElementById('paymentNumber').value;
    
    if (!customerPhone || !paymentMethod) {
        alert('يرجى ملء جميع البيانات المطلوبة');
        return;
    }
    
    // إعداد بيانات الطلب الكاملة
    const fullOrderData = {
        ...orderData,
        customer_phone: customerPhone,
        payment_method: paymentMethod,
        payment_number: paymentNumber
    };
    
    // إرسال الطلب للخادم
    fetch('/send_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(fullOrderData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // فتح الواتساب مع الرسالة المعدة
            const whatsappUrl = `https://wa.me/${data.phone}?text=${encodeURIComponent(data.whatsapp_message)}`;
            window.open(whatsappUrl, '_blank');
            
            // إغلاق المودال
            closeModal();
            
            // عرض رسالة تأكيد
            showSuccessMessage('تم إرسال الطلب بنجاح! سيتم فتح الواتساب الآن.');
        } else {
            alert('حدث خطأ في إرسال الطلب: ' + data.message);
        }
    })
    .catch(error => {
        console.error('خطأ:', error);
        alert('حدث خطأ في إرسال الطلب');
    });
}

// إغلاق المودال
function closeModal() {
    const modal = document.querySelector('.order-modal');
    if (modal) {
        modal.remove();
    }
}

// تحديث الأسعار (للإدارة)
function handlePriceUpdate(event) {
    const button = event.target;
    const form = button.closest('.price-editor');
    
    if (!form) return;
    
    const game = form.dataset.game;
    const platform = form.dataset.platform;
    const accountType = form.dataset.accountType;
    const newPrice = form.querySelector('input[type="number"]').value;
    
    if (!newPrice || newPrice <= 0) {
        alert('يرجى إدخال سعر صحيح');
        return;
    }
    
    // إرسال التحديث للخادم
    fetch('/update_prices', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            game: game,
            platform: platform,
            account_type: accountType,
            price: parseInt(newPrice)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showSuccessMessage('تم تحديث السعر بنجاح!');
            updatePricesDisplay();
        } else {
            alert('حدث خطأ في تحديث السعر: ' + data.message);
        }
    })
    .catch(error => {
        console.error('خطأ:', error);
        alert('حدث خطأ في تحديث السعر');
    });
}

// تحديث عرض الأسعار
function updatePricesDisplay() {
    // هنا يتم تحديث الأسعار في الصفحة
    // يمكن إضافة Ajax call لجلب الأسعار الجديدة
    console.log('تم تحديث الأسعار');
}

// عرض رسالة نجاح
function showSuccessMessage(message) {
    const alert = document.createElement('div');
    alert.className = 'alert success';
    alert.textContent = message;
    
    document.body.appendChild(alert);
    
    setTimeout(() => {
        alert.remove();
    }, 3000);
}

// إضافة أنماط المودال
function addModalStyles() {
    if (document.getElementById('modal-styles')) return;
    
    const styles = document.createElement('style');
    styles.id = 'modal-styles';
    styles.textContent = `
        .order-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal-content {
            background: white;
            border-radius: 15px;
            width: 90%;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 2rem;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .close-btn {
            font-size: 2rem;
            cursor: pointer;
            color: #666;
        }
        
        .modal-body {
            padding: 2rem;
        }
        
        .order-summary {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        
        .order-form input,
        .order-form select {
            width: 100%;
            padding: 0.8rem;
            margin-bottom: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 1rem;
        }
        
        .modal-footer {
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
        }
        
        .confirm-order-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
        }
        
        .cancel-btn {
            background: #f44336;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
        }
        
        .alert {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 2rem;
            border-radius: 5px;
            z-index: 1001;
        }
        
        .alert.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
    `;
    
    document.head.appendChild(styles);
}

// وظائف إضافية
function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
    }
}

// تحديث الساعة (اختياري)
function updateClock() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('ar-EG');
    const clockElement = document.getElementById('clock');
    
    if (clockElement) {
        clockElement.textContent = timeString;
    }
}

// تشغيل الساعة كل ثانية
setInterval(updateClock, 1000);

// تتبع الإحصائيات (اختياري)
function trackOrder(orderData) {
    // هنا يمكن إضافة تتبع للطلبات
    console.log('تم تسجيل طلب جديد:', orderData);
}

// التحقق من الاتصال بالإنترنت
function checkConnection() {
    if (!navigator.onLine) {
        showErrorMessage('لا يوجد اتصال بالإنترنت');
    }
}

window.addEventListener('online', () => {
    showSuccessMessage('تم استعادة الاتصال بالإنترنت');
});

window.addEventListener('offline', () => {
    showErrorMessage('انقطع الاتصال بالإنترنت');
});
