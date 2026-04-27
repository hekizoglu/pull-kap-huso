import pykap
import sys

def ana_islem(hisse_kodu):
    print(f"--- {hisse_kodu} için KAP Verileri Çekiliyor ---")
    
    try:
        print("\n[1] Genel Bilgiler:")
        info = pykap.get_general_info(tick=hisse_kodu)
        for key, value in info.items():
            print(f"{key}: {value}")
        
        print(f"\n[2] {hisse_kodu} Son 5 Beklenen Bildirim:")
        comp = pykap.BISTCompany(hisse_kodu)
        beklenenler = comp.get_expected_disclosure_list(count=5)
        if beklenenler:
            for b in beklenenler:
                print(f"- {b}")
        else:
            print("Beklenen bildirim bulunamadı.")
            
    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == "__main__":
    # Eğer dışarıdan bir hisse kodu girilmezse varsayılan olarak THYAO kullan
    hisse = sys.argv[1].upper() if len(sys.argv) > 1 else 'THYAO'
    ana_islem(hisse)
