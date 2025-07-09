// نظام الأمان والحماية الشامل
class SecuritySystem {
    constructor() {
        this.config = {
            maxRequestsPerMinute: 60,
            maxFailedAttempts: 5,
            sessionTimeout: 30 * 60 * 1000, // 30 دقيقة
            allowedOrigins: ['https://yourdomain.com'],
            CSPEnabled: true
        };
        
        this.requestCounts = new Map();
        this.failedAttempts = new Map();
        this.blockedIPs = new Set();
        this.sessions = new Map();
        
        this.init();
    }
    
    // تهيئة نظام الأمان
    init() {
        this.setupCSP();
        this.setupXSSProtection();
        this.setupRateLimiting();
        this.setupInputValidation();
        this.setupSessionManagement();
        this.setupSecurityHeaders();
        this.monitorSecurity();
    }
    
    // إعداد Content Security Policy
    setupCSP() {
        if (!this.config.CSPEnabled) return;
        
        const cspHeader = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://api.telegram.org",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "connect-src 'self' https://api.telegram.org https://api.whatsapp.com",
            "font-src 'self'",
            "frame-src 'none'",
            "object-src 'none'"
        ].join('; ');
        
        const meta = document.createElement('meta');
        meta.httpEquiv = 'Content-Security-Policy';
        meta.content = cspHeader;
        document.head.appendChild(meta);
        
        console.log('🔒 تم تفعيل CSP');
    }
    
    // حماية من XSS
    setupXSSProtection() {
        // تنظيف المدخلات
        const originalInnerHTML = Element.prototype.innerHTML;
        
        Object.defineProperty(Element.prototype, 'innerHTML', {
            set: function(value) {
                const cleanValue = this.sanitizeHTML(value);
                originalInnerHTML.call(this, cleanValue);
            },
            get: function() {
                return originalInnerHTML.call(this);
            }
        });
        
        // تنظيف المعاملات من URL
        this.sanitizeURLParams();
        
        console.log('🔒 تم تفعيل حماية XSS');
    }
    
    // تنظيف HTML
    sanitizeHTML(html) {
        const temp = document.createElement('div');
        temp.innerHTML = html;
        
        // إزالة السكريبتات
        const scripts = temp.querySelectorAll('script');
        scripts.forEach(script => script.remove());
        
        // إزالة الأحداث
        const elements = temp.querySelectorAll('*');
        elements.forEach(element => {
            const attributes = element.attributes;
            for (let i = attributes.length - 1; i >= 0; i--) {
                const attr = attributes[i];
                if (attr.name.startsWith('on') || attr.name === 'href' && attr.value.startsWith('javascript:')) {
                    element.removeAttribute(attr.name);
                }
            }
        });
        
        return temp.innerHTML;
    }
    
    // تنظيف معاملات URL
    sanitizeURLParams() {
        const urlParams = new URLSearchParams(window.location.search);
        let hasUnsafeParam = false;
        
        for (const [key, value] of urlParams) {
            if (this.containsXSS(value)) {
                urlParams.delete(key);
                hasUnsafeParam = true;
            }
        }
        
        if (hasUnsafeParam) {
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.history.replaceState({}, '', newUrl);
        }
    }
    
    // فحص XSS
    containsXSS(input) {
        const xssPatterns = [
            /
    
        
        
    
