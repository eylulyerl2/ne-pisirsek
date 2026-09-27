# 🍽️ Ne Pişirsek?

Kişiselleştirilmiş haftalık yemek planlama ve öneri web uygulaması. Bireyler ve aileler için, Türk mutfağına ve bölgesel yemeklere odaklanır.

## Özellikler
- Bireysel ve aile grubu yemek planlaması
- Aileye bağlantı + tek kullanımlık şifreyle katılım; e-postası olmayan çocuklar ve büyükler kullanıcı adıyla hesap açabilir
- Şifre sıfırlama: aile yöneticisi, ailenin açtığı hesaplar için bağlantı + tek kullanımlık şifre üretir; giriş yapan herkes Tercihler'den şifresini değiştirebilir
- Tam sofra menüsü: çorba + ana yemek + yan yemek (pilav vb.) + salata
- Her yemeği değiştirme, "başka öner", kaldırma; tarif isteğe bağlı
- Kural tabanlı öneri motoru (bütçe, süre, kalori, sebze/baklagil/çorba sıklığı, puanlar)
- Otomatik alışveriş listesi
- 140'tan fazla Türk yemeği, 8 bölge (Karadeniz, Ege, Marmara, Akdeniz, İç Anadolu, Doğu Anadolu, Güneydoğu, Türkiye geneli)

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Frontend | React + TypeScript (Vite), TanStack Query |
| Backend | Python + FastAPI, SQLAlchemy |
| Veritabanı | PostgreSQL (Neon) |
| Auth | JWT |

## Geliştirme ortamı

### Backend
```
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements-dev.txt   # yalnızca çalıştırmak için requirements.txt yeterli
copy .env.example .env        # DATABASE_URL ve SECRET_KEY değerlerini doldurun
python create_tables.py       # tabloları oluşturur (var olan veritabanı için migrations/ klasöründeki SQL'leri tarih sırasıyla uygulayın)
python seed.py                # kategoriler ve Türk yemekleri
uvicorn app.main:app --port 8000
pytest                        # hızlı testler (birim)
pytest -m integration         # gerçek veritabanına yazan API testleri (~3 dk), sonunda kendini temizler
```
API dokümantasyonu: http://localhost:8000/docs

### Frontend
```
cd frontend
npm install
copy .env.example .env        # gerekirse VITE_API_URL
npm run dev                   # http://localhost:3000
npm test                      # birim ve bileşen testleri
npm run build
```

## Yayına alma (ücretsiz: Render + Vercel)

Depo bir monorepo olduğu için her iki serviste de kök dizin backend/ ve frontend/ olarak ayrıca ayarlanır.

1. **Backend (Render):** render.com → *New +* → *Blueprint* → bu GitHub deposunu seçin. Render kök dizindeki `render.yaml`'ı otomatik bulur (`rootDir: backend`). Deploy'dan önce panelde şu ortam değişkenlerini girin:
   - `DATABASE_URL` — `backend/.env` dosyanızdaki Neon bağlantı adresinin aynısı
   - `SECRET_KEY` — `backend/.env` dosyanızdaki değerin aynısı
   - `ALLOWED_ORIGINS` — şimdilik boş bırakın, 3. adımda dolduracağız

   Deploy bitince size `https://ne-pisirsek-api-xxxx.onrender.com` gibi bir adres verir, not edin. Ücretsiz plan 15 dakika kullanılmayınca uyur; ilk istek 30-60 saniye gecikebilir, bu normaldir.

2. **Frontend (Vercel):** vercel.com → *Add New* → *Project* → aynı depoyu seçin. *Root Directory* alanına `frontend` yazın (önemli). *Environment Variables* kısmına `VITE_API_URL` = 1. adımdaki Render adresi (sonunda `/` olmadan) ekleyin. Deploy edin; size `https://ne-pisirsek-xxxx.vercel.app` gibi bir adres verir — arkadaşlarınızla paylaşacağınız adres budur.

3. Render paneline dönüp `ALLOWED_ORIGINS` değişkenini 2. adımdaki Vercel adresiyle doldurun (örn. `https://ne-pisirsek-xxxx.vercel.app`, sonunda `/` olmadan) ve yeniden deploy edin. Bu adım olmadan frontend backend'e istek atamaz (CORS hatası alırsınız).

Not: Üretim, geliştirmede kullandığınız Neon veritabanının aynısını kullanır — test verileriniz ve gerçek kullanıcı kayıtları aynı veritabanında birlikte olur. İleride ayırmak isterseniz Neon'da ikinci bir proje/veritabanı açıp `DATABASE_URL`'i ona göre güncellemeniz yeterli.

## Lisans
MIT
