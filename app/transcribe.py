"""Ses -> metin. faster-whisper yerelde çalışır, API ücreti yoktur.

Çıktı: [{"start": sn, "end": sn, "text": "..."}] biçiminde segment listesi.
Konuşmacı (koç/danışan) ayrımı burada değil, analysis.py'de yapılır.
"""
from functools import lru_cache

from .config import TRANSCRIBE_MODE, WHISPER_DEVICE, WHISPER_LANGUAGE, WHISPER_MODEL

# Mock modda kullanılan örnek seans: gerçek ses olmadan tüm hattı denemek için.
SAMPLE_DIALOGUE = [
    "Merhaba, hoş geldiniz. Bugünkü seanstan ne almak istersiniz?",
    "Merhaba. Aslında ekibimle iletişimde zorlanıyorum, özellikle geri bildirim verirken.",
    "Geri bildirim verirken tam olarak neler yaşıyorsunuz?",
    "Kırıcı olmaktan korkuyorum, o yüzden ya hiç söylemiyorum ya da çok geç söylüyorum.",
    "Bu korku size neyi koruyormuş gibi geliyor?",
    "Sanırım ilişkileri bozmak istemiyorum. Herkesin beni sevmesini istiyorum galiba.",
    "Bunu fark etmek size ne hissettiriyor?",
    "Biraz şaşırdım açıkçası. Liderlik yerine sevilmeyi seçiyormuşum.",
    "Bu seansın sonunda neyi farklı yapmak isterdiniz?",
    "Bu hafta en az bir kişiye zamanında ve net bir geri bildirim vermek istiyorum.",
    "Bunu yaparken neye ihtiyacınız olacak?",
    "Ne söyleyeceğimi önceden yazmam iyi olabilir. Bir de sakin bir zaman seçmem.",
    "Harika. Bunu ne zaman ve kiminle yapacaksınız?",
    "Perşembe günü proje toplantısından sonra Ayşe ile konuşacağım.",
]


def transcribe(audio_path: str) -> list[dict]:
    if TRANSCRIBE_MODE == "mock":
        return [
            {"start": i * 12.0, "end": i * 12.0 + 10.0, "text": text}
            for i, text in enumerate(SAMPLE_DIALOGUE)
        ]
    model = _whisper_model()
    segments, _info = model.transcribe(
        audio_path, language=WHISPER_LANGUAGE, vad_filter=True, word_timestamps=True
    )
    # Whisper bir segmentte iki kişinin konuşmasını birleştirebilir; konuşmacı ayrımı doğru
    # olsun diye kelime zaman damgalarıyla cümle cümle bölüyoruz.
    out: list[dict] = []
    for s in segments:
        words = [w for w in (s.words or []) if w.word.strip()]
        if not words:
            if s.text.strip():
                out.append({"start": round(float(s.start), 2), "end": round(float(s.end), 2), "text": s.text.strip()})
            continue
        buf: list = []
        for w in words:
            buf.append(w)
            if w.word.strip()[-1] in ".?!…":
                out.append(_sentence(buf))
                buf = []
        if buf:
            out.append(_sentence(buf))
    return out


def _sentence(words) -> dict:
    return {
        "start": round(float(words[0].start), 2),
        "end": round(float(words[-1].end), 2),
        "text": "".join(w.word for w in words).strip(),
    }


@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel

    compute_type = "float16" if WHISPER_DEVICE == "cuda" else "int8"
    return WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=compute_type)
