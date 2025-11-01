# scraper.py
from requests_html import HTMLSession
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup 
import logging
import requests # لإمكانية استخدام Requests في حال فشلت الجلسة الآلية

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
        search_url = NOOR_BOOK_BASE_URL + "/search?query=" + encoded_query # استخدام هذا النمط يضمن عمل الرابط
        
        logging.info(f"Searching and Rendering: {search_url}")
        
        try:
            # 1. جلب الصفحة (بواسطة requests_html)
            response = self.session.get(search_url, headers=self.headers, timeout=30)
            
            # 2. تنفيذ JavaScript: هذه الخطوة الحاسمة!
            # ننتظر 3 ثوانٍ لتحميل المحتوى الديناميكي (قد تحتاج الاستضافة إلى مكتبات إضافية مثل pyppeteer)
            response.html.render(sleep=3, timeout=40, scrolldown=1) 
            
            # 3. استخدام المحتوى المُنفذ (Rendered Content)
            soup = BeautifulSoup(response.html.html, 'lxml') 
            
            # محددات البحث (نستهدف أي رابط يحتوي في خاصية href على مسار كتاب)
            book_links = soup.select('a[href*="/book-"]')
            
            unique_books = {}
            for link in book_links:
                book_link_partial = link.get('href')
                
                if book_link_partial and book_link_partial not in unique_books:
                    book_full_link = urljoin(NOOR_BOOK_BASE_URL, book_link_partial)
                    book_title = link.get('title', link.text).strip()
                    
                    if len(book_title) > 5 and book_title.lower() not in ['details', 'read more']:
                        unique_books[book_link_partial] = {
                            'title': book_title,
                            'url': book_full_link
                        }

            results = list(unique_books.values())[:MAX_SEARCH_RESULTS]
            
            return results

        except Exception as e:
            logging.error(f"Critical Error during rendering/scraping search: {e}")
            # في حال فشل التقديم (Rendering) بسبب عدم توفر المتصفح الآلي
            return []

    def get_download_info(self, book_url):
        """تستخرج رابط التحميل المباشر."""
        logging.info(f"Visiting book page: {book_url}")
        
        try:
            # استخدام requests العادي لصفحة التحميل قد يكون أسرع
            response = requests.get(book_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            download_button = soup.select_one(
                'a[href$=".pdf"], '       
                'a[href$=".epub"], '      
                'a[download], '           
                'a.btn-download, '        
                'a[href*="/download/"]'   
            )
            
            if download_button:
                download_link_partial = download_button.get('href')
                download_link = urljoin(NOOR_BOOK_BASE_URL, download_link_partial)
                
                file_ext = '.pdf' if '.pdf' in download_link.lower() else '.epub'
                
                return download_link, file_ext
            
            return None, None

        except Exception as e:
            logging.error(f"Error during download link extraction: {e}")
            return None, None
