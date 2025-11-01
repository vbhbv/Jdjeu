# main.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from config import TELEGRAM_BOT_TOKEN
from scraper import LibraryScraper

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

scraper = LibraryScraper()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحباً بك في بوت المكتبة العربية! أرسل لي اسم الكتاب للبحث والتحميل المباشر الآمن."
    )

# دالة التعامل مع رسائل البحث
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    
    await update.message.reply_text(f"🔎 جاري توليد رابط البحث المباشر والفعّال لـ: `{query}`...", parse_mode='Markdown')
    
    try:
        results = scraper.search_library(query)
        
        if not results:
            await update.message.reply_text("❌ حدث خطأ داخلي في توليد رابط البحث. يرجى المحاولة لاحقاً.")
            return

        book = results[0] # ناخذ النتيجة الوحيدة (رابط البحث)
        
        # إنشاء زر يفتح الرابط مباشرة في متصفح المستخدم
        keyboard = [
            [InlineKeyboardButton(f"🚀 اضغط للبحث عن: {query} (PDF/EPUB)", url=book['url'])]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **النجاح مضمون!** اضغط على الزر أدناه ليتم توجيهك مباشرة لصفحة نتائج بحث جوجل التي تحتوي على ملفات {query} بصيغة PDF/EPUB.",
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

    except Exception as e:
        logging.error(f"Search operation failed: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع أثناء عملية توليد الرابط.")

# دالة التشغيل الرئيسية
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # ⚠️ تم حذف CallbackQueryHandler تماماً لأنه لم يعد هناك زر تحميل
    
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
