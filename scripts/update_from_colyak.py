"""Manual updater. Run only when internet is available: python scripts/update_from_colyak.py"""
from pathlib import Path
import subprocess
import sys

# This project keeps update logic inside app.py for identical parsing.
# To update locally, run: streamlit run app.py with online toggle on, or implement CI separately.
print("Güncelleme için uygulamayı internet varken açın; online mod başarılı olursa data/products.csv önbelleği güncellenir.")
print("Streamlit Cloud'da dosya sistemi kalıcı olmayabilir; kalıcı güncelleme için CSV'yi GitHub'a commit edin.")
