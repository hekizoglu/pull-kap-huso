import pykap
import sys
import json
import csv

def ana_islem(hisse_kodu):
    print(f"--- {hisse_kodu} için KAP Verileri Çekiliyor ---")
    
    rapor_verisi = {
        "hisse_kodu": hisse_kodu,
        "genel_bilgiler": {},
        "beklenen_bildirimler": []
    }
    
    try:
        print("\n[1] Genel Bilgiler:")
        info = pykap.get_general_info(tick=hisse_kodu)
        rapor_verisi["genel_bilgiler"] = info
        for key, value in info.items():
            print(f"{key}: {value}")
        
        print(f"\n[2] {hisse_kodu} Son 5 Beklenen Bildirim:")
        comp = pykap.BISTCompany(hisse_kodu)
        beklenenler = comp.get_expected_disclosure_list(count=5)
        if beklenenler:
            rapor_verisi["beklenen_bildirimler"] = beklenenler
            for b in beklenenler:
                print(f"- {b}")
        else:
            print("Beklenen bildirim bulunamadı.")
            
        # Sonuçları JSON olarak kaydet
        with open(f"{hisse_kodu}_rapor.json", "w", encoding="utf-8") as f:
            json.dump(rapor_verisi, f, ensure_ascii=False, indent=4)
            
        # Beklenen bildirimleri CSV olarak kaydet
        if beklenenler:
            csv_dosya = f"{hisse_kodu}_beklenen_bildirimler.csv"
            with open(csv_dosya, "w", encoding="utf-8", newline="") as f:
                basliklar = beklenenler[0].keys()
                writer = csv.DictWriter(f, fieldnames=basliklar)
                writer.writeheader()
                writer.writerows(beklenenler)
            print(f"\n🚀 Raporlar başarıyla oluşturuldu: {hisse_kodu}_rapor.json ve {csv_dosya}")
            
    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == "__main__":
    hisse = sys.argv[1].upper() if len(sys.argv) > 1 else 'THYAO'
    ana_islem(hisse)
