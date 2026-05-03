from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
import unicodedata

import pandas as pd
import streamlit as st

#try:
    #import requests
    #from bs4 import BeautifulSoup
#except Exception:  # offline/local env without optional deps
    requests = None
    BeautifulSoup = None

APP_TITLE = "Gluten Kontrol"
SOURCE_URL = "https://colyak.org.tr/glutensiz-urunler/"
LOCAL_CSV = Path("data/products.csv")
MIN_ONLINE_ROWS = 50

st.set_page_config(page_title=APP_TITLE, page_icon="🌾", layout="wide")


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\ufeff", "")
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def search_key(value: object) -> str:
    text = normalize_text(value).casefold()
    text = text.replace("ı", "i")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9ğüşöçıİĞÜŞÖÇ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_product_name(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"^[•\-–—*\d.)\s]+", "", text)
    text = text.strip(" .;,-–—\t")
    return text


def looks_like_category(text: str) -> bool:
    text = clean_product_name(text)
    if len(text) < 2 or len(text) > 70:
        return False
    if any(x in text.lower() for x in ["çölyak", "glutensiz ürün", "anasayfa", "iletişim"]):
        return False
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return uppercase_ratio > 0.75


def build_df(rows: list[dict]) -> pd.DataFrame:
    cols = ["category", "name", "status", "source", "source_url", "note", "last_checked"]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return pd.DataFrame(columns=cols)
    for col in ["category", "name", "status", "source", "source_url", "note", "last_checked"]:
        df[col] = df[col].map(normalize_text)
    df = df[(df["category"] != "") & (df["name"] != "")]
    df = df.drop_duplicates(subset=["category", "name"]).sort_values(["category", "name"])
    return df.reset_index(drop=True)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_online_products() -> tuple[pd.DataFrame, str]:
    """Try to fetch live data. Never raises to UI; returns df and status message."""
    if requests is None or BeautifulSoup is None:
        return pd.DataFrame(), "Online kütüphaneler yok; offline veri kullanılıyor."

    try:
        response = requests.get(
            SOURCE_URL,
            timeout=7,
            headers={"User-Agent": "GlutenKontrol/1.0 (+offline fallback)"},
        )
        response.raise_for_status()
    except Exception as exc:
        return pd.DataFrame(), f"İnternet/kaynak bağlantısı kurulamadı; offline veri kullanılıyor. Detay: {type(exc).__name__}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove elements that usually contain menus, scripts and irrelevant text.
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find(class_=re.compile("content|entry|post", re.I)) or soup.body or soup
    elements = main.find_all(["h1", "h2", "h3", "h4", "strong", "b", "p", "li", "td"])

    rows: list[dict] = []
    current_category = ""
    blocked_phrases = [
        "glutensiz ürünler", "liste", "kaynak", "anasayfa", "telefon", "email", "e-posta",
        "çölyakla yaşam", "derneği", "güncelle", "bilgilendirme", "duyuru", "sosyal medya",
    ]

    for el in elements:
        text = clean_product_name(el.get_text(" ", strip=True))
        if not text or len(text) < 2:
            continue
        low = text.casefold()
        if any(p in low for p in blocked_phrases) and len(text) > 35:
            continue

        # Headings / all caps lines are treated as category.
        if el.name in ["h1", "h2", "h3", "h4"] or looks_like_category(text):
            if looks_like_category(text):
                current_category = text.upper()
            continue

        if not current_category:
            continue

        # Split multi-line or bullet-like product blocks.
        parts = re.split(r"\n|\r|(?<=\))\s{2,}|\s•\s", text)
        for part in parts:
            name = clean_product_name(part)
            if not name or len(name) < 2:
                continue
            if looks_like_category(name):
                current_category = name.upper()
                continue
            if any(p in name.casefold() for p in blocked_phrases) and len(name) > 25:
                continue
            rows.append({
                "category": current_category,
                "name": name,
                "status": "site_listesinde_var_uygun",
                "source": "Çölyakla Yaşam Derneği",
                "source_url": SOURCE_URL,
                "note": "Canlı siteden çekildi; yine de güncel etiket/alerjen bilgisi kontrol edilmeli.",
                "last_checked": date.today().isoformat(),
            })

    df = build_df(rows)
    if len(df) < MIN_ONLINE_ROWS:
        return pd.DataFrame(), f"Canlı veri beklenenden az geldi ({len(df)} satır); güvenlik için offline CSV kullanılıyor."
    return df, f"Online mod aktif: canlı listeden {len(df)} satır okundu."


def load_local_products() -> tuple[pd.DataFrame, str]:
    if not LOCAL_CSV.exists():
        return pd.DataFrame(), f"Yerel veri bulunamadı: {LOCAL_CSV}"
    try:
        df = pd.read_csv(LOCAL_CSV, encoding="utf-8-sig")
    except Exception as exc:
        return pd.DataFrame(), f"Yerel CSV okunamadı: {type(exc).__name__}"
    required = {"category", "name"}
    if not required.issubset(df.columns):
        return pd.DataFrame(), "Yerel CSV içinde category ve name kolonları olmalı."
    defaults = {
        "status": "site_listesinde_var_uygun",
        "source": "Yerel CSV",
        "source_url": SOURCE_URL,
        "note": "Yerel/offline veri kaydı.",
        "last_checked": "",
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
    return build_df(df.to_dict("records")), f"Offline mod: yerel CSV'den {len(df)} satır okundu."


def load_products(prefer_online: bool) -> tuple[pd.DataFrame, str, str]:
    if prefer_online:
        online_df, online_msg = fetch_online_products()
        if not online_df.empty:
            # Best effort cache update; if filesystem is read-only, app still works.
            try:
                LOCAL_CSV.parent.mkdir(parents=True, exist_ok=True)
                online_df.to_csv(LOCAL_CSV, index=False, encoding="utf-8-sig")
            except Exception:
                pass
            return online_df, "online", online_msg
        local_df, local_msg = load_local_products()
        if not local_df.empty:
            return local_df, "offline", online_msg + " | " + local_msg
        return pd.DataFrame(), "error", online_msg + " | " + local_msg

    local_df, local_msg = load_local_products()
    if not local_df.empty:
        return local_df, "offline", local_msg
    online_df, online_msg = fetch_online_products()
    if not online_df.empty:
        return online_df, "online", online_msg
    return pd.DataFrame(), "error", local_msg + " | " + online_msg


RISKY_TERMS = [
    "buğday", "bugday", "wheat", "arpa", "barley", "çavdar", "cavdar", "rye",
    "gluten", "malt", "malt özü", "malt ekstraktı", "maltodextrin buğday", "bulgur",
    "irmik", "semolina", "tritikale", "seitan", "galeta", "ekmek kırıntısı",
]
MAY_CONTAIN_TERMS = [
    "eser miktarda", "iz miktarda", "aynı hatta", "aynı tesiste", "bulaşma", "kontaminasyon",
    "gluten içerebilir", "buğday içerebilir", "may contain", "traces of",
]


def ingredient_risk(text: str) -> tuple[str, list[str]]:
    key = search_key(text)
    found = []
    for term in RISKY_TERMS + MAY_CONTAIN_TERMS:
        if search_key(term) in key:
            found.append(term)
    if found:
        return "❌ UYGUN DEĞİL", found
    if not key:
        return "⚠️ İçindekiler girilmedi", []
    return "⚠️ BELİRSİZ / RİSKLİ", []


def product_card(row: pd.Series) -> None:
    st.success("✅ Site listesinde var: çölyak/glutensiz kullanım için uygun olarak listelenmiş.")
    st.write(f"**Kategori:** {row.get('category', '')}")
    st.write(f"**Marka/Ürün:** {row.get('name', '')}")
    st.write(f"**Kaynak:** {row.get('source', '')}")
    if row.get("last_checked", ""):
        st.caption(f"Son kontrol/veri tarihi: {row.get('last_checked', '')}")
    st.warning("Yine de ürünü satın almadan önce ambalajdaki güncel içerik, alerjen ve 'eser miktarda gluten/buğday' uyarılarını kontrol edin.")


st.title("🌾 Gluten Kontrol")
st.caption("Çölyak hastaları için güvenli tarafta kalan ürün kontrol uygulaması")

with st.sidebar:
    st.header("Veri modu")
    prefer_online = st.toggle("İnternet varsa canlı listeyi dene", value=True)
    st.caption("Bağlantı yoksa uygulama otomatik olarak offline CSV ile çalışır.")
    st.divider()
    st.caption("Kaynak: Çölyakla Yaşam Derneği glutensiz ürün listesi")

products, mode, message = load_products(prefer_online=prefer_online)

if mode == "online":
    st.info("🌐 Online mod aktif. " + message)
elif mode == "offline":
    st.warning("📴 Offline mod aktif. " + message)
else:
    st.error("Veri yüklenemedi. İnternet yoksa `data/products.csv` dosyası repo içinde bulunmalı.")
    st.code(message)
    st.stop()

if products.empty:
    st.error("Liste verisi boş.")
    st.stop()

products["_name_key"] = products["name"].map(search_key)
products["_cat_key"] = products["category"].map(search_key)

st.subheader("1) Kategori → marka/ürün seç")
categories = sorted(products["category"].dropna().unique())
selected_category = st.selectbox("Kategori seç", categories)
category_df = products[products["category"] == selected_category].copy()
product_names = sorted(category_df["name"].dropna().unique())
selected_product = st.selectbox("Marka/ürün seç", product_names)
selected_rows = category_df[category_df["name"] == selected_product]
if not selected_rows.empty:
    product_card(selected_rows.iloc[0])

st.divider()
st.subheader("2) İsimle ara")
query = st.text_input("Ürün, marka veya kategori yaz", placeholder="Örn: Balparmak, peynir, yoğurt...")
if query:
    q = search_key(query)
    mask = products["_name_key"].str.contains(q, na=False) | products["_cat_key"].str.contains(q, na=False)
    result = products[mask].drop(columns=["_name_key", "_cat_key"], errors="ignore")
    if result.empty:
        st.error("❌ Site listesinde bulunamadı. Çölyak için güvenli kabul etmeyin; etiket ve üretici teyidi gerekir.")
    else:
        st.write(f"{len(result)} sonuç bulundu.")
        st.dataframe(result[["category", "name", "status", "last_checked"]], use_container_width=True, hide_index=True)

st.divider()
st.subheader("3) İçindekilerden offline risk kontrolü")
ing = st.text_area("Ürün içindekiler / alerjen uyarısı", placeholder="Örn: mısır unu, pirinç unu, eser miktarda buğday içerebilir...")
if ing:
    verdict, found = ingredient_risk(ing)
    if verdict.startswith("❌"):
        st.error(verdict)
        st.write("Riskli ifade(ler): " + ", ".join(found))
    else:
        st.warning(verdict)
        st.write("Riskli kelime bulunmasa bile liste dışı ürün çölyak için güvenli kabul edilmemelidir.")

st.caption("Bu uygulama tıbbi karar yerine geçmez. Çölyakta çok düşük bulaşma riski bile önemli olduğundan belirsiz ürünler uygun kabul edilmez.")
