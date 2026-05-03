# Gluten Kontrol

Çölyak hastaları için muhafazakâr ürün kontrolü yapan Streamlit tabanlı MVP.

## Özellikler

- Yerel CSV veri tabanı ile çevrimdışı ürün arama
- Çölyakla Yaşam Derneği listesindeki ürünler için durum gösterimi
- Listede bulunmayan ürünler için içerik/alerjen bazlı risk yorumu
- Çok düşük riskte bile “uygun değil / teyit gerekli” yaklaşımı
- OCR, barkod ve LLM entegrasyonuna hazır mimari

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Veriyi güncelleme

```bash
python scripts/update_from_colyak.py
```

Not: Dernek sayfasındaki liste üretici beyanlarına göre güncellenir. Uygulama, tıbbi tavsiye yerine geçmez. Ürün listede olsa bile etiket, alerjen uyarısı ve üretici teyidi kontrol edilmelidir.

## GitHub'a yükleme

```bash
git init
git add .
git commit -m "Initial Gluten Kontrol Streamlit MVP"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADIN/gluten-kontrol.git
git push -u origin main
```
