from pathlib import Path
from datetime import datetime
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://colyak.org.tr/glutensiz-urunler/"
BASE_DIR = Path(__file__).resolve().parents[1]
OUT = BASE_DIR / "data" / "products.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 GlutenKontrolBot/1.0"}

IGNORE_TEXTS = {
    "glutensiz ürünler", "anasayfa", "iletişim", "iletisim", "menü", "menu",
    "facebook", "instagram", "twitter", "arama", "search"
}

SAMPLE_ROWS = [
    {"category": "BAL", "brand": "Anavarza Bal", "product_name": "Anavarza Bal", "status": "Kaynak sitede yer alıyor; çölyak için uygun olarak değerlendirilebilir. Etiket kontrolü zorunludur."},
    {"category": "BAL", "brand": "Balparmak", "product_name": "Balparmak", "status": "Kaynak sitede yer alıyor; çölyak için uygun olarak değerlendirilebilir. Etiket kontrolü zorunludur."},
    {"category": "BAL", "brand": "Binboğa Balı", "product_name": "Binboğa Balı (Çam Balı, Çiçek Balı, Keven&Kekik Balı)", "status": "Kaynak sitede yer alıyor; çölyak için uygun olarak değerlendirilebilir. Etiket kontrolü zorunludur."},
    {"category": "BAL", "brand": "Saklı Cennet Bal", "product_name": "Saklı Cennet Bal", "status": "Kaynak sitede yer alıyor; çölyak için uygun olarak değerlendirilebilir. Etiket kontrolü zorunludur."},
    {"category": "BAL", "brand": "TKV Bal", "product_name": "TKV Bal", "status": "Kaynak sitede yer alıyor; çölyak için uygun olarak değerlendirilebilir. Etiket kontrolü zorunludur."},
]

def clean(txt: str) -> str:
    txt = re.sub(r"\s+", " ", str(txt).strip())
    txt = txt.strip(" .:-–—")
    return txt

def norm(txt: str) -> str:
    tr = str.maketrans("ıİğĞüÜşŞöÖçÇ", "iIgGuUsSoOcC")
    return clean(txt).translate(tr).lower()

def looks_like_category(txt: str, tag_name: str = "") -> bool:
    t = clean(txt)
    if len(t) < 2 or len(t) > 80:
        return False
    if norm(t) in IGNORE_TEXTS:
        return False
    if tag_name in {"h1", "h2", "h3", "h4", "strong", "b"} and len(t.split()) <= 6:
        return True
    letters = re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü]", "", t)
    if letters and letters.upper() == letters and len(t.split()) <= 6:
        return True
    return False

def brand_from_product(product: str) -> str:
    p = clean(product)
    # Parantez ürün varyantıdır; marka kısmını parantez öncesinden al.
    p = re.sub(r"\s*\([^)]*\)\s*", "", p).strip()
    # Gereksiz nokta/virgül temizliği.
    p = p.strip(" .,")
    return p

def extract_rows_from_page(html: str):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find("article") or soup.body or soup
    rows = []
    current_category = "GENEL"

    # Sayfanın doğal akışını korumak için başlık ve liste elemanlarını sırayla dolaş.
    for el in main.find_all(["h1", "h2", "h3", "h4", "strong", "b", "li", "p", "td"], recursive=True):
        text = clean(el.get_text(" ", strip=True))
        if not text or len(text) < 2:
            continue
        ntext = norm(text)
        if ntext in IGNORE_TEXTS:
            continue
        if looks_like_category(text, el.name):
            current_category = text.upper()
            continue
        # Liste dışı uzun açıklamaları ürün sanma.
        if el.name in {"p", "td"} and len(text) > 140:
            continue
        if current_category == "GENEL" and len(text.split()) > 10:
            continue
        rows.append({
            "category": current_category,
            "brand": brand_from_product(text),
            "product_name": text,
            "status": "Kaynak sitede yer alıyor; çölyak için uygun olarak değerlendirilebilir. Etiket/alerjen kontrolü zorunludur.",
            "source": URL,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return rows

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        rows = extract_rows_from_page(r.text)
    except Exception as e:
        print(f"Site güncellemesi başarısız: {e}")

    if not rows:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = [{**x, "source": "local fallback", "updated_at": now} for x in SAMPLE_ROWS]

    df = pd.DataFrame(rows)
    for col in ["category", "brand", "product_name", "status", "source", "updated_at"]:
        if col not in df.columns:
            df[col] = ""
    df = df.drop_duplicates(subset=["category", "brand", "product_name"])
    df = df.sort_values(["category", "brand", "product_name"], kind="stable")
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Yazıldı: {OUT} ({len(df)} satır)")

if __name__ == "__main__":
    main()
