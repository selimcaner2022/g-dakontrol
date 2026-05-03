from pathlib import Path
import re
import streamlit as st
import pandas as pd

APP_NAME = "Gluten Kontrol"
DATA_PATH = Path(__file__).parent / "data" / "products.csv"

st.set_page_config(page_title=APP_NAME, page_icon="✅", layout="wide")
st.title("✅ Gluten Kontrol")
st.caption("Çölyak hastaları için kaynak liste + güvenli tarafta kalan AI risk yorumu.")

RISK_KEYWORDS = [
    "buğday", "arpa", "çavdar", "yulaf", "gluten", "malt", "bulgur", "irmik",
    "kus kus", "couscous", "seitan", "tritikale", "ekmek kırıntısı", "galeta",
    "malt özü", "malt ekstrakt", "wheat", "barley", "rye", "oat", "spelt",
    "eser miktarda gluten", "eser miktarda buğday", "aynı hatta", "çapraz bulaşma"
]

SAFE_NOTE = "Bu uygulama tıbbi karar yerine geçmez. Çölyak için ürün etiketi, alerjen uyarısı ve üretici beyanı mutlaka kontrol edilmelidir. Belirsizlikte uygun değildir."

@st.cache_data
def load_products():
    if not DATA_PATH.exists():
        return pd.DataFrame(columns=["category", "brand", "product_name", "status", "source", "updated_at"])
    df = pd.read_csv(DATA_PATH)
    # Eski CSV formatı için uyumluluk.
    if "name" in df.columns and "product_name" not in df.columns:
        df["product_name"] = df["name"]
    if "brand" not in df.columns:
        df["brand"] = df.get("product_name", "").astype(str).str.replace(r"\s*\([^)]*\)", "", regex=True).str.strip(" .,;")
    for col in ["category", "brand", "product_name", "status", "source", "updated_at"]:
        if col not in df.columns:
            df[col] = ""
    return df[["category", "brand", "product_name", "status", "source", "updated_at"]].fillna("")

def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    text = re.sub(r"\s+", " ", text)
    return text

def ai_risk_comment(query: str, ingredients: str = ""):
    combined = normalize_text(query + " " + ingredients)
    hits = [k for k in RISK_KEYWORDS if normalize_text(k) in combined]
    if hits:
        return "UYGUN DEĞİL / TEYİT GEREKLİ", f"Riskli ifade bulundu: {', '.join(sorted(set(hits)))}. Çölyakta çok düşük risk bile kabul edilmemelidir."
    if not ingredients.strip():
        return "SİTEDE BULUNMADI — AI'YA GÖRE BELİRSİZ, UYGUN DEĞİL", "İçindekiler/alerjen bilgisi girilmediği için güvenli kabul edilemez."
    return "SİTEDE BULUNMADI — AI'YA GÖRE DÜŞÜK RİSK AMA TEYİT GEREKLİ", "Açık gluten anahtar kelimesi bulunmadı; yine de çapraz bulaşma ve alerjen uyarısı kontrol edilmelidir."

def show_result(rows: pd.DataFrame):
    if rows.empty:
        return
    st.success("Kaynak listede bulundu: çölyak için uygun olarak değerlendirilebilir. Yine de etiket/alerjen kontrolü zorunludur.")
    st.dataframe(rows[["category", "brand", "product_name", "status", "updated_at"]], use_container_width=True, hide_index=True)

products = load_products()

with st.sidebar:
    st.header("Veri durumu")
    st.write(f"Kayıt sayısı: **{len(products)}**")
    st.write(f"Kategori sayısı: **{products['category'].nunique() if not products.empty else 0}**")
    st.write(f"Veri dosyası: `{DATA_PATH}`")
    if DATA_PATH.exists():
        st.success("Veri dosyası bulundu.")
    else:
        st.warning("Veri dosyası bulunamadı.")

st.subheader("1) Listeden seçerek kontrol")
if products.empty:
    st.warning("Liste verisi yok. Önce `python scripts/update_from_colyak.py` çalıştırın veya data/products.csv ekleyin.")
else:
    c1, c2, c3 = st.columns(3)
    categories = sorted([x for x in products["category"].astype(str).unique() if x.strip()])
    with c1:
        selected_category = st.selectbox("Kategori seç", ["Seçiniz"] + categories)
    filtered = products.copy()
    if selected_category != "Seçiniz":
        filtered = filtered[filtered["category"] == selected_category]
    brands = sorted([x for x in filtered["brand"].astype(str).unique() if x.strip()])
    with c2:
        selected_brand = st.selectbox("Marka / ürün grubu seç", ["Seçiniz"] + brands)
    if selected_brand != "Seçiniz":
        filtered = filtered[filtered["brand"] == selected_brand]
    product_names = sorted([x for x in filtered["product_name"].astype(str).unique() if x.strip()])
    with c3:
        selected_product = st.selectbox("Ürün / varyant seç", ["Tümünü göster"] + product_names)
    if selected_category != "Seçiniz":
        result = filtered if selected_product == "Tümünü göster" else filtered[filtered["product_name"] == selected_product]
        show_result(result)

st.divider()
st.subheader("2) İsim yazarak ara")
query = st.text_input("Ürün, marka veya kategori ara", placeholder="Örn: Balparmak, Anavarza Bal, bal, pirinç unu...")
ingredients = st.text_area("Sitede yoksa AI yorumu için içindekiler / alerjen bilgisi", placeholder="Örn: mısır unu, pirinç unu, eser miktarda buğday/gluten içerebilir...")

if query:
    qn = normalize_text(query)
    tmp = products.copy()
    for col in ["category", "brand", "product_name"]:
        tmp[f"_{col}"] = tmp[col].map(normalize_text)
    matches = tmp[
        tmp["_category"].str.contains(qn, na=False) |
        tmp["_brand"].str.contains(qn, na=False) |
        tmp["_product_name"].str.contains(qn, na=False)
    ].drop(columns=["_category", "_brand", "_product_name"], errors="ignore")
    if not matches.empty:
        show_result(matches)
    else:
        status, comment = ai_risk_comment(query, ingredients)
        if "UYGUN DEĞİL" in status:
            st.error(status)
        else:
            st.warning(status)
        st.write(comment)

st.caption(SAFE_NOTE)
