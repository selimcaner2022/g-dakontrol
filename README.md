# Gluten Kontrol v7 Hibrit

Bu sürüm hibrit çalışır:

- İnternet varsa: Çölyakla Yaşam Derneği ürün listesini canlı çekmeyi dener.
- İnternet yoksa veya canlı veri güvenli gelmezse: `data/products.csv` dosyasını kullanarak offline çalışır.
- Hiçbir durumda bağlantı hatası yüzünden uygulama çökmez; offline moda düşer.

## Streamlit Cloud

Main file path:

```text
app.py
```

## Önemli

`data/products.csv` GitHub reposunda mutlaka bulunmalı. Bu dosya offline modun temelidir.

## Çalıştırma

```bash
pip install -r requirements.txt
streamlit run app.py
```
