# استخدام صورة بايثون أساسية تدعم Playwright (buster-slim)
FROM mcr.microsoft.com/playwright/python:v1.46.0-buster-slim

# تعيين دليل العمل
WORKDIR /app

# نسخ ملف متطلبات المكتبات
COPY requirements.txt .

# تثبيت متطلبات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود المتبقي
COPY . .

# أمر التشغيل النهائي
CMD ["python", "main.py"]
