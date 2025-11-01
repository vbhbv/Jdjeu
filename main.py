import os
import asyncio
import tempfile
import aiofiles
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def fetch_html(session: ClientSession, url: str, params=None):
    async with session.get(url, params=params, timeout=20) as resp:
        resp.raise_for_status()
        return await resp.text()

async def search_kotobati(session: ClientSession, query: str):
    url = "https://www.kotobati.com/"
    params = {"s": query}
    html = await fetch_html(session, url, params=params)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for a in soup.select("article a[href]")[:6]:
        title = a.get_text(strip=True)
        href = a["href"]
        results.append({"title": title, "link": href})
    return results

async def search_noor(session: ClientSession, query: str):
    url = "https://www.noor-book.com/"
    params = {"s": query}
    html = await fetch_html(session, url, params=params)
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for el in soup.select(".book-item a[href]")[:6]:
        title = el.get_text(strip=True)
        href = el["href"]
        results.append({"title": title, "link": href})
    return results

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 مرحبًا بك في بوت تحميل الكتب!\n"
        "أرسل أمر /search متبوعًا باسم الكتاب أو المؤلف للبحث في مكتبة نور وكتوباتي.\n\n"
        "مثال:\n/search قلعة العز"
    )

async def search_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("استخدم: /search اسم الكتاب أو المؤلف")
        return

    msg = await update.message.reply_text("🔍 أبحث عن الكتاب...")
    async with ClientSession() as session:
        done = await asyncio.gather(
            search_kotobati(session, query),
            search_noor(session, query),
            return_exceptions=True,
        )

    results = []
    for r in done:
        if isinstance(r, list):
            results.extend(r)

    if not results:
        await msg.edit_text("❌ لم أجد نتائج. حاول بكلمات مختلفة.")
        return

    buttons = []
    text_lines = []
    for i, item in enumerate(results[:5], start=1):
        title = item.get("title")[:120]
        link = item.get("link")
        text_lines.append(f"{i}. {title}")
        buttons.append([InlineKeyboardButton(f"📥 تحميل {i}", callback_data=f"dl|{link}")])

    reply = "\n".join(text_lines)
    await msg.edit_text(reply, reply_markup=InlineKeyboardMarkup(buttons))

async def download_and_send_pdf(context, chat_id, pdf_url, title="book.pdf"):
    async with ClientSession() as session:
        async with session.get(pdf_url) as resp:
            if resp.status != 200:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ لم أتمكن من تحميل الملف من المصدر.")
                return
            tmp_dir = tempfile.gettempdir()
            file_path = os.path.join(tmp_dir, title.replace("/", "_")[:40] + ".pdf")
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(await resp.read())

    try:
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
        await query.edit_message_text("⏳ أبحث عن رابط الملف...")
        async with ClientSession() as session:
            try:
                html = await fetch_html(session, link)
                soup = BeautifulSoup(html, "html.parser")
                pdf_link = None
                for a in soup.select("a[href]"):
                    href = a["href"]
                    if href.lower().endswith(".pdf"):
                        pdf_link = href
                        break
                if not pdf_link:
                    iframe = soup.find("iframe")
                    if iframe and iframe.get("src", "").lower().endswith(".pdf"):
                        pdf_link = iframe["src"]

                if pdf_link:
                    await download_and_send_pdf(context, query.message.chat_id, pdf_link)
                else:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"📄 لم أجد رابط PDF مباشر. هذا هو المصدر:\n{link}",
                    )
            except Exception as e:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"⚠️ حدث خطأ أثناء جلب الكتاب: {e}",
                )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()

if __name__ == "__main__":
    main()

