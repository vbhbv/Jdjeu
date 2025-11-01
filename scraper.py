# scraper.py (الكود النهائي باستخدام requests_html)
from requests_html import HTMLSession # 💡 تغيير الاستيراد
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup 
import logging

from config import NOOR_BOOK_BASE_URL, NOOR_BOOK_SEARCH_URL, MAX_SEARCH_RESULTS

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        # استخدام HTMLSession للتعامل مع الـ DOM وتنفيذ JS
        self.session = HTMLSession()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def search_library(self, query):
        """يبحث وينفذ JavaScript للصفحة لضمان ظهور النتائج."""
        encoded_query = quote(query)
        search_url = NOOR_BOOK_SEARCH_URL.format(query=encoded_query)
        
        logging.info(f"Searching and Rendering: {search_url}")
        
        try:
            # 1. جلب الصفحة
            response = self.session.get(search_url, headers=self.headers, timeout=20)
            
            # 2. 💡 تنفيذ JavaScript: هذه الخطوة الحاسمة!
            # نجعل البوت ينتظر 3 ثوانٍ لتحميل المحتوى الديناميكي
            response.html.render(sleep=3, timeout=30, scrolldown=1) 
            
            # 3. استخدام المحتوى المُنفذ (Rendered Content) مع BeautifulSoup
            soup = BeautifulSoup(response.html.html, 'lxml') 
            results = []
            
            # محددات البحث (نستخدم المحددات المرنة التي عملنا عليها سابقاً)
            book_links = soup.select('a[href*="/book-"]')
            
            unique_books = {}
            for link in book_links:
                book_link_partial = link.get('href')
                
                if book_link_partial and book_link_partial not in unique_books:
                    book_full_link = urljoin(NOOR_BOOK_BASE_URL, book_link_partial)
                    book_title = link.get('title', link.text).strip()
                    
                    if len(book_title) > 5 and book_title.lower() != 'details':
                        unique_books[book_link_partial] = {
                            'title': book_title,
                            'url': book_full_link
                        }

            results = list(unique_books.values())[:MAX_SEARCH_RESULTS]
            
            return results

        except Exception as e:
            logging.error(f"Critical Error during rendering/scraping search: {e}")
            return []
    
    # دالة get_download_info لا تحتاج إلى تغيير كبير لأنها تستهدف رابط تحميل ثابت
    def get_download_info(self, book_url):
        # ... (احتفظ بالكود الأصلي لهذه الدالة لكن استخدم self.session)
        # مثال: response = self.session.get(book_url, headers=self.headers, timeout=15)
        # ... (يجب تعديل استخدام requests.get إلى self.session.get في هذه الدالة أيضاً)
        pass # سيتم وضع الكود الكامل أدناه

# الكود الكامل والمحدث لـ scraper.py (لاستبدال الملف كاملاً)
