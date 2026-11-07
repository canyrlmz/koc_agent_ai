"""Genel panel ve Kurumsal İçgörü ve Anonimleştirme Ajanı (4 ajandan 4.'sü, bkz. agents.py).

Anonimleştirme kuralları:
  - Kurum yöneticisi kişi adı, transkript ve kişi bazlı puan görmez.
  - En az MIN_GROUP (3) kişiden oluşmayan gruplar (birim, tema kümesi) gösterilmez (k-anonimlik).
  - Yapay zekâya kişi adı gönderilmez; çıktıda isim geçerse "bir katılımcı" ile değiştirilir.

Behavioral AI'ın kurumsal ayağı (hocanın notu: "bireysel ve kurumsal verimlilik"): Bir kurumun
veya sosyal birimin tüm danışanlarından anonim, toplu içgörü çıkarılır. Birim yöneticisi kişisel
seans içeriğini görmez; ortak temaları, riskleri ve program önerilerini görür.
"""
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import db, llm
from .agent import behavior_metrics
from .context import ORG_TYPES
from .schemas import OrgInsight


MIN_GROUP = 3  # k-anonimlik eşiği

_STOP = {"ve", "ile", "bir", "için", "da", "de", "ya", "çok", "daha", "en", "kendi"}


def _tokens(text: str) -> set[str]:
    """Basit Türkçe kök: küçük harf, ilk 5 harf (geri bildirim / geri bildirimler aynı kümeye düşsün)."""
    words = re.findall(r"\w+", text.replace("I", "ı").replace("İ", "i").lower())
    return {w[:5] for w in words if w not in _STOP and len(w) > 2}


def cluster_themes(items: list[tuple[int, str]], threshold: float = 0.34) -> list[dict]:
    """Tema kümeleme (tek bağlantılı, Jaccard benzerliği). items = [(danışan_id, tema), ...]
    Benzer temaları tek küme yapar; her kümenin kaç FARKLI kişide görüldüğünü sayar."""
    clusters: list[dict] = []
    for cid, theme in items:
        tok = _tokens(theme)
        if not tok:
            continue
        best, best_sim = None, 0.0
        for c in clusters:
            sim = max(len(tok & t) / len(tok | t) for t in c["_tok"])
            if sim > best_sim:
                best, best_sim = c, sim
        if best and best_sim >= threshold:
            best["_tok"].append(tok)
            best["temalar"][theme] += 1
            best["kisiler"].add(cid)
        else:
            clusters.append({"_tok": [tok], "temalar": Counter({theme: 1}), "kisiler": {cid}})
    out = [{"etiket": c["temalar"].most_common(1)[0][0], "temalar": [t for t, _ in c["temalar"].most_common(5)],
            "kisi_sayisi": len(c["kisiler"]), "gorulme": sum(c["temalar"].values())} for c in clusters]
    return sorted(out, key=lambda c: (-c["kisi_sayisi"], -c["gorulme"]))


def _icf_avg(sessions: list[dict]) -> float | None:
    vals = [s["icf"]["ortalama"] for s in sessions if s.get("icf") and s["icf"].get("ortalama")]
    return round(sum(vals) / len(vals), 2) if vals else None


def dashboard(coach_id: int | None = None) -> dict:
    today = date.today()
    # coach_id verilirse yalnızca o koçun danışanları (admin için None = herkes)
    f, p = ("AND c.coach_id = ?", (coach_id,)) if coach_id is not None else ("", ())
    sessions = db.all_rows(
        f"""SELECT s.id, s.client_id, s.title, s.status, s.created_at, s.icf_json, c.name AS client_name
            FROM sessions s JOIN clients c ON c.id = s.client_id WHERE 1=1 {f} ORDER BY s.id DESC""", p
    )
    month_start = today.replace(day=1).isoformat()
    tasks = db.all_rows(
        f"""SELECT t.*, c.name AS client_name FROM tasks t JOIN clients c ON c.id = t.client_id
            WHERE t.status = 'acik' {f} ORDER BY t.due_date LIMIT 8""", p
    )
    alerts = db.all_rows(
        f"""SELECT a.*, c.name AS client_name FROM agent_actions a JOIN clients c ON c.id = a.client_id
            WHERE a.kind = 'uyari' AND a.applied = 1 {f} ORDER BY a.id DESC LIMIT 5""", p
    )
    actions_week = db.all_rows(
        f"""SELECT COUNT(*) AS n FROM agent_actions a JOIN clients c ON c.id = a.client_id
            WHERE a.applied = 1 AND a.created_at >= ? {f}""",
        ((today - timedelta(days=7)).isoformat(), *p),
    )[0]["n"]
    all_tasks = db.all_rows(f"SELECT t.status, t.due_date FROM tasks t JOIN clients c ON c.id = t.client_id WHERE 1=1 {f}", p)
    client_count = len(db.list_clients(coach_id=coach_id))
    done = sum(t["status"] == "yapildi" for t in all_tasks)
    closed = sum(t["status"] != "acik" or t["due_date"] < today.isoformat() for t in all_tasks)
    completed = [s for s in sessions if s["status"] == "tamamlandi"]
    trend = [{"tarih": s["created_at"][:10], "puan": s["icf"]["ortalama"]}
             for s in reversed(completed) if s.get("icf")][-12:]
    return {
        "aktif_danisan": client_count,
        "bu_ay_seans": sum(s["created_at"] >= month_start for s in sessions),
        "icf_ortalama": _icf_avg(completed),
        "gorev_tamamlama": round(done / closed * 100) if closed else None,
        "ajan_eylemi_7g": actions_week,
        "icf_trendi": trend,
        "son_seanslar": [{k: s[k] for k in ("id", "client_id", "client_name", "title", "status", "created_at")}
                         | {"icf": (s.get("icf") or {}).get("ortalama")} for s in sessions[:6]],
        "yaklasan_gorevler": tasks,
        "uyarilar": alerts,
    }


def organization_overview(org_id: int, coach_id: int | None = None) -> dict:
    org = db.get_organization(org_id)
    clients = db.list_clients(org_id, coach_id=coach_id)
    sessions, themes, areas = [], Counter(), Counter()
    task_rates, moods = [], []
    theme_items: list[tuple[int, str]] = []
    units: dict[str, dict] = defaultdict(lambda: {"kisi": 0, "moods": [], "rates": []})
    for c in clients:
        cs = db.completed_sessions(c["id"])
        for s in cs:
            s["icf"] = db.get_session(s["id"])["icf"]
            r = s["report"] or {}
            themes.update(r.get("ana_temalar", []))
            areas.update(g["baslik"] for g in r.get("gelisim_alanlari", []))
            theme_items += [(c["id"], t) for t in r.get("ana_temalar", [])]
            theme_items += [(c["id"], g["baslik"]) for g in r.get("gelisim_alanlari", [])]
        sessions += cs
        b = behavior_metrics(c["id"])
        u = units[c["unit"] or "Belirtilmedi"]
        u["kisi"] += 1
        if b["gorev_tamamlama_orani"] is not None:
            task_rates.append(b["gorev_tamamlama_orani"])
            u["rates"].append(b["gorev_tamamlama_orani"])
        if b["ruh_hali_ortalama"] is not None:
            moods.append(b["ruh_hali_ortalama"])
            u["moods"].append(b["ruh_hali_ortalama"])
    org_mood = sum(moods) / len(moods) if moods else None
    org_rate = sum(task_rates) / len(task_rates) if task_rates else None
    signals = []
    for name, u in units.items():
        if u["kisi"] < MIN_GROUP:
            continue
        if org_mood and u["moods"]:
            m = sum(u["moods"]) / len(u["moods"])
            if m <= org_mood - 0.5:
                signals.append(f"{name}: ruh hali ortalaması {m:.1f}/5, kurum ortalamasının "
                               f"{org_mood - m:.1f} puan altında ({u['kisi']} kişi)")
        if org_rate is not None and u["rates"]:
            r = sum(u["rates"]) / len(u["rates"])
            if r <= org_rate - 15:
                signals.append(f"{name}: görev tamamlama %{r:.0f}, kurum ortalamasının "
                               f"{org_rate - r:.0f} puan altında ({u['kisi']} kişi)")
    return {
        **org,
        "org_type_label": ORG_TYPES.get(org["org_type"], org["org_type"]),
        "clients": clients,
        "seans_sayisi": len(sessions),
        "icf_ortalama": _icf_avg(sessions),
        "gorev_tamamlama": round(sum(task_rates) / len(task_rates)) if task_rates else None,
        "ruh_hali_ortalama": round(sum(moods) / len(moods), 1) if moods else None,
        "temalar": themes.most_common(8),
        "gelisim_alanlari": areas.most_common(8),
        "birimler": Counter(c["unit"] or "Belirtilmedi" for c in clients).most_common(),
        "tema_kumeleri": cluster_themes(theme_items)[:8],
        "risk_sinyalleri": signals,
        "min_grup": MIN_GROUP,
    }


def anonymize(ov: dict) -> dict:
    """Kurum yöneticisi görünümü: kişi adları ve kişi bazlı puanlar çıkarılır."""
    clients = ov.pop("clients")
    small = len(clients) < MIN_GROUP
    units = ov["birimler"]
    hidden = sum(n for _, n in units if n < MIN_GROUP)
    ov["birimler"] = [(u, n) for u, n in units if n >= MIN_GROUP] + ([("Diğer (küçük gruplar)", hidden)] if hidden else [])
    ov["tema_kumeleri"] = [k for k in ov["tema_kumeleri"] if k["kisi_sayisi"] >= MIN_GROUP]
    if small:  # çok az kişi varsa tema ve gelişim alanı listeleri de kişiyi ele verebilir
        ov["temalar"], ov["gelisim_alanlari"] = [], []
    return {
        **ov,
        "kucuk_grup": small,
        "danisan_sayisi": len(clients),
        "danisan_tipleri": Counter(c["client_type"] for c in clients).most_common(),
        "odak_alanlari": Counter(c["focus_area"] or "Belirtilmedi" for c in clients).most_common(),
    }


def client_progress(client_id: int) -> dict:
    """Danışanın kendi gelişim portalı. Koçun ICF değerlendirmesi ve transkript yer almaz."""
    c = db.get_client(client_id)
    sessions = db.completed_sessions(client_id)
    trainings = [t for t in db.list_trainings(client_id) if t["status"] == "tamamlandi"]
    tasks = db.list_tasks(client_id)
    return {
        "profile": {k: c.get(k) for k in ("id", "name", "focus_area", "goals", "client_type", "role_title",
                                          "unit", "organization_name", "coach_name")},
        "behavior": behavior_metrics(client_id),
        "sessions": [{
            "id": s["id"], "title": s["title"], "created_at": s["created_at"],
            "ozet": (s["report"] or {}).get("ozet", ""),
            "temalar": (s["report"] or {}).get("ana_temalar", []),
            "gorevler": (s["report"] or {}).get("danisan_gorevleri", []),
            "calisilan_konular": [g["baslik"] for g in (s["report"] or {}).get("gelisim_alanlari", [])],
        } for s in reversed(sessions)],
        "tasks": tasks,
        "checkins": db.list_checkins(client_id)[-10:],
        "messages": [a for a in db.list_agent_actions(client_id) if a["applied"] and a["target"] == "danisan"],
        "trainings": [{"id": t["id"], "title": t["title"], "area": t["area"]["baslik"], "created_at": t["created_at"]}
                      for t in trainings],
        "commitments": db.list_commitments(client_id),
        # Danışan kendi gözlemci isteklerinin durumunu görür (gözlemcinin puanı değil)
        "observations": [{k: o[k] for k in ("id", "commitment_id", "observer_name", "relation", "status", "created_at")}
                         for o in db.list_observations(client_id)],
    }


def organization_insight(org_id: int, coach_id: int | None = None) -> OrgInsight:
    ov = organization_overview(org_id, coach_id=coach_id)
    if not ov["seans_sayisi"]:
        raise ValueError("Bu kurumda analiz edilmiş seans yok; önce danışanlarla seans yapılmalı.")
    # Kişisel veriyi korumak için modele isim değil, yalnızca anonim toplu veri gönderilir
    summary = {
        "kurum": ov["name"], "tur": ov["org_type_label"], "sektor": ov["sector"],
        "danisan_sayisi": len(ov["clients"]), "seans_sayisi": ov["seans_sayisi"],
        "icf_ortalama": ov["icf_ortalama"], "gorev_tamamlama_orani": ov["gorev_tamamlama"],
        "ruh_hali_ortalama": ov["ruh_hali_ortalama"], "birimler": ov["birimler"],
        "sik_temalar": ov["temalar"], "sik_gelisim_alanlari": ov["gelisim_alanlari"],
        "tema_kumeleri": [{k: c[k] for k in ("etiket", "temalar", "kisi_sayisi")} for c in ov["tema_kumeleri"]],
        "birim_risk_sinyalleri": ov["risk_sinyalleri"],
        "danisan_tipleri": Counter(c["client_type"] for c in ov["clients"]).most_common(),
    }
    prompt = (
        f"=== KURUMSAL HAFIZA ===\n{(ov['knowledge'] or '(girilmemiş)')[:3000]}\n\n"
        f"=== ANONİM TOPLU VERİ ===\n{json.dumps(summary, ensure_ascii=False)}\n\n"
        "Bu kurum/birim yöneticisi için davranış değişimi ve verimlilik odaklı kısa bir içgörü "
        "raporu hazırla. Kişi adı verme. Önerilerin kurumun değerleri ve öncelikleriyle uyumlu olsun."
    )
    system = (
        "Sen kurumsal koçluk programlarını değerlendiren bir davranış bilimi (Behavioral AI) "
        "danışmanısın. Türkçe, net ve eyleme dönük yaz. Veride olmayan şeyi uydurma."
    )
    result = llm.structured(system, prompt, OrgInsight, effort="medium")
    return scrub_names(result, [c["name"] for c in ov["clients"]])


def scrub_names(result: OrgInsight, names: list[str]) -> OrgInsight:
    """Model yine de bir isim yazarsa kurum yöneticisine gitmeden temizlenir."""
    parts = {p for n in names for p in re.sub(r"\(.*?\)", "", n).split() if len(p) > 2}
    if not parts:
        return result
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, sorted(parts, key=len, reverse=True))) + r")\b",
                         re.IGNORECASE)
    data = result.model_dump()

    def clean(v):
        if isinstance(v, str):
            return pattern.sub("bir katılımcı", v)
        if isinstance(v, list):
            return [clean(x) for x in v]
        return v
    return OrgInsight(**{k: clean(v) for k, v in data.items()})
