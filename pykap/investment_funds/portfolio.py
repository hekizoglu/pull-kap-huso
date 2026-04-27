import requests
import json
import base64
import google.generativeai as genai
from typing import List, Dict

def fetch_kap_disclosure_list(year: int, month: int) -> List[Dict]:
    """
    KAP'tan belirli ay/yıl için portföy dağılım bildirim listesini çeker.
    "SKP" (Portföy Dağılım Raporu) tipindeki bildirimleri filtreler.
    """
    url = f"https://www.kap.org.tr/tr/api/disclosures/year/{year}/month/{month}"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json'
    }
    
    print(f"KAP Bildirim listesi çekiliyor: {year}/{month}")
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        print(f"Hata: {response.status_code}")
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
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"PDF indirilemedi. Status: {response.status_code}")

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
        # JSON bloğunu temizle (bazı durumlarda Gemini ```json ekleyebilir)
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        kayitlar = json.loads(text)
        # Şirket adını doldur (Eğer PDF'den gelmediyse)
        for k in kayitlar:
            if not k.get('fund_company_name'):
                k['fund_company_name'] = sirket_adi
        return kayitlar
    except Exception as e:
        print(f"Gemini parse hatası: {e}")
        return []
