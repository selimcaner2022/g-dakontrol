from pathlib import Path
import re
import csv
import requests
from bs4 import BeautifulSoup
from datetime import date

URL = "https://colyak.org.tr/glutensiz-urunler/"
OUT = Path("data/products.csv")
RISK_WORDS = ["dikkat", "okuy", "uyarı", "gluten içeriyor", "gluten içerebilir", "hariç", "dışında", "etiket", "ambalaj", "sorgula", "yazmalı"]

def clean_text(s: str) -> str:
    s = s.replace("\u200d", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip(" .;:-")
    return s

def is_heading(tag, text):
    if tag.name in ["h2", "h3"]:
        return True
    if len(text) <= 60 and text.upper() == text and not text.startswith("©"):
        return True
    return False

def main():
    r = requests.get(URL, timeout=30, headers={"User-Agent": "GlutenKontrol/1.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    content = soup.get_text("\n")
    lines = [clean_text(x) for x in content.splitlines()]
    lines = [x for x in lines if x]

    start = next((i for i,x in enumerate(lines) if x.upper() == "ATIŞTIRMALIK"), 0)
    stop_words = ["Çölyakla Yaşam Derneği", "Derneğimiz", "AB Projesi", "© Copyright"]

    rows=[]; current=None
    for x in lines[start:]:
        if any(sw in x for sw in stop_words):
            break
        # headings: short uppercase or lines that are category-like
        heading_candidate = re.sub(r"[^A-ZÇĞİÖŞÜ0-9 ]", "", x.upper()).strip()
        if (x.startswith("##") or (len(x) < 70 and heading_candidate and heading_candidate == re.sub(r"[^A-ZÇĞİÖŞÜ0-9 ]", "", x).strip())):
            current = clean_text(x.replace("#", ""))
            if not current:
                continue
            continue
        if current and len(x) > 1:
            low=x.casefold()
            risky=any(w in low for w in RISK_WORDS)
            rows.append({
                "category": current,
                "name": x,
                "status": "uygun_degil_tedbirli" if risky else "site_listesinde_var_uygun",
                "source": "Çölyakla Yaşam Derneği",
                "source_url": URL,
                "note": "Risk/uyarı içerdiği için çölyak açısından uygun kabul edilmedi; etiket ve üretici teyidi gerekir." if risky else "Çölyakla Yaşam Derneği listesinde yer alıyor; yine de güncel etiket/alerjen bilgisi kontrol edilmeli.",
                "last_checked": date.today().isoformat(),
            })

    # de-duplicate
    out=[]; seen=set()
    for row in rows:
        key=(row["category"].casefold(), row["name"].casefold())
        if key not in seen:
            seen.add(key); out.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w=csv.DictWriter(f, fieldnames=["category","name","status","source","source_url","note","last_checked"])
        w.writeheader(); w.writerows(out)
    print(f"Yazıldı: {OUT} ({len(out)} satır)")

if __name__ == "__main__":
    main()
