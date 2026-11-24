# Farkora

İnsan koçlarını destekleyen, danışanın gelişimini takip eden ve kendiliğinden harekete geçen **yapay zekâ destekli koçluk platformu**. Koçun yerini almaz, koça asistanlık yapar.

> Hazırlayan: Şevket Can Yorulmaz · Kasım 2026

## Dört yapay zekâ ajanı

| # | Ajan | Ne yapar | Kod |
|---|---|---|---|
| 1 | **Seans Analiz ve Metrik** | Transkript, konuşmacı ayrımı, ses metrikleri, seans raporu, ICF 8 yetkinlik puanı (kanıtlı), duygu dili, önceki planların izi | `analysis.py`, `video.py`, `transcribe.py` |
| 2 | **Müfredat ve Mikro-Öğrenme Tasarım** | Gelişim alanı → OpenAlex'te bilimsel kaynak → oyunlaştırılmış mikro-eğitim + koç için özet | `training.py`, `research.py` |
| 3 | **Davranış Takip ve Proaktif Eylem** | Görev ve eğer–o zaman planı takibi, ruh hali uyarısı, mesajlar (uygulama, e-posta, WhatsApp), davranış kanıtı | `agent.py`, `notify.py` |
| 4 | **Kurumsal İçgörü ve Anonimleştirme** | Anonim kurum paneli, k-anonimlik (en az 3 kişi), tema kümeleri, birim risk sinyalleri | `insights.py` |

Ajanlar zincir gibi çalışır: analiz ajanının bulduğu gelişim alanı müfredat ajanına, oradaki plan davranış ajanına, hepsinin anonim özeti kurum ajanına gider. Uygulamadaki **Yapay Zekâ Ajanları** sayfası her ajanın görevini ve kaç kez çalıştığını gösterir.

## Özellikler

**Seans girişi (dört yol)**
- **Sesli:** kayıt dosyası veya tarayıcıdan canlı ses kaydı
- **Görsel:** video dosyası, canlı kayıt (Zoom/Teams **ekran kaydı** veya kamera), **fotoğraf** (beyaz tahta, not, hedef panosu)
- **Yazılı:** “Koç:/Danışan:” satırları veya WhatsApp dökümü
- **Toplantı botu:** Zoom / Teams / Meet bağlantısıyla toplantıya katılıp kaydı alır (Recall.ai; anahtar yoksa simülasyon)

**Analiz ve koç desteği**
- Seans raporu, danışan hafızası (önceki seanslarla bağlantı), seans öncesi hazırlık brifi
- ICF 8 temel yetkinlik puanı, her puan transkriptten alıntıyla
- Ses analizi: konuşma payı, hızı, açık uçlu soru oranı, düşünme süresi
- **Duygu dili:** danışanın kendi sözleriyle söylediği duygular (yalnızca metinden; yüzden duygu çıkarımı bilerek yapılmaz, AB Yapay Zekâ Yasası md. 5(1)(f))
- Görsel analiz: video kareleri ve fotoğraflarda görünen içerik

**Coaching → Training (oyunlaştırılmış eğitim)**
- Hikâye gibi kaydırılan bilgi kartları, mini çizgi roman, Mit mi gerçek mi, eşleştirme, “Sen olsan ne yapardın?” senaryosu, quiz
- Puan, seviye (Çaylak → Usta), güven ölçer, konfeti ve rozet
- **Eğer–o zaman planı** (Gollwitzer & Sheeran) ve 2 gün sonra açılan tekrar turu
- Her bilgi OpenAlex makalesinin numarasıyla

**Davranışın gerçek hayatta kanıtı**
1. Danışanın öz-bildirimi (“Planlarım” sekmesi: Yaptım / Kısmen / Fırsat olmadı / Yapamadım)
2. Paydaş gözlemi: danışanın onayıyla bir yakınına giden, girişsiz, tek seferlik bağlantı
3. Sonraki seansta planın izi

**Koçsuz mod (kendi kendine koçluk)**
- Koçu olmayan kullanıcı giriş ekranından kendisi kayıt olur (18 yaş ve üstü, KVKK rızası, “terapi değildir” onayı)
- 5 adımda kendini tanıtır: temel bilgiler, zevkler, 10 soruluk kişilik testi (TIPI), zaman ve imkânlar, sorun
- Asistan arkadaş gibi konuşur: kısa mesajlar, her seferinde tek soru, en fazla 6 soru; sonra “Seni böyle anladım” profili (kullanıcı onaylar ya da düzeltir)
- Yaşa, karaktere, zevklere, imkânlara ve sorunun şiddetine göre 4 haftalık, kolaydan zora giden plan; her görevde “neden sana uygun”, zorluk, süre ve haritada arama bağlantısı; “Bu bana uymaz” ile görev değiştirme
- Her hafta sonunda ajan haftayı değerlendirir, gelecek haftayı kolaylaştırır ya da zorlaştırır; kişiye özel eğitim ve hatırlatmalar mevcut sistemden gelir
- **Güvenlik:** kendine zarar / intihar ifadesi (kural tabanlı + yapay zekâ) görülürse plan durur, sabit destek mesajı ve 112 gösterilir; ağır belirtilerde uzman önerilir; tanı ve ilaç konuşulmaz
- İstenirse “Bir koçla eşleş” ile yöneticiye istek gider; koç atanınca profil ve plan koçun ekranında görünür

**Roller:** yönetici, koç (yalnızca kendi danışanları), danışan (kendi gelişimi; ICF ve transkript görünmez), kurum yöneticisi (anonim panel). KVKK açık rızası olmadan kayıt yüklenemez.

**Arayüz:** açık/koyu tema, telefona uyumlu, daraltılabilir menü.

## Kurulum (Windows)

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python run.py
```

Tarayıcıda **http://localhost:8765** adresini açın.

**Kolay başlatma ve otomatik güncelleme:** Proje `git clone` ile indirildiyse `Farkora_Baslat.bat` dosyasına çift tıklamak yeterli. Her açılışta GitHub'daki son sürümü indirir, eksik paketleri kurar ve uygulamayı tarayıcıda açar. `.env` ve `data/` güncellemeden etkilenmez; yeni veritabanı alanları açılışta otomatik eklenir.

**Masaüstü kısayolu:** `Masaustu_Kisayolu_Olustur.bat` masaüstüne Farkora simgeli bir kısayol ekler. Site tarayıcıda açıkken adres çubuğundaki “Uygulama olarak yükle” ile de masaüstü / telefon uygulaması gibi kurulabilir.

**İnternete açmak (geçici link):** `Farkora_Yayinla.bat` uygulamayı başlatır ve Cloudflare geçici tüneliyle herkese açık bir link verir (link panoya kopyalanır). `cloudflared` kurulu olmalıdır (`winget install Cloudflare.cloudflared`). Link her açılışta değişir ve yalnızca pencere ve bilgisayar açıkken çalışır. FFmpeg kurulu olmalıdır. İlk açılışta yönetici hesabı oluşturulur; “Örnek veriyle göster” kurgusal verileri yükler.

## Ayarlar (`.env`)

| Ayar | Açıklama |
|---|---|
| `LLM_PROVIDER` | `mock` (anahtarsız örnek cevaplar), `gemini` (`GEMINI_API_KEY`) veya `claude` (`ANTHROPIC_API_KEY`) |
| `TRANSCRIBE_MODE` | `mock` veya `whisper` (yerelde, ücretsiz) |
| `RESEARCH_MODE` | `openalex` veya `mock` |
| `DATABASE_URL` | Boş = SQLite. PostgreSQL için `postgresql://kullanici:sifre@sunucu:5432/farkora` |
| `SMTP_*`, `WHATSAPP_*` | E-posta ve WhatsApp bildirimleri (boşsa “simüle”) |
| `RECALL_API_KEY` | Gerçek toplantı botu (boşsa simülasyon) |

Tüm ayarlar ve açıklamaları `.env.example` dosyasında. **`.env` dosyası asla depoya eklenmez.**

## Testler

```bash
.venv\Scripts\python -m pytest -q
```

27 uçtan uca test (SQLite). Koçsuz moddan önceki 23 test PostgreSQL üzerinde de denendi.

## Klasör yapısı

```
app/
  main.py        Web API (FastAPI), rol bazlı yetki
  agents.py      4 ajanın tanımı ve istatistikleri
  analysis.py    Seans analiz hattı
  video.py       Video kareleri ve fotoğraf analizi
  transcribe.py  Ses → metin (faster-whisper)
  training.py    Mikro-eğitim üretimi
  research.py    OpenAlex bilimsel kaynak tarama
  agent.py       Davranış takip ajanı, davranış kanıtı
  selfcoach.py   Koçsuz mod: tanışma sohbeti, profil, kişiye özel plan, haftalık ayar
  safety.py      Koçsuz mod güvenlik kuralları (kriz tespiti)
  notify.py      Uygulama içi, e-posta, WhatsApp bildirimleri
  meetingbot.py  Zoom / Teams / Meet toplantı botu
  insights.py    Paneller, kurumsal içgörü ve anonimleştirme
  llm.py         Dil modeli katmanı (Gemini / Claude / mock)
  db.py          SQLite / PostgreSQL
static/          Web arayüzü
tests/           Uçtan uca testler
```

## Sınırlar ve yol haritası

- [ ] Toplantı botu, e-posta ve WhatsApp için gerçek servis anahtarları (kod hazır)
- [ ] Telefona kurulabilir uygulama (PWA)
- [ ] ICF puanlarının uzman koçla doğrulanması
- [ ] Kurum veya sosyal birimde pilot

> ICF puanlaması gelişim amaçlı bir ön değerlendirmedir, resmî akreditasyon puanı değildir.
> Ücretsiz yapay zekâ anahtarlarıyla yalnızca kurgusal veri kullanın. Gerçek danışan verisi için açık rıza (KVKK) ve veri işleme sözleşmeli bir hizmet gerekir.

## Lisans ve kullanım

© 2026 Şevket Can Yorulmaz. **Tüm hakları saklıdır.**

Bu depo, kodun incelenebilmesi için herkese açıktır; açık kaynak lisansı **değildir**. Kod yalnızca okunabilir ve akademik değerlendirme amacıyla incelenebilir. Yazılı izin olmadan kopyalanamaz, değiştirilemez, dağıtılamaz, yayımlanamaz ve ticari ya da başka bir amaçla kullanılamaz. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakın. İzin için proje sahibiyle iletişime geçin.
