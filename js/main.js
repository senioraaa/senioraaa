// Global Variables
const gameData = {
    fc25: {
        name: "EA Sports FC 25",
        platforms: {
            ps5: {
                name: "PlayStation 5",
                prices: { primary: 60, secondary: 40, full: 100 }
            },
            ps4: {
                name: "PlayStation 4", 
                prices: { primary: 50, secondary: 30, full: 80 }
            },
            xbox: {
                name: "Xbox",
                prices: { primary: 55, secondary: 35, full: 90 }
            },
            pc: {
                name: "PC",
                prices: { primary: 45, secondary: 25, full: 70 }
            }
        }
    }
};

let selectedPlatform = 'ps5';
let selectedType = '';
let selectedPrice = 0;

// DOM Elements
const platformTabs = document.querySelectorAll('.tab-btn');
const orderButtons = document.querySelectorAll('.order-btn');
const modal = document.getElementById('orderModal');
const closeModal = document.querySelector('.close');
const confirmOrder = document.getElementById('confirm-order');
const cancelOrder = document.getElementById('cancel-order');
const navToggle = document.querySelector('.nav-toggle');
const navMenu = document.querySelector('.nav-menu');

// Initialize App
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    updatePrices();
    loadTestimonials();
    setupSmoothScroll();
    setupMobileMenu();
}

// Event Listeners
function setupEventListeners() {
    // Platform tabs
    platformTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const platform = this.dataset.platform;
            selectPlatform(platform);
        });
    });

    // Order buttons
    orderButtons.forEach(button => {
        button.addEventListener('click', function() {
            const type = this.dataset.type;
            openOrderModal(type);
        });
    });

    // Modal events
    if (closeModal) {
        closeModal.addEventListener('click', closeOrderModal);
    }

    if (confirmOrder) {
        confirmOrder.addEventListener('click', processOrder);
    }

    if (cancelOrder) {
        cancelOrder.addEventListener('click', closeOrderModal);
    }

    // Close modal on outside click
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeOrderModal();
        }
    });

    // Form validation
    const phoneInput = document.getElementById('phone');
    const paymentInput = document.getElementById('payment-number');
    
    if (phoneInput) {
        phoneInput.addEventListener('input', validatePhone);
    }
    
    if (paymentInput) {
        paymentInput.addEventListener('input', validatePaymentNumber);
    }
}

// Platform Selection
function selectPlatform(platform) {
    selectedPlatform = platform;
    
    // Update active tab
    platformTabs.forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.platform === platform) {
            tab.classList.add('active');
        }
    });
    
    // Update prices
    updatePrices();
    
    // Update platform display
    updatePlatformDisplay(platform);
}

// Update Prices
function updatePrices() {
    const platformData = gameData.fc25.platforms[selectedPlatform];
    
    if (platformData) {
        const primaryPrice = document.getElementById('primary-price');
        const secondaryPrice = document.getElementById('secondary-price');
        const fullPrice = document.getElementById('full-price');
        
        if (primaryPrice) primaryPrice.textContent = platformData.prices.primary;
        if (secondaryPrice) secondaryPrice.textContent = platformData.prices.secondary;
        if (fullPrice) fullPrice.textContent = platformData.prices.full;
    }
}

// Update Platform Display
function updatePlatformDisplay(platform) {
    const platformName = gameData.fc25.platforms[platform].name;
    const selectedPlatformSpan = document.getElementById('selected-platform');
    
    if (selectedPlatformSpan) {
        selectedPlatformSpan.textContent = platformName;
    }
}

// Open Order Modal
function openOrderModal(type) {
    selectedType = type;
    selectedPrice = gameData.fc25.platforms[selectedPlatform].prices[type];
    
    // Update modal content
    updateModalContent();
    
    // Show modal
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Add fade in animation
    setTimeout(() => {
        modal.classList.add('fade-in');
    }, 10);
}

// Update Modal Content
function updateModalContent() {
    const selectedPlatformSpan = document.getElementById('selected-platform');
    const selectedTypeSpan = document.getElementById('selected-type');
    const selectedPriceSpan = document.getElementById('selected-price');
    
    if (selectedPlatformSpan) {
        selectedPlatformSpan.textContent = gameData.fc25.platforms[selectedPlatform].name;
    }
    
    if (selectedTypeSpan) {
        const typeNames = {
            primary: 'Primary',
            secondary: 'Secondary',
            full: 'Full'
        };
        selectedTypeSpan.textContent = typeNames[selectedType];
    }
    
    if (selectedPriceSpan) {
        selectedPriceSpan.textContent = selectedPrice;
    }
}

// Close Order Modal
function closeOrderModal() {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
    modal.classList.remove('fade-in');
    
    // Reset form
    resetOrderForm();
}

// Reset Order Form
function resetOrderForm() {
    const phoneInput = document.getElementById('phone');
    const paymentInput = document.getElementById('payment-number');
    
    if (phoneInput) phoneInput.value = '';
    if (paymentInput) paymentInput.value = '';
    
    // Reset radio buttons
    const paymentRadios = document.querySelectorAll('input[name="payment"]');
    paymentRadios.forEach(radio => {
        if (radio.value === 'vodafone') {
            radio.checked = true;
        } else {
            radio.checked = false;
        }
    });
}

// Process Order
function processOrder() {
    const phone = document.getElementById('phone').value;
    const paymentNumber = document.getElementById('payment-number').value;
    const selectedPayment = document.querySelector('input[name="payment"]:checked').value;
    
    // Validate inputs
    if (!validateOrderInputs(phone, paymentNumber)) {
        return;
    }
    
    // Prepare order data
    const orderData = {
        game: 'FC 25',
        platform: gameData.fc25.platforms[selectedPlatform].name,
        type: selectedType,
        price: selectedPrice,
        phone: phone,
        paymentNumber: paymentNumber,
        paymentMethod: selectedPayment,
        timestamp: new Date().toISOString()
    };
    
    // Save order locally
    saveOrder(orderData);
    
    // Send to Telegram
    sendTelegramNotification(orderData);
    
    // Redirect to WhatsApp
    sendWhatsAppMessage(orderData);
    
    // Close modal
    closeOrderModal();
    
    // Show success message
    showSuccessMessage();
}

// Validate Order Inputs
function validateOrderInputs(phone, paymentNumber) {
    if (!phone || phone.length < 11) {
        alert('يرجى إدخال رقم هاتف صحيح');
        return false;
    }
    
    if (!paymentNumber || paymentNumber.length < 11) {
        alert('يرجى إدخال رقم المحفظة صحيح');
        return false;
    }
    
    return true;
}

// Validate Phone Number
function validatePhone(e) {
    const phone = e.target.value;
    const phoneRegex = /^01[0-9]{9}$/;
    
    if (phone && !phoneRegex.test(phone)) {
        e.target.style.borderColor = '#e74c3c';
        e.target.title = 'رقم الهاتف يجب أن يبدأ بـ 01 ويتكون من 11 رقم';
    } else {
        e.target.style.borderColor = '#27ae60';
        e.target.title = '';
    }
}

// Validate Payment Number
function validatePaymentNumber(e) {
    const paymentNumber = e.target.value;
    const numberRegex = /^01[0-9]{9}$/;
    
    if (paymentNumber && !numberRegex.test(paymentNumber)) {
        e.target.style.borderColor = '#e74c3c';
        e.target.title = 'رقم المحفظة يجب أن يبدأ بـ 01 ويتكون من 11 رقم';
    } else {
        e.target.style.borderColor = '#27ae60';
        e.target.title = '';
    }
}

// Save Order Locally
function saveOrder(orderData) {
    let orders = JSON.parse(localStorage.getItem('orders')) || [];
    orders.push({
        id: Date.now(),
        ...orderData,
        status: 'pending'
    });
    localStorage.setItem('orders', JSON.stringify(orders));
}

// Show Success Message
function showSuccessMessage() {
    const message = document.createElement('div');
    message.innerHTML = `

    `;
    
    document.body.appendChild(message);
    
    setTimeout(() => {
        message.remove();
    }, 5000);
}

// Load Testimonials
function loadTestimonials() {
    const testimonials = [
        {
            name: "أحمد محمد",
            location: "القاهرة",
            text: "خدمة ممتازة وسرعة في التسليم. حصلت على FC 25 PS5 في نفس اليوم!",
            rating: 5
        },
        {
            name: "عمر سعيد", 
            location: "الإسكندرية",
            text: "أسعار رائعة ومصداقية عالية. أنصح بشدة!",
            rating: 5
        },
        {
            name: "محمد عبدالله",
            location: "الجيزة", 
            text: "دعم فني رائع وشرح وافي للفروقات بين الحسابات",
            rating: 5
        }
    ];
    
    // Dynamic testimonials loading can be implemented here
}

// Setup Smooth Scroll
function setupSmoothScroll() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Setup Mobile Menu
function setupMobileMenu() {
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
        
        // Close menu when clicking on a link
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });
    }
}

// Utility Functions
function formatPrice(price) {
    return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function getCurrentTime() {
    return new Date().toLocaleString('ar-EG', {
        timeZone: 'Africa/Cairo',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function generateOrderId() {
    return 'ORD-' + Date.now().toString(36).toUpperCase();
}

// Analytics
function trackEvent(eventName, properties = {}) {
    if (typeof gtag !== 'undefined') {
        gtag('event', eventName, properties);
    }
    
    // Custom analytics can be added here
    console.log('Event tracked:', eventName, properties);
}

// Error Handling
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    
    // You can implement error reporting here
    // For example, send to a logging service
});

// Page Visibility API
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden');
    } else {
        console.log('Page visible');
    }
});

// Performance Monitoring
window.addEventListener('load', function() {
    const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
    console.log('Page load time:', loadTime + 'ms');
    
    // Track page load time
    trackEvent('page_load_time', {
        time: loadTime,
        page: window.location.pathname
    });
});
    
