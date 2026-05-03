"""Çölyakla Yaşam Derneği sayfasından ürün listesini CSV'ye dönüştürmek için yardımcı script.
Kullanım: python scripts/update_from_colyak.py
Not: Site yapısı değişirse parser güncellenmelidir. Veriyi yeniden yayımlamadan önce kaynak izinleri ve atıf kontrol edilmelidir.
"""
import re
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://colyak.org.tr/glutensiz-urunler/"
OUT = Path(__file__).resolve().parents[1] / "data" / "products.csv"
NEGATIVE_HINTS = ["tüketmemelerini", "çapraz bulaşma", "buğday proteini", "glutenli", "gluten içerir", "gluten icerebilir"]
CONDITIONAL_HINTS = ["dikkat", "koşuluyla", "etiket", "alerjen", "glutensiz etiketi", "okunmalı", "kullanınız"]

def clean(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()

def classify(text, current_heading):
    t = text.lower()
    if any(h in t for h in NEGATIVE_HINTS):
        return "uygun_degil"
    if any(h in t for h in CONDITIONAL_HINTS) or "koşul" in current_heading.lower():
        return "kosullu"
    return "uygun"

def main():
    html = requests.get(URL, timeout=30, headers={"User-Agent": "GlutenKontrol/0.1"}).text
    soup = BeautifulSoup(html, "html.parser")
    content = soup.get_text("\n")
    rows, category = [], None
    capture = False
    for raw in content.splitlines():
        line = clean(raw)
        if not line:
            continue
        if line == "Glutensiz Ürünler":
            capture = True
            continue
        if not capture:
            continue
        # Başlıkları yakala: kısa, büyük harf ağırlıklı satırlar
        if len(line) < 80 and (line.isupper() or line.startswith("MABEL") or line.endswith(":")):
            category = line.strip("# :")
            continue
        if category and len(line) > 2 and not line.startswith(("Sevgili", "Derneğimize", "Bir başka", "Üretici")):
            rows.append({
                "name": line,
                "category": category,
                "status": classify(line, category),
                "source": "Çölyakla Yaşam Derneği",
                "note": "Otomatik çekildi; etiket/alerjen kontrolü gerekir."
            })
    df = pd.DataFrame(rows).drop_duplicates(subset=["name", "category"])
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Yazıldı: {OUT} ({len(df)} satır)")

if __name__ == "__main__":
    main()
