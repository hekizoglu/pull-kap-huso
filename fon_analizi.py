import os
import sys
import json
import csv
from datetime import datetime
from pykap.investment_funds import fetch_kap_disclosure_list, download_pdf, gemini_pdf_parse, deepseek_pdf_parse

def run_analysis(year, month, model_type):
    gemini_key = os.environ.get('GEMINI_API_KEY')
    deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
    
    if model_type == "gemini" and not gemini_key:
        print("Hata: GEMINI_API_KEY bulunamadı.")
        return
    if model_type == "deepseek" and not deepseek_key:
        print("Hata: DEEPSEEK_API_KEY bulunamadı.")
        return

    bildirimler = fetch_kap_disclosure_list(year, month)
    if not bildirimler:
        print(f"{year}/{month} dönemi için Portföy Dağılım Raporu (SKP) bulunamadı.")
        return

    print(f"Toplam {len(bildirimler)} adet Portföy Dağılım Raporu bulundu.")
    
    all_data = []
    MAX_ISLEM = 5 
    
    for i, b in enumerate(bildirimler[:MAX_ISLEM]):
        bildirim_id = b.get('id') or b.get('bildirimId')
        sirket_adi = b.get('sirketAdi') or b.get('kurulusAdi') or 'Bilinmeyen Şirket'
        print(f"\n[{i+1}/{MAX_ISLEM}] İşleniyor: {sirket_adi}")
        
        try:
            pdf_bytes = download_pdf(bildirim_id)
            
            if model_type == "gemini":
                parsed_rows = gemini_pdf_parse(pdf_bytes, gemini_key, sirket_adi)
            else:
                parsed_rows = deepseek_pdf_parse(pdf_bytes, deepseek_key, sirket_adi)
            
            if parsed_rows:
                print(f"   -> BAŞARILI: {len(parsed_rows)} hisse senedi verisi ayıklandı.")
                for row in parsed_rows:
                    row['model'] = model_type
                    row['report_year_month'] = f"{year}{str(month).zfill(2)}"
                    row['source_url'] = f"https://www.kap.org.tr/tr/Bildirim/{bildirim_id}"
                    all_data.append(row)
            else:
                print("   -> UYARI: Veri ayıklanamadı.")
                
        except Exception as e:
            print(f"   -> HATA: {e}")

    # Sonuçları Kaydet
    if all_data:
        json_filename = f"fon_analiz_{year}_{month}_{model_type}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        
        csv_filename = f"fon_analiz_{year}_{month}_{model_type}.csv"
        with open(csv_filename, "w", encoding="utf-8", newline="") as f:
            headers = all_data[0].keys()
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\n✅ Analiz tamamlandı. {len(all_data)} kayıt kaydedildi.")
        print(f"Dosyalar: {json_filename}, {csv_filename}")
    else:
        print("\n❌ Hiçbir veri çekilemedi.")

if __name__ == "__main__":
    # Komut satırı: python fon_analizi.py <yil> <ay> <model: gemini|deepseek>
    yil = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.now().year
    ay = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.now().month
    model = sys.argv[3].lower() if len(sys.argv) > 3 else "gemini"
    
    run_analysis(yil, ay, model)
