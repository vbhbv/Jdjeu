# scraper.py
import logging
import re
import requests
import time
from config import MAX_SEARCH_RESULTS
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup 

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        # رؤوس ثابتة لمحاكاة متصفح حقيقي
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def search_library(self, query):
        """
        تُجري بحثاً عاماً وشاملاً للعثور على صفحة الكتاب التفصيلية عبر محرك البحث.
        (لضمان العثور على الكتاب حتى لو لم يكن ملف PDF مفهرساً)
        """
        logging.info(f"Initiating broad search for book page: {query}")
        
        # 1. إنشاء استعلامات بحث عامة (استهداف صفحات الكتاب)
        search_queries = [
            f"site:noor-book.com {query} كتاب", # البحث عن صفحة الكتاب
            f"site:kutubati.com {query} كتاب"
        ]
        
        books = []
        
        # 2. تنفيذ البحث عبر أداة Google Search
        try:
            # 💡 يتم استخدام الأداة google:search هنا
            search_results = google.search(queries=search_queries)
        except Exception as e:
            logging.error(f"Google Search Tool Failed: {e}")
            return []
            
        
        # 3. فلترة النتائج وتجهيزها
        for result in search_results:
            url = result.url.lower()
            
            # التأكد من أن الرابط يشير لصفحة كتاب أو تحميل
            if 'book' in url or 'download' in url:
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
        تتأكد من نوع الملف وتعود بالرابط المباشر للملف عبر تتبع إعادة التوجيه.
        """
        logging.info(f"Checking link for direct file: {book_url}")
        
        try:
            # 1. محاولة تتبع إعادة التوجيه مباشرة من رابط النتيجة
            response = requests.get(book_url, allow_redirects=True, timeout=15, headers=self.headers)
            final_url = response.url
            
            # إذا كان الرابط النهائي يشير مباشرة لملف
            if final_url.lower().endswith(('.pdf', '.epub')):
                file_ext = '.pdf' if final_url.lower().endswith('.pdf') else '.epub'
                return final_url, file_ext
            
            # 2. إذا كان الرابط لا يزال صفحة ويب، نقوم بالكشط السريع لزر التحميل (كحل احتياطي)
            soup = BeautifulSoup(response.content, 'lxml')
            download_button = soup.select_one('a[href*="/download/"], a.btn-download')
            
            if download_button:
                download_link_partial = download_button.get('href')
                # استخدام final_url كـ base url في حال تم تحويل الرابط في الخطوة 1
                full_download_link = urljoin(final_url, download_link_partial) 
                
                # تتبع الرابط الجديد للتأكد من الرابط النهائي للملف
                final_file_response = requests.get(full_download_link, allow_redirects=True, timeout=30, headers=self.headers)
                final_file_url = final_file_response.url
                
                if final_file_url.lower().endswith(('.pdf', '.epub')):
                    file_ext = '.pdf' if final_file_url.lower().endswith('.pdf') else '.epub'
                    return final_file_url, file_ext

            return None, "link" # لم نجد رابط ملف مباشر
            
        except Exception as e:
            logging.error(f"Error during link check/redirection: {e}")
            return None, "error"
