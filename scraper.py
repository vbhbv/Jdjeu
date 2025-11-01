# scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import logging

from config import NOOR_BOOK_BASE_URL, NOOR_BOOK_SEARCH_URL, MAX_SEARCH_RESULTS

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        # استخدام رؤوس HTTP لمحاكاة متصفح حقيقي (لتجنب الحظر)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search_library(self, query):
        """
        تبحث عن الكتب في مكتبة النور (أو موقع مستهدف آخر) وتستخرج الروابط لصفحات الكتب.
        """
        encoded_query = quote(query)
        search_url = NOOR_BOOK_SEARCH_URL.format(query=encoded_query)
        
        logging.info(f"Searching: {search_url}")
        
        try:
            # تنفيذ طلب HTTP GET لصفحة البحث
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # تحليل المحتوى باستخدام BeautifulSoup
            soup = BeautifulSoup(response.content, 'lxml')
            results = []
            
            # محدد CSS لبطاقات الكتب (يجب مطابقته لهيكل الموقع الهدف)
            book_cards = soup.select('.book-card-item a.book-card-link') 
            
            for card in book_cards[:MAX_SEARCH_RESULTS]:
                book_title = card.select_one('.book-card-title').text.strip() if card.select_one('.book-card-title') else "غير محدد"
                book_link_partial = card.get('href')
                
                if book_link_partial:
                    # بناء الرابط المطلق لصفحة الكتاب
                    book_full_link = urljoin(NOOR_BOOK_BASE_URL, book_link_partial)
                    results.append({
                        'title': book_title,
                        'url': book_full_link
                    })
            
            return results

        except Exception as e:
            logging.error(f"Error during scraping search: {e}")
            return []

    def get_download_info(self, book_url):
        """
        تدخل صفحة الكتاب وتستخرج رابط التحميل المباشر للملف (PDF/EPUB).
        """
        logging.info(f"Visiting book page: {book_url}")
        
        try:
            # 1. جلب صفحة الكتاب
            response = requests.get(book_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 2. البحث عن رابط التحميل المباشر
            # محددات CSS تستهدف الروابط التي تنتهي بـ .pdf أو .epub أو تحتوي على خاصية 'download'
            download_button = soup.select_one('a.btn-download[href$=".pdf"], a.btn-download[href$=".epub"], a[download]')
            
            if download_button:
                download_link_partial = download_button.get('href')
                download_link = urljoin(NOOR_BOOK_BASE_URL, download_link_partial)
                
                # تخمين الامتداد من الرابط
                file_ext = '.pdf' if '.pdf' in download_link.lower() else '.epub'
                
                return download_link, file_ext
            
            return None, None

        except Exception as e:
            logging.error(f"Error during download link extraction: {e}")
            return None, None
