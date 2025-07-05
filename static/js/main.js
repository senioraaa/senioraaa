class ProgressTracker {
    constructor() {
        this.steps = [
            { id: 'whatsapp', name: 'رقم الواتساب', required: true },
            { id: 'platform', name: 'المنصة المفضلة', required: true },
            { id: 'payment', name: 'طريقة الدفع', required: true },
            { id: 'ea_email', name: 'بريد EA', required: false },
            { id: 'telegram', name: 'ربط التليجرام', required: false },
            { id: 'profile', name: 'إكمال الملف', required: false }
        ];
        
        this.userData = this.loadUserData();
        this.init();
    }
    
    init() {
        this.createProgressHTML();
        this.updateProgress();
    }
    
    createProgressHTML() {
        const container = document.getElementById('progress-tracker');
        if (!container) return;
        
        container.innerHTML = this.steps.map((step, index) => `
            <div class="progress-step" data-step="${step.id}">
                <div class="step-circle" id="step-${step.id}">
                    ${index + 1}
                </div>
                <div class="step-label">${step.name}</div>
            </div>
        `).join('');
    }
    
    updateProgress() {
        this.steps.forEach((step, index) => {
            const circle = document.getElementById(`step-${step.id}`);
            const stepElement = document.querySelector(`[data-step="${step.id}"]`);
            
            if (!circle || !stepElement) return;
            
            const isCompleted = this.isStepCompleted(step.id);
            const isRequired = step.required;
            
            circle.className = 'step-circle';
            stepElement.className = 'progress-step';
            
            if (isCompleted) {
                circle.classList.add('completed');
                stepElement.classList.add('completed');
                circle.innerHTML = '<i class="fas fa-check"></i>';
            } else if (isRequired) {
                circle.classList.add('pending');
                stepElement.classList.add('pending');
                circle.innerHTML = index + 1;
            } else {
                circle.classList.add('current');
                stepElement.classList.add('current');
                circle.innerHTML = index + 1;
            }
        });
        
        this.updateCompletionPercentage();
    }
    
    isStepCompleted(stepId) {
        switch(stepId) {
            case 'whatsapp':
                return this.userData.whatsapp && this.userData.whatsapp.length > 0;
            case 'platform':
                return this.userData.preferred_platform && this.userData.preferred_platform.length > 0;
            case 'payment':
                return this.userData.preferred_payment && this.userData.preferred_payment.length > 0;
            case 'ea_email':
                return this.userData.ea_email && this.userData.ea_email.length > 0;
            case 'telegram':
                return this.userData.telegram_id && this.userData.telegram_id.length > 0;
            case 'profile':
                const requiredSteps = this.steps.filter(s => s.required);
                return requiredSteps.every(s => this.isStepCompleted(s.id));
            default:
                return false;
        }
    }
    
    updateCompletionPercentage() {
        const completed = this.steps.filter(step => this.isStepCompleted(step.id)).length;
        const percentage = Math.round((completed / this.steps.length) * 100);
        
        const percentageElement = document.getElementById('completion-percentage');
        if (percentageElement) {
            percentageElement.textContent = `${percentage}%`;
        }
        
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
        }
    }
    
    loadUserData() {
        const userData = localStorage.getItem('userData');
        return userData ? JSON.parse(userData) : {};
    }
    
    saveUserData(data) {
        this.userData = { ...this.userData, ...data };
        localStorage.setItem('userData', JSON.stringify(this.userData));
        this.updateProgress();
    }
}

class AutoSave {
    constructor() {
        this.saveTimeout = null;
        this.isOnline = navigator.onLine;
        this.indicator = document.getElementById('saveIndicator');
        this.progressTracker = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupOfflineHandling();
    }
    
    setupEventListeners() {
        document.addEventListener('input', (e) => {
            if (e.target.matches('.auto-save')) {
                this.handleInput(e.target);
            }
        });
        
        document.addEventListener('change', (e) => {
            if (e.target.matches('.auto-save')) {
                this.handleChange(e.target);
            }
        });
    }
    
    setupOfflineHandling() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.syncPendingChanges();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }
    
    handleInput(field) {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        
        this.saveTimeout = setTimeout(() => {
            this.saveField(field);
        }, 500);
    }
    
    handleChange(field) {
        this.saveField(field);
    }
    
    async saveField(field) {
        if (!this.isOnline) {
            this.saveToLocal(field);
            return;
        }
        
        this.showIndicator('saving', 'جاري الحفظ...');
        
        try {
            const formData = new FormData();
            formData.append(field.name, field.value);
            formData.append('field', field.name);
            
            const response = await fetch('/profile/update', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showIndicator('saved', 'تم الحفظ ✓');
                
                if (this.progressTracker) {
                    this.progressTracker.saveUserData({ [field.name]: field.value });
                }
            } else {
                throw new Error(result.message || 'خطأ في الحفظ');
            }
            
        } catch (error) {
            console.error('خطأ في الحفظ التلقائي:', error);
            this.showIndicator('error', 'فشل الحفظ ✗');
            this.saveToLocal(field);
        }
    }
    
    saveToLocal(field) {
        const pendingChanges = JSON.parse(localStorage.getItem('pendingChanges') || '{}');
        pendingChanges[field.name] = field.value;
        localStorage.setItem('pendingChanges', JSON.stringify(pendingChanges));
        
        this.showIndicator('saved', 'محفوظ محلياً');
    }
    
    async syncPendingChanges() {
        const pendingChanges = JSON.parse(localStorage.getItem('pendingChanges') || '{}');
      
        if (Object.keys(pendingChanges).length === 0) return;
        
        try {
            const formData = new FormData();
            Object.entries(pendingChanges).forEach(([key, value]) => {
                formData.append(key, value);
            });
            
            const response = await fetch('/profile/update', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                localStorage.removeItem('pendingChanges');
                this.showIndicator('saved', 'تم المزامنة ✓');
                
                if (this.progressTracker) {
                    this.progressTracker.saveUserData(pendingChanges);
                }
            }
            
        } catch (error) {
            console.error('خطأ في المزامنة:', error);
        }
    }
    
    showIndicator(type, message) {
        if (!this.indicator) return;
        
        this.indicator.className = `save-indicator ${type}`;
        this.indicator.textContent = message;
        
        setTimeout(() => {
            this.indicator.style.opacity = '0';
            setTimeout(() => {
                this.indicator.className = 'save-indicator';
            }, 300);
        }, 2000);
    }
}

class TelegramBot {
    constructor() {
        this.botUsername = 'YourBotUsername';
        this.init();
    }
    
    init() {
        this.setupTelegramButtons();
    }
    
    setupTelegramButtons() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('.telegram-connect-btn')) {
                this.openTelegramBot();
            }
        });
    }
    
    openTelegramBot() {
        const userId = this.getCurrentUserId();
        const startParam = btoa(userId);
        const telegramUrl = `https://t.me/${this.botUsername}?start=${startParam}`;
        
        window.open(telegramUrl, '_blank');
        
        this.showInstructions();
    }
    
    showInstructions() {
        const modal = this.createInstructionModal();
        document.body.appendChild(modal);
        
        setTimeout(() => {
            modal.style.opacity = '1';
            modal.style.visibility = 'visible';
        }, 100);
    }
    
    createInstructionModal() {
        const modal = document.createElement('div');
        modal.className = 'telegram-modal';
        modal.innerHTML = `
            <div class="modal-overlay">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3><i class="fab fa-telegram"></i> ربط حساب التليجرام</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="instruction-steps">
                            <div class="step">
                                <div class="step-number">1</div>
                                <div class="step-text">اضغط على زر "ابدأ" في البوت</div>
                            </div>
                            <div class="step">
                                <div class="step-number">2</div>
                                <div class="step-text">أرسل أي رسالة للبوت</div>
                            </div>
                            <div class="step">
                                <div class="step-number">3</div>
                                <div class="step-text">ستحصل على User ID تلقائياً</div>
                            </div>
                        </div>
                        <div class="instruction-note">
                            <i class="fas fa-info-circle"></i>
                            سيتم ربط حسابك تلقائياً بعد إرسال الرسالة الأولى
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        modal.querySelector('.modal-close').onclick = () => {
            modal.style.opacity = '0';
            modal.style.visibility = 'hidden';
            setTimeout(() => {
                document.body.removeChild(modal);
            }, 300);
        };
        
        modal.querySelector('.modal-overlay').onclick = (e) => {
            if (e.target === modal.querySelector('.modal-overlay')) {
                modal.querySelector('.modal-close').click();
            }
        };
        
        return modal;
    }
    
    getCurrentUserId() {
        const metaTag = document.querySelector('meta[name="user-id"]');
        return metaTag ? metaTag.content : Date.now().toString();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    window.progressTracker = new ProgressTracker();
    window.autoSave = new AutoSave();
    window.telegramBot = new TelegramBot();
    
    window.autoSave.progressTracker = window.progressTracker;
});

window.updateProgressTracker = function() {
    if (window.progressTracker) {
        window.progressTracker.updateProgress();
    }
};
