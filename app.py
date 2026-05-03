import streamlit as st
import pandas as pd
from pathlib import Path
import re

APP_NAME = "Gluten Kontrol"
DATA_PATH = Path(__file__).parent / "data" / "products.csv"

st.set_page_config(page_title=APP_NAME, page_icon="✅", layout="wide")
st.title("✅ Gluten Kontrol")
st.caption("Çölyak hastaları için ürün kontrol uygulaması. Belirsizlik varsa güvenli tarafta kalır.")

RISK_KEYWORDS = [
    "buğday", "arpa", "çavdar", "yulaf", "gluten", "malt", "bulgur", "irmik",
    "kus kus", "couscous", "seitan", "tritikale", "ekmek kırıntısı", "galeta",
    "malt özü", "malt ekstrakt", "wheat", "barley", "rye", "oat", "spelt"
]

SAFE_NOTE = "Bu sonuç tıbbi/klinik karar yerine geçmez. Ürün etiketini, alerjen bilgisini ve çapraz bulaşma uyarılarını mutlaka kontrol edin."

@st.cache_data
def load_products():
    if not DATA_PATH.exists():
        return pd.DataFrame(columns=["name", "category", "status", "source", "updated_at"])
    df = pd.read_csv(DATA_PATH)
    for col in ["name", "category", "status", "source", "updated_at"]:
        if col not in df.columns:
            df[col] = ""
    return df.fillna("")

def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    text = re.sub(r"\s+", " ", text)
    return text

def ai_risk_comment(query: str, ingredients: str = ""):
    combined = normalize_text(query + " " + ingredients)
    hits = [k for k in RISK_KEYWORDS if normalize_text(k) in combined]
    if hits:
        return "UYGUN DEĞİL / TEYİT GEREKLİ", f"Riskli ifade bulundu: {', '.join(sorted(set(hits)))}. Çölyak için çok düşük riskte bile uygun değildir."
    if not ingredients.strip():
        return "SİTEDE BULUNMADI — AI'YA GÖRE BELİRSİZ, UYGUN DEĞİL", "İçindekiler girilmediği için güvenli kabul edilemez."
    return "SİTEDE BULUNMADI — AI'YA GÖRE DÜŞÜK RİSK AMA TEYİT GEREKLİ", "Açık gluten anahtar kelimesi bulunmadı; yine de çapraz bulaşma ve alerjen uyarısı kontrol edilmelidir."

products = load_products()

with st.sidebar:
    st.header("Veri durumu")
    st.write(f"Ürün sayısı: **{len(products)}**")
    st.write(f"Veri dosyası: `{DATA_PATH}`")
    if DATA_PATH.exists():
        st.success("Veri dosyası bulundu.")
    else:
        st.warning("Veri dosyası bulunamadı. Uygulama yine de AI/risk yorumu yapabilir.")

query = st.text_input("Ürün adı ara", placeholder="Örn: pirinç unu, çikolata, makarna...")
ingredients = st.text_area("İçindekiler / alerjen bilgisi varsa buraya yaz", placeholder="Örn: mısır unu, pirinç unu, eser miktarda buğday/gluten içerebilir...")

if query:
    qn = normalize_text(query)
    if not products.empty:
        tmp = products.copy()
        tmp["_norm"] = tmp["name"].map(normalize_text)
        matches = tmp[tmp["_norm"].str.contains(qn, na=False) | tmp["category"].map(normalize_text).str.contains(qn, na=False)]
    else:
        matches = pd.DataFrame()

    st.subheader("Sonuç")
    if not matches.empty:
        st.success("Ürün/ifade kaynak listede bulundu.")
        st.dataframe(matches.drop(columns=["_norm"], errors="ignore"), use_container_width=True)
        status_joined = " ".join(matches["status"].astype(str).tolist()).lower()
        if "uygun" in status_joined or "glutensiz" in status_joined:
            st.info("Kaynak listede var: çölyak için uygun/glutensiz olarak değerlendirilmiş olabilir. Yine de etiket kontrolü zorunludur.")
        else:
            st.warning("Kaynak listede var ama uygunluk açık değil. Etiket ve üretici teyidi gerekir.")
    else:
        status, comment = ai_risk_comment(query, ingredients)
        if "UYGUN DEĞİL" in status:
            st.error(status)
        else:
            st.warning(status)
        st.write(comment)

    st.caption(SAFE_NOTE)
else:
    st.info("Başlamak için ürün adı yazın.")
