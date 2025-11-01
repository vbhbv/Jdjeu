# main.py
from telethon import TelegramClient, events
import logging
import asyncio

# استيراد الإعدادات
from config import API_ID, API_HASH, TARGET_CHANNEL_ID, TELEGRAM_BOT_TOKEN 

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# تعريف البوت وحساب المستخدم (يتم استخدام نفس الـ ID والـ Hash لكلا العميلين)
# عميل البوت: مسؤول عن الرد على المستخدم
bot_client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=TELEGRAM_BOT_TOKEN)
# عميل المستخدم: مسؤول عن قوة البحث الفعلية
user_client = TelegramClient('user_session', API_ID, API_HASH)

async def search_and_forward(event):
    """
    يقوم بالبحث داخل القناة باستخدام حساب المستخدم وإعادة توجيه النتيجة عبر البوت.
    """
    query = event.raw_text.strip()
    chat_id = event.chat_id
    
    if query.startswith('/start'):
        await bot_client.send_message(
            chat_id, 
            f"👋 مرحباً! أنا الآن أستخدم حساباً قوياً للبحث عن ملفاتك داخل قناة `{TARGET_CHANNEL_ID}`. أرسل لي اسم الكتاب!"
        )
        return

    if not query:
        return

    logging.info(f"Searching for: {query} in {TARGET_CHANNEL_ID}")
    
    # 1. إرسال رسالة "جاري البحث"
    status_message = await bot_client.send_message(
        chat_id, 
        f"🔎 جاري البحث المتقدم عن الملفات لـ: `{query}`..."
    )

    try:
        # 2. الاتصال بحساب المستخدم والبحث داخله
        if not user_client.is_connected():
            await user_client.connect()
            
        # البحث باستخدام دالة get_messages القوية (لا يمكن للبوت العادي الوصول إليها)
        messages = await user_client.get_messages(
            TARGET_CHANNEL_ID, 
            limit=1,  # أفضل نتيجة واحدة
            search=query
        )

        if messages:
            # 3. إرسال النتيجة عبر البوت (عميل البوت هو الذي يرد على المستخدم)
            await bot_client.send_message(
                chat_id, 
                "✅ تم العثور على الملف! جاري إعادة توجيهه..."
            )
            
            # إعادة توجيه الرسالة التي عثر عليها حساب المستخدم إلى المستخدم
            await bot_client.forward_messages(
                chat_id, 
                messages[0], 
                TARGET_CHANNEL_ID
            )
            
            # 4. حذف رسالة الحالة
            await bot_client.delete_messages(chat_id, status_message)
            
        else:
            # 5. فشل البحث
            await bot_client.edit_message(
                chat_id, 
                status_message, 
                f"❌ عذراً، لم يتم العثور على كتاب يطابق '{query}' في قناة `{TARGET_CHANNEL_ID}`. حاول بكلمات مفتاحية أخرى."
            )

    except Exception as e:
        logging.error(f"Error during Telethon search/forward: {e}")
        await bot_client.edit_message(
            chat_id, 
            status_message, 
            f"❌ حدث خطأ غير متوقع أثناء عملية البحث. (تأكد من أن البوت والحساب عضوين في القناة)."
        )

# معالج الرسائل الجديدة (يرد على أي رسالة ليست أمراً)
@bot_client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and not e.text.startswith('/')))
async def message_handler(event):
    await search_and_forward(event)

# ----------------
# التشغيل الرئيسي
# ----------------
async def main():
    print("Bot is running... Ready for Telethon search.")
    # ابدأ البوت (للتفاعل مع المستخدمين)
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    try:
        # عند التشغيل لأول مرة، سيطلب Telethon رمز التحقق (Verification Code) لحساب المستخدم
        # يجب أن تكون مستعدًا لإدخال هذا الرمز في السجل (الـ Console)
        with bot_client:
            bot_client.loop.run_until_complete(main())
    except Exception as e:
        print(f"An error occurred during startup: {e}")
