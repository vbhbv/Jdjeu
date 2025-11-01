import os
import asyncio
import tempfile
import aiofiles
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- إعدادات Google CSE ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # مفتاح API
GOOGLE_CX = os.getenv("GOOGLE_CX")           # معرّف محرك البحث المخصص (CX)
SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# --- دوال مساعدة للشبكة (Utility Functions) ---

async def fetch_json(session: ClientSession, url: str, params=None):
    async with session.get(url, params=params, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.json()

async def fetch_html(session: ClientSession, url: str):
    async with session.get(url, timeout=20) as resp:
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
    
    # استدعاء Google Custom Search API
    data = await fetch_json(session, SEARCH_URL, params=params)
    
    results = []
    # Google API يعيد قائمة بالنتائج في المفتاح "items"
    for item in data.get("items", [])[:5]: # نقتصر على أول 5 نتائج
        title = item.get("title")
        link = item.get("link")
        
        # التأكد من أن الرابط من أحد المصادر الموثوقة (اختياري لكن جيد للأمان)
        if "kotobati.com" in link or "noor-book.com" in link:
             results.append({"title": title, "link": link})

    return results

# --- دوال أوامر تيليجرام (Telegram Commands) ---

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 مرحبًا بك في بوت تحميل الكتب!\n"
        "البحث يتم الآن عبر Google API لضمان أفضل نتائج من كتوباتي ونور.\n\n"
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
            # استخدام دالة البحث الجديدة
            results = await search_google_cse(session, query)

        if not results:
            await msg.edit_text("❌ لم أجد نتائج. حاول بكلمات مختلفة.")
            return

        buttons = []
        text_lines = []
        # عرض أول 5 نتائج فقط
        for i, item in enumerate(results[:5], start=1):
            title = item.get("title")[:120]
            link = item.get("link")
            text_lines.append(f"{i}. {title}")
            # نمرر الرابط لزر التحميل
            buttons.append([InlineKeyboardButton(f"📥 تحميل {i}", callback_data=f"dl|{link}")])
            
        reply = "\n".join(text_lines)
        await msg.edit_text(reply, reply_markup=InlineKeyboardMarkup(buttons))
        
    except ValueError as e:
         await msg.edit_text(f"⚠️ خطأ في الإعداد: {e}")
    except Exception as e:
         await msg.edit_text(f"⚠️ حدث خطأ أثناء البحث: {e}")


async def download_and_send_pdf(context, chat_id, pdf_url, title="book.pdf"):
    # (هذه الدالة تبقى كما هي للتحميل المباشر بعد إيجاد رابط الـ PDF النهائي)
    async with ClientSession() as session:
        async with session.get(pdf_url) as resp:
            if resp.status != 200:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ لم أتمكن من تحميل الملف من المصدر.")
                return

            # تأمين مكان مؤقت لكتابة الملف
            tmp_dir = tempfile.gettempdir()
            file_path = os.path.join(tmp_dir, title.replace("/", "_")[:40] + ".pdf")
            
            # كتابة الملف بشكل غير متزامن
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(await resp.read())
            
            # إرسال الملف ومسحه
            try:
                # يجب فتح الملف للقراءة
                await context.bot.send_document(chat_id=chat_id, document=open(file_path, "rb"))
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

async def callback_handler(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("dl|"):
        link = data.split("|", 1)[1]
        await query.edit_message_text("⏳ أبحث عن رابط ملف PDF داخل صفحة المصدر...")
        
        async with ClientSession() as session:
            try:
                # جلب محتوى الصفحة التي أعادتها Google (سواء كتوباتي أو نور)
                html = await fetch_html(session, link)
                soup = BeautifulSoup(html, "html.parser")
                pdf_link = None
                
                # البحث عن رابط PDF مباشر داخل الصفحة
                for a in soup.select("a[href]"):
                    href = a["href"]
                    # بحث عن رابط ينتهي بـ .pdf
                    if href.lower().endswith(".pdf") or "download" in href.lower():
                        # يجب التأكد من أنه رابط كامل
                        if href.startswith("/"):
                            # إنشاء الرابط الكامل (مثال: kotobati.com/...)
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

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("البوت بدأ العمل... اضغط Ctrl+C للإيقاف.")
    app.run_polling()

if __name__ == "__main__":
    main()
