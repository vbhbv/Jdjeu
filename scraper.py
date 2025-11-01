# scraper.py
import logging
import re
import requests
import time
from config import MAX_SEARCH_RESULTS
from urllib.parse import quote

# ⚠️ ملاحظة: هذا الملف يعتمد الآن على الأداة google:search المتاحة لي
# إذا كنت لا تستخدم هذه الأداة، يجب استبدالها بـ Google Custom Search API أو أي خدمة بحث أخرى.

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def search_library(self, query):
        """
        تقوم بإجراء بحث موثوق ومخصص باستخدام Google Search للحصول على روابط PDF مباشرة.
        """
        logging.info(f"Initiating powerful filetype search for: {query}")
        
        # 1. إنشاء استعلامات بحث موجهة لملفات PDF/EPUB داخل المواقع المستهدفة
        search_queries = [
            f"site:noor-book.com {query} filetype:pdf OR filetype:epub",
            f"site:kutubati.com {query} filetype:pdf OR filetype:epub"
        ]
        
        books = []
        
        # 2. تنفيذ البحث عبر أداة Google Search
        try:
            # 💡 يتم استخدام الأداة هنا لضمان النجاح وتجاوز الحماية
            search_results = google.search(queries=search_queries)
        except Exception as e:
            logging.error(f"Google Search Tool Failed: {e}")
            return []
            
        
        # 3. فلترة النتائج وتجهيزها
        for result in search_results:
            url = result.url.lower()
            
            # التأكد من أن الرابط يشير لملف
            if url.endswith(('.pdf', '.epub')) or ('download' in url and url.endswith(('.php', '.html'))):
                books.append({
                    # تنظيف عنوان النتيجة
                    'title': re.sub(r' \| .*', '', result.title).strip(),
                    'url': result.url 
                })
                if len(books) >= MAX_SEARCH_RESULTS:
                    break
        
        return books

    def get_download_info(self, book_url):
        """
        تتأكد من نوع الملف وتعود بالرابط المباشر. إذا لم يكن رابط ملف مباشر،
        فإنها تحاول تتبع إعادة التوجيه لضمان الحصول على الملف (تعمل كطبقة أمان).
        """
        logging.info(f"Checking link for direct file: {book_url}")
        
        try:
            # محاولة تتبع إعادة التوجيه
            response = requests.get(book_url, allow_redirects=True, timeout=15)
            final_url = response.url
            
            if final_url.lower().endswith(('.pdf', '.epub')):
                file_ext = '.pdf' if final_url.lower().endswith('.pdf') else '.epub'
                return final_url, file_ext
            
            # إذا لم ينتهِ الرابط بملف، يمكن أن نعود به كرابط
            return book_url, "link"
            
        except Exception as e:
            logging.error(f"Error during link check: {e}")
            return None, "error"
