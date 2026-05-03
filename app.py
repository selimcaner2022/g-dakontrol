import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from rapidfuzz import fuzz, process

APP_NAME = "Gluten Kontrol"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_PATH = DATA_DIR / "products.csv"
SOURCE_URL = "https://colyak.org.tr/glutensiz-urunler/"

RISK_TERMS = {
    "Kesin gluten / uygunsuz": [
        "buğday", "bugday", "wheat", "arpa", "barley", "çavdar", "cavdar", "rye",
        "tritikale", "triticale", "malt", "malt özü", "malt extract", "bulgur", "irmik",
        "semolina", "kuskus", "couscous", "seitan", "gluten", "glüten", "galeta",
        "ekmek kırıntısı", "wheat flour", "barley malt"
    ],
    "Çapraz bulaşma / uyarı": [
        "gluten içerebilir", "glüten içerebilir", "eser miktarda gluten", "eser miktarda glüten",
        "aynı hatta", "aynı tesiste", "çapraz bulaş", "may contain gluten", "may contain wheat",
        "traces of gluten", "contains wheat", "buğday proteini", "alerjen gluten"
    ],
    "Riskli / teyit gerekli": [
        "nişasta", "nisasta", "modifiye nişasta", "doğal aroma", "aroma verici", "hidrolize protein",
        "soya sosu", "yulaf", "oats", "oat", "mısır gevreği", "baharat karışımı", "köri",
        "köfte baharı", "sos", "kaplama", "pane", "drajeler", "un"
    ]
}

SAMPLE_ROWS = [
    {"name": "Örnek sertifikalı glutensiz ürün", "category": "Örnek", "status": "uygun", "note": "Gerçek liste güncellemesi için scripts/update_from_colyak.py çalıştırın."},
]


def normalize(text: str) -> str:
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"[^a-z0-9ğüşöç\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def ensure_data_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        pd.DataFrame(SAMPLE_ROWS).to_csv(DATA_PATH, index=False, encoding="utf-8")


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    ensure_data_file()
    df = pd.read_csv(DATA_PATH)
    required = ["name", "category", "status", "note"]
    for col in required:
        if col not in df.columns:
            df[col] = ""
    df = df[required].copy()
    df["name"] = df["name"].fillna("")
    df["name_norm"] = df["name"].map(normalize)
    df["category"] = df["category"].fillna("")
    df["status"] = df["status"].fillna("bilinmiyor")
    df["note"] = df["note"].fillna("")
    return df


def status_label(status: str):
    mapping = {
        "uygun": ("✅ Sitede var: çölyak için uygun görünüyor", "success"),
        "kosullu": ("⚠️ Sitede var: koşullu / etiket kontrolü gerekli", "warning"),
        "uygun_degil": ("⛔ Sitede var: çölyak için uygun değil", "error"),
    }
    return mapping.get(str(status), ("❓ Durum bilinmiyor", "info"))


def search_product(query: str, df: pd.DataFrame):
    q = normalize(query)
    if not q or df.empty:
        return []
    choices = df["name_norm"].tolist()
    hits = process.extract(q, choices, scorer=fuzz.WRatio, limit=8)
    results = []
    for _, score, idx in hits:
        if score >= 55:
            row = df.iloc[idx].to_dict()
            row["score"] = int(score)
            results.append(row)
    return results


def ai_rule_assessment(product_name: str, ingredients: str = ""):
    text = normalize(f"{product_name} {ingredients}")
    found = []
    for level, terms in RISK_TERMS.items():
        for term in terms:
            if normalize(term) and normalize(term) in text:
                found.append((level, term))
    if any(level == "Kesin gluten / uygunsuz" for level, _ in found):
        verdict = "⛔ Sitede bulunmamakta. Yapay zekâ/risk kuralına göre çölyak için uygun değil."
        risk = "Yüksek"
    elif any(level == "Çapraz bulaşma / uyarı" for level, _ in found):
        verdict = "⛔ Sitede bulunmamakta. Çapraz bulaşma/alerjen uyarısı nedeniyle uygun değil."
        risk = "Yüksek"
    elif any(level == "Riskli / teyit gerekli" for level, _ in found):
        verdict = "⛔ Sitede bulunmamakta. Belirsiz/riskli içerik nedeniyle çölyak için uygun değil; üretici teyidi gerekir."
        risk = "Orta-Belirsiz"
    else:
        verdict = "⚠️ Sitede bulunmamakta. Belirgin gluten sinyali yok; çölyak için yalnızca 'glutensiz' sertifikası/etiketi ve üretici teyidi varsa tüketilmeli."
        risk = "Düşük-Belirsiz"
    return verdict, risk, found


st.set_page_config(page_title=APP_NAME, page_icon="🌾", layout="wide")
st.title("🌾 Gluten Kontrol")
st.caption("Çölyak hastaları için muhafazakâr ürün kontrolü. En küçük belirsizlikte tüketmeme/teyit önerir.")

with st.sidebar:
    st.header("Durum")
    st.write(f"Çalışan dosya: `{Path(__file__).name}`")
    st.write(f"Veri dosyası: `{DATA_PATH}`")
    st.write("Ana liste: Çölyakla Yaşam Derneği glutensiz ürünler sayfası")
    try:
        st.link_button("Kaynağı aç", SOURCE_URL)
    except Exception:
        st.markdown(f"[Kaynağı aç]({SOURCE_URL})")
    st.warning("Bu uygulama tıbbi tavsiye değildir. Etiket, alerjen uyarısı ve üretici teyidi her zaman kontrol edilmelidir.")

try:
    df = load_data()
except Exception as e:
    st.error("Uygulama veri dosyasını okuyamadı.")
    st.exception(e)
    st.stop()

st.success(f"Uygulama çalışıyor. Yerel veritabanında {len(df)} ürün kaydı var.")

tab1, tab2, tab3, tab4 = st.tabs(["Ürün ara", "İçerik/etiket analizi", "Veri tabanı", "Kurulum"])

with tab1:
    q = st.text_input("Ürün / marka adı yazın", placeholder="Örn: Schar, Nutella, gofret")
    if q:
        hits = search_product(q, df)
        if hits:
            st.subheader("Eşleşmeler")
            for row in hits:
                label, kind = status_label(row["status"])
                getattr(st, kind)(f"{label} — **{row['name']}** | Kategori: {row['category']} | Benzerlik: %{row['score']}")
                if row.get("note"):
                    st.caption(str(row["note"]))
        else:
            verdict, risk, found = ai_rule_assessment(q)
            st.warning(verdict)
            st.write("Risk seviyesi:", risk)
            st.caption("Bu sonuç yerel kural tabanlı AI yorumudur; resmî listede ürün bulunamadı.")

with tab2:
    product = st.text_input("Ürün adı", key="product_scan")
    ingredients = st.text_area("İçindekiler / alerjen bilgisi", height=180)
    img = st.file_uploader("Etiket fotoğrafı yükle", type=["png", "jpg", "jpeg"])
    if img:
        st.image(img, width=350)
        st.info("Bu MVP'de OCR otomatik değil. Etiketteki içindekileri metin alanına yazın/yapıştırın.")
    if st.button("Risk analizi yap", type="primary"):
        verdict, risk, found = ai_rule_assessment(product, ingredients)
        st.write(verdict)
        st.write("Risk seviyesi:", risk)
        if found:
            st.error("Tespit edilen risk ifadeleri: " + ", ".join(sorted(set(x[1] for x in found))))
        else:
            st.info("Belirgin risk ifadesi bulunmadı; çölyakta yine de sertifikalı glutensiz ibaresi ve üretici teyidi aranmalı.")

with tab3:
    st.dataframe(df.drop(columns=["name_norm"], errors="ignore"), use_container_width=True, hide_index=True)
    st.download_button("CSV indir", df.drop(columns=["name_norm"], errors="ignore").to_csv(index=False).encode("utf-8"), "gluten_kontrol_products.csv", "text/csv")

with tab4:
    st.markdown("""
### Streamlit Cloud için kritik ayar
Deploy ederken **Main file path** alanı mutlaka şu olmalı:

`app.py`

`update_from_colyak.py` ana uygulama dosyası değildir; sadece veri güncelleme scriptidir.

### Güncelleme
Yerelde veya GitHub Actions içinde:

```bash
python scripts/update_from_colyak.py
```

Sonra `data/products.csv` repo'ya commit edilir.
""")
