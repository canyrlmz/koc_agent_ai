"""Davranış Takip ve Proaktif Eylem Ajanı (4 ajandan 3.'sü, bkz. agents.py).

Kullanıcı bir şey sormadan danışanın durumunu izler ve harekete geçer.

Mimari (algıla -> karar ver -> uygula):
  1. ALGILA  (kural tabanlı, ucuz): Her danışan için tetikleri bulur.
             Örnek: seans bitti, görevin süresi doluyor, bir haftadır check-in yok, ruh hali düştü.
  2. KARAR   (LLM): Ajan danışanın tüm bağlamına bakar ve her tetik için eylemi yapıp
             yapmayacağına karar verir. Yapacaksa kişiye özel mesajı yazar.
  3. UYGULA  (korumalı): Eylemi kaydeder. Aynı tetik iki kez çalışmaz. Eğitim üretimi
             gibi "eylem yetkili" adımları başlatır.

Ajan iki yolla çalışır:
  - Olay geldiğinde: seans analizi bittiğinde veya danışan check-in yaptığında
  - Zamanlayıcıyla: AGENT_INTERVAL_MIN dakikada bir tüm danışanlar için

Mesajlar uygulama içi gelen kutusuna düşer; danışan izin verdiyse e-posta / WhatsApp ile de
gider (notify.py). Danışanın "Eğer–o zaman" planlarının günü gelince "oldu mu, ne yaptın?" diye
sorar; cevaplar ve paydaş gözlemleri davranış kanıtı olarak koça raporlanır.
"""
import threading
import traceback
from datetime import date, datetime, timedelta

from . import db, llm, notify
from .config import AGENT_AUTO_TRAINING, TASK_DUE_DAYS
from .context import client_profile
from .schemas import AgentPlan

SYSTEM = (
    "Sen bir koçluk platformunun proaktif yapay zekâ ajanısın. İnsan koçla birlikte çalışır, "
    "danışanın seanslar arasındaki gelişimini desteklersin. ICF etik ilkelerine uyarsın: "
    "danışana akıl vermek yerine farkındalık uyandıran kısa sorular sorarsın; teşhis koymazsın; "
    "baskı kurmazsın. Danışana giden mesajlar kısa (en fazla 3 cümle), samimi ve 'siz' diliyle "
    "Türkçe olur. Koça giden uyarılar net ve eyleme dönük olur. Gereksiz veya çok sık mesaj "
    "rahatsız edicidir: bir tetik o an anlamsızsa uygulamamaya karar ver. Danışan notlarında "
    "kendine zarar verme veya ciddi kriz işareti görürsen koça yönelik uyarıda bunu açıkça "
    "belirt ve profesyonel destek önermesini söyle."
)

TRIGGER_INFO = {
    "takip": ("danisan", "Seans sonrası takip: seansın kısa hatırlatması, üstlenilen görevler ve bir yansıtma sorusu"),
    "hatirlatma": ("danisan", "Görev hatırlatma: süresi yaklaşan veya geçen görev"),
    "checkin": ("danisan", "Haftalık check-in daveti: bir haftadır haber alınamadı"),
    "uyari": ("koc", "Koça uyarı: danışanın ruh hali düştü veya düşük"),
    "egitim": ("koc", "Otomatik eğitim: seanstaki gelişim alanı için kişiye özel eğitim içeriği hazırlanacak"),
    "plan": ("danisan", "Eğer–o zaman planı takibi: planın kontrol günü geldi. Planı hatırlat, durumun yaşanıp "
                        "yaşanmadığını ve ne yaptığını yargılamadan sor; cevabını Farkora'daki 'Planlarım' bölümüne "
                        "yazmaya davet et. Yapamadıysa bunun da öğretici olduğunu hissettir."),
    "haftalik": ("danisan", "Koçsuz mod haftalık değerlendirme: hafta bitti, gelecek haftanın görevleri ayarlanacak"),
}

SELF_GUIDED_NOTE = (
    "ÖNEMLİ: Bu kullanıcı KOÇSUZ MODDA (kendi kendine koçluk); insan koçu yok. 'uyari' tetiğinde mesajı doğrudan "
    "kullanıcıya yaz: sıcak, destekleyici ve sade ol; ruh hali çok düşükse güvendiği biriyle konuşmasını ve bir ruh "
    "sağlığı uzmanına başvurmayı nazikçe öner, tehlikedeyse 112'yi hatırlat. Kullanıcıya 'sen' diye hitap et."
)

_lock = threading.Lock()  # zamanlayıcı ve olaylar aynı anda çalışırsa sırayla işlensin


# --- 1. ALGILA ---------------------------------------------------------------


def detect_triggers(client_id: int, today: date | None = None) -> list[dict]:
    today = today or date.today()
    handled = db.handled_trigger_keys(client_id)
    sessions = db.completed_sessions(client_id)
    tasks = db.list_tasks(client_id)
    checkins = db.list_checkins(client_id)
    triggers: list[dict] = []

    def add(key: str, kind: str, detail: str, **extra):
        if key not in handled:
            triggers.append({"key": key, "kind": kind, "detail": detail, **extra})

    for s in sessions:
        add(f"takip:s{s['id']}", "takip", f"'{s['title']}' seansı analiz edildi.", session_id=s["id"])
        areas = (s["report"] or {}).get("gelisim_alanlari", [])
        if AGENT_AUTO_TRAINING and areas and not db.trainings_for_session(s["id"]):
            add(f"egitim:s{s['id']}", "egitim", f"Gelişim alanı: {areas[0]['baslik']}",
                session_id=s["id"], area=areas[0])

    for t in tasks:
        if t["status"] != "acik":
            continue
        due = date.fromisoformat(t["due_date"])
        if due < today:
            add(f"gecikme:t{t['id']}", "hatirlatma",
                f"Görevin süresi {(today - due).days} gün önce doldu: {t['text']}", task_id=t["id"])
        elif due <= today + timedelta(days=1):
            add(f"hatirlatma:t{t['id']}", "hatirlatma", f"Görevin son günü {t['due_date']}: {t['text']}",
                task_id=t["id"])

    self_profile = db.get_self_profile(client_id)
    if self_profile and self_profile["phase"] == "kriz":
        return []  # kriz anında hatırlatma / görev mesajı gönderilmez
    plan_start = None
    if self_profile and self_profile["plan"] and self_profile["phase"] == "aktif":
        plan_start = date.fromisoformat(self_profile["plan"]["baslangic"])
        from .selfcoach import due_weeks

        for n in due_weeks(client_id, today):
            add(f"haftalik:w{n}", "haftalik", f"{n}. hafta bitti.", week=n)

    if sessions or plan_start:
        last_session_day = datetime.fromisoformat(sessions[-1]["created_at"]).date() if sessions else None
        last_checkin_day = datetime.fromisoformat(checkins[-1]["created_at"]).date() if checkins else None
        quiet_since = max(d for d in (last_session_day, last_checkin_day, plan_start) if d)
        silent_days = (today - quiet_since).days
        if silent_days >= 7:  # sessizliğin her tam haftası için en fazla bir davet
            add(f"checkin:{quiet_since}:h{silent_days // 7}", "checkin", f"{silent_days} gündür haber yok.")

    for k in db.list_commitments(client_id):
        if k["status"] == "aktif" and k["check_date"] <= today.isoformat():
            add(f"plan:k{k['id']}", "plan", f"Plan: Eğer {k['durum']}, o zaman {k['davranis']}. "
                f"Kontrol günü {k['check_date']}.", commitment_id=k["id"])

    if checkins:
        last = checkins[-1]
        prev = checkins[-2] if len(checkins) > 1 else None
        if last["mood"] <= 2 or (prev and prev["mood"] - last["mood"] >= 2):
            trend = f" (önceki: {prev['mood']}/5)" if prev else ""
            add(f"uyari:c{last['id']}", "uyari",
                f"Son check-in ruh hali {last['mood']}/5{trend}. Not: {last['note'] or '-'}")

    return triggers


# --- 2. KARAR ----------------------------------------------------------------


def _context(client: dict) -> str:
    sessions = db.completed_sessions(client["id"])[-3:]
    tasks = db.list_tasks(client["id"])
    checkins = db.list_checkins(client["id"])[-5:]
    recent = db.list_agent_actions(client["id"])[:5]
    parts = [client_profile(client)]
    for s in sessions:
        r = s["report"] or {}
        parts.append(f"SEANS '{s['title']}' ({s['created_at'][:10]}): {r.get('ozet', '')}")
    parts.append("GÖREVLER: " + ("; ".join(f"[{t['status']}, son gün {t['due_date']}] {t['text']}"
                                          for t in tasks) or "yok"))
    parts.append("CHECK-IN'LER: " + ("; ".join(f"{c['created_at'][:10]} ruh hali {c['mood']}/5: {c['note']}"
                                              for c in checkins) or "yok"))
    plans = db.list_commitments(client["id"])[:5]
    parts.append("EĞER–O ZAMAN PLANLARI: " + ("; ".join(
        f"[{k['status']}] Eğer {k['durum']}, o zaman {k['davranis']}" + (f" (yansıtma: {k['reflection']})" if k["reflection"] else "")
        for k in plans) or "yok"))
    parts.append("SON AJAN MESAJLARI: " + ("; ".join(f"{a['created_at'][:10]} {a['kind']}: {a['message']}"
                                                  for a in recent if a["applied"]) or "yok"))
    return "\n".join(parts)


def decide(client: dict, triggers: list[dict]) -> AgentPlan:
    trigger_lines = "\n".join(
        f"- tetik_kodu={t['key']} | tür={t['kind']} | hedef={TRIGGER_INFO[t['kind']][0]} | "
        f"anlamı: {TRIGGER_INFO[t['kind']][1]} | ayrıntı: {t['detail']}"
        for t in triggers
    )
    note = f"{SELF_GUIDED_NOTE}\n\n" if client.get("self_guided") else ""
    prompt = (
        f"{note}=== DANIŞAN DURUMU ===\n{_context(client)}\n\n"
        f"=== ŞU AN AKTİF TETİKLER ===\n{trigger_lines}\n\n"
        "Her tetik için karar ver. Aynı gün danışana birden fazla mesaj gidecekse bunları "
        "tek bir doğal mesajda birleştirmeyi düşün: birini uygula, diğerlerini 'birleştirildi' "
        "gerekçesiyle atla. 'egitim' tetiği için mesaj, koça ajanın neden bu eğitimi "
        "hazırladığını anlatan tek cümle olsun."
    )
    return llm.structured(SYSTEM, prompt, AgentPlan, effort="medium")


# --- 3. UYGULA ---------------------------------------------------------------


def deliver(client: dict, target: str, message: str, action_id: int | None = None) -> list[dict]:
    """Uygulama içi gelen kutusu + danışanın izin verdiği kanallar (e-posta / WhatsApp)."""
    return notify.deliver(client, target, message, action_id)


def run_for_client(client_id: int, today: date | None = None) -> list[dict]:
    trainings_to_generate = []
    with _lock:
        client = db.get_client(client_id)
        triggers = detect_triggers(client_id, today)
        done = _run_weekly(client, [t for t in triggers if t["kind"] == "haftalik"])
        triggers = [t for t in triggers if t["kind"] != "haftalik"]
        if not triggers:
            return done
        plan = decide(client, triggers)
        decisions = {d.tetik_kodu: d for d in plan.kararlar}
        for t in triggers:
            d = decisions.get(t["key"])
            if d is None:  # model bu tetiğe karar vermediyse kaydetme; sonraki turda yeniden denenir
                continue
            target = TRIGGER_INFO[t["kind"]][0]
            if client.get("self_guided") and target == "koc" and t["kind"] == "uyari":
                target = "danisan"  # koçsuz modda koç yok: destek mesajı kullanıcının kendisine gider
            message = d.mesaj if d.uygula else ""
            if not db.add_agent_action(client_id, t["key"], t["kind"], target, d.uygula, message, d.gerekce):
                continue  # başka bir çalışma bu tetiği az önce işledi
            if d.uygula:
                if t["kind"] == "egitim":
                    training = db.create_training(client_id, t["session_id"], t["area"])
                    trainings_to_generate.append(training["id"])
                else:
                    deliver(client, target, message, db.agent_action_id(client_id, t["key"]))
            done.append({"trigger": t["key"], "applied": d.uygula})

    # Uzun süren eğitim üretimi kilidin dışında yapılır
    from .training import generate_training

    for training_id in trainings_to_generate:
        generate_training(training_id)
    return done


def _run_weekly(client: dict, triggers: list[dict]) -> list[dict]:
    """Koçsuz mod: biten haftayı değerlendir, gelecek haftayı ayarla, kullanıcıya kısa mesaj gönder."""
    from .selfcoach import weekly_review

    done = []
    for t in triggers:
        message = weekly_review(client["id"], t["week"])
        if db.add_agent_action(client["id"], t["key"], "haftalik", "danisan", True, message,
                               f"{t['week']}. hafta bitti; gelecek hafta kullanıcının durumuna göre ayarlandı."):
            deliver(client, "danisan", message, db.agent_action_id(client["id"], t["key"]))
            done.append({"trigger": t["key"], "applied": True})
    return done


def run_safely(client_id: int) -> None:
    """Arka plan görevleri için: hata ajanın diğer işlerini durdurmasın."""
    try:
        run_for_client(client_id)
    except Exception:  # noqa: BLE001
        traceback.print_exc()


def run_all() -> None:
    for client_id in db.client_ids():
        run_safely(client_id)


# --- Görev oluşturma ve zamanlayıcı ---------------------------------------------


def create_tasks_from_report(session: dict, report: dict) -> None:
    start = datetime.fromisoformat(session["created_at"]).date()
    due = (start + timedelta(days=TASK_DUE_DAYS)).isoformat()
    for text in report.get("danisan_gorevleri", []):
        db.create_task(session["client_id"], session["id"], text, due)


def start_scheduler(interval_min: int) -> threading.Event:
    stop = threading.Event()

    def loop():
        while not stop.wait(interval_min * 60):
            run_all()

    threading.Thread(target=loop, name="agent-scheduler", daemon=True).start()
    return stop


# --- Davranış paneli (Behavioral AI metrikleri) --------------------------------


def behavior_metrics(client_id: int, today: date | None = None) -> dict:
    today = today or date.today()
    tasks = db.list_tasks(client_id)
    checkins = db.list_checkins(client_id)
    done = sum(t["status"] == "yapildi" for t in tasks)
    failed = sum(t["status"] == "yapilmadi" for t in tasks)
    overdue = sum(t["status"] == "acik" and date.fromisoformat(t["due_date"]) < today for t in tasks)
    closed = done + failed + overdue
    return {
        "gorev_toplam": len(tasks),
        "gorev_tamamlanan": done,
        "gorev_tamamlama_orani": round(done / closed * 100) if closed else None,
        "geciken_gorev": overdue,
        "checkin_sayisi": len(checkins),
        "ruh_hali_serisi": [{"tarih": c["created_at"][:10], "puan": c["mood"]} for c in checkins[-10:]],
        "ruh_hali_ortalama": round(sum(c["mood"] for c in checkins) / len(checkins), 1) if checkins else None,
        **behavior_evidence(client_id),
    }


# Paydaş gözlem ölçeği (0-3) ve öz-bildirim durumları
OBS_SCALE = {0: "Hiç görmedim", 1: "Bir kez", 2: "Birkaç kez", 3: "Düzenli olarak"}
PLAN_STATUS = {"aktif": "Bekliyor", "yapildi": "Yaptım", "kismen": "Kısmen", "firsat_olmadi": "Fırsat olmadı",
               "yapilamadi": "Yapamadım"}


def behavior_evidence(client_id: int) -> dict:
    """Dış dünyadaki davranışın üç kaynaktan kanıtı: öz-bildirim, paydaş gözlemi, sonraki seans."""
    plans = db.list_commitments(client_id)
    answered = [k for k in plans if k["status"] != "aktif"]
    obs = [o for o in db.list_observations(client_id) if o["status"] == "yanitlandi"]
    return {
        "plan_sayisi": len(plans),
        "plan_yanitlanan": len(answered),
        "plan_uygulanan": sum(k["status"] in ("yapildi", "kismen") for k in answered),
        "gozlem_sayisi": len(obs),
        "gozlem_ortalama": round(sum(o["rating"] for o in obs) / len(obs), 1) if obs else None,
    }
