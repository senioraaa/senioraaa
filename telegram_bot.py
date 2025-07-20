import os
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import json

# إعداد الـ Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغيرات البيئة
BOT_TOKEN = "7607085569:AAFE_NO4pVcgfVenU5R_GSEnauoFIQ0iVXo"
ADMIN_CHAT_ID = "1124247595"
WEBHOOK_URL = "https://senioraaa.onrender.com"

# قاعدة البيانات البسيطة للأسعار
PRICES_DB = {
    "ps4_primary": {"name": "PS4 Primary", "price": 100},
    "ps5_primary": {"name": "PS5 Primary", "price": 150},
    "fc25": {"name": "FC25", "price": 50}
}

# دالة فحص المشرف
def is_admin(user_id):
    return str(user_id) == ADMIN_CHAT_ID

# دالة /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
🎮 مرحباً بك في بوت شحن شاهد سينيور!

الأوامر المتاحة:
/help - قائمة الأوامر
/prices - عرض الأسعار
/status - حالة النظام

للمشرفين فقط:
/setprice - تعديل السعر
/editprices - تعديل جميع الأسعار
    """
    await update.message.reply_text(welcome_text)
    logger.info(f"User {update.effective_user.id} started the bot")

# دالة /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🔧 قائمة الأوامر المتاحة:

👤 للجميع:
/start - بدء البوت
/help - عرض المساعدة
/prices - عرض الأسعار الحالية
/status - حالة النظام

🔐 للمشرفين فقط:
/setprice [اللعبة] [السعر] - تحديد سعر لعبة
/editprices - تعديل جميع الأسعار

مثال لتغيير السعر:
/setprice ps4_primary 120
    """
    await update.message.reply_text(help_text)

# دالة /prices
async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices_text = "💰 الأسعار الحالية:\n\n"
    
    for key, game in PRICES_DB.items():
        prices_text += f"🎮 {game['name']}: {game['price']} جنيه\n"
    
    prices_text += "\n📞 للطلب تواصل معنا عبر الموقع"
    
    await update.message.reply_text(prices_text)
    logger.info(f"Prices displayed to user {update.effective_user.id}")

# دالة /setprice
async def setprice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ استخدم الأمر هكذا:\n/setprice [اللعبة] [السعر]\n\nمثال:\n/setprice ps4_primary 120"
            )
            return
        
        game_key = context.args[0].lower()
        new_price = int(context.args[1])
        
        if game_key in PRICES_DB:
            old_price = PRICES_DB[game_key]["price"]
            PRICES_DB[game_key]["price"] = new_price
            
            success_text = f"""
✅ تم تحديث السعر بنجاح!

🎮 اللعبة: {PRICES_DB[game_key]["name"]}
📊 السعر القديم: {old_price} جنيه
📈 السعر الجديد: {new_price} جنيه
            """
            await update.message.reply_text(success_text)
            logger.info(f"Price updated by admin {update.effective_user.id}: {game_key} = {new_price}")
        else:
            await update.message.reply_text(
                f"❌ لعبة غير موجودة!\n\nالألعاب المتاحة:\n" + 
                "\n".join([f"• {key}" for key in PRICES_DB.keys()])
            )
    
    except ValueError:
        await update.message.reply_text("❌ السعر لازم يكون رقم!")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

# دالة /editprices
async def editprices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ هذا الأمر للمشرفين فقط!")
        return
    
    edit_text = """
📝 تعديل الأسعار:

استخدم الأمر /setprice لتحديث كل سعر:

🎮 الألعاب المتاحة:
"""
    
    for key, game in PRICES_DB.items():
        edit_text += f"• /setprice {key} [السعر الجديد] - {game['name']} (حالياً: {game['price']} جنيه)\n"
    
    await update.message.reply_text(edit_text)

# دالة /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = """
📊 حالة النظام:

✅ البوت: يعمل بنجاح
✅ الأسعار: متوفرة
✅ قاعدة البيانات: متصلة

🕐 آخر تحديث: الآن
    """
    await update.message.reply_text(status_text)

# معالج الرسائل العادية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    response = f"تم استلام رسالتك: {text}\n\nاستخدم /help لمعرفة الأوامر المتاحة 😊"
    await update.message.reply_text(response)

# معالج الأخطاء
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f'Update {update} caused error {context.error}')
    
    if update and update.message:
        await update.message.reply_text(
            "❌ حدث خطأ في البوت! المطور تم إشعاره بالمشكلة."
        )

def main():
    """تشغيل البوت"""
    logger.info("🚀 بدء تشغيل البوت...")
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("prices", prices_command))
    application.add_handler(CommandHandler("setprice", setprice_command))
    application.add_handler(CommandHandler("editprices", editprices_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # معالج الرسائل العادية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # تشغيل البوت
    logger.info("✅ البوت يعمل الآن!")
    print("🎮 بوت شاهد سينيور يعمل الآن...")
    
    # استخدام polling للتطوير والاختبار
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
