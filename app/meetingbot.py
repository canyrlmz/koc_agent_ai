"""Toplantı botu: Zoom / Microsoft Teams / Google Meet toplantısına "not asistanı" olarak katılır,
toplantı bitince kaydı indirir ve Seans Analiz ajanına verir.

Sağlayıcılar:
  - recall: Recall.ai (https://docs.recall.ai). RECALL_API_KEY tanımlıysa kullanılır. Bot
    `POST /api/v1/bot/` ile oluşturulur; durumu `done` olunca kaydın indirme adresi
    `GET /api/v1/bot/{id}/` cevabındaki `media_shortcuts.video_mixed.data.download_url` alanındadır.
  - simulasyon: anahtar yoksa, sunum ve deneme için. Gerçek toplantıya katılmaz; birkaç saniye
    sonra örnek bir görüşme metniyle seans oluşturur (başlıkta "Simülasyon" yazar).

Etik: Bot toplantıya görünür bir katılımcı olarak ve adında "Not Asistanı" yazarak girer; danışanın
KVKK açık rızası olmadan bot gönderilemez (main.py).
"""
import re
import threading
import traceback
import uuid
from datetime import datetime

import requests

from . import db
from .config import MEETING_BOT_NAME, RECALL_API_KEY, RECALL_REGION, UPLOAD_DIR

MEETING_HOSTS = re.compile(r"^https://([\w-]+\.)*(zoom\.us|teams\.microsoft\.com|teams\.live\.com|meet\.google\.com)/", re.I)
POLL_SECONDS = 20

SIM_DIALOG = """Koç: Merhaba, bugün neyi konuşmak istersiniz?
Danışan: Geçen hafta kurduğum planı denedim. Burak teslimi kaçırınca aynı gün konuştum.
Koç: Bu konuşma sizin için nasıl geçti?
Danışan: İlk defa ertelemeden söyledim. Biraz gergindim ama rahatladım da.
Koç: Bu deneyimden kendinizle ilgili ne fark ettiniz?
Danışan: Net olmanın aslında ilişkiyi bozmadığını gördüm. Bunu ekipteki diğer kişilerle de denemek istiyorum.
Koç: Önümüzdeki hafta bunu hangi durumda deneyebilirsiniz?
Danışan: Pazartesi sprint toplantısında, gecikmeyi fark ettiğim anda kısa bir birebir isteyeceğim."""


def provider() -> str:
    return "recall" if RECALL_API_KEY else "simulasyon"


def _api(path: str) -> str:
    return f"https://{RECALL_REGION}.recall.ai/api/v1/{path}"


def _headers() -> dict:
    return {"Authorization": f"Token {RECALL_API_KEY}", "Content-Type": "application/json"}


def valid_url(url: str) -> bool:
    return bool(MEETING_HOSTS.match(url.strip()))


def send_bot(client_id: int, meeting_url: str, title: str) -> dict:
    row = db.create_meeting_bot(client_id, provider(), meeting_url.strip(), title)
    if row["provider"] == "recall":
        try:
            r = requests.post(_api("bot/"), headers=_headers(), timeout=30, json={
                "meeting_url": row["meeting_url"], "bot_name": MEETING_BOT_NAME,
                "recording_config": {"video_mixed_mp4": {}},
            })
            r.raise_for_status()
            db.update_meeting_bot(row["id"], bot_id=r.json().get("id", ""))
        except requests.RequestException as e:
            db.update_meeting_bot(row["id"], status="hata", error=f"Bot oluşturulamadı: {e}"[:400])
    return db.get_meeting_bot(row["id"])


def _download_url(bot: dict) -> str | None:
    for rec in bot.get("recordings") or []:
        url = (((rec.get("media_shortcuts") or {}).get("video_mixed") or {}).get("data") or {}).get("download_url")
        if url:
            return url
    return bot.get("video_url")  # eski API sürümleri


def _start_session(row: dict, path: str, source: str) -> None:
    from . import analysis

    session = db.create_session(row["client_id"], row["title"] or "Toplantı kaydı", path, source)
    db.update_meeting_bot(row["id"], status="isleniyor", session_id=session["id"])
    analysis.process_session(session["id"])
    done = db.get_session(session["id"])
    db.update_meeting_bot(row["id"], status="tamamlandi" if done["status"] == "tamamlandi" else "hata",
                          error=done.get("error"))


def poll_once() -> None:
    for row in db.list_meeting_bots(active_only=True):
        try:
            if row["provider"] == "simulasyon":
                age = (datetime.now() - datetime.fromisoformat(row["created_at"])).total_seconds()
                if row["status"] == "katiliyor" and age > 4:
                    db.update_meeting_bot(row["id"], status="kayitta")
                elif row["status"] == "kayitta" and age > 10:
                    path = UPLOAD_DIR / f"{uuid.uuid4().hex}.txt"
                    path.write_text(SIM_DIALOG, encoding="utf-8")
                    _start_session(row, str(path), "metin")
                continue
            r = requests.get(_api(f"bot/{row['bot_id']}/"), headers=_headers(), timeout=30)
            r.raise_for_status()
            bot = r.json()
            codes = [c.get("code") for c in bot.get("status_changes") or []]
            last = codes[-1] if codes else ""
            if last in ("fatal",) or "fatal" in codes:
                db.update_meeting_bot(row["id"], status="hata", error="Bot toplantıya katılamadı veya kayıt alınamadı.")
            elif last == "done":
                url = _download_url(bot)
                if not url:
                    continue  # kayıt hazırlanıyor; sonraki turda tekrar bakılır
                path = UPLOAD_DIR / f"{uuid.uuid4().hex}.mp4"
                with requests.get(url, stream=True, timeout=300) as dl:
                    dl.raise_for_status()
                    with path.open("wb") as f:
                        for chunk in dl.iter_content(1 << 20):
                            f.write(chunk)
                _start_session(row, str(path), "upload")
            elif last in ("in_call_recording", "recording_permission_allowed"):
                if row["status"] != "kayitta":
                    db.update_meeting_bot(row["id"], status="kayitta")
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            db.update_meeting_bot(row["id"], status="hata", error=str(e)[:400])


def start_poller() -> threading.Event:
    stop = threading.Event()

    def loop():
        while not stop.wait(POLL_SECONDS):
            if db.list_meeting_bots(active_only=True):
                poll_once()

    threading.Thread(target=loop, name="meeting-bot-poller", daemon=True).start()
    return stop
