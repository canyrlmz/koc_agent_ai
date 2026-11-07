"""Bildirim kanalları: Davranış Takip ajanının mesajlarını danışana ve koça ulaştırır.

Her mesaj önce uygulama içi gelen kutusuna düşer (her zaman). Danışan ayrıca izin verdiyse
(danışan formundaki "Bildirim kanalları") e-posta ve/veya WhatsApp ile de gönderilir.

- E-posta: SMTP (SMTP_HOST vb. .env'de). Ayarlı değilse gönderilmez, "simüle" kaydedilir.
- WhatsApp: Meta WhatsApp Business Cloud API. Danışan son 24 saatte yazmadıysa yalnızca
  ONAYLI ŞABLON mesajı gönderilebilir; bu yüzden WHATSAPP_TEMPLATE tanımlıysa şablon kullanılır.

Her gönderim denemesi `notifications` tablosuna (giden kutusu) yazılır; koç neyin, hangi kanaldan,
ne zaman gittiğini görür.
"""
import re
import smtplib
import traceback
from email.message import EmailMessage

import requests

from . import auth, db
from .config import (PUBLIC_BASE_URL, SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER,
                     WHATSAPP_API_VERSION, WHATSAPP_PHONE_ID, WHATSAPP_TEMPLATE, WHATSAPP_TEMPLATE_LANG,
                     WHATSAPP_TOKEN)

CHANNELS = {"eposta": "E-posta", "whatsapp": "WhatsApp"}


def channels_of(client: dict) -> list[str]:
    return [c for c in (client.get("notify_channels") or "").split(",") if c in CHANNELS]


def _phone(raw: str) -> str:
    """WhatsApp için uluslararası biçim (yalnızca rakam): 0532... -> 90532..."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0"):
        digits = "90" + digits[1:]
    return digits


def send_email(to: str, subject: str, body: str) -> tuple[str, str]:
    if not to:
        return "hata", "E-posta adresi yok"
    if not SMTP_HOST:
        return "simule", "SMTP ayarlı değil (.env: SMTP_HOST)"
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = SMTP_FROM, to, subject
    msg.set_content(f"{body}\n\nFarkora'da görüntüle: {PUBLIC_BASE_URL}\n")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
        return "gonderildi", ""
    except Exception as e:  # noqa: BLE001
        return "hata", str(e)[:300]


def send_whatsapp(phone: str, body: str) -> tuple[str, str]:
    to = _phone(phone)
    if not to:
        return "hata", "Telefon numarası yok"
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID):
        return "simule", "WhatsApp Cloud API ayarlı değil (.env: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID)"
    if WHATSAPP_TEMPLATE:  # işletmenin başlattığı mesaj: onaylı şablon, metin {{1}} değişkeninde
        payload = {"messaging_product": "whatsapp", "to": to, "type": "template",
                   "template": {"name": WHATSAPP_TEMPLATE, "language": {"code": WHATSAPP_TEMPLATE_LANG},
                                "components": [{"type": "body", "parameters": [{"type": "text", "text": body[:1000]}]}]}}
    else:  # yalnızca danışan son 24 saatte yazdıysa çalışır
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body[:4000]}}
    try:
        r = requests.post(f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_ID}/messages",
                          json=payload, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=20)
        if r.ok:
            return "gonderildi", ""
        return "hata", r.text[:300]
    except requests.RequestException as e:
        return "hata", str(e)[:300]


def deliver(client: dict, target: str, message: str, action_id: int | None = None) -> list[dict]:
    """Mesajı hedefe (danisan / koc) ulaştırır; her kanalın sonucunu giden kutusuna yazar."""
    results = []

    def log(channel: str, recipient: str, status: str, detail: str = ""):
        db.add_notification(client["id"], action_id, channel, recipient, message, status, detail)
        results.append({"channel": channel, "status": status})

    try:
        if target == "danisan":
            log("uygulama", client["name"], "gonderildi")
            chans = channels_of(client) if client.get("consent") else []
            if "eposta" in chans:
                log("eposta", client.get("email", ""), *send_email(client.get("email", ""), "Farkora: koçluk sürecinizden bir not", message))
            if "whatsapp" in chans:
                log("whatsapp", client.get("phone", ""), *send_whatsapp(client.get("phone", ""), message))
        else:  # koça: panel uyarısı + e-posta
            log("uygulama", client.get("coach_name") or "Koç", "gonderildi")
            coach = auth.get_user(client["coach_id"]) if client.get("coach_id") else None
            if coach and coach.get("email") and not coach.get("is_demo"):
                log("eposta", coach["email"], *send_email(coach["email"], f"Farkora: {client['name']} için uyarı", message))
    except Exception:  # noqa: BLE001 - bildirim hatası ajanı durdurmasın
        traceback.print_exc()
    return results


def status() -> dict:
    return {
        "eposta": bool(SMTP_HOST),
        "whatsapp": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID),
        "whatsapp_sablon": bool(WHATSAPP_TEMPLATE),
    }
