"""Seans analiz hattı: transkript -> konuşmacı ayrımı -> metrikler -> rapor + ICF puanlaması.

Danışan hafızası: yeni seans analiz edilirken aynı danışanın önceki seans raporları
modele bağlam olarak verilir, böylece sistem "geçen sefer ne konuşulmuştu" bilir.
"""
import json
import re
import traceback
from pathlib import Path

from . import db, llm, video
from .config import MEMORY_SESSION_COUNT
from .context import client_profile
from .icf import rubric_text
from .schemas import ICFEvaluation, PreSessionBrief, SessionReport, SpeakerLabels
from .textsession import parse_text
from .transcribe import transcribe

SYSTEM = (
    "Sen deneyimli bir koçluk süpervizörü ve ICF (International Coaching Federation) "
    "yetkinlik modelini iyi bilen bir yapay zekâ asistanısın. İnsan koçlara seans "
    "hazırlığı ve seans sonrası değerlendirmede destek oluyorsun. Türkçe yaz. "
    "Yorumlarını transkriptteki kanıtlara dayandır; transkriptte olmayan bilgiyi uydurma. "
    "Tıbbi veya psikolojik teşhis koyma."
)

OPEN_QUESTION_WORDS = re.compile(
    r"\b(ne|neyi|neler|nasıl|neden|niçin|niye|hangi|kim|kimle|kiminle|nerede|nereye|ne zaman)\b",
    re.IGNORECASE,
)
CLOSED_QUESTION_PARTICLE = re.compile(r"\b(mi|mı|mu|mü)(sin|sın|sun|sün|siniz|sınız|yım|yim|dir|dır)?\b")


# --- Ana hat ---------------------------------------------------------------


def process_session(session_id: int) -> None:
    """Arka planda çalışır; her adımda durumu veritabanına yazar."""
    session = db.get_session(session_id)
    try:
        if session["source"] == "foto":
            report = _process_photo_session(session_id, session)
        else:
            report = _process_recorded_session(session_id, session)
    except Exception as e:  # noqa: BLE001 - hatayı kullanıcıya göstermek için yakalıyoruz
        traceback.print_exc()
        db.update_session(session_id, status="hata", error=str(e))
        return

    # Seans bitti: görevleri takibe al ve ajanı uyandır (takip mesajı, otomatik eğitim vb.)
    from . import agent

    if not db.list_tasks_for_session(session_id):  # tekrar analizde görevler çoğalmasın
        agent.create_tasks_from_report(session, report.model_dump())
    agent.run_safely(session["client_id"])


def _process_photo_session(session_id: int, session: dict) -> SessionReport:
    """Fotoğraflı seans: ses/transkript yok; fotoğraflar + koçun notu -> görsel analiz + rapor.
    Koçun konuşması olmadığı için ICF puanlaması yapılmaz."""
    notes_path = Path(session["audio_path"])
    notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
    db.update_session(session_id, status="gorsel", error=None)
    visual = video.analyze_photos(session_id, notes)
    db.update_session(session_id, visual=visual, metrics={"kaynak_turu": "foto"}, transcript=[])
    db.update_session(session_id, status="rapor")
    client = db.get_client(session["client_id"])
    history = db.previous_reports(session["client_id"], session_id, MEMORY_SESSION_COUNT)
    report = make_report(client, [], {}, history, video.summary_for_report(visual), notes=notes)
    db.update_session(session_id, report=report.model_dump(), status="tamamlandi")
    return report


def _process_recorded_session(session_id: int, session: dict) -> SessionReport:
    """Ses, video veya yazılı seans."""
    db.update_session(session_id, status="transkript", error=None)
    is_text = session["source"] == "metin"
    if is_text:
        segments = parse_text(Path(session["audio_path"]).read_text(encoding="utf-8"))
    else:
        segments = transcribe(session["audio_path"])
    if not segments:
        raise ValueError("Kayıtta konuşma bulunamadı.")

    db.update_session(session_id, status="konusmaci_ayrimi")
    if not all("speaker" in s for s in segments):
        segments = label_by_names(segments) or label_speakers(segments)
    metrics = compute_metrics(segments, audio=not is_text)
    db.update_session(session_id, transcript=segments, metrics=metrics)

    # Görsel seans: video kaydıysa karelerden görsel analiz (hata olursa seans yine tamamlanır)
    visual = None
    if not is_text and video.has_video(session["audio_path"]):
        db.update_session(session_id, status="gorsel", source="video")
        try:
            visual = video.analyze(session_id, session["audio_path"], segments)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            visual = {"hata": str(e)}
        db.update_session(session_id, visual=visual)

    db.update_session(session_id, status="rapor")
    client = db.get_client(session["client_id"])
    history = db.previous_reports(session["client_id"], session_id, MEMORY_SESSION_COUNT)
    report = make_report(client, segments, metrics, history, video.summary_for_report(visual))
    db.update_session(session_id, report=report.model_dump())

    db.update_session(session_id, status="icf")
    icf = evaluate_icf(segments, metrics)
    icf_data = icf.model_dump()
    scores = [c["puan"] for c in icf_data["yetkinlikler"]]
    icf_data["ortalama"] = round(sum(scores) / len(scores), 2) if scores else None
    db.update_session(session_id, icf=icf_data, status="tamamlandi")
    return report


# --- Adımlar ---------------------------------------------------------------


def _numbered(segments: list[dict], with_speaker: bool = False) -> str:
    lines = []
    for i, s in enumerate(segments):
        who = f" {'KOÇ' if s.get('speaker') == 'koc' else 'DANIŞAN'}:" if with_speaker else ""
        name = f" <{s['name']}>" if s.get("name") and not with_speaker else ""
        lines.append(f"\n[{i}] ({_fmt_time(s['start'])}){name}{who} {s['text']}")
    return "".join(lines)


COACH_HINTS = ("koç", "koc", "coach", "hoca", "mentor", "danışman")


def label_by_names(segments: list[dict]) -> list[dict] | None:
    """İsimli yazışmalarda (ör. WhatsApp) koçu yapay zekâya sormadan bulur; istek tasarrufu.

    Tam iki kişi varsa: adında "koç/hoca/coach" geçen ya da daha çok soru soran kişi koçtur.
    Emin olunamazsa None döner ve yapay zekâya sorulur.
    """
    if not all(s.get("name") for s in segments):
        return None
    names = list(dict.fromkeys(s["name"] for s in segments))
    if len(names) != 2:
        return None
    hinted = [n for n in names if any(h in n.lower() for h in COACH_HINTS)]
    if len(hinted) == 1:
        coach = hinted[0]
    else:
        def question_ratio(name):
            msgs = [s["text"] for s in segments if s["name"] == name]
            return sum("?" in m for m in msgs) / len(msgs)
        a, b = (question_ratio(n) for n in names)
        if abs(a - b) < 0.2:  # fark belirgin değilse tahmin etme
            return None
        coach = names[0] if a > b else names[1]
    return [{**s, "speaker": "koc" if s["name"] == coach else "danisan"} for s in segments]


def label_speakers(segments: list[dict]) -> list[dict]:
    """Konuşmacı ayrımını içerikten yapar (koç soru sorar, danışan anlatır).

    Ses tabanlı diarization (pyannote vb.) ileride eklenebilir; MVP için içerik
    tabanlı etiketleme ek model kurmadan yeterli doğruluk verir.
    """
    prompt = (
        "Aşağıda bir koçluk seansının numaralı transkript segmentleri var. Her segmenti "
        "konuşan kişiyi belirle: 'koc' veya 'danisan'. Koç genelde soru sorar, yansıtır ve "
        "süreci yönetir; danışan kendi durumunu anlatır. Bir segment ikiye bölünmüş bir "
        "cümlenin devamıysa önceki konuşmacıyla aynı olabilir. <İsim> verilmişse aynı isim "
        "her zaman aynı kişidir; isimlerden hangisinin koç olduğunu içerikten çıkar.\n"
        f"Toplam {len(segments)} segment var; labels listesi tam {len(segments)} elemanlı olmalı.\n"
        f"{_numbered(segments)}"
    )
    result = llm.structured(SYSTEM, prompt, SpeakerLabels, effort="low")
    labels = list(result.labels)
    if len(labels) < len(segments):  # model eksik dönerse son etiketle tamamla
        labels += [labels[-1] if labels else "danisan"] * (len(segments) - len(labels))
    return [{**s, "speaker": label} for s, label in zip(segments, labels)]


def compute_metrics(segments: list[dict], audio: bool = True) -> dict:
    """LLM'siz, ölçülebilir seans metrikleri (koç geri bildirimi için nesnel veri).

    audio=False (yazılı seans): süreler kelime sayısından tahmin edildiği için konuşma payı
    "yazı payı" anlamına gelir; ses ve zamanlama metrikleri hesaplanmaz.
    """
    talk = {"koc": 0.0, "danisan": 0.0}
    questions = {"acik": 0, "kapali": 0, "diger": 0}
    longest_coach = 0.0
    run_speaker, run_len = None, 0.0

    for s in segments:
        duration = max(0.0, s["end"] - s["start"])
        talk[s["speaker"]] += duration
        if s["speaker"] == run_speaker:
            run_len += duration
        else:
            run_speaker, run_len = s["speaker"], duration
        if run_speaker == "koc":
            longest_coach = max(longest_coach, run_len)

        if s["speaker"] == "koc":
            for sentence in re.findall(r"[^.!?]*\?", s["text"]):
                if OPEN_QUESTION_WORDS.search(sentence):
                    questions["acik"] += 1
                elif CLOSED_QUESTION_PARTICLE.search(sentence):
                    questions["kapali"] += 1
                else:
                    questions["diger"] += 1

    # --- Ses / zamanlama analizi (Whisper zaman damgalarından) ---
    words = {"koc": 0, "danisan": 0}
    for s in segments:
        words[s["speaker"]] += len(s["text"].split())
    wait_times, long_silences = [], 0
    for cur, nxt in zip(segments, segments[1:]):
        gap = max(0.0, nxt["start"] - cur["end"])
        if gap >= 3:
            long_silences += 1
        # Koç soru sorduktan sonra danışana ne kadar düşünme alanı tanıdı (ICF: Varlığını Sürdürür)
        if cur["speaker"] == "koc" and cur["text"].rstrip().endswith("?") and nxt["speaker"] == "danisan":
            wait_times.append(gap)

    def wpm(who: str) -> int | None:
        return round(words[who] / (talk[who] / 60)) if talk[who] else None

    total = talk["koc"] + talk["danisan"] or 1.0
    total_q = sum(questions.values())
    return {
        "kaynak_turu": "ses" if audio else "metin",
        "koc_konusma_hizi": wpm("koc") if audio else None,
        "danisan_konusma_hizi": wpm("danisan") if audio else None,
        "ort_bekleme_sn": (round(sum(wait_times) / len(wait_times), 1) if wait_times else None) if audio else None,
        "uzun_sessizlik": long_silences if audio else None,
        "mesaj_sayisi": {"koc": sum(s["speaker"] == "koc" for s in segments),
                         "danisan": sum(s["speaker"] == "danisan" for s in segments)},
        "sure_dk": round((segments[-1]["end"] - segments[0]["start"]) / 60, 1) if audio else None,
        "koc_konusma_orani": round(talk["koc"] / total * 100),
        "danisan_konusma_orani": round(talk["danisan"] / total * 100),
        "koc_soru_sayisi": total_q,
        "acik_uclu_soru": questions["acik"],
        "kapali_soru": questions["kapali"],
        "acik_uclu_oran": round(questions["acik"] / total_q * 100) if total_q else None,
        "en_uzun_koc_konusmasi_sn": round(longest_coach) if audio else None,
        "segment_sayisi": len(segments),
    }


def _history_text(history: list[dict]) -> str:
    if not history:
        return "Bu danışanla daha önce analiz edilmiş seans yok."
    parts = []
    for h in history:
        r = h["report"]
        parts.append(
            f"ÖNCEKİ SEANS — {h['title']} ({h['created_at'][:10]})\n"
            f"Özet: {r['ozet']}\n"
            f"Hedefler: {'; '.join(r['danisan_hedefleri'])}\n"
            f"Üstlenilen görevler: {'; '.join(r['danisan_gorevleri'])}\n"
            f"Gelişim alanları: {'; '.join(g['baslik'] for g in r['gelisim_alanlari'])}"
        )
    return "\n\n".join(parts)


def make_report(client: dict, segments: list[dict], metrics: dict, history: list[dict],
                visual_summary: str = "", notes: str | None = None) -> SessionReport:
    visual_part = f"=== GÖRSEL GÖZLEMLER ===\n{visual_summary}\n\n" if visual_summary else ""
    if notes is not None:  # fotoğraflı seans: transkript yerine koçun notu
        visual_part += (f"=== KOÇUN SEANS NOTU ===\n{notes.strip() or '(not yok)'}\n\n"
                        "(Bu seans fotoğraf ve koç notuyla girildi; konuşma kaydı yok. Kanıtları fotoğraf "
                        "ve nottan al, olmayan konuşmayı uydurma.)\n\n")
    plans = [k for k in db.list_commitments(client["id"])][:5]
    if plans:
        visual_part += ("=== ÖNCEKİ EĞER–O ZAMAN PLANLARI (seansta bahsedildi mi, kanıtla değerlendir) ===\n"
                        + "\n".join(f"PLAN: Eğer {k['durum']}, o zaman {k['davranis']} | danışanın öz-bildirimi: "
                                    f"{k['status']} {k['reflection']}" for k in plans) + "\n\n")
    transcript_part = (f"=== BU SEANSIN TRANSKRİPTİ ==={_numbered(segments, with_speaker=True)}\n\n"
                       if segments else "")
    prompt = (
        f"{client_profile(client)}\n\n"
        f"=== DANIŞAN HAFIZASI ===\n{_history_text(history)}\n\n"
        f"=== SEANS METRİKLERİ ===\n{json.dumps(metrics, ensure_ascii=False)}\n\n"
        f"{visual_part}"
        f"{transcript_part}"
        "Bu seans için koça yönelik bir seans sonrası rapor hazırla. Gelişim alanlarını, "
        "danışana sonradan kişiye özel eğitim içeriği üretilebilecek şekilde somut yaz. "
        "Önceki seanslar varsa ilerlemeyi ve tekrar eden örüntüleri mutlaka belirt."
        " Duygu dili bölümüne yalnızca danışanın kelimelerle açıkça söylediği duyguları yaz; yüz, ses tonu "
        "veya tahminle duygu çıkarma."
    )
    return llm.structured(SYSTEM, prompt, SessionReport, effort="medium")


def evaluate_icf(segments: list[dict], metrics: dict) -> ICFEvaluation:
    prompt = (
        f"=== ICF YETKİNLİK RUBRİĞİ ===\n{rubric_text()}\n\n"
        f"=== SEANS METRİKLERİ ===\n{json.dumps(metrics, ensure_ascii=False)}\n"
        "(konusma_hizi = dakikadaki kelime; ort_bekleme_sn = koçun sorusundan sonra danışanın "
        "cevaba başlamasına kadar geçen süre, düşünme alanının göstergesi; uzun_sessizlik = 3 sn "
        "üzeri sessizlik sayısı)\n\n"
        f"=== TRANSKRİPT ==={_numbered(segments, with_speaker=True)}\n\n"
        "KOÇUN performansını 8 yetkinliğin her biri için 1-5 arası puanla. Her puan için "
        "koçun konuşmasından kanıt alıntıla. Kanıt yoksa bunu belirt ve düşük puan ver. "
        "Puanları şişirme; amaç koçun gelişimi."
    )
    return llm.structured(SYSTEM, prompt, ICFEvaluation, effort="high")


def make_brief(client_id: int) -> PreSessionBrief:
    """Seans öncesi hazırlık: danışanın tüm geçmişinden koç için brif."""
    client = db.get_client(client_id)
    history = db.previous_reports(client_id, before_session_id=10**12, limit=MEMORY_SESSION_COUNT)
    if not history:
        raise ValueError("Bu danışanın analizi tamamlanmış seansı yok; önce bir seans yükleyin.")
    prompt = (
        f"{client_profile(client)}\n\n"
        f"=== DANIŞAN HAFIZASI ===\n{_history_text(history)}\n\n"
        "Koç bu danışanla bir sonraki seansa girecek. Ona kısa ve kullanışlı bir seans "
        "öncesi hazırlık brifi hazırla."
    )
    return llm.structured(SYSTEM, prompt, PreSessionBrief, effort="medium")


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"
