"""Metin / mesajlaşma seansları: Ses kaydı yerine yazılı koçluk görüşmesi.

Desteklenen biçimler (karışık da olabilir):
  Koç: Bugün ne konuşmak istersiniz?          -> koç/danışan doğrudan etiketlenir
  Danışan: Ekibimle ilgili...
  [04.11.2026 14:03] Ayşe Yılmaz: Merhaba      -> WhatsApp dışa aktarma biçimi
  04.11.2026 14:03 - Ayşe Yılmaz: Merhaba
  Ayşe: ...                                    -> isimli satırlar; kimin koç olduğunu LLM bulur
Ön eki olmayan satırlar bir önceki mesajın devamı sayılır.

Seansta gerçek zaman bilgisi olmadığı için konuşma süreleri kelime sayısından tahmin edilir
(dakikada ~150 kelime). Ses analizi metrikleri (hız, bekleme süresi, sessizlik) hesaplanmaz.
"""
import re

COACH_NAMES = {"koç", "koc", "coach", "k", "kouç"}
CLIENT_NAMES = {"danışan", "danisan", "client", "d", "coachee"}
_TIMESTAMP = r"(?:\[?\d{1,2}[./]\d{1,2}[./]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\]?\s*-?\s*)?"
LINE = re.compile(rf"^\s*{_TIMESTAMP}([^:\n]{{1,40}}?)\s*[:：]\s*(.+)$")
WORDS_PER_SEC = 2.5


def parse_text(text: str) -> list[dict]:
    messages: list[dict] = []
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = LINE.match(line)
        if m and not m.group(1).strip().startswith("http"):
            name, body = m.group(1).strip(), m.group(2).strip()
            messages.append({"name": name, "text": body})
        elif messages:
            messages[-1]["text"] += " " + line
        else:
            messages.append({"name": "", "text": line})

    segments, t = [], 0.0
    for msg in messages:
        duration = max(2.0, len(msg["text"].split()) / WORDS_PER_SEC)
        seg = {"start": round(t, 1), "end": round(t + duration, 1), "text": msg["text"]}
        key = msg["name"].lower()
        if key in COACH_NAMES:
            seg["speaker"] = "koc"
        elif key in CLIENT_NAMES:
            seg["speaker"] = "danisan"
        elif msg["name"]:
            seg["name"] = msg["name"]
        segments.append(seg)
        t += duration + 1.0
    return segments
