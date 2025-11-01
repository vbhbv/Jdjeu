# scraper.py (الكود النهائي والأكثر تحصيناً)
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import logging

from config import NOOR_BOOK_BASE_URL, NOOR_BOOK_SEARCH_URL, MAX_SEARCH_RESULTS

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7' # لضمان عرض المحتوى العربي
        }

    def search_library(self, query):
        """يبحث عن الكتب باستخدام محددات تركز على مسار الرابط (Path) بدلاً من الكلاسات."""
        encoded_query = quote(query)
        search_url = NOOR_BOOK_SEARCH_URL.format(query=encoded_query)
        
        logging.info(f"Searching: {search_url}")
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            results = []
            
            # 💡 التعديل المبتكر والحاسم:
            # نستهدف أي رابط (a) يحتوي في خاصية href على مسار يبدو كصفحة كتاب
            # هذا المحدد أقل عرضة للتغيير من الكلاسات
            book_links = soup.select('a[href*="/book-"]')
            
            if not book_links:
                logging.warning(f"No book links found using a[href*='/book-'] for query: {query}")
                
                # محاولة احتياطية: استهداف أي رابط يحتوي على عنوان (قد يعمل)
                book_links = soup.select('a[title]') 

            
            # فلترة الروابط وتجميع النتائج
            unique_books = {}
            for link in book_links:
                book_link_partial = link.get('href')
                
                if book_link_partial and book_link_partial not in unique_books:
                    book_full_link = urljoin(NOOR_BOOK_BASE_URL, book_link_partial)
                    
                    # استخلاص العنوان من نص الرابط أو خاصية العنوان
                    book_title = link.get('title', link.text).strip()
                    
                    if len(book_title) > 5: # تجاهل الروابط القصيرة أو الفارغة
                        unique_books[book_link_partial] = {
                            'title': book_title,
                            'url': book_full_link
                        }

            # تحويل القاموس إلى قائمة وترتيبها
            results = list(unique_books.values())[:MAX_SEARCH_RESULTS]
            
            return results

        except Exception as e:
            logging.error(f"Critical Error during scraping search: {e}")
            return []

    def get_download_info(self, book_url):
        # ... (هذه الدالة تعمل بشكل جيد، سنبقيها كما هي)
        logging.info(f"Visiting book page: {book_url}")
        
        try:
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
