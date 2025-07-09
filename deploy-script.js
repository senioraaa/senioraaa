#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const https = require('https');
const { execSync } = require('child_process');

class DeploymentManager {
    constructor() {
        this.config = {
            siteName: 'shahd-senior-platform',
            domain: 'shahd-senior.onrender.com',
            buildCommand: './build.sh',
            gitRepo: 'https://github.com/username/shahd-senior-platform',
            renderAPIKey: process.env.RENDER_API_KEY,
            telegramBotToken: process.env.TELEGRAM_BOT_TOKEN,
            chatId: process.env.TELEGRAM_CHAT_ID
        };
        
        this.deploymentLog = [];
    }
    
    async deploy() {
        console.log('🚀 بدء عملية النشر...');
        
        try {
            // 1. التحقق من البيئة
            await this.checkEnvironment();
            
            // 2. تشغيل الاختبارات
            await this.runTests();
            
            // 3. بناء المشروع
            await this.buildProject();
            
            // 4. رفع الملفات
            await this.uploadFiles();
            
            // 5. التحقق من النشر
            await this.verifyDeployment();
            
            // 6. إرسال إشعار النجاح
            await this.sendSuccessNotification();
            
            console.log('✅ تم النشر بنجاح!');
            
        } catch (error) {
            console.error('❌ خطأ في النشر:', error);
            await this.sendErrorNotification(error);
            process.exit(1);
        }
    }
    
    async checkEnvironment() {
        this.log('🔍 التحقق من البيئة...');
        
        // التحقق من Node.js
        const nodeVersion = process.version;
        console.log(`Node.js version: ${nodeVersion}`);
        
        // التحقق من Git
        try {
            const gitVersion = execSync('git --version', { encoding: 'utf8' });
            console.log(`Git version: ${gitVersion.trim()}`);
        } catch (error) {
            throw new Error('Git غير مثبت');
        }
        
        // التحقق من متغيرات البيئة
        const requiredEnvVars = ['RENDER_API_KEY', 'TELEGRAM_BOT_TOKEN'];
        for (const envVar of requiredEnvVars) {
            if (!process.env[envVar]) {
                throw new Error(`متغير البيئة ${envVar} غير موجود`);
            }
        }
        
        this.log('✅ البيئة جاهزة');
    }
    
    async runTests() {
        this.log('🧪 تشغيل الاختبارات...');
        
        try {
            // تشغيل اختبارات الوحدة
            execSync('npm test', { stdio: 'inherit' });
            
            // تشغيل اختبارات الأداء
            execSync('npm run test:performance', { stdio: 'inherit' });
            
            this.log('✅ جميع الاختبارات نجحت');
            
        } catch (error) {
            throw new Error('فشلت الاختبارات');
        }
    }
    
    async buildProject() {
        this.log('🔨 بناء المشروع...');
        
        try {
            // تشغيل سكريبت البناء
            execSync(this.config.buildCommand, { stdio: 'inherit' });
            
            // التحقق من وجود مجلد dist
            if (!fs.existsSync('dist')) {
                throw new Error('مجلد dist غير موجود');
            }
            
            // التحقق من الملفات الأساسية
            const requiredFiles = ['index.html', 'fc25.html', 'css/style.css', 'js/main.js'];
            for (const file of requiredFiles) {
                if (!fs.existsSync(path.join('dist', file))) {
                    throw new Error(`الملف ${file} غير موجود`);
                }
            }
            
            this.log('✅ تم بناء المشروع بنجاح');
            
        } catch (error) {
            throw new Error(`خطأ في بناء المشروع: ${error.message}`);
        }
    }
    
    async uploadFiles() {
        this.log('📤 رفع الملفات...');
        
        try {
            // رفع الملفات إلى Git
            execSync('git add dist/', { stdio: 'inherit' });
            execSync('git commit -m "Production build"', { stdio: 'inherit' });
            execSync('git push origin main', { stdio: 'inherit' });
            
            this.log('✅ تم رفع الملفات بنجاح');
            
        } catch (error) {
            throw new Error(`خطأ في رفع الملفات: ${error.message}`);
        }
    }
    
    async verifyDeployment() {
        this.log('✅ التحقق من النشر...');
        
        const maxRetries = 10;
        const retryDelay = 30000; // 30 ثانية
        
        for (let i = 0; i < maxRetries; i++) {
            try {
                const response = await this.makeRequest(`https://${this.config.domain}`);
                if (response.statusCode === 200) {
                    this.log('✅ الموقع يعمل بشكل صحيح');
                    return;
                }
            } catch (error) {
                console.log(`المحاولة ${i + 1}/${maxRetries} فشلت، إعادة المحاولة...`);
                if (i < maxRetries - 1) {
                    await this.sleep(retryDelay);
                }
            }
        }
        
        throw new Error('فشل في التحقق من النشر');
    }
    
    async sendSuccessNotification() {
        const message = `
🎉 تم نشر موقع شهد السنيورة بنجاح!

🌐 الرابط: https://${this.config.domain}
⏰ الوقت: ${new Date().toLocaleString('ar-EG')}
📊 الإحصائيات:
${this.deploymentLog.join('\n')}

✅ الموقع جاهز للاستخدام!
        `;
        
        await this.sendTelegramMessage(message);
    }
    
    async sendErrorNotification(error) {
        const message = `
❌ فشل في نشر موقع شهد السنيورة

🔥 الخطأ: ${error.message}
⏰ الوقت: ${new Date().toLocaleString('ar-EG')}
📊 سجل العملية:
${this.deploymentLog.join('\n')}

يرجى مراجعة الأخطاء وإعادة المحاولة.
        `;
        
        await this.sendTelegramMessage(message);
    }
    
    async sendTelegramMessage(message) {
        const url = `https://api.telegram.org/bot${this.config.telegramBotToken}/sendMessage`;
        const data = JSON.stringify({
            chat_id: this.config.chatId,
            text: message,
            parse_mode: 'HTML'
        });
        
        try {
            await this.makeRequest(url, 'POST', data);
            console.log('✅ تم إرسال الإشعار');
        } catch (error) {
            console.error('❌ فشل إرسال الإشعار:', error);
        }
    }
    
    makeRequest(url, method = 'GET', data = null) {
        return new Promise((resolve, reject) => {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'User-Agent': 'Shahd-Senior-Deploy/1.0'
                }
            };
            
            if (data) {
                options.headers['Content-Length'] = Buffer.byteLength(data);
            }
            
            const req = https.request(url, options, (res) => {
                let body = '';
                res.on('data', (chunk) => body += chunk);
                res.on('end', () => {
                    resolve({
                        statusCode: res.statusCode,
                        headers: res.headers,
                        body: body
                    });
                });
            });
            
            req.on('error', reject);
            
            if (data) {
                req.write(data);
            }
            
            req.end();
        });
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    log(message) {
        console.log(message);
        this.deploymentLog.push(`${new Date().toISOString()}: ${message}`);
    }
}

// تشغيل النشر
if (require.main === module) {
    const deployment = new DeploymentManager();
    deployment.deploy();
}

module.exports = DeploymentManager;
    
