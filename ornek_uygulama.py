import pykap
import sys
import json
import csv
import traceback

def ana_islem(hisse_kodu):
    print(f"--- {hisse_kodu} için KAPSAMLI KAP Verileri Çekiliyor ---")
    
    rapor_verisi = {
        "hisse_kodu": hisse_kodu,
        "genel_bilgiler": {},
        "finansal_tablolar": {}
    }
    
    comp = pykap.BISTCompany(hisse_kodu)
    
    try:
        print("\n[1] Genel Bilgiler:")
        info = pykap.get_general_info(tick=hisse_kodu)
        rapor_verisi["genel_bilgiler"] = info
        for key, value in info.items():
            print(f"{key}: {value}")
            
    except Exception as e:
        print(f"Genel bilgiler çekilirken hata: {e}")

    try:
        print(f"\n[2] {hisse_kodu} Son 1 Yıllık GERÇEK Finansal Tablo Verileri (Bilanço/Gelir Tablosu) Çekiliyor (Bu işlem biraz sürebilir)...")
        finansallar = comp.get_financial_reports()
        
        if finansallar:
            rapor_verisi["finansal_tablolar"] = finansallar
            for donem, veri in finansallar.items():
                kalem_sayisi = len(veri.get('results', {})) if veri.get('results') else 0
                print(f"- {donem} dönemi için finansal veriler çekildi. Toplam {kalem_sayisi} bilanço kalemi bulundu.")
                
            with open(f"{hisse_kodu}_finansal_tablolar.json", "w", encoding="utf-8") as f:
                json.dump(finansallar, f, ensure_ascii=False, indent=4)
        else:
            print("Son 1 yıla ait finansal tablo bulunamadı.")
            
    except Exception as e:
        print(f"Finansal veriler çekilirken hata: {e}")
        traceback.print_exc()

    try:
        print(f"\n[3] {hisse_kodu} Son Faaliyet Raporları (PDF) İndiriliyor...")
        comp.save_operating_review()
        print("Faaliyet raporları indirildi.")
    except Exception as e:
        print(f"Faaliyet raporları indirilirken hata: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    hisse = sys.argv[1].upper() if len(sys.argv) > 1 else 'THYAO'
    ana_islem(hisse)

