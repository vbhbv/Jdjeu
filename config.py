# config.py

# 1. رمز بوت تليجرام (Telegram Bot Token)
# يجب الحصول عليه من @BotFather
TELEGRAM_BOT_TOKEN = "7176379503:AAFWxDvwEQ9ZJo_1d_LD7fFsWxQc-Qnyz_E"

# 2. إعدادات أخرى
# عدد نتائج البحث المراد عرضها للمستخدم في كل قائمة
MAX_SEARCH_RESULTS = 5 

# 3. الروابط الأساسية للمكتبات الهدف (مكتبة النور كمثال للكشط)
# انتبه: يجب أن يكون هذا الرابط دقيقاً ليعمل الكشط
NOOR_BOOK_BASE_URL = "https://www.noor-book.com"
NOOR_BOOK_SEARCH_URL = NOOR_BOOK_BASE_URL + "/search?query={query}"
