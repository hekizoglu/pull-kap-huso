import os
import sys
import json
import csv
from datetime import datetime
from pykap.investment_funds import fetch_kap_disclosure_list, download_pdf, gemini_pdf_parse

def run_analysis(year, month, gemini_key):
    if not gemini_key:
        print("Hata: GEMINI_API_KEY bulunamadı. Lütfen GitHub Secrets üzerinden ayarlayın.")
        return

    bildirimler = fetch_kap_disclosure_list(year, month)
    if not bildirimler:
        print(f"{year}/{month} dönemi için Portföy Dağılım Raporu (SKP) bulunamadı.")
        return

    print(f"Toplam {len(bildirimler)} adet Portföy Dağılım Raporu bulundu.")
    
    all_data = []
    # Quota/Hız yönetimi: Şimdilik ilk 5 tanesini işle (Test amaçlı)
    # Gerçek kullanımda bu sayı artırılabilir.
    MAX_ISLEM = 5 
    
    for i, b in enumerate(bildirimler[:MAX_ISLEM]):
        bildirim_id = b.get('id') or b.get('bildirimId')
        sirket_adi = b.get('sirketAdi') or b.get('kurulusAdi') or 'Bilinmeyen Şirket'
        print(f"\n[{i+1}/{MAX_ISLEM}] İşleniyor: {sirket_adi}")
        print(f"   -> Bildirim ID: {bildirim_id}")
        
        try:
            # 1. PDF İndir
            pdf_bytes = download_pdf(bildirim_id)
            
            # 2. Gemini ile Parse Et
            print(f"   -> Gemini AI ile PDF analiz ediliyor...")
            parsed_rows = gemini_pdf_parse(pdf_bytes, gemini_key, sirket_adi)
            
            if parsed_rows:
                print(f"   -> BAŞARILI: {len(parsed_rows)} hisse senedi verisi ayıklandı.")
                for row in parsed_rows:
                    row['report_year_month'] = f"{year}{str(month).zfill(2)}"
                    row['source_url'] = f"https://www.kap.org.tr/tr/Bildirim/{bildirim_id}"
                    all_data.append(row)
            else:
                print("   -> UYARI: PDF'den anlamlı veri ayıklanamadı.")
                
        except Exception as e:
            print(f"   -> HATA: {e}")

    # 3. Sonuçları Kaydet
    if all_data:
        json_filename = f"fon_analiz_{year}_{month}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        
        csv_filename = f"fon_analiz_{year}_{month}.csv"
        with open(csv_filename, "w", encoding="utf-8", newline="") as f:
            headers = all_data[0].keys()
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_data)
            
        print(f"\n✅ İŞLEM TAMAMLANDI!")
        print(f"Toplam {len(all_data)} satır veri çekildi.")
        print(f"Dosyalar oluşturuldu: {json_filename}, {csv_filename}")
    else:
        print("\n❌ Hiçbir veri çekilemedi.")

if __name__ == "__main__":
    # Komut satırı argümanları: yil ay
    # Örn: python fon_analizi.py 2024 3
    now = datetime.now()
    
    yil = int(sys.argv[1]) if len(sys.argv) > 1 else now.year
    ay = int(sys.argv[2]) if len(sys.argv) > 2 else now.month
    
    gemini_key = os.environ.get('GEMINI_API_KEY')
    run_analysis(yil, ay, gemini_key)
