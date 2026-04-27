import requests
import json
import base64
import google.generativeai as genai
import pdfplumber
import io
from openai import OpenAI
from typing import List, Dict

def fetch_kap_disclosure_list(year: int, month: int) -> List[Dict]:
    """
    KAP'tan belirli ay/yıl için portföy dağılım bildirim listesini çeker.
    "SKP" (Portföy Dağılım Raporu) tipindeki bildirimleri filtreler.
    """
    url = f"https://www.kap.org.tr/tr/api/disclosures/year/{year}/month/{month}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    print(f"KAP Bildirim listesi çekiliyor: {year}/{month}")
    response = None
    import time
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code == 200:
                break
            print(f"Hata: {response.status_code}. Deneme: {attempt+1}/3")
        except Exception as e:
            print(f"Bağlantı hatası: {e}. Deneme: {attempt+1}/3")
        time.sleep(5)
        
    if not response or response.status_code != 200:
        return []
    
    try:
        data = response.json()
        # Tip filtresi: "SKP" = Portföy Dağılım Raporu
        return [b for b in data if b.get('tip') == 'SKP']
    except Exception as e:
        print(f"JSON parse hatası: {e}")
        return []

def download_pdf(bildirim_id: str) -> bytes:
    """Belirli bir bildirim ID'si için PDF dosyasını indirir."""
    url = f"https://www.kap.org.tr/tr/api/BildirimPdf/{bildirim_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    import time
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=60)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            if attempt == 2:
                raise Exception(f"PDF indirilemedi. Hata: {e}")
            time.sleep(5)
    raise Exception(f"PDF indirilemedi. Status: {response.status_code if 'response' in locals() and response else 'Bilinmiyor'}")

def gemini_pdf_parse(pdf_content: bytes, api_key: str, sirket_adi: str) -> List[Dict]:
    """
    Gemini 2.0 Flash modelini kullanarak PDF içeriğinden hisse senedi portföy satırlarını ayıklar.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
    
    prompt = """Bu PDF bir Türk yatırım fonu portföy dağılım raporudur.
Tablodaki her satır için şu JSON array'i döndür (başka hiçbir şey yazma):
[{"fund_company_name":"","fund_name":"","ticker":"","isin":"","weight_pct":0.0, "position_try":0.0, "report_date":""}]
- weight_pct: yüzde ağırlık (sayısal)
- position_try: TL nominal değer (sayısal, yoksa 0)
- report_date: YYYY-MM-DD formatında
- Hisse senedi olmayan satırları (nakit, repo vb.) dahil etme."""

    try:
        response = model.generate_content([
            {'mime_type': 'application/pdf', 'data': base64_pdf},
            prompt
        ])
        
        text = response.text.strip()
        # JSON bloğunu temizle
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        kayitlar = json.loads(text)
        for k in kayitlar:
            if not k.get('fund_company_name'):
                k['fund_company_name'] = sirket_adi
        return kayitlar
    except Exception as e:
        print(f"Gemini parse hatası: {e}")
        return []

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """PDF içeriğinden metni çıkarır."""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        print(f"Metin çıkarma hatası: {e}")
    return text

def deepseek_pdf_parse(pdf_content: bytes, api_key: str, sirket_adi: str) -> List[Dict]:
    """
    DeepSeek API kullanarak PDF metninden portföy verilerini ayıklar.
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    print("   -> PDF'den metin ayıklanıyor...")
    pdf_text = extract_text_from_pdf(pdf_content)
    
    if not pdf_text.strip():
        print("   -> HATA: PDF'den metin çıkarılamadı (Resim formatında olabilir).")
        return []

    prompt = f"""Aşağıda bir Türk yatırım fonunun portföy dağılım raporu metni yer almaktadır.
Bu metindeki hisse senedi portföy tablosunu bul ve her bir hisse senedi satırı için şu JSON array'ini döndür:
[
  {{"fund_company_name": "{sirket_adi}", "fund_name": "", "ticker": "", "isin": "", "weight_pct": 0.0, "position_try": 0.0, "report_date": ""}}
]
- Sadece JSON döndür.
- Hisse senedi olmayan (nakit, repo vb.) satırları dahil etme.

METİN:
{pdf_text[:15000]}
"""

    try:
        print("   -> DeepSeek AI ile analiz yapılıyor...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Sen finansal tabloları JSON formatına dönüştüren uzman bir asistansın."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        
        text = response.choices[0].message.content.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        return json.loads(text)
    except Exception as e:
        print(f"DeepSeek parse hatası: {e}")
        return []
