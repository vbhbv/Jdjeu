# scraper.py (الكود النهائي للكشط المباشر والتفاوض الآلي)
import logging
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, urlparse
from config import MAX_SEARCH_RESULTS, NOOR_BOOK_BASE_URL

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        # رؤوس ثابتة لمحاكاة متصفح Chrome
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def search_library(self, query):
        """
        الكشط المباشر: يبحث عن روابط الكتاب الثابتة (/book-). (تم إصلاح المشكلة)
        """
        encoded_query = quote(query)
        # 💡 تم استبدال NOOR_BOOK_SEARCH_URL بالرابط المباشر لضمان عدم وجود خطأ
        search_url = NOOR_BOOK_BASE_URL + "/search?query=" + encoded_query 
        
        logging.info(f"Direct Scraping Search: {search_url}")
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            results = []
            
            # محدد CSS ثابت: استهداف أي رابط يحتوي على مسار الكتاب 
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
            logging.error(f"Error during direct scraping search: {e}")
            return []

    def get_download_info(self, book_url):
        """
        منطق التفاوض الآلي لفك تشفير رابط التحميل (محصن ضد الأخطاء).
        """
        logging.info(f"Attempting Automated Negotiation for download link: {book_url}")
        
        # تحديث رأس Referer ديناميكياً
        referer_domain = urlparse(book_url).scheme + "://" + urlparse(book_url).netloc
        current_headers = self.headers.copy()
        current_headers['Referer'] = referer_domain
        
        try:
            # 1. جلب صفحة الكتاب
            response = requests.get(book_url, headers=current_headers, timeout=15, allow_redirects=True)
            
            if response.status_code >= 400:
                logging.warning(f"Initial book page request failed with status: {response.status_code}")
                return None, "error"
                
            soup = BeautifulSoup(response.content, 'lxml')
            
            # 2. البحث عن أزرار التحميل الأكثر شيوعاً
            download_button = soup.select_one('a[href*="/download/"], a.btn-download, a[download], button')
            
            if download_button:
                download_link_partial = download_button.get('href') or download_button.get('data-href')

                if download_link_partial:
                    full_download_link = urljoin(response.url, download_link_partial)

                    # 3. التفاوض الآلي
                    negotiation_headers = self.headers.copy()
                    negotiation_headers['Referer'] = response.url

                    final_file_response = requests.get(
                        full_download_link, 
                        headers=negotiation_headers, 
                        timeout=30, 
                        allow_redirects=True
                    )
                    
                    final_url = final_file_response.url 
                    
                    # 4. التحقق من الرابط النهائي 
                    if final_url.lower().endswith(('.pdf', '.epub')):
                        file_ext = '.pdf' if final_url.lower().endswith('.pdf') else '.epub'
                        logging.info(f"Success! Found direct file link: {final_url}")
                        return final_url, file_ext
                
            return None, "link"
            
        except Exception as e:
            logging.error(f"Critical error during Automated Negotiation: {e}")
            return None, "error"
