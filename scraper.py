# scraper.py (الكود المحصن)
import logging
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, urlparse # استيراد urlparse
from config import MAX_SEARCH_RESULTS, NOOR_BOOK_BASE_URL

logging.basicConfig(level=logging.INFO)

class LibraryScraper:
    
    def __init__(self):
        # لم نعد نحدد Referer هنا بل نحدده ديناميكياً
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    # ... (دالة search_library تبقى كما هي)
    # ...

    def get_download_info(self, book_url):
        """
        المنطق المحصن: تفاوض آلي، تحديث ديناميكي لرأس Referer، ومعالجة أخطاء أفضل.
        """
        logging.info(f"Attempting Automated Negotiation for download link: {book_url}")
        
        # 💡 النقد 4: تحديث رأس Referer ديناميكياً
        # نستخدم book_url كمرجع لتحميل الروابط من نفس النطاق
        referer_domain = urlparse(book_url).scheme + "://" + urlparse(book_url).netloc
        
        current_headers = self.base_headers.copy()
        current_headers['Referer'] = referer_domain
        
        try:
            # 1. جلب صفحة الكتاب (النقد 5: مرونة أفضل)
            response = requests.get(book_url, headers=current_headers, timeout=15, allow_redirects=True)
            
            # 💡 النقد 5: لا نستخدم raise_for_status() بشكل صارم في البداية
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

                    # 3. التفاوض الآلي: طلب الرابط المباشر
                    # يجب أن يكون full_download_link هو الآن المرجع (Referer) للخطوة التالية
                    negotiation_headers = self.base_headers.copy()
                    negotiation_headers['Referer'] = response.url # صفحة الكتاب هي المرجع

                    final_file_response = requests.get(
                        full_download_link, 
                        headers=negotiation_headers, # استخدام الرؤوس الجديدة
                        timeout=30, 
                        allow_redirects=True
                    )
                    
                    final_url = final_file_response.url 
                    
                    # 4. التحقق من الرابط النهائي (النقد 2: تجاهل صفحة الانتظار)
                    # إذا كان الرابط النهائي يشير إلى ملف، أو إذا كان الرابط ينتهي بـ .php أو .html
                    if final_url.lower().endswith(('.pdf', '.epub')):
                        file_ext = '.pdf' if final_url.lower().endswith('.pdf') else '.epub'
                        logging.info(f"Success! Found direct file link: {final_url}")
                        return final_url, file_ext
                    
                    # 💡 النقد 2: فشل التحقق النهائي
                    logging.warning(f"Final URL is not a file: {final_url}")
            
            # 💡 النقد 1: لم نجد زر تحميل وظيفي (بسبب JavaScript)
            logging.warning("Failed to find a functional download link (JS dependency likely).")
            return None, "link"
            
        except Exception as e:
            logging.error(f"Critical error during Automated Negotiation: {e}")
            return None, "error"
