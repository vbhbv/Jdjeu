# main.py
import logging
import os
import requests
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

from config import TELEGRAM_BOT_TOKEN
from scraper import LibraryScraper

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

scraper = LibraryScraper()

# 1. أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحباً بك في بوت المكتبة العربية! أرسل لي اسم الكتاب للبحث والتحميل المباشر الآمن."
    )

# 2. دالة التعامل مع رسائل البحث
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    await update.message.reply_text(f"🔎 جاري البحث عن: `{query}`...", parse_mode='Markdown')
    
    try:
        results = scraper.search_library(query)
        
        if not results:
            await update.message.reply_text(
                f"عذراً، لم يتم العثور على نتائج لـ `{query}`. يرجى التأكد من اسم الكتاب أو المحاولة بكلمات مختلفة.", 
                parse_mode='Markdown'
            )
            return

        book_list_text = f"📚 نتائج البحث ({len(results)} نتائج):\n"
        keyboard = []
        
        for i, book in enumerate(results):
            book_list_text += f"\n**{i + 1}. {book['title']}**"
            book_id_callback = f"download_{book['url']}" 
            keyboard.append([InlineKeyboardButton(f"⬇️ تحميل {i + 1}", callback_data=book_id_callback)])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            book_list_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

    except Exception as e:
        logging.error(f"Search operation failed: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع أثناء عملية البحث.")

# 3. دالة التعامل مع طلب التحميل والحذف الفوري
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """المنطق الكامل: جلب الرابط المباشر -> تحميل الملف -> إرساله -> حذفه فوراً."""
    query_callback = update.callback_query
    data = query_callback.data
    
    if data.startswith("download_"):
        book_url = data.replace("download_", "", 1)
        
        await query_callback.answer("جاري استخلاص رابط التحميل المباشر...")
        
        # 1. جلب رابط الملف المباشر (باستخدام المنطق المبتكر)
        download_link, file_ext = scraper.get_download_info(book_url)
        
        if not download_link or file_ext not in ['.pdf', '.epub']:
            await query_callback.message.reply_text("عذراً، لم نتمكن من العثور على رابط ملف مباشر (PDF/EPUB) لهذا الكتاب.")
            return

        await query_callback.message.reply_text("⏳ جاري تحميل الملف (PDF/EPUB) مؤقتاً على السيرفر، يرجى الانتظار...")
        
        temp_file_name = f"temp_book_{os.path.basename(book_url).split('?')[0]}_{time.time()}{file_ext}"
        
        try:
            # 2. تحميل الملف مباشرة من الرابط المكتشف
            file_response = requests.get(download_link, stream=True, timeout=90) # زيادة المهلة
            file_response.raise_for_status()
            
            with open(temp_file_name, 'wb') as temp_file:
                for chunk in file_response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
            
            # 3. إرسال الملف إلى تليجرام كوثيقة
            with open(temp_file_name, 'rb') as doc_file:
                await query_callback.message.reply_document(
                    document=doc_file,
                    caption="✅ تم تحميل الكتاب بنجاح. (تم **حذف الملف فوراً** من السيرفر للحفاظ على الذاكرة)",
                    parse_mode='Markdown'
                )

            # 4. الحذف الفوري
            os.remove(temp_file_name)
            logging.info(f"File {temp_file_name} successfully sent and deleted.")
            await query_callback.answer("تم إرسال الملف وحذفه من الذاكرة.")
            
        except Exception as e:
            logging.error(f"Error during file download/send: {e}")
            await query_callback.message.reply_text("❌ حدث خطأ أثناء تحميل الملف. قد يكون حجم الملف كبيراً جداً.")
        finally:
            # تنظيف أي ملفات متبقية في حالة وجود خطأ
            if os.path.exists(temp_file_name):
                os.remove(temp_file_name)
                logging.info(f"Cleaned up residual file: {temp_file_name}")

# 4. دالة التشغيل الرئيسية
def main():
    """تشغيل البوت."""
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
