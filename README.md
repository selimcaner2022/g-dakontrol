# Gluten Kontrol Veri Dosyası

Bu pakette `data/products.csv` dosyası vardır. Streamlit projesinde aynı klasör yapısıyla kullanın:

```text
app.py
data/products.csv
scripts/update_from_colyak.py
```

CSV kolonları:
- `category`: kategori
- `name`: ürün/marka satırı
- `status`: `site_listesinde_var_uygun` veya `uygun_degil_tedbirli`
- `source_url`: kaynak sayfa
- `note`: güvenlik notu
- `last_checked`: kontrol tarihi

Kaynak: https://colyak.org.tr/glutensiz-urunler/

Not: Dernek sayfası üretici beyanlarına dayandığını ve ürün listede olsa bile etiket/alerjen bilgilerinin kontrol edilmesi gerektiğini belirtir.
