# ⚽ Futbol Telegram Botu

Telegram üzerinde çalışan tam kapsamlı bir futbol simülasyon botu. Gerçek takımlar ve oyuncularla lig yönetimi, maç simülasyonu, transfer pazarı ve antrenman sistemi içerir.

---

## 🚀 Kurulum

### 1. Projeyi İndir
```bash
git clone https://github.com/kullanici_adi/futbol-bot.git
cd futbol-bot
```

### 2. Bağımlılıkları Yükle
```bash
pip install -r requirements.txt
```

### 3. Botu Başlat
```bash
python bot.py
```

---

## ☁️ Railway'e Deploy

1. Projeyi GitHub'a push et
2. [railway.app](https://railway.app) → **New Project → Deploy from GitHub Repo**
3. Repoyu seç → otomatik deploy başlar
4. Bot çalışmaya başlar ✅

> Token zaten `bot.py` içine entegre edilmiştir. Eğer güvenli tutmak istiyorsan Railway'de **Variables** sekmesine `TELEGRAM_TOKEN` ekle ve `bot.py`'deki şu satırı değiştir:
> ```python
> # Şu an:
> TOKEN = "8618492952:AAFk5EPHoYYl9ZMJLYTDiEjrjlMyuhPkAl8"
>
> # Güvenli hâli:
> import os
> TOKEN = os.environ.get("TELEGRAM_TOKEN")
> ```

---

## 📁 Proje Yapısı

```
futbol-py/
├── bot.py              ← Ana bot — tüm komutlar burada
├── match_engine.py     ← Maç simülasyonu ve lig motoru
├── leagues.py          ← Lig/takım/oyuncu arama fonksiyonları
├── data_manager.py     ← JSON tabanlı veri kayıt sistemi
├── requirements.txt    ← Bağımlılıklar
├── railway.toml        ← Railway deploy ayarları
└── data/
    └── leagues.json    ← 7 lig, 19 takım, 400+ oyuncu verisi
```

---

## 📋 Komutlar

### 👤 Takım Komutları

| Komut | Açıklama |
|---|---|
| `/takim` | Seçili takımının bilgisini gösterir |
| `/takimsec <takım adı>` | Bir takım seç |
| `/kadro [takım adı]` | Kadroyu pozisyona göre listele |
| `/takimlar [lig_id]` | Tüm ligleri veya bir ligin takımlarını göster |

**Örnek:**
```
/takimsec Manchester City
/takimsec Real Madrid
/kadro Arsenal
```

---

### 🏋️ Antrenman Komutları

| Komut | Açıklama |
|---|---|
| `/antrenman` | Mevcut antrenman tiplerini listele |
| `/antrenman kondisyon` | Dayanıklılık antrenmanı |
| `/antrenman teknik` | Pas ve top kontrolü |
| `/antrenman taktik` | Savunma/hücum organizasyonu |
| `/antrenman gucantrenman` | Fiziksel güç ve hız |
| `/antrenman atismapraktik` | Şut isabeti |

> ⏳ Antrenmanlar arasında **6 saat** bekleme süresi vardır.

---

### 💰 Transfer Komutları

| Komut | Açıklama |
|---|---|
| `/transfer` | Transfer menüsü |
| `/transferara <oyuncu adı>` | Oyuncu ara |
| `/oyuncu <oyuncu adı>` | Oyuncu detayını göster |
| `/pazar` | Günlük rastgele transfer pazarı |

**Örnek:**
```
/transferara Haaland
/oyuncu Vinicius
/transferara Mbappe
```

---

### 📊 Lig & Sonuçlar

| Komut | Açıklama |
|---|---|
| `/puan <lig_id>` | Puan durumunu göster |
| `/sonuclar` | Son 10 maç sonucunu listele |
| `/fikstür <lig_id>` | Yaklaşan 3 haftanın fikstürü |

**Örnek:**
```
/puan premier_league
/fikstür la_liga
```

---

### ⚙️ Admin Komutları

> Bu komutlar yalnızca grup yöneticileri tarafından kullanılabilir.

| Komut | Açıklama |
|---|---|
| `/ligbaslat <lig_id>` | Lig simülasyonunu başlat |
| `/ligdurdur <lig_id>` | Aktif ligi durdur |
| `/ligsifirla <lig_id>` | Ligi sıfırla ve sil |
| `/ligler` | Aktif ligleri listele |
| `/adminpuan <lig_id>` | Tam puan durumu tablosu |
| `/simule` | Manuel maç simülasyonunu tetikle |
| `/kanal` | Bu grubu duyuru kanalı olarak ayarla |

---

## 🌍 Lig ID'leri

| ID | Lig |
|---|---|
| `premier_league` | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League |
| `la_liga` | 🇪🇸 La Liga |
| `bundesliga` | 🇩🇪 Bundesliga |
| `serie_a` | 🇮🇹 Serie A |
| `ligue_1` | 🇫🇷 Ligue 1 |
| `eredivisie` | 🇳🇱 Eredivisie |
| `primeira_liga` | 🇵🇹 Primeira Liga |

---

## ⚡ Otomatik Maçlar

Bot her gün **18:00 ve 20:00 (Türkiye saati)** itibarıyla tüm aktif liglerde bir sonraki hafta maçlarını otomatik olarak simüle eder ve duyuru kanalına gönderir.

Manuel tetiklemek için `/simule` komutunu kullan.

---

## 🛠️ Teknik Detaylar

- **Dil:** Python 3.11+
- **Kütüphane:** python-telegram-bot 21.6
- **Zamanlayıcı:** APScheduler (job-queue)
- **Veri Saklama:** JSON dosyaları (`data/guilds/` klasörü)
- **Maç Motoru:** Oyuncu OVR değerlerine dayalı ağırlıklı rastgele simülasyon, ev sahibi avantajı +3 güç bonusu

---

## 📊 Veri Kaynağı

`data/leagues.json` içinde 2024-25 sezonu verilerine göre hazırlanmış:
- 7 Avrupa ligi
- 19 takım
- 400+ gerçek oyuncu (isim, yaş, milliyet, mevki, OVR, maaş)

---

## 📄 Lisans

MIT License — özgürce kullanabilir ve değiştirebilirsin.
