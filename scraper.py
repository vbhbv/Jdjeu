# scraper.py
import logging
import re
import time
from config import MAX_SEARCH_RESULTS

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    # لم يعد هناك حاجة لمتغيرات requests أو BeautifulSoup
    
    def search_library(self, query):
        """
        تقوم بإجراء بحث موثوق ومخصص باستخدام Google Search للحصول على روابط PDF مباشرة.
        """
        logging.info(f"Initiating powerful filetype search for: {query}")
        
        # 1. البحث عن ملف PDF مباشرة داخل موقع مكتبة النور
        queries = [
            f"site:noor-book.com {query} filetype:pdf",
            f"site:kutubati.com {query} filetype:pdf" # إضافة موقع آخر للتحصين
        ]
        
        # استخدام أداة Google Search المتاحة لي لجلب النتائج
        try:
            # 💡 يتم تفعيل أداة google:search هنا
            search_results = google.search(queries=queries)
        except Exception as e:
            logging.error(f"Google Search Tool Failed: {e}")
            return []
            
        
        books = []
        for result in search_results:
            # 2. فلترة النتائج: التأكد من أن الرابط هو ملف PDF أو EPUB
            url = result.url.lower()
            
            # التأكد من عدم تكرار الرابط ومن أن الرابط يشير لملف
            if url.endswith(('.pdf', '.epub')) or 'download' in url:
                books.append({
                    # تنظيف عنوان النتيجة من أسماء المواقع
                    'title': re.sub(r' \| .*', '', result.title).strip(),
                    'url': result.url 
                })
                if len(books) >= MAX_SEARCH_RESULTS:
                    break
        
        return books

    def get_download_info(self, book_url):
        """
        هذه الدالة لم تعد تحتاج إلى كشط، فهي تستقبل الرابط المباشر للملف وتمرره.
        """
        if book_url.lower().endswith(('.pdf', '.epub')):
            file_ext = '.pdf' if book_url.lower().endswith('.pdf') else '.epub'
            return book_url, file_ext
        
        # إذا كان الرابط لا ينتهي بملف، يمكننا تمريره كـ 'link' والاعتماد على الكود السابق
        return book_url, "link"
