import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from rapidfuzz import fuzz, process

APP_NAME = "Gluten Kontrol"
DATA_PATH = Path(__file__).parent / "data" / "products.csv"
SOURCE_URL = "https://colyak.org.tr/glutensiz-urunler/"

RISK_TERMS = {
    "Kesin gluten / uygunsuz": [
        "buğday", "bugday", "wheat", "arpa", "barley", "çavdar", "cavdar", "rye",
        "tritikale", "triticale", "malt", "malt özü", "malt extract", "bulgur", "irmik",
        "semolina", "kuskus", "couscous", "seitan", "gluten", "glüten", "gofret",
        "galeta", "ekmek kırıntısı", "un", "wheat flour", "barley malt"
    ],
    "Çapraz bulaşma / uyarı": [
        "gluten içerebilir", "glüten içerebilir", "eser miktarda gluten", "eser miktarda glüten",
        "aynı hatta", "aynı tesiste", "çapraz bulaş", "may contain gluten", "may contain wheat",
        "traces of gluten", "contains wheat", "buğday proteini", "alerjen gluten"
    ],
    "Riskli / teyit gerekli": [
        "nişasta", "nisasta", "modifiye nişasta", "doğal aroma", "aroma verici", "hidrolize protein",
        "soya sosu", "yulaf", "oats", "oat", "mısır gevreği", "baharat karışımı", "köri",
        "köfte baharı", "sos", "kaplama", "pane", "drajeler"
    ]
}

def normalize(text: str) -> str:
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    text = re.sub(r"[^a-z0-9ğüşöçİı\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df["name_norm"] = df["name"].map(normalize)
    df["category"] = df["category"].fillna("")
    df["status"] = df["status"].fillna("bilinmiyor")
    df["note"] = df["note"].fillna("")
    return df

def status_label(status):
    mapping = {
        "uygun": ("✅ Sitede var: çölyak için uygun görünüyor", "success"),
        "kosullu": ("⚠️ Sitede var: koşullu / etiket kontrolü gerekli", "warning"),
        "uygun_degil": ("⛔ Sitede var: çölyak için uygun değil", "error"),
    }
    return mapping.get(status, ("❓ Durum bilinmiyor", "info"))

def search_product(query, df):
    q = normalize(query)
    if not q:
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
            if normalize(term) in text:
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
        verdict = "⚠️ Sitede bulunmamakta. Girilen bilgiye göre belirgin gluten sinyali yok; ancak çölyak için yalnızca 'glutensiz' sertifikası/etiketi ve üretici teyidi varsa tüketilmeli."
        risk = "Düşük-Belirsiz"
    return verdict, risk, found

st.set_page_config(page_title=APP_NAME, page_icon="🌾", layout="wide")
st.title("🌾 Gluten Kontrol")
st.caption("Çölyak hastaları için muhafazakâr ürün kontrolü. En küçük belirsizlikte tüketmeme/teyit önerir.")

with st.sidebar:
    st.header("Veri kaynağı")
    st.write("Ana liste: Çölyakla Yaşam Derneği glutensiz ürünler sayfası")
    st.link_button("Kaynağı aç", SOURCE_URL)
    st.warning("Bu uygulama tıbbi tavsiye değildir. Etiket, alerjen uyarısı ve üretici teyidi her zaman kontrol edilmelidir.")
    st.write(f"Yerel veri dosyası: `{DATA_PATH.name}`")

try:
    df = load_data()
except Exception as e:
    st.error(f"Veri okunamadı: {e}")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["Ürün ara", "İçerik/etiket analizi", "Veri tabanı", "Geliştirme notları"])

with tab1:
    q = st.text_input("Ürün / marka adı yazın", placeholder="Örn: Nutella, Schar, Mabel Gofret, Eti Pronot")
    if q:
        hits = search_product(q, df)
        if hits:
            st.subheader("Eşleşmeler")
            for row in hits:
                label, kind = status_label(row["status"])
                box = getattr(st, kind)
                box(f"{label} — **{row['name']}**  | Kategori: {row['category']} | Benzerlik: %{row['score']}")
                if row.get("note"):
                    st.write("Not:", row["note"])
        else:
            verdict, risk, found = ai_rule_assessment(q)
            st.warning(verdict)
            st.write("Risk seviyesi:", risk)
            st.caption("Bu sonuç yerel kural tabanlı AI yorumudur; resmî listede ürün bulunamadı.")

with tab2:
    st.subheader("İçindekiler veya etiket metni ile kontrol")
    product = st.text_input("Ürün adı", key="product_scan")
    ingredients = st.text_area("İçindekiler / alerjen bilgisi", height=180, placeholder="Etiketteki içerikleri buraya yazın veya OCR çıktısını yapıştırın.")
    img = st.file_uploader("Etiket fotoğrafı yükle (opsiyonel)", type=["png", "jpg", "jpeg"])
    if img:
        st.info("Fotoğraf yüklendi. Bu MVP sürümünde OCR manuel/opsiyonel tutuldu. Üretimde Google Vision, Azure OCR veya Tesseract bağlanabilir.")
        st.image(img, width=350)
    if st.button("Risk analizi yap", type="primary"):
        verdict, risk, found = ai_rule_assessment(product, ingredients)
        st.write(verdict)
        st.write("Risk seviyesi:", risk)
        if found:
            st.error("Tespit edilen risk ifadeleri: " + ", ".join(sorted(set([x[1] for x in found]))))
        else:
            st.info("Belirgin risk ifadesi bulunmadı; çölyakta yine de sertifikalı glutensiz ibaresi ve üretici teyidi aranmalı.")

with tab3:
    st.subheader("Yerel ürün listesi")
    st.dataframe(df.drop(columns=["name_norm"]), use_container_width=True, hide_index=True)
    st.download_button("CSV indir", df.drop(columns=["name_norm"]).to_csv(index=False).encode("utf-8"), "gluten_kontrol_products.csv", "text/csv")

with tab4:
    st.markdown("""
### Üretim sürümünde önerilen entegrasyonlar
- **Barkod tarama:** Open Food Facts API + Türkiye ürün barkod eşlemesi.
- **Etiket OCR:** Google Vision, Azure Computer Vision veya Tesseract.
- **LLM güvenlik katmanı:** İçerik metnini sınıflandırır ama nihai kararı muhafazakâr kurallar verir.
- **Güncelleme paneli:** Dernek sayfasından veri yenileme, manuel düzeltme ve versiyonlama.
- **Kaynak ayrımı:** Resmî dernek listesi, üretici beyanı, kullanıcı katkısı ve AI yorumu ayrı tutulmalıdır.

### Karar politikası
- Listede `uygun_degil` veya içerikte gluten/çapraz bulaşma varsa: **uygun değil**.
- Listede `kosullu` ise: **etiket ve üretici teyidi gerekli**.
- Listede yoksa: AI yorumu verilir, fakat çölyak için belirsizlikte **uygun değil / teyit gerekli** yaklaşımı kullanılır.
""")
