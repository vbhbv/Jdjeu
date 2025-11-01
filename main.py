import os
import asyncio
import tempfile
import aiofiles
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
# تم إضافة ContextTypes هنا لتصحيح الخطأ!
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes 

# --- إعدادات Google CSE والمفاتيح ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
GOOGLE_CX = os.getenv("GOOGLE_CX")           
SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# --- متغيرات ثابتة ---
USER_AGENT_HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
MIN_PDF_SIZE_BYTES = 50 * 1024 # 50 كيلوبايت كحد أدنى للملف
TEMP_LINKS_KEY = "current_search_links" 

# --- دوال مساعدة للشبكة (Utility Functions) ---

async def fetch_json(session: ClientSession, url: str, params=None):
    async with session.get(url, params=params, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.json()

async def fetch_html(session: ClientSession, url: str):
    """جلب HTML مع User-Agent لتجاوز حظر الخوادم (403)."""
    async with session.get(url, headers=USER_AGENT_HEADER, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.text()

# --- دالة البحث الرئيسية باستخدام Google CSE ---

async def search_google_cse(session: ClientSession, query: str):
    """يبحث في محرك Google المخصص ويعيد النتائج."""
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        raise ValueError("Google API Key or CX is missing in environment variables.")
        
    params = {
        "q": query,
        "cx": GOOGLE_CX,
        "key": GOOGLE_API_KEY
    }
    
    data = await fetch_json(session, SEARCH_URL, params=params)
    
    results = []
    for item in data.get("items", [])[:5]:
        title = item.get("title")
        link = item.get("link")
        
        # التأكد من أن الرابط من أحد المصادر الموثوقة (اختياري لكن جيد للأمان)
        if "kotobati.com" in link or "noor-book.com" in link:
             results.append({"title": title, "link": link})

    return results

# --- دالة التحميل والإرسال والحذف (مُحسّنة) ---
async def download_and_send_pdf(context, chat_id, pdf_url, title="book.pdf"):
    """تحميل الملف، إرساله إلى المستخدم، ثم حذفه من القرص الصلب."""
    tmp_dir = tempfile.gettempdir()
    file_path = os.path.join(tmp_dir, title.replace("/", "_")[:40] + ".pdf")
    
    async with ClientSession() as session:
        # استخدام User-Agent لتجاوز حظر التحميل
        async with session.get(pdf_url, headers=USER_AGENT_HEADER) as resp:
            if resp.status != 200:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"⚠️ لم أتمكن من تحميل الملف من المصدر. رمز الخطأ: {resp.status}"
                )
                return
            
            # قراءة محتوى الاستجابة
            content = await resp.read()

            # التحقق من حجم المحتوى (حل مشكلة الملفات الفارغة)
            if len(content) < MIN_PDF_SIZE_BYTES:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text="⚠️ فشل التحميل: الملف المُرسَل يبدو فارغًا أو حجمه صغير جدًا. قد يكون رابط التحميل غير صحيح."
                )
                return
            
            # كتابة الملف بشكل غير متزامن
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
            
            # إرسال الملف ومسحه
            try:
                # إرسال الملف (يجب فتحه للقراءة الثنائية)
                await context.bot.send_document(
                    chat_id=chat_id, 
                    document=open(file_path, "rb")
                )
                await context.bot.send_message(chat_id=chat_id, text="✅ تم إرسال الكتاب بنجاح.")
            except Exception as e:
                 await context.bot.send_message(chat_id=chat_id, text=f"⚠️ خطأ أثناء إرسال الملف إلى تيليجرام: {e}")
            finally:
                # ضمان حذف الملف من النظام بعد انتهاء محاولة الإرسال
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"تم حذف الملف المؤقت: {file_path}")
                
# --- دوال أوامر تيليجرام (Telegram Commands) ---

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 مرحبًا بك في بوت تحميل الكتب!\n"
        "أرسل أمر /search متبوعًا باسم الكتاب أو المؤلف.\n\n"
        "مثال:\n/search قلعة العز"
    )

async def search_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("استخدم: /search اسم الكتاب أو المؤلف")
        return

    msg = await update.message.reply_text("🔍 أبحث عن الكتاب عبر Google API...")
    
    try:
        async with ClientSession() as session:
            results = await search_google_cse(session, query)

        if not results:
            await msg.edit_text("❌ لم أجد نتائج. حاول بكلمات مختلفة.")
            return

        buttons = []
        text_lines = []
        
        # حفظ قائمة الروابط الكاملة مؤقتاً في بيانات المستخدم لحل مشكلة Button_data_invalid
        context.user_data[TEMP_LINKS_KEY] = [item.get("link") for item in results[:5]]
        
        # عرض أول 5 نتائج
        for i, item in enumerate(results[:5], start=0): # البدء من الفهرس 0
            title = item.get("title")[:120]
            # نستخدم i كفهرس (رقم قصير) بدلاً من الرابط الطويل
            text_lines.append(f"{i+1}. {title}")
            buttons.append([InlineKeyboardButton(f"📥 تحميل {i+1}", callback_data=f"dl|{i}")])
            
        reply = "\n".join(text_lines)
        await msg.edit_text(reply, reply_markup=InlineKeyboardMarkup(buttons))
        
    except ValueError as e:
         await msg.edit_text(f"⚠️ خطأ في الإعداد: {e}")
    except Exception as e:
         await msg.edit_text(f"⚠️ حدث خطأ أثناء البحث: {e}")


async def callback_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("dl|"):
        try:
            # استرجاع الرابط من context.user_data
            index_str = data.split("|", 1)[1]
            index = int(index_str)
            
            # التحقق من وجود الروابط المخزنة
            if TEMP_LINKS_KEY not in context.user_data or index >= len(context.user_data[TEMP_LINKS_KEY]):
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ انتهت صلاحية رابط التحميل أو لم يعد موجودًا. يرجى البحث مجدداً.",
                )
                return

            # جلب الرابط الكامل من القائمة المخزنة
            link = context.user_data[TEMP_LINKS_KEY][index]

        except Exception:
            # معالجة خطأ Button_data_invalid
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⚠️ حدث خطأ أثناء معالجة زر التحميل (رابط غير صالح). يرجى البحث مجدداً.",
            )
            return
            
        await query.edit_message_text("⏳ أبحث عن رابط ملف PDF داخل صفحة المصدر...")
        
        async with ClientSession() as session:
            try:
                # نستخدم دالة fetch_html المحسّنة برأس User-Agent
                html = await fetch_html(session, link) 
                soup = BeautifulSoup(html, "html.parser")
                pdf_link = None
                
                # البحث عن رابط PDF مباشر داخل الصفحة
                for a in soup.select("a[href]"):
                    href = a["href"]
                    if href.lower().endswith(".pdf") or "download" in href.lower():
                        if href.startswith("/"):
                            from urllib.parse import urljoin
                            pdf_link = urljoin(link, href)
                        else:
                            pdf_link = href
                        break 
                        
                if pdf_link:
                    await download_and_send_pdf(context, query.message.chat_id, pdf_link, title=soup.title.string if soup.title else "book")
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"📄 لم أجد رابط PDF مباشر داخل الصفحة. هذا هو رابط المصدر:\n{link}",
                    )
            except Exception as e:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"⚠️ حدث خطأ أثناء جلب الملف من المصدر: {e}",
                )

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing in environment variables.")

    # تأكد من استيراد ContextTypes في الأعلى!
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("البوت بدأ العمل... اضغط Ctrl+C للإيقاف.")
    app.run_polling()

if __name__ == "__main__":
    main()
