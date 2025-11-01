# في main.py

# ... (كل التعريفات والدوال السابقة تبقى كما هي، بما في ذلك fetch_html و download_and_send_pdf المعدلتين بالـ User-Agent) ...

# ... (نستخدم USER_DATA لتخزين الروابط بشكل مؤقت لكل مستخدم)
# هذا يُخزن بيانات مؤقتة داخل الذاكرة (Memory) للبوت
TEMP_LINKS_KEY = "current_search_links" 


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
        
        # --- التعديل هنا: تخزين الروابط في context.user_data ---
        
        # حفظ قائمة الروابط الكاملة مؤقتاً في بيانات المستخدم
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
            # --- التعديل هنا: استرجاع الرابط من context.user_data ---
            index_str = data.split("|", 1)[1] # نجلب الفهرس (0، 1، 2، إلخ)
            index = int(index_str)
            
            # التأكد من وجود الروابط المخزنة
            if TEMP_LINKS_KEY not in context.user_data or index >= len(context.user_data[TEMP_LINKS_KEY]):
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ انتهت صلاحية رابط التحميل أو لم يعد موجودًا. يرجى البحث مجدداً.",
                )
                return

            # جلب الرابط الكامل من القائمة المخزنة
            link = context.user_data[TEMP_LINKS_KEY][index]

        except Exception:
            # معالجة الخطأ الذي ظهر لك: Button_data_invalid
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="⚠️ حدث خطأ أثناء معالجة زر التحميل (رابط غير صالح). يرجى البحث مجدداً.",
            )
            return
            
        await query.edit_message_text("⏳ أبحث عن رابط ملف PDF داخل صفحة المصدر...")
        
        async with ClientSession() as session:
            try:
                # ... (باقي كود جلب وتحليل HTML يبقى كما هو) ...
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

# ... (دالة main تبقى كما هي) ...

