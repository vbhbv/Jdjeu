# main.py (الكود النهائي المُحسَّن لحلقة التشغيل)
from telethon import TelegramClient, events
import logging
import asyncio
from config import API_ID, API_HASH, TARGET_CHANNEL_ID, TELEGRAM_BOT_TOKEN 

# إعداد التسجيل...
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# تعريف العملاء
bot_client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=TELEGRAM_BOT_TOKEN)
user_client = TelegramClient('user_session', API_ID, API_HASH)

# ... (بقية الدالة search_and_forward كما هي) ...

# ... (بقية الدالة message_handler كما هي) ...

# ----------------
# التشغيل الرئيسي المُحسن والأكثر استقراراً
# ----------------
async def run_bot():
    print("Attempting to connect User Client (This may ask for phone number/code)...")
    
    # 💡 الخطوة الحرجة: محاولة الاتصال الصريح بحساب المستخدم 
    # يتم استخدام start() هنا بشكل مباشر
    await user_client.start()
    
    print("User Client connected successfully (or session file found).")
    
    # يجب أن يتم الاتصال بالبوت بعد نجاح اتصال المستخدم لضمان استقرار API
    print("Bot Client started and ready.")
    
    print(f"Bot is running... Ready for Telethon search in {TARGET_CHANNEL_ID}.")
    
    # ابدأ البوت (للتفاعل مع المستخدمين) وانتظر حتى يتم إيقافه
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    try:
        # يتم تشغيل الكود بطريقة Telethon الموصى بها
        with user_client:
            user_client.loop.run_until_complete(run_bot())
    except Exception as e:
        # في حال حدوث خطأ، يجب أن يحاول Telethon إعادة الاتصال
        print(f"An error occurred during startup: {e}")
