import os
import asyncio
import tempfile
import aiofiles
import json
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes 
from playwright.async_api import async_playwright 
from urllib.parse import urljoin 

# استيراد مكتبة Gemini AI
from google import genai
from google.genai import types

# --- إعدادات Google CSE والمفاتيح ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
GOOGLE_CX = os.getenv("GOOGLE_CX")           
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # مفتاح Gemini
SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

# --- متغيرات ثابتة ---
USER_AGENT_HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
MIN_PDF_SIZE_BYTES = 50 * 1024 # 50 كيلوبايت كحد أدنى للملف
TEMP_LINKS_KEY = "current_search_links" 

# --- دوال مساعدة للشبكة (Utility Functions) ---

async def fetch_json(session: ClientSession, url: str, params=None):
    """جلب بيانات JSON (تستخدم لاستدعاء Google API)."""
    async with session.get(url, params=params, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.json()

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
    # جلب جميع النتائج المتاحة بغض النظر عن الموقع، وسيتم تصفيتها بواسطة Gemini
    for item in data.get("items", [])[:10]: # نأخذ أول 10 نتائج لنقدمها للذكاء الاصطناعي
        title = item.get("title")
        link = item.get("link")
        results.append({"title": title, "link": link})

    return results

# --- دالة تحليل الروابط باستخدام Gemini ---
async def analyze_search_results(query: str, results: list):
    """تستخدم Gemini لتقييم الروابط وتصفية الأفضل للتحميل."""
    
    if not GEMINI_API_KEY:
        print("⚠️ مفتاح GEMINI_API_KEY مفقود. سيتم تخطي تحليل الذكاء الاصطناعي.")
        return [item for item in results if "kotobati.com" in item.get('link') or "noor-book.com" in item.get('link')][:5]

    try:
        # تهيئة العميل (يستخدم المفتاح من متغيرات البيئة تلقائياً)
        client = genai.Client()
        
        # تحويل قائمة النتائج إلى نص منظم
        results_text = "\n".join([f"Link {i+1}: {item.get('title')} | {item.get('link')}" for i, item in enumerate(results)])

        # تعليمات النموذج
        prompt = f"""
        أنت خبير في البحث عن الكتب. طلب البحث الأصلي هو: "{query}".
        حلل قائمة الروابط التالية. حدد الروابط التي من المرجح أن تكون ملفات PDF أو صفحات تحميل كتب مباشرة (مثل نور بوك أو كتباتي) وتجاهل الروابط الإعلانية أو روابط المدونات.
        
        أعد النتائج على شكل قائمة Python (JSON) فقط، بدون أي نص إضافي أو شرح. يجب أن تحتوي القائمة على 5 نتائج كحد أقصى. لكل نتيجة، يجب أن يكون هناك مفتاح "is_relevant" بقيمة "نعم" أو "لا".
        
        مثال على التنسيق المطلوب:
        [
            {{"title": "العنوان", "link": "الرابط", "is_relevant": "نعم"}},
            ...
        ]
        
        الروابط للتحليل:
        {results_text}
        """
        
        # استدعاء نموذج Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        # تحليل استجابة JSON
        filtered_list = json.loads(response.text)
        
        # تصفية الروابط التي قال عنها النموذج "نعم"
        final_filtered_results = [
            item for item in filtered_list 
            if item.get('is_relevant', '').lower() == 'نعم'
        ]
        
        # العودة بالروابط التي تمت تصفيتها فقط (5 نتائج كحد أقصى)
        return final_filtered_results[:5]

    except Exception as e:
        print(f"⚠️ فشل تحليل الذكاء الاصطناعي: {e}. العودة إلى التصفية اليدوية.")
        return [item for item in results if "kotobati.com" in item.get('link') or "noor-book.com" in item.get('link')][:5]


# --- دالة مساعدة لاستخلاص رابط PDF باستخدام Playwright (النسخة الأكثر موثوقية) ---
async def get_pdf_link_from_page(link: str):
    """يستخدم Playwright لفتح الصفحة واستخلاص رابط PDF النهائي والمباشر."""
    pdf_link = None
    page_title = "book" 
    browser = None 

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # الانتقال بانتظار تحميل الهيكل (domcontentloaded)
            await page.goto(link, wait_until="domcontentloaded", timeout=30000) 
            
            html_content = await page.content()

            soup = BeautifulSoup(html_content, "html.parser")
            page_title = soup.title.string if soup.title else "book"
            
            # 1. الاستراتيجية الخاصة بنور بوك: البحث عن زر التحميل (book-dl-btn)
            if "noor-book.com" in link:
                download_button = soup.select_one("a.book-dl-btn")
                if download_button and download_button.get("href"):
                    href = download_button.get("href")
                    pdf_link = urljoin(link, href)
                    
            # 2. الاستراتيجية العامة: البحث عن رابط مباشر
            if not pdf_link:
                for a in soup.select("a[href]"):
                    href = a["href"]
                    if href.lower().endswith(".pdf") or "download" in href.lower():
                        if href.startswith("/"):
                            pdf_link = urljoin(link, href)
                        else:
                            pdf_link = href
                        break 
            
        return pdf_link, page_title
    
    except Exception as e:
        raise e
    
    finally:
        # ضمان إغلاق المتصفح في كل الأحوال
        if browser:
            await browser.close()
            print("تم ضمان إغلاق متصفح Playwright.")


# --- دالة التحميل والإرسال والحذف ---
async def download_and_send_pdf(context, chat_id, pdf_url, title="book.pdf"):
    """تحميل الملف، إرساله إلى المستخدم، ثم حذفه من القرص الصلب."""
    tmp_dir = tempfile.gettempdir()
    file_path = os.path.join(tmp_dir, title.replace("/", "_")[:40] + ".pdf")
    
    async with ClientSession() as session:
        # ClientSession يعالج إعادة التوجيه (Redirection) تلقائياً
        async with session.get(pdf_url, headers=USER_AGENT_HEADER) as resp:
            if resp.status != 200:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"⚠️ لم أتمكن من تحميل الملف من المصدر. رمز الخطأ: {resp.status}"
                )
                return
            
            content = await resp.read()

            if len(content) < MIN_PDF_SIZE_BYTES:
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text="⚠️ فشل التحميل: الملف المُرسَل يبدو فارغًا أو حجمه صغير جدًا. قد يكون رابط التحميل غير صحيح."
                )
                return
            
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
            
            try:
                await context.bot.send_document(
                    chat_id=chat_id, 
                    document=open(file_path, "rb")
                )
                await context.bot.send_message(chat_id=chat_id, text="✅ تم إرسال الكتاب بنجاح.")
            except Exception as e:
                 await context.bot.send_message(chat_id=chat_id, text=f"⚠️ خطأ أثناء إرسال الملف إلى تيليجرام: {e}")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"تم حذف الملف المؤقت: {file_path}")
                
# --- دوال أوامر تيليجرام (Telegram Commands) ---

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 مرحبًا بك في بوت تحميل الكتب الذكي!\n"
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
            # 1. جلب النتائج الأولية من Google CSE
            initial_results = await search_google_cse(session, query) 

        if not initial_results:
            await msg.edit_text("❌ لم أجد نتائج. حاول بكلمات مختلفة.")
            return

        # 2. تحليل النتائج باستخدام Gemini لتصفيتها
        await msg.edit_text("🧠 جاري تحليل النتائج باستخدام الذكاء الاصطناعي...")
        results = await analyze_search_results(query, initial_results)
        
        if not results:
            await msg.edit_text("❌ لم يجد الذكاء الاصطناعي أي رابط تحميل شرعي من بين النتائج. حاول بكلمات بحث أخرى.")
            return

        buttons = []
        text_lines = []
        
        # حفظ قائمة الروابط الكاملة التي تم تصفيتها
        context.user_data[TEMP_LINKS_KEY] = [item.get("link") for item in results]
        
        # عرض النتائج التي تم تصفيتها
        for i, item in enumerate(results, start=0):
            title = item.get("title")[:120]
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
            index_str = data.split("|", 1)[1]
            index = int(index_str)
            
            if TEMP_LINKS_KEY not in context.user_data or index >= len(context.user_data[TEMP_LINKS_KEY]):
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ انتهت صلاحية رابط التحميل أو لم يعد موجودًا. يرجى البحث مجدداً.",
                )
                return

            link = context.user_data[TEMP_LINKS_KEY][index]

        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⚠️ حدث خطأ أثناء معالجة زر التحميل (رابط غير صالح). يرجى البحث مجدداً.",
            )
            return
            
        await query.edit_message_text("⏳ أستخدم متصفح وهمي لجلب رابط الملف النهائي...")
        
        # --- استدعاء الدالة المنفصلة ---
        try:
            pdf_link, title = await get_pdf_link_from_page(link)
            
            if pdf_link:
                await download_and_send_pdf(context, query.message.chat_id, pdf_link, title=title if title else "book")
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"📄 لم أجد رابط PDF مباشر. هذا هو المصدر:\n{link}",
                )
        
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"⚠️ خطأ Playwright أثناء جلب الملف من المصدر: {e}",
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
