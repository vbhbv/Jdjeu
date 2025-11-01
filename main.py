# main.py (الكود المعدل لضمان الاتصال)
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
# التشغيل الرئيسي المُحسن
# ----------------
async def main_loop():
    print("Attempting to connect User Client (This may ask for phone number/code)...")
    
    # 💡 الخطوة الحرجة: محاولة الاتصال الصريح بحساب المستخدم
    # إذا لم يكن هناك ملف user_session.session، سيطلب Telethon التسجيل.
    await user_client.start()
    
    print("User Client connected successfully (or session file found).")
    
    print("Bot is running... Ready for Telethon search in @lovekotob.")
    
    # ابدأ البوت (للتفاعل مع المستخدمين) وانتظر حتى يتم إيقافه
    await bot_client.run_until_disconnected()

if __name__ == '__main__':
    try:
        # يتم تشغيل حلقة الحدث (Event Loop) وتشغيل الدالة الرئيسية
        asyncio.run(main_loop())
    except Exception as e:
        print(f"An error occurred during startup: {e}")
