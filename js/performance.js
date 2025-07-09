// نظام تحسين الأداء الشامل
class PerformanceOptimizer {
    constructor() {
        this.metrics = {
            loadTime: 0,
            renderTime: 0,
            memoryUsage: 0,
            networkRequests: 0
        };
        
        this.cache = new Map();
        this.imageCache = new Map();
        this.init();
    }
    
    // تهيئة نظام الأداء
    init() {
        this.measurePageLoadTime();
        this.optimizeImages();
        this.setupLazyLoading();
        this.optimizeNetwork();
        this.setupServiceWorker();
        this.monitorPerformance();
    }
    
    // قياس وقت تحميل الصفحة
    measurePageLoadTime() {
        const startTime = performance.now();
        
        document.addEventListener('DOMContentLoaded', () => {
            const domLoadTime = performance.now() - startTime;
            this.metrics.loadTime = domLoadTime;
            
            console.log(`📊 وقت تحميل DOM: ${domLoadTime.toFixed(2)}ms`);
        });
        
        window.addEventListener('load', () => {
            const fullLoadTime = performance.now() - startTime;
            this.metrics.renderTime = fullLoadTime;
            
            console.log(`📊 وقت التحميل الكامل: ${fullLoadTime.toFixed(2)}ms`);
            
            // تقييم الأداء
            this.evaluatePerformance();
        });
    }
    
    // تحسين الصور
    optimizeImages() {
        const images = document.querySelectorAll('img');
        
        images.forEach(img => {
            // تحسين تحميل الصور
            if (!img.hasAttribute('loading')) {
                img.setAttribute('loading', 'lazy');
            }
            
            // ضغط الصور
            this.compressImage(img);
            
            // تحسين أبعاد الصور
            this.optimizeImageDimensions(img);
        });
    }
    
    // ضغط الصور
    compressImage(img) {
        img.addEventListener('load', () => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            
            canvas.width = img.width;
            canvas.height = img.height;
            
            ctx.drawImage(img, 0, 0);
            
            // ضغط الصورة
            const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.8);
            
            // حفظ في الكاش
            this.imageCache.set(img.src, compressedDataUrl);
        });
    }
    
    // تحسين أبعاد الصور
    optimizeImageDimensions(img) {
        const container = img.parentElement;
        const containerWidth = container.offsetWidth;
        
        if (img.naturalWidth > containerWidth) {
            img.style.width = '100%';
            img.style.height = 'auto';
        }
    }
    
    // تحميل كسول للعناصر
    setupLazyLoading() {
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const element = entry.target;
                        
                        // تحميل الصور
                        if (element.tagName === 'IMG' && element.dataset.src) {
                            element.src = element.dataset.src;
                            element.removeAttribute('data-src');
                        }
                        
                        // تحميل المحتوى
                        if (element.dataset.load) {
                            this.loadContent(element);
                        }
                        
                        observer.unobserve(element);
                    }
                });
            });
            
            // مراقبة الصور
            document.querySelectorAll('img[data-src]').forEach(img => {
                observer.observe(img);
            });
            
            // مراقبة العناصر الأخرى
            document.querySelectorAll('[data-load]').forEach(element => {
                observer.observe(element);
            });
        }
    }
    
    // تحسين الشبكة
    optimizeNetwork() {
        // تجميع الطلبات
        this.batchRequests();
        
        // ضغط البيانات
        this.compressData();
        
        // تحسين الكاش
        this.optimizeCache();
    }
    
    // تجميع الطلبات
    batchRequests() {
        const requestQueue = [];
        let batchTimeout;
        
        const originalFetch = window.fetch;
        
        window.fetch = (...args) => {
            return new Promise((resolve, reject) => {
                requestQueue.push({
                    args: args,
                    resolve: resolve,
                    reject: reject
                });
                
                clearTimeout(batchTimeout);
                batchTimeout = setTimeout(() => {
                    this.processBatchRequests(requestQueue);
                }, 100);
            });
        };
    }
    
    // معالجة الطلبات المجمعة
    processBatchRequests(requests) {
        requests.forEach(request => {
            const [url, options] = request.args;
            
            // تحقق من الكاش أولاً
            if (this.cache.has(url)) {
                request.resolve(this.cache.get(url));
                return;
            }
            
            // تنفيذ الطلب
            fetch(url, options)
                .then(response => {
                    // حفظ في الكاش
                    this.cache.set(url, response.clone());
                    request.resolve(response);
                })
                .catch(error => {
                    request.reject(error);
                });
        });
        
        requests.length = 0;
    }
    
    // ضغط البيانات
    compressData() {
        const originalJSON = JSON.stringify;
        
        JSON.stringify = function(obj) {
            const result = originalJSON.call(this, obj);
            
            // ضغط البيانات المكررة
            return result.replace(/\"([^\"]+)\":/g, (match, key) => {
                const shortKey = key.length > 10 ? key.substring(0, 10) : key;
                return `"${shortKey}":`;
            });
        };
    }
    
    // تحسين الكاش
    optimizeCache() {
        const maxCacheSize = 50;
        
        setInterval(() => {
            if (this.cache.size > maxCacheSize) {
                // حذف العناصر الأقدم
                const keys = Array.from(this.cache.keys());
                const keysToDelete = keys.slice(0, keys.length - maxCacheSize);
                
                keysToDelete.forEach(key => {
                    this.cache.delete(key);
                });
            }
        }, 60000); // كل دقيقة
    }
    
    // إعداد Service Worker
    setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('✅ Service Worker مسجل:', registration);
                })
                .catch(error => {
                    console.error('❌ فشل تسجيل Service Worker:', error);
                });
        }
    }
    
    // مراقبة الأداء
    monitorPerformance() {
        // مراقبة الذاكرة
        if ('memory' in performance) {
            setInterval(() => {
                this.metrics.memoryUsage = performance.memory.usedJSHeapSize / 1024 / 1024;
                
                if (this.metrics.memoryUsage > 100) {
                    console.warn('⚠️ استخدام الذاكرة مرتفع:', this.metrics.memoryUsage.toFixed(2) + 'MB');
                    this.optimizeMemory();
                }
            }, 30000); // كل 30 ثانية
        }
        
        // مراقبة الشبكة
        this.monitorNetworkRequests();
        
        // مراقبة FPS
        this.monitorFPS();
    }
    
    // مراقبة طلبات الشبكة
    monitorNetworkRequests() {
        const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            
            entries.forEach(entry => {
                if (entry.entryType === 'resource') {
                    this.metrics.networkRequests++;
                    
                    // تحقق من الطلبات البطيئة
                    if (entry.duration > 3000) {
                        console.warn('⚠️ طلب شبكة بطيء:', entry.name, entry.duration + 'ms');
                    }
                }
            });
        });
        
        observer.observe({ entryTypes: ['resource'] });
    }
    
    // مراقبة FPS
    monitorFPS() {
        let lastTime = performance.now();
        let frameCount = 0;
        
        const measureFPS = () => {
            const currentTime = performance.now();
            frameCount++;
            
            if (currentTime - lastTime >= 1000) {
                const fps = frameCount;
                frameCount = 0;
                lastTime = currentTime;
                
                if (fps < 30) {
                    console.warn('⚠️ FPS منخفض:', fps);
                    this.optimizeRendering();
                }
            }
            
            requestAnimationFrame(measureFPS);
        };
        
        requestAnimationFrame(measureFPS);
    }
    
    // تحسين الذاكرة
    optimizeMemory() {
        // تنظيف الكاش
        this.cache.clear();
        this.imageCache.clear();
        
        // تنظيف المتغيرات
        if (typeof gc !== 'undefined') {
            gc();
        }
        
        console.log('🧹 تم تنظيف الذاكرة');
    }
    
    // تحسين الرندر
    optimizeRendering() {
        // تقليل التحديثات
        const elements = document.querySelectorAll('.animated');
        elements.forEach(element => {
            element.style.animationPlayState = 'paused';
        });
        
        // تحسين التمرير
        document.documentElement.style.scrollBehavior = 'auto';
        
        setTimeout(() => {
            // إعادة التفعيل
            elements.forEach(element => {
                element.style.animationPlayState = 'running';
            });
            
            document.documentElement.style.scrollBehavior = 'smooth';
        }, 5000);
    }
    
    // تحميل المحتوى
    loadContent(element) {
        const contentType = element.dataset.load;
        
        switch (contentType) {
            case 'games':
                this.loadGamesContent(element);
                break;
            case 'prices':
                this.loadPricesContent(element);
                break;
            case 'reviews':
                this.loadReviewsContent(element);
                break;
        }
    }
    
    // تحميل محتوى الألعاب
    loadGamesContent(element) {
        if (this.cache.has('games-content')) {
            element.innerHTML = this.cache.get('games-content');
            return;
        }
        
        fetch('data/games.json')
            .then(response => response.json())
            .then(data => {
                const html = this.renderGamesHTML(data);
                element.innerHTML = html;
                this.cache.set('games-content', html);
            });
    }
    
    // تحميل محتوى الأسعار
    loadPricesContent(element) {
        if (this.cache.has('prices-content')) {
            element.innerHTML = this.cache.get('prices-content');
            return;
        }
        
        fetch('data/games.json')
            .then(response => response.json())
            .then(data => {
                const html = this.renderPricesHTML(data);
                element.innerHTML = html;
                this.cache.set('prices-content', html);
            });
    }
    
    // تقييم الأداء
    evaluatePerformance() {
        const score = this.calculatePerformanceScore();
        
        console.log(`📊 نتيجة الأداء: ${score}/100`);
        
        if (score < 50) {
            console.warn('⚠️ الأداء ضعيف - يحتاج تحسين');
            this.suggestOptimizations();
        } else if (score < 80) {
            console.log('📈 الأداء جيد - يمكن تحسينه');
        } else {
            console.log('✅ الأداء ممتاز');
        }
    }
    
    // حساب نتيجة الأداء
    calculatePerformanceScore() {
        let score = 100;
        
        // تقييم وقت التحميل
        if (this.metrics.loadTime > 3000) score -= 20;
        else if (this.metrics.loadTime > 1000) score -= 10;
        
        // تقييم استخدام الذاكرة
        if (this.metrics.memoryUsage > 100) score -= 15;
        else if (this.metrics.memoryUsage > 50) score -= 5;
        
        // تقييم عدد الطلبات
        if (this.metrics.networkRequests > 50) score -= 10;
        else if (this.metrics.networkRequests > 20) score -= 5;
        
        return Math.max(0, score);
    }
    
    // اقتراحات التحسين
    suggestOptimizations() {
        const suggestions = [];
        
        if (this.metrics.loadTime > 3000) {
            suggestions.push('تحسين وقت التحميل - ضغط الملفات');
        }
        
        if (this.metrics.memoryUsage > 100) {
            suggestions.push('تحسين استخدام الذاكرة - تنظيف الكاش');
        }
        
        if (this.metrics.networkRequests > 50) {
            suggestions.push('تقليل طلبات الشبكة - تجميع الملفات');
        }
        
        console.log('💡 اقتراحات التحسين:', suggestions);
        
        return suggestions;
    }
    
    // تقرير الأداء
    generateReport() {
        return {
            metrics: this.metrics,
            score: this.calculatePerformanceScore(),
            suggestions: this.suggestOptimizations(),
            timestamp: new Date().toISOString()
        };
    }
}

// إنشاء نسخة من محسن الأداء
const performanceOptimizer = new PerformanceOptimizer();

// تقرير الأداء كل 5 دقائق
setInterval(() => {
    const report = performanceOptimizer.generateReport();
    console.log('📊 تقرير الأداء:', report);
}, 300000);
    
