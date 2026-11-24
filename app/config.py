"""Uygulama ayarları. Değerler .env dosyasından veya ortam değişkenlerinden okunur."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# "claude" = gerçek analiz, "mock" = API anahtarı olmadan sahte cevaplarla deneme
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
# Ana modelin günlük ücretsiz kotası dolunca sırayla denenecek modeller (her birinin kendi kotası var)
GEMINI_FALLBACK_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_FALLBACK_MODELS", "gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-flash-lite-latest"
).split(",") if m.strip()]

# "whisper" = gerçek transkript (yerelde, ücretsiz), "mock" = hazır örnek diyalog
TRANSCRIBE_MODE = os.getenv("TRANSCRIBE_MODE", "mock").lower()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny / base / small / medium / large-v3
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # NVIDIA ekran kartı varsa "cuda"
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "tr")

# "openalex" = gerçek akademik yayın araması (ücretsiz), "mock" = örnek makaleler (test için)
RESEARCH_MODE = os.getenv("RESEARCH_MODE", "openalex").lower()
# Anahtarsız kullanımda günlük kota çok küçük ve aynı ağdaki herkesle ortak.
# Ücretsiz anahtar (günlük daha yüksek kota): https://openalex.org/settings/api
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "")

DATA_DIR =Path(os.getenv("DATA_DIR", ROOT / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "koc_agent.db"

# Hafıza: yeni seans analiz edilirken danışanın kaç önceki seansı dikkate alınsın
MEMORY_SESSION_COUNT = int(os.getenv("MEMORY_SESSION_COUNT", "5"))

# Aktif ajan: kaç dakikada bir tüm danışanları kontrol etsin (0 = zamanlayıcı kapalı)
AGENT_INTERVAL_MIN = int(os.getenv("AGENT_INTERVAL_MIN", "30"))
# Ajan, seanstaki gelişim alanı için eğitim içeriğini kendiliğinden üretsin mi
AGENT_AUTO_TRAINING = os.getenv("AGENT_AUTO_TRAINING", "true").lower() == "true"
# Seansta üstlenilen görevlerin varsayılan süresi (gün)
TASK_DUE_DAYS = int(os.getenv("TASK_DUE_DAYS", "7"))

# Eğer–o zaman planı kaydedildikten kaç gün sonra ajan "oldu mu?" diye sorsun
COMMITMENT_CHECK_DAYS = int(os.getenv("COMMITMENT_CHECK_DAYS", "3"))

# Bağlantılarda kullanılacak adres (gözlemci linki, e-postadaki "uygulamayı aç" linki)
# Render gibi sağlayıcılar kendi adresini RENDER_EXTERNAL_URL ile verir
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or os.getenv("RENDER_EXTERNAL_URL")
                   or "http://127.0.0.1:8765").rstrip("/")

# --- Sunucu kurulumu (isteğe bağlı) ---
# Hiç hesap yokken ilk yönetici bu bilgilerle oluşturulur (sunucuda ilk ziyaretçinin yönetici olmasını önler)
INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "").strip().lower()
INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")
# İlk açılışta, veritabanında hiç danışan yoksa kurgusal örnek veriyi yükle
SEED_DEMO = os.getenv("SEED_DEMO", "false").lower() == "true"

# --- Bildirim kanalları (boş bırakılırsa mesaj gönderilmez, giden kutusuna "simüle" yazılır) ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "farkora@localhost")
# WhatsApp Business Cloud API (Meta). İşletmenin başlattığı mesajlar için onaylı şablon gerekir.
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_TEMPLATE = os.getenv("WHATSAPP_TEMPLATE", "")        # ör. "farkora_bildirim" (tek {{1}} değişkenli)
WHATSAPP_TEMPLATE_LANG = os.getenv("WHATSAPP_TEMPLATE_LANG", "tr")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")

# --- Toplantı botu (Zoom / Teams / Google Meet'e katılıp kaydı alır) ---
# Recall.ai: https://docs.recall.ai — anahtar yoksa bot özelliği kapalıdır (örnek modda simülasyon).
RECALL_API_KEY = os.getenv("RECALL_API_KEY", "")
RECALL_REGION = os.getenv("RECALL_REGION", "us-east-1")
MEETING_BOT_NAME = os.getenv("MEETING_BOT_NAME", "Farkora Not Asistanı")

# Veritabanı: boşsa SQLite (data/koc_agent.db). PostgreSQL için ör.
# DATABASE_URL=postgresql://kullanici:sifre@localhost:5432/farkora
DATABASE_URL = os.getenv("DATABASE_URL", "")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
