# scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import logging

from config import NOOR_BOOK_BASE_URL, NOOR_BOOK_SEARCH_URL, MAX_SEARCH_RESULTS

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        # محاكاة متصفح حقيقي لتجنب حظر الخادم
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def search_library(self, query):
        """يبحث عن الكتب باستخدام محددات CSS أكثر مرونة."""
        encoded_query = quote(query)
        search_url = NOOR_BOOK_SEARCH_URL.format(query=encoded_query)
        
        logging.info(f"Searching: {search_url}")
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            results = []
            
            # 💡 التعديل المبتكر: استهداف الحاويات المشتركة (Container)
            # نبحث عن كلاسات شائعة لبطاقات الكتب (تم إضافة بدائل)
            book_containers = soup.select('.book-card-item, .book-card, .book-item') 
            
            if not book_containers:
                logging.warning("No book containers found using common selectors.")
            
            for container in book_containers[:MAX_SEARCH_RESULTS]:
                
                # 1. البحث عن رابط الكتاب داخل الحاوية (رابط صفحة الكتاب التفصيلية)
                # نحاول استهداف أي رابط داخل الحاوية يؤدي إلى صفحة كتاب محددة (URL path contains /book-)
                book_link_element = container.select_one('a[href*="/book-"]')
                
                if book_link_element:
                    book_link_partial = book_link_element.get('href')
                    book_full_link = urljoin(NOOR_BOOK_BASE_URL, book_link_partial)
                    
                    # 2. البحث عن العنوان (نحاول استخلاصه من عدة أماكن شائعة)
                    title_element = container.select_one('.book-card-title, h3 a, h4 a, .book-title')
                    
                    # إذا لم نجد عنواناً محدداً، نستخدم النص داخل رابط العنصر
                    book_title = title_element.text.strip() if title_element else book_link_element.text.strip()
                    
                    if book_title and book_full_link:
                        results.append({
                            'title': book_title,
                            'url': book_full_link
                        })
            
            return results

        except Exception as e:
            logging.error(f"Error during scraping search: {e}")
            return []

    def get_download_info(self, book_url):
        """تستخرج رابط التحميل المباشر باستخدام محددات أكثر موثوقية."""
        logging.info(f"Visiting book page: {book_url}")
        
        try:
            response = requests.get(book_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 💡 التعديل المبتكر: استهداف زر التحميل المباشر
            # هذا المحدد الشامل يغطي معظم احتمالات رابط التحميل المباشر
            download_button = soup.select_one(
                'a[href$=".pdf"], '       # رابط ينتهي بـ .pdf
                'a[href$=".epub"], '      # رابط ينتهي بـ .epub
                'a[download], '           # وسم يحمل خاصية download (قياسي)
                'a.btn-download, '        # كلاس شائع لزر التحميل
                'a[href*="/download/"]'   # رابط يحتوي على مسار /download/
            )
            
            if download_button:
                download_link_partial = download_button.get('href')
                download_link = urljoin(NOOR_BOOK_BASE_URL, download_link_partial)
                
                # تخمين الامتداد
                file_ext = '.pdf' if '.pdf' in download_link.lower() else '.epub'
                
                return download_link, file_ext
            
            return None, None

        except Exception as e:
            logging.error(f"Error during download link extraction: {e}")
            return None, None
