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
                    <input type="text" id="customerPhone" placeholder="رقم الواتساب (مثال: 01234567890)" required pattern="01[0-2][0-9]{8}">
                    <div id="phoneError" class="error-message" style="display: none;">رقم الواتساب يجب أن يكون 11 رقم ويبدأ بـ 01</div>
                    
                    <div class="payment-methods">
                        <h4>طريقة الدفع:</h4>
                        <div class="payment-grid">
                            <div class="payment-option" onclick="selectPayment('vodafone_cash')">
                                <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMjAiIGZpbGw9IiNFNjAwMDAiLz4KPHN2ZyB4PSI4IiB5PSI4IiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI+CjxwYXRoIGQ9Ik0xOSA3SDE0VjVIMTBWN0g1QzMuOSA3IDMgNy45IDMgOVYxN0MzIDE4LjEgMy45IDE5IDUgMTlIMTlDMjAuMSAxOSAyMSAxOC4xIDIxIDE3VjlDMjEgNy45IDIwLjEgNyAxOSA3WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo=" alt="Vodafone Cash">
                                <span>Vodafone Cash</span>
                            </div>
                            <div class="payment-option" onclick="selectPayment('etisalat_cash')">
                                <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMjAiIGZpbGw9IiNGRkE1MDAiLz4KPHN2ZyB4PSI4IiB5PSI4IiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI+CjxwYXRoIGQ9Ik0xOSA3SDE0VjVIMTBWN0g1QzMuOSA3IDMgNy45IDMgOVYxN0MzIDE4LjEgMy45IDE5IDUgMTlIMTlDMjAuMSAxOSAyMSAxOC4xIDIxIDE3VjlDMjEgNy45IDIwLjEgNyAxOSA3WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo=" alt="Etisalat Cash">
                                <span>Etisalat Cash</span>
                            </div>
                            <div class="payment-option" onclick="selectPayment('we_cash')">
                                <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMjAiIGZpbGw9IiM5QjU5QjYiLz4KPHN2ZyB4PSI4IiB5PSI4IiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI+CjxwYXRoIGQ9Ik0xOSA3SDE0VjVIMTBWN0g1QzMuOSA3IDMgNy45IDMgOVYxN0MzIDE4LjEgMy45IDE5IDUgMTlIMTlDMjAuMSAxOSAyMSAxOC4xIDIxIDE3VjlDMjEgNy45IDIwLjEgNyAxOSA3WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo=" alt="WE Cash">
                                <span>WE Cash</span>
                            </div>
                            <div class="payment-option" onclick="selectPayment('orange_cash')">
                                <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMjAiIGZpbGw9IiNGRjY2MDAiLz4KPHN2ZyB4PSI4IiB5PSI4IiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI+CjxwYXRoIGQ9Ik0xOSA3SDE0VjVIMTBWN0g1QzMuOSA3IDMgNy45IDMgOVYxN0MzIDE4LjEgMy45IDE5IDUgMTlIMTlDMjAuMSAxOSAyMSAxOC4xIDIxIDE3VjlDMjEgNy45IDIwLjEgNyAxOSA3WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo=" alt="Orange Cash">
                                <span>Orange Cash</span>
                            </div>
                            <div class="payment-option" onclick="selectPayment('bank_wallet')">
                                <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMjAiIGZpbGw9IiM0Q0FGNTFCL2NpcmNsZSI+CjxzdmcgeD0iOCIgeT0iOCIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiPgo8cGF0aCBkPSJNMTIgMkwxMyA5SDE4TDIwIDEyTDE4IDE0SDEzTDEyIDIxSDEwTDkgMTNINUwyIDEyTDUgMTBIOUwxMCAySDE0WiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+Cjwvc3ZnPgo=" alt="Bank Wallet">
                                <span>Bank Wallet</span>
                            </div>
                            <div class="payment-option" onclick="selectPayment('instapay')">
                                <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMjAiIGN5PSIyMCIgcj0iMjAiIGZpbGw9IiMwMDc4RDQiLz4KPHN2ZyB4PSI4IiB5PSI4IiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI+CjxwYXRoIGQ9Ik0xMiAyTDEzLjA5IDguMjZMMjAgN0wyMSAxMEwyMCAxM0gxN0wxNiAyMUgxNEwxMyAxNUg5TDggMTNMOSAxMEwxMiA5VjJaIiBmaWxsPSJ3aGl0ZSIvPgo8L3N2Zz4KPC9zdmc+Cjwvc3ZnPgo=" alt="InstaPay">
                                <span>InstaPay</span>
                            </div>
                        </div>
                    </div>
                    
                    <input type="hidden" id="selectedPayment" value="">
                    <div id="paymentError" class="error-message" style="display: none;">يرجى اختيار طريقة الدفع</div>
                    
                    <div id="paymentNumberGroup" style="display: none;">
                        <input type="text" id="paymentNumber" placeholder="رقم الدفع">
                        <div id="paymentNumberError" class="error-message" style="display: none;">يرجى إدخال رقم الدفع</div>
                    </div>
                    
                    <div id="instaPayGroup" style="display: none;">
                        <input type="text" id="instaPayUsername" placeholder="يوزر InstaPay أو الرابط">
                        <div id="instaPayError" class="error-message" style="display: none;">يرجى إدخال يوزر InstaPay أو الرابط</div>
                    </div>
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

// اختيار طريقة الدفع
function selectPayment(paymentType) {
    // إزالة التحديد من جميع الخيارات
    document.querySelectorAll('.payment-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // إضافة التحديد للخيار المختار
    event.target.closest('.payment-option').classList.add('selected');
    
    // تحديث الحقل المخفي
    document.getElementById('selectedPayment').value = paymentType;
    
    // إخفاء رسالة الخطأ
    document.getElementById('paymentError').style.display = 'none';
    
    // إظهار الحقل المناسب
    const paymentNumberGroup = document.getElementById('paymentNumberGroup');
    const instaPayGroup = document.getElementById('instaPayGroup');
    const paymentNumberInput = document.getElementById('paymentNumber');
    const instaPayInput = document.getElementById('instaPayUsername');
    
    if (paymentType === 'instapay') {
        paymentNumberGroup.style.display = 'none';
        instaPayGroup.style.display = 'block';
        instaPayInput.placeholder = 'يوزر InstaPay أو الرابط';
    } else {
        paymentNumberGroup.style.display = 'block';
        instaPayGroup.style.display = 'none';
        paymentNumberInput.placeholder = 'رقم الدفع';
    }
}

// تأكيد الطلب وإرسال للواتساب
function confirmOrder(orderData) {
    const customerPhone = document.getElementById('customerPhone').value;
    const selectedPayment = document.getElementById('selectedPayment').value;
    const paymentNumber = document.getElementById('paymentNumber').value;
    const instaPayUsername = document.getElementById('instaPayUsername').value;
    
    // التحقق من رقم الواتساب
    const phoneRegex = /^01[0-2][0-9]{8}$/;
    if (!phoneRegex.test(customerPhone)) {
        document.getElementById('phoneError').style.display = 'block';
        return;
    } else {
        document.getElementById('phoneError').style.display = 'none';
    }
    
    // التحقق من اختيار طريقة الدفع
    if (!selectedPayment) {
        document.getElementById('paymentError').style.display = 'block';
        return;
    } else {
        document.getElementById('paymentError').style.display = 'none';
    }
    
    // التحقق من بيانات الدفع
    if (selectedPayment === 'instapay') {
        if (!instaPayUsername) {
            document.getElementById('instaPayError').style.display = 'block';
            return;
        } else {
            document.getElementById('instaPayError').style.display = 'none';
        }
    } else {
        if (!paymentNumber) {
            document.getElementById('paymentNumberError').style.display = 'block';
            return;
        } else {
            document.getElementById('paymentNumberError').style.display = 'none';
        }
    }
    
    // إعداد بيانات الطلب الكاملة
    const fullOrderData = {
        ...orderData,
        customer_phone: customerPhone,
        payment_method: selectedPayment,
        payment_number: selectedPayment === 'instapay' ? instaPayUsername : paymentNumber
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
            max-width: 600px;
            max-height: 90vh;
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
        
        .order-form input {
            width: 100%;
            padding: 0.8rem;
            margin-bottom: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 1rem;
            box-sizing: border-box;
        }
        
        .payment-methods {
            margin: 2rem 0;
        }
        
        .payment-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .payment-option {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .payment-option:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }
        
        .payment-option.selected {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .payment-option img {
            width: 40px;
            height: 40px;
            margin-bottom: 0.5rem;
        }
        
        .payment-option span {
            font-size: 0.9rem;
            font-weight: 500;
            text-align: center;
        }
        
        .error-message {
            color: #f44336;
            font-size: 0.9rem;
            margin-top: -0.5rem;
            margin-bottom: 1rem;
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
        
        @media (max-width: 768px) {
            .payment-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .modal-content {
                width: 95%;
            }
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
