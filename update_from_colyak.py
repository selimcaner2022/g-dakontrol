from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://colyak.org.tr/glutensiz-urunler/"
BASE_DIR = Path(__file__).resolve().parents[1]
OUT = BASE_DIR / "data" / "products.csv"

HEADERS = {"User-Agent": "Mozilla/5.0 GlutenKontrolBot/1.0"}

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text_items = []
        for el in soup.select("li, td, p, h2, h3, h4"):
            txt = " ".join(el.get_text(" ", strip=True).split())
            if len(txt) >= 3:
                text_items.append(txt)
        seen = set()
        for txt in text_items:
            key = txt.lower()
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "name": txt,
                "category": "Çölyak Derneği listesi",
                "status": "Kaynak sitede yer alıyor; etiket/alerjen kontrolü gerekir",
                "source": URL,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    except Exception as e:
        print(f"Site güncellemesi başarısız: {e}")

    if not rows:
        rows = [{
            "name": "Örnek: Pirinç",
            "category": "Başlangıç verisi",
            "status": "Doğal olarak glutensiz olabilir; paketli üründe çapraz bulaşma kontrol edilir",
            "source": "local fallback",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]

    df = pd.DataFrame(rows).drop_duplicates(subset=["name", "category"])
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Yazıldı: {OUT} ({len(df)} satır)")

if __name__ == "__main__":
    main()
