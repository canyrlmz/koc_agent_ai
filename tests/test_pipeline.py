"""Uçtan uca test: mock modda (API anahtarı ve ses dosyası gerekmez)."""
import io
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["LLM_PROVIDER"] = "mock"
os.environ["TRANSCRIBE_MODE"] = "mock"
os.environ["RESEARCH_MODE"] = "mock"
os.environ["AGENT_INTERVAL_MIN"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app.analysis import compute_metrics  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
# İlk kurulum: yönetici hesabı (test istemcisi bu oturumla devam eder)
assert client.post("/api/auth/setup", json={
    "name": "Test Yönetici", "email": "admin@test.local", "password": "guclu-sifre-123"}).status_code == 200


def _upload(client_id: int, title: str):
    return client.post(
        f"/api/clients/{client_id}/sessions",
        files={"file": ("seans.mp3", io.BytesIO(b"fake-audio"), "audio/mpeg")},
        data={"title": title},
    )


def test_full_pipeline_with_memory():
    c = client.post("/api/clients", json={"name": "Deneme Danışan", "focus_area": "Liderlik", "consent": True}).json()

    first = _upload(c["id"], "1. seans").json()
    s1 = client.get(f"/api/sessions/{first['id']}").json()
    assert s1["status"] == "tamamlandi", s1["error"]
    assert len(s1["icf"]["yetkinlikler"]) == 8
    assert s1["icf"]["ortalama"] > 0
    assert {t["speaker"] for t in s1["transcript"]} == {"koc", "danisan"}
    assert s1["report"]["onceki_seanslarla_baglanti"] == "Bu danışanla yapılan ilk seans."

    # İkinci seansta hafıza devreye girmeli
    second = _upload(c["id"], "2. seans").json()
    s2 = client.get(f"/api/sessions/{second['id']}").json()
    assert s2["status"] == "tamamlandi"
    assert "Önceki seansta" in s2["report"]["onceki_seanslarla_baglanti"]

    brief = client.post(f"/api/clients/{c['id']}/brief")
    assert brief.status_code == 200
    assert brief.json()["onerilen_sorular"]


def test_training_from_development_area():
    c = client.post("/api/clients", json={"name": "Eğitim Danışanı", "focus_area": "Liderlik", "consent": True}).json()
    s = _upload(c["id"], "1. seans").json()

    t = client.post(f"/api/sessions/{s['id']}/trainings", json={"area_index": 0}).json()
    t = client.get(f"/api/trainings/{t['id']}").json()
    assert t["status"] == "tamamlandi", t["error"]
    assert t["query"]
    assert t["papers"]
    assert len(t["content"]["cizgi_roman"]) == 4
    assert t["content"]["quiz"]

    listed = client.get(f"/api/clients/{c['id']}/trainings").json()
    assert listed[0]["title"] == t["content"]["baslik"]

    bad = client.post(f"/api/sessions/{s['id']}/trainings", json={"area_index": 99})
    assert bad.status_code == 400


def test_proactive_agent():
    from datetime import date, timedelta

    from app import agent

    c = client.post("/api/clients", json={"name": "Ajan Danışanı", "focus_area": "Liderlik", "consent": True}).json()
    _upload(c["id"], "1. seans")

    # Seans biter bitmez ajan kendiliğinden: takip mesajı + otomatik eğitim
    ov = client.get(f"/api/clients/{c['id']}/agent").json()
    kinds = {a["kind"] for a in ov["actions"]}
    assert {"takip", "egitim"} <= kinds
    assert ov["tasks"], "seans görevleri takibe alınmalı"
    trainings = client.get(f"/api/clients/{c['id']}/trainings").json()
    assert trainings and trainings[0]["status"] == "tamamlandi"

    # Tekrar çalıştırınca aynı tetikler yeniden işlenmez
    assert client.post(f"/api/clients/{c['id']}/agent/run").json()["done"] == []

    # Görevin son günü -> hatırlatma; süre geçince -> gecikme + haftalık check-in daveti
    due = date.fromisoformat(ov["tasks"][0]["due_date"])  # seanstan 7 gün sonra
    on_due = {d["trigger"].split(":")[0] for d in agent.run_for_client(c["id"], today=due)}
    assert on_due >= {"hatirlatma", "checkin"}
    later = {d["trigger"].split(":")[0] for d in agent.run_for_client(c["id"], today=due + timedelta(days=2))}
    assert later == {"gecikme"}  # check-in daveti aynı hafta tekrar gönderilmez

    # Ruh hali düşünce koça uyarı
    client.post(f"/api/clients/{c['id']}/checkins", json={"mood": 4, "note": "iyi"})
    client.post(f"/api/clients/{c['id']}/checkins", json={"mood": 1, "note": "çok kötü bir hafta"})
    ov = client.get(f"/api/clients/{c['id']}/agent").json()
    assert any(a["kind"] == "uyari" and a["target"] == "koc" for a in ov["actions"])
    assert ov["behavior"]["checkin_sayisi"] == 2

    # Görev tamamlanınca davranış metriği güncellenir
    client.patch(f"/api/tasks/{ov['tasks'][0]['id']}", json={"status": "yapildi"})
    b = client.get(f"/api/clients/{c['id']}/agent").json()["behavior"]
    assert b["gorev_tamamlanan"] == 1

    assert client.post(f"/api/clients/{c['id']}/checkins", json={"mood": 9}).status_code == 400


def test_openalex_abstract_reconstruction():
    from app.research import _abstract

    assert _abstract({"feedback": [1], "Good": [0], "matters": [2]}) == "Good feedback matters"


def test_rejects_unsupported_file():
    c = client.post("/api/clients", json={"name": "X", "consent": True}).json()
    r = client.post(
        f"/api/clients/{c['id']}/sessions",
        files={"file": ("notlar.pdf", io.BytesIO(b"x"), "application/pdf")},
    )
    assert r.status_code == 400


def test_brief_without_sessions():
    c = client.post("/api/clients", json={"name": "Yeni"}).json()
    assert client.post(f"/api/clients/{c['id']}/brief").status_code == 400


def test_consent_required_for_upload():
    c = client.post("/api/clients", json={"name": "Rızasız"}).json()
    assert _upload(c["id"], "x").status_code == 400
    client.put(f"/api/clients/{c['id']}", json={"name": "Rızasız", "consent": True})
    assert client.get(f"/api/clients/{c['id']}").json()["consent_at"]
    assert _upload(c["id"], "x").status_code == 200


def test_organization_profile_and_insight():
    org = client.post("/api/organizations", json={
        "name": "Test Sosyal Birim", "org_type": "sosyal_birim", "knowledge": "Değer: güçlendirme"}).json()
    c = client.post("/api/clients", json={
        "name": "Kurum Danışanı", "client_type": "yonetici", "organization_id": org["id"],
        "unit": "Aile Programı", "role_title": "Veli", "goals": "İletişim", "consent": True}).json()
    assert c["organization_name"] == "Test Sosyal Birim"

    from app.context import client_profile

    profile = client_profile(c)
    assert "Yönetici" in profile and "Sosyal hizmet birimi" in profile and "güçlendirme" in profile

    assert client.post(f"/api/organizations/{org['id']}/insight").status_code == 400  # henüz seans yok
    _upload(c["id"], "1. seans")
    ov = client.get(f"/api/organizations/{org['id']}").json()
    assert ov["seans_sayisi"] == 1 and ov["temalar"]
    insight = client.post(f"/api/organizations/{org['id']}/insight")
    assert insight.status_code == 200 and insight.json()["kurumsal_oneriler"]


def test_image_analysis():
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
           b"\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
    c = client.post("/api/clients", json={"name": "Görsel", "consent": True}).json()
    img = client.post(f"/api/clients/{c['id']}/images", files={"file": ("pano.png", io.BytesIO(png), "image/png")},
                      data={"note": "hedef panom"}).json()
    listed = client.get(f"/api/clients/{c['id']}/images").json()
    assert listed[0]["id"] == img["id"] and listed[0]["status"] == "tamamlandi"
    assert listed[0]["analysis"]["koc_icin_sorular"]
    assert client.get(f"/api/images/{img['id']}/file").status_code == 200
    bad = client.post(f"/api/clients/{c['id']}/images", files={"file": ("x.txt", io.BytesIO(b"x"), "text/plain")})
    assert bad.status_code == 400


def test_demo_seed_and_dashboard():
    assert client.post("/api/demo/seed").status_code == 200
    d = client.get("/api/dashboard").json()
    assert d["aktif_danisan"] >= 3 and d["icf_trendi"] and d["uyarilar"]
    orgs = client.get("/api/organizations").json()
    sos = next(o for o in orgs if o["org_type"] == "sosyal_birim" and o["name"].startswith("Örnek"))
    assert client.get(f"/api/organizations/{sos['id']}").json()["clients"]

    # Örnek hesaplarla şifresiz giriş (sunum kolaylığı)
    assert set(client.get("/api/auth/state").json()["demo_roles"]) == {"koc", "danisan", "kurum"}
    for role, check in [("koc", "/api/clients"), ("danisan", "/api/me/portal"), ("kurum", "/api/me/organization")]:
        t = TestClient(app)
        assert t.post("/api/auth/demo-login", json={"role": role}).status_code == 200
        assert t.get(check).status_code == 200
    assert TestClient(app).post("/api/auth/demo-login", json={"role": "admin"}).status_code == 404


def test_text_session_parsing():
    from app.textsession import parse_text

    segs = parse_text("Koç: Bugün ne konuşalım?\nDanışan: İşimle ilgili\nbir konu var.\nKoç: Anlatır mısınız?")
    assert [s["speaker"] for s in segs] == ["koc", "danisan", "koc"]
    assert segs[1]["text"] == "İşimle ilgili bir konu var."

    wa = parse_text("[04.11.2026 14:03] Ayşe Yılmaz: Merhaba\n04.11.2026 14:05 - Koç Ali: Hoş geldiniz, nasılsınız?")
    assert [s.get("name") for s in wa] == ["Ayşe Yılmaz", "Koç Ali"] and "speaker" not in wa[0]


def test_video_session_visual_analysis():
    import shutil
    import subprocess

    import pytest

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg yok")
    video_path = os.path.join(os.environ["DATA_DIR"], "deneme.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=4:size=320x240:rate=10",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-shortest", video_path], check=True)
    c = client.post("/api/clients", json={"name": "Video Danışanı", "consent": True}).json()
    with open(video_path, "rb") as f:
        s = client.post(f"/api/clients/{c['id']}/sessions", files={"file": ("seans.mp4", f, "video/mp4")},
                        data={"title": "Görsel seans"}).json()
    s = client.get(f"/api/sessions/{s['id']}").json()
    assert s["status"] == "tamamlandi", s["error"]
    assert s["source"] == "video"
    assert s["visual"]["kare_sayisi"] >= 1 and s["visual"]["kareler"][0]["t"] is not None
    assert client.get(f"/api/sessions/{s['id']}/frames/0").status_code == 200

    # Ses dosyasında görsel analiz yapılmaz
    a = client.get(f"/api/sessions/{_upload(c['id'], 'Sesli').json()['id']}").json()
    assert a["visual"] is None and a["source"] == "upload"


def test_whatsapp_speakers_without_llm():
    from app.analysis import label_by_names
    from app.textsession import parse_text

    chat = ("[12.11.2026 20:14] Ege: Hocam merhaba, kötüyüm bugün.\n"
            "[12.11.2026 20:15] Selin Hoca: Merhaba Ege. Seni ne zorladı?\n"
            "[12.11.2026 20:17] Ege: Deneme sonucu geldi.\n"
            "[12.11.2026 20:18] Selin Hoca: İçinden neler geçti?")
    segs = label_by_names(parse_text(chat))
    assert [s["speaker"] for s in segs] == ["danisan", "koc", "danisan", "koc"]

    # İsimde ipucu yoksa daha çok soru soran koçtur
    chat2 = "Ali: Bugün ne konuşalım?\nAyşe: İşimle ilgili.\nAli: Neler oluyor?\nAyşe: Yoruldum."
    assert [s["speaker"] for s in label_by_names(parse_text(chat2))] == ["koc", "danisan", "koc", "danisan"]
    # Üç kişi varsa tahmin etmez (yapay zekâya bırakır)
    assert label_by_names(parse_text("A: x?\nB: y\nC: z")) is None


def test_text_session_end_to_end():
    c = client.post("/api/clients", json={"name": "Yazılı", "consent": True}).json()
    assert client.post(f"/api/clients/{c['id']}/sessions/text", json={"text": "kısa"}).status_code == 400
    text = "\n".join(["Koç: Bugünkü görüşmeden ne almak istersiniz?", "Danışan: Zaman yönetimi konusunda zorlanıyorum.",
                      "Koç: Bu zorluk size en çok nerede hissettiriyor?", "Danışan: Sabahları işe başlarken."])
    s = client.post(f"/api/clients/{c['id']}/sessions/text", json={"title": "WhatsApp", "text": text}).json()
    s = client.get(f"/api/sessions/{s['id']}").json()
    assert s["status"] == "tamamlandi", s["error"]
    assert s["source"] == "metin" and s["metrics"]["kaynak_turu"] == "metin"
    assert s["metrics"]["ort_bekleme_sn"] is None and s["metrics"]["acik_uclu_soru"] == 2
    assert s["report"] and s["icf"]


def _login(email: str, password: str) -> TestClient:
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200
    return c


def test_auth_required_and_setup_once():
    anon = TestClient(app)
    assert anon.get("/api/clients").status_code == 401
    assert anon.get("/api/auth/state").json()["setup_needed"] is False
    assert anon.post("/api/auth/setup", json={"name": "X", "email": "x@x.com", "password": "12345678"}).status_code == 400
    assert anon.post("/api/auth/login", json={"email": "admin@test.local", "password": "yanlis-sifre"}).status_code == 400


def test_coach_sees_only_own_clients():
    client.post("/api/users", json={"name": "Koç A", "email": "koca@test.local", "role": "koc", "password": "sifre-koc-a1"})
    client.post("/api/users", json={"name": "Koç B", "email": "kocb@test.local", "role": "koc", "password": "sifre-koc-b1"})
    a, b = _login("koca@test.local", "sifre-koc-a1"), _login("kocb@test.local", "sifre-koc-b1")
    mine = a.post("/api/clients", json={"name": "A'nın danışanı", "consent": True}).json()
    assert mine["coach_name"] == "Koç A"
    assert [c["id"] for c in a.get("/api/clients").json()] == [mine["id"]]
    assert b.get(f"/api/clients/{mine['id']}").status_code == 403
    assert b.get("/api/clients").json() == []
    assert a.get("/api/users").status_code == 403  # kullanıcı yönetimi yalnızca yöneticide
    assert any(c["id"] == mine["id"] for c in client.get("/api/clients").json())  # yönetici hepsini görür


def test_client_portal_account():
    c = client.post("/api/clients", json={"name": "Portal Danışanı", "consent": True}).json()
    s = _upload(c["id"], "1. seans").json()
    assert client.post(f"/api/clients/{c['id']}/account", json={"email": "portal@test.local", "password": "kisa"}).status_code == 400
    assert client.post(f"/api/clients/{c['id']}/account", json={"email": "portal@test.local", "password": "danisan-sifre-1"}).status_code == 200
    assert client.get(f"/api/clients/{c['id']}").json()["account"]["email"] == "portal@test.local"

    d = _login("portal@test.local", "danisan-sifre-1")
    portal = d.get("/api/me/portal").json()
    assert portal["profile"]["name"] == "Portal Danışanı" and portal["sessions"] and portal["messages"]
    assert "icf" not in portal["sessions"][0] and "transcript" not in portal["sessions"][0]
    assert d.get("/api/clients").status_code == 403
    assert d.get(f"/api/sessions/{s['id']}").status_code == 403  # koç değerlendirmesine erişemez
    assert d.post("/api/me/checkins", json={"mood": 4, "note": "iyi"}).status_code == 200
    task = portal["tasks"][0]
    assert d.patch(f"/api/tasks/{task['id']}", json={"status": "yapildi"}).status_code == 200
    if portal["trainings"]:
        assert d.get(f"/api/trainings/{portal['trainings'][0]['id']}").status_code == 200

    other = client.post("/api/clients", json={"name": "Başkası", "consent": True}).json()
    assert d.get(f"/api/clients/{other['id']}/portal").status_code == 403


def test_org_manager_sees_anonymous_panel():
    org = client.post("/api/organizations", json={"name": "Anonim Kurum", "org_type": "kamu"}).json()
    c = client.post("/api/clients", json={"name": "Gizli İsim", "organization_id": org["id"], "consent": True}).json()
    _upload(c["id"], "1. seans")
    client.post("/api/users", json={"name": "Birim Sorumlusu", "email": "kurum@test.local", "role": "kurum",
                                    "password": "kurum-sifre-1", "organization_id": org["id"]})
    k = _login("kurum@test.local", "kurum-sifre-1")
    panel = k.get("/api/me/organization").json()
    assert panel["danisan_sayisi"] == 1 and "clients" not in panel and "Gizli İsim" not in str(panel)
    assert k.get("/api/clients").status_code == 403
    assert k.get(f"/api/organizations/{org['id']}").status_code == 403


def test_metrics_question_types():
    segs = [
        {"start": 0, "end": 10, "speaker": "koc", "text": "Bu size ne hissettiriyor? Hazır mısınız?"},
        {"start": 10, "end": 40, "speaker": "danisan", "text": "Biraz gerginim."},
    ]
    m = compute_metrics(segs)
    assert m["acik_uclu_soru"] == 1
    assert m["kapali_soru"] == 1
    assert m["koc_konusma_orani"] == 25


def test_photo_session_visual_analysis():
    import shutil
    import subprocess

    import pytest

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg yok")
    img = os.path.join(os.environ["DATA_DIR"], "tahta.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=white:s=640x480",
                    "-frames:v", "1", img], check=True)
    c = client.post("/api/clients", json={"name": "Foto Danışanı", "consent": True}).json()
    with open(img, "rb") as f1, open(img, "rb") as f2:
        r = client.post(f"/api/clients/{c['id']}/sessions/photos",
                        files=[("files", ("tahta.png", f1, "image/png")), ("files", ("plan.png", f2, "image/png"))],
                        data={"title": "Hedef panosu", "notes": "Danışan hedef panosunu getirdi."})
    assert r.status_code == 200, r.text
    s = client.get(f"/api/sessions/{r.json()['id']}").json()
    assert s["status"] == "tamamlandi", s["error"]
    assert s["source"] == "foto" and s["icf"] is None and s["report"]["ozet"]
    assert s["visual"]["kare_sayisi"] == 2 and s["visual"]["kareler"][0]["t"] is None
    assert client.get(f"/api/sessions/{s['id']}/frames/1").status_code == 200

    # Desteklenmeyen tür ve boş yükleme reddedilir
    bad = client.post(f"/api/clients/{c['id']}/sessions/photos",
                      files=[("files", ("not.txt", b"merhaba", "text/plain"))])
    assert bad.status_code == 400


def test_behavior_loop_plan_followup_and_observer():
    from datetime import date, timedelta

    from app import agent, db

    c = client.post("/api/clients", json={"name": "Plan Danışanı", "consent": True, "email": "plan@ornek.com",
                                          "phone": "0532 000 00 00", "notify_channels": ["eposta", "whatsapp"]}).json()
    assert c["notify_channels"] == "eposta,whatsapp"
    s = _upload(c["id"], "Seans").json()
    t = client.post(f"/api/sessions/{s['id']}/trainings", json={"area_index": 0}).json()
    detail = client.get(f"/api/trainings/{t['id']}").json()
    assert detail["content"]["koc_ozeti"] and detail["content"]["eslestirme"]

    k = client.post(f"/api/trainings/{t['id']}/commitment",
                    json={"durum": "Ekip üyesi teslimi kaçırırsa", "davranis": "aynı gün birebir konuşurum"}).json()
    assert k["status"] == "aktif"
    # Kontrol günü gelince ajan planı sorar ve izin verilen kanallara gönderir (ayar yoksa "simüle")
    db.update_commitment(k["id"], check_date=date.today().isoformat())
    done = agent.run_for_client(c["id"], today=date.today() + timedelta(days=1))
    assert any(d["trigger"] == f"plan:k{k['id']}" for d in done)
    notes = db.list_notifications(c["id"])
    assert {n["channel"] for n in notes} >= {"uygulama", "eposta", "whatsapp"}
    assert all(n["status"] in ("gonderildi", "simule") for n in notes)

    r = client.post(f"/api/commitments/{k['id']}/response", json={"status": "yapildi", "reflection": "Konuştum"}).json()
    assert r["status"] == "yapildi"

    # Koç gözlemci eklerken danışan onayı şart
    assert client.post(f"/api/commitments/{k['id']}/observer", json={"observer_name": "Ayşe"}).status_code == 400
    obs = client.post(f"/api/commitments/{k['id']}/observer",
                      json={"observer_name": "Ayşe", "relation": "Ekip arkadaşı", "consent": True}).json()
    token = obs["token"]
    assert obs["link"].endswith(f"/#/gozlem/{token}")
    info = client.get(f"/api/observe/{token}").json()
    assert info["danisan"] == "Plan" and "birebir" in info["davranis"] and "email" not in info
    assert client.post(f"/api/observe/{token}", json={"rating": 3, "example": "Toplantı sonrası konuştu"}).status_code == 200
    assert client.post(f"/api/observe/{token}", json={"rating": 2}).status_code == 400  # ikinci kez olmaz

    ev = client.get(f"/api/clients/{c['id']}/evidence").json()
    assert ev["summary"]["plan_uygulanan"] == 1 and ev["summary"]["gozlem_ortalama"] == 3

    # Sonraki seans raporu planı değerlendirir
    s2 = client.get(f"/api/sessions/{_upload(c['id'], 'Seans 2').json()['id']}").json()
    assert s2["report"]["plan_degerlendirmesi"] and s2["report"]["duygu_dili"]


def test_meeting_bot_simulation_and_agents_page():
    from datetime import datetime, timedelta

    from app import db, meetingbot

    c = client.post("/api/clients", json={"name": "Bot Danışanı", "consent": True}).json()
    assert client.post(f"/api/clients/{c['id']}/meeting-bot", json={"meeting_url": "https://example.com/x"}).status_code == 400
    bot = client.post(f"/api/clients/{c['id']}/meeting-bot",
                      json={"meeting_url": "https://us02web.zoom.us/j/123456789"}).json()
    assert bot["provider"] == "simulasyon" and bot["status"] == "katiliyor"
    old = (datetime.now() - timedelta(seconds=30)).isoformat(timespec="seconds")
    db.update_meeting_bot(bot["id"], created_at=old)
    meetingbot.poll_once()  # katılıyor -> kayıtta
    meetingbot.poll_once()  # kayıtta -> seans oluşturulur ve analiz edilir
    b = db.get_meeting_bot(bot["id"])
    assert b["status"] == "tamamlandi" and b["session_id"]
    assert client.get(f"/api/sessions/{b['session_id']}").json()["status"] == "tamamlandi"

    data = client.get("/api/agents").json()
    assert [a["key"] for a in data["agents"]] == ["analiz", "mufredat", "davranis", "kurum"]


def test_org_anonymity_threshold():
    from app.insights import anonymize, cluster_themes

    ov = {"clients": [{"client_type": "bireysel", "focus_area": "x"}] * 2, "birimler": [("A", 2)],
          "tema_kumeleri": [{"etiket": "t", "kisi_sayisi": 2}], "temalar": [("t", 2)], "gelisim_alanlari": [("g", 1)]}
    a = anonymize(ov)
    assert a["kucuk_grup"] and a["temalar"] == [] and a["tema_kumeleri"] == []
    assert a["birimler"] == [("Diğer (küçük gruplar)", 2)]
    k = cluster_themes([(1, "Geri bildirim"), (2, "Geri bildirim verme"), (3, "Liderlik")])
    assert k[0]["kisi_sayisi"] == 2


# --- Koçsuz mod (kendi kendine koçluk) ----------------------------------------------

_INTAKE = {"meslek": "Muhasebeci", "yer": "sehir", "yasam": "aile", "hobiler": ["Bahçe işleri", "Tavla"],
           "ortamlar": ["Sakin", "Doğa"], "zaman": "orta", "butce": "az", "konu": "kaygi",
           "sorun": "Yeni insanlarla konuşurken çok geriliyorum, kalabalıkta nefesim daralıyor."}
_TIPI = [2, 3, 6, 6, 4, 6, 6, 2, 3, 4]


def _register(email: str, age: int = 30, **extra):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"name": "Deneme Kullanıcı", "email": email, "password": "kendi-sifre-1",
                                           "age": age, "kvkk": True, "not_therapy": True, **extra})
    return c, r


def test_self_guided_register_rules():
    _, r = _register("genc@test.local", age=17)
    assert r.status_code == 400 and "18" in r.json()["detail"]
    _, r = _register("onaysiz@test.local", kvkk=False)
    assert r.status_code == 400
    u, r = _register("bireysel@test.local")
    assert r.status_code == 200
    st = u.get("/api/auth/state").json()["user"]
    assert st["self_guided"] is True and st["role"] == "danisan"
    assert u.get("/api/me/self").json()["phase"] == "form"
    assert u.get("/api/clients").status_code == 403
    # koçun eklediği danışan koçsuz mod uçlarını kullanamaz
    c = client.post("/api/clients", json={"name": "Koçlu Danışan", "consent": True}).json()
    client.post(f"/api/clients/{c['id']}/account", json={"email": "koclu@test.local", "password": "danisan-sifre-2"})
    assert _login("koclu@test.local", "danisan-sifre-2").get("/api/me/self").status_code == 403


def test_self_guided_intake_profile_plan_and_training():
    u, _ = _register("akis@test.local", age=55)
    assert u.post("/api/me/self/start", json={"intake": _INTAKE, "tipi": [1, 2]}).status_code == 400  # test eksik
    st = u.post("/api/me/self/start", json={"intake": _INTAKE, "tipi": _TIPI}).json()
    assert st["phase"] == "sohbet" and st["personality"]["disa_doniklik"] == 2.0  # (2 + 8-6) / 2
    assert st["messages"][-1]["sender"] == "ajan"

    st = u.post("/api/me/self/chat", json={"text": "En çok toplantılarda ve düğünlerde oluyor."}).json()
    st = u.post("/api/me/self/chat", json={"text": "Nefes egzersizi denedim, biraz iyi geldi."}).json()
    assert st["phase"] == "onay" and st["profile"]["ozet"]

    st = u.post("/api/me/self/correct", json={"text": "Aslında kalabalıktan değil, tanımadığım insanlardan geriliyorum."}).json()
    assert st["phase"] == "onay"

    st = u.post("/api/me/self/confirm").json()
    st = u.get("/api/me/self").json()
    assert st["phase"] == "aktif", st["error"]
    assert len(st["plan"]["haftalar"]) == 4 and st["plan"]["baslangic"]
    tasks = st["plan_tasks"]
    assert len(tasks) == 12 and {t["detail"]["hafta"] for t in tasks} == {1, 2, 3, 4}
    assert any(t["detail"]["harita_arama"] for t in tasks)

    portal = u.get("/api/me/portal").json()
    assert portal["trainings"], "kişiye özel eğitim hazırlanmalı"
    assert portal["sessions"] == []  # tanışma kaydı seans olarak görünmez

    # Görev değiştirme
    swapped = u.post(f"/api/me/self/tasks/{tasks[0]['id']}/swap", json={"text": "Dizlerim ağrıyor"}).json()
    assert swapped["detail"]["degisti"] is True and swapped["detail"]["hafta"] == tasks[0]["detail"]["hafta"]

    # Serbest sohbet (plan sonrası)
    st = u.post("/api/me/self/chat", json={"text": "Bugün biraz yorgunum."}).json()
    assert st["messages"][-1]["sender"] == "ajan" and st["phase"] == "aktif"

    # Koç eşleştirme isteği yöneticiye düşer
    u.post("/api/me/self/coach")
    assert any(r["name"] == "Deneme Kullanıcı" for r in client.get("/api/self-guided/requests").json())


def test_self_guided_crisis_and_weekly_review():
    from datetime import date, timedelta

    from app import agent, db

    u, _ = _register("kriz@test.local", age=40)
    st = u.post("/api/me/self/start", json={"intake": {**_INTAKE, "sorun": "Bazen yaşamak istemiyorum, çok yoruldum."},
                                            "tipi": _TIPI}).json()
    assert st["phase"] == "kriz" and "112" in st["messages"][-1]["text"]
    st = u.post("/api/me/self/chat", json={"text": "tamam"}).json()
    assert st["phase"] == "kriz"  # krizde plan / soru sorulmaz
    st = u.post("/api/me/self/resume").json()
    assert st["phase"] == "sohbet"

    # Planı tamamla
    u.post("/api/me/self/chat", json={"text": "Toplantılarda oluyor."})
    u.post("/api/me/self/chat", json={"text": "Bir şey denemedim."})
    u.post("/api/me/self/confirm")
    st = u.get("/api/me/self").json()
    assert st["phase"] == "aktif"
    cid = u.get("/api/auth/state").json()["user"]["client_id"]

    # 1. hafta bitince ajan haftayı değerlendirir ve 2. haftanın görevlerini yeniler
    start = date.fromisoformat(st["plan"]["baslangic"])
    done = agent.run_for_client(cid, today=start + timedelta(days=8))
    assert any(d["trigger"] == "haftalik:w1" for d in done)
    week2 = [t for t in db.list_tasks(cid) if t.get("detail") and t["detail"]["hafta"] == 2]
    assert week2 and all("9. hafta" in t["text"] for t in week2)  # mock yeni görevleri yazdı
    assert any(m["kind"] == "haftalik" for m in u.get("/api/me/portal").json()["messages"])

    # Koçsuz modda düşük ruh hali uyarısı kullanıcının kendisine gider
    u.post("/api/me/checkins", json={"mood": 1, "note": "berbat bir gün"})
    agent.run_for_client(cid)
    assert any(a["kind"] == "uyari" and a["target"] == "danisan" for a in db.list_agent_actions(cid))

    # Check-in notunda kriz ifadesi -> destek akışı
    u.post("/api/me/checkins", json={"mood": 1, "note": "kendime zarar vermek istiyorum"})
    assert u.get("/api/me/self").json()["phase"] == "kriz"


def test_safety_patterns():
    from app.safety import is_crisis

    assert is_crisis("Bazen ÖLMEK İSTİYORUM")
    assert is_crisis("intihar etmeyi düşündüm")
    assert is_crisis("kendimi öldürmek")
    assert not is_crisis("Sınavdan çok korkuyorum")
    assert not is_crisis("Yeni insanlarla tanışmak istiyorum")


def test_admin_role_change_and_client_delete():
    from app import db

    k = client.post("/api/users", json={"name": "Yetki Koç", "email": "yetki@test.local", "role": "koc",
                                        "password": "sifre-yetki-1"}).json()
    org = client.post("/api/organizations", json={"name": "Yetki Kurumu"}).json()
    koc = _login("yetki@test.local", "sifre-yetki-1")
    mine = koc.post("/api/clients", json={"name": "Silinecek Danışan", "consent": True}).json()
    other = client.post("/api/clients", json={"name": "Başka Danışan", "consent": True}).json()

    # Koç yetki veremez; yönetici verir
    assert koc.patch(f"/api/users/{k['id']}", json={"role": "admin"}).status_code == 403
    me = client.get("/api/auth/state").json()["user"]
    assert client.patch(f"/api/users/{me['id']}", json={"role": "koc"}).status_code == 400  # kendi yetkisi
    assert client.patch(f"/api/users/{k['id']}", json={"role": "kurum"}).status_code == 400  # kurum seçilmeli
    assert client.patch(f"/api/users/{k['id']}", json={"role": "admin"}).json()["role"] == "admin"
    assert any(c["id"] == other["id"] for c in koc.get("/api/clients").json())  # artık her şeyi görür
    client.patch(f"/api/users/{k['id']}", json={"role": "koc"})

    # Koç yalnızca kendi danışanını silebilir; silinince tüm verisi gider
    s = _upload(mine["id"], "1. seans").json()
    client.post(f"/api/clients/{mine['id']}/account", json={"email": "silinecek@test.local", "password": "danisan-sil-1"})
    assert koc.delete(f"/api/clients/{other['id']}").status_code == 403
    assert koc.delete(f"/api/clients/{mine['id']}").status_code == 200
    assert client.get(f"/api/clients/{mine['id']}").status_code == 404
    assert db.get_session(s["id"]) is None and not db.list_tasks(mine["id"])
    assert TestClient(app).post("/api/auth/login", json={"email": "silinecek@test.local", "password": "danisan-sil-1"}).status_code == 400

    # Kurum yöneticisi yapılan koçun danışanları koçsuz kalır
    kept = koc.post("/api/clients", json={"name": "Kalan Danışan", "consent": True}).json()
    assert client.patch(f"/api/users/{k['id']}", json={"role": "kurum", "organization_id": org["id"]}).status_code == 200
    assert client.get(f"/api/clients/{kept['id']}").json()["coach_id"] is None


def test_forgot_password_code(monkeypatch):
    from app import auth

    client.post("/api/users", json={"name": "Unutkan Koç", "email": "unutkan@test.local", "role": "koc",
                                    "password": "eski-sifre-12"})
    anon = TestClient(app)
    codes = iter(["123456", "654321"])
    monkeypatch.setattr(auth, "new_reset_code", lambda: next(codes))

    r = anon.post("/api/auth/forgot", json={"email": "unutkan@test.local"}).json()
    assert r["ok"] and r["eposta_ayarli"] is False  # testte SMTP yok: kod sunucu penceresine yazılır
    # Olmayan hesap da aynı cevabı alır (hesap var mı yok mu belli olmaz)
    assert anon.post("/api/auth/forgot", json={"email": "yok@test.local"}).json()["ok"] is True
    # Hemen tekrar istenirse yeni kod üretilmez
    anon.post("/api/auth/forgot", json={"email": "unutkan@test.local"})

    bad = anon.post("/api/auth/reset", json={"email": "unutkan@test.local", "code": "000000", "password": "yeni-sifre-12"})
    assert bad.status_code == 400
    ok = anon.post("/api/auth/reset", json={"email": "unutkan@test.local", "code": "123456", "password": "yeni-sifre-12"})
    assert ok.status_code == 200 and anon.get("/api/auth/state").json()["user"]["email"] == "unutkan@test.local"
    # Kod tek kullanımlık; eski şifre artık çalışmaz, yenisi çalışır
    assert anon.post("/api/auth/reset", json={"email": "unutkan@test.local", "code": "123456",
                                              "password": "baska-sifre-1"}).status_code == 400
    assert TestClient(app).post("/api/auth/login", json={"email": "unutkan@test.local", "password": "eski-sifre-12"}).status_code == 400
    _login("unutkan@test.local", "yeni-sifre-12")

    # 5 yanlış denemeden sonra doğru kod da kabul edilmez
    rows = auth.db.all_rows("SELECT id FROM users WHERE email = 'unutkan@test.local'")
    with auth.db.connect() as conn:
        conn.execute("UPDATE password_resets SET created_at = '2000-01-01T00:00:00' WHERE user_id = ?", (rows[0]["id"],))
    anon.post("/api/auth/forgot", json={"email": "unutkan@test.local"})  # yeni kod: 654321
    for _ in range(5):
        anon.post("/api/auth/reset", json={"email": "unutkan@test.local", "code": "111111", "password": "x-sifre-123"})
    assert anon.post("/api/auth/reset", json={"email": "unutkan@test.local", "code": "654321",
                                              "password": "x-sifre-123"}).status_code == 400
