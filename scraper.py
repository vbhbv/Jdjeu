# scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import logging
import time # للتأخير في حال الحاجة

from config import NOOR_BOOK_BASE_URL, NOOR_BOOK_SEARCH_URL, MAX_SEARCH_RESULTS

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        # رؤوس ثابتة لمحاكاة متصفح Chrome على ويندوز
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def search_library(self, query):
        """يبحث عن الكتب باستخدام محددات تركز على مسار الرابط الثابت (/book-)."""
        encoded_query = quote(query)
        search_url = NOOR_BOOK_BASE_URL + "/search?query=" + encoded_query
        
        logging.info(f"Searching: {search_url}")
        
        try:
            # إضافة تأخير بسيط لتجنب الكشف الآلي
            time.sleep(1) 
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            results = []
            
            # محدد CSS قوي: استهداف أي رابط يحتوي على '/book-' في مساره
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
            logging.error(f"Error during search: {e}")
            return []

    def get_download_info(self, book_url):
        """
        المنطق المبتكر: يتتبع إعادة التوجيه للوصول إلى الرابط المباشر للملف (PDF/EPUB).
        """
        logging.info(f"Visiting book page to find download link: {book_url}")
        
        try:
            # 1. جلب صفحة الكتاب
            response = requests.get(book_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 2. تحديد موقع زر التحميل (أكثر المحددات ثباتاً)
            download_button = soup.select_one('a[href*="/download/"], a.btn-download')
            
            if download_button:
                download_link_partial = download_button.get('href')
                full_download_link = urljoin(NOOR_BOOK_BASE_URL, download_link_partial)

                # 3. الخطوة الحاسمة: تتبع إعادة التوجيه
                # نستخدم allow_redirects=True للحصول على الرابط النهائي بعد التحويلات
                final_file_response = requests.get(
                    full_download_link, 
                    headers=self.headers, 
                    timeout=30, 
                    allow_redirects=True
                )
                
                final_url = final_file_response.url 
                
                # 4. التحقق من الرابط النهائي 
                if final_url.lower().endswith(('.pdf', '.epub')):
                    file_ext = '.pdf' if final_url.lower().endswith('.pdf') else '.epub'
                    return final_url, file_ext
                
            return None, None

        except Exception as e:
            logging.error(f"Error during Direct URL Engineering: {e}")
            return None, None
