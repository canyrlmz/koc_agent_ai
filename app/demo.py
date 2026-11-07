"""Örnek veri: Sistemi tek tıkla dolu hâliyle göstermek için (hoca/jüri sunumu).

API anahtarı gerektirmez, anında yüklenir. Tüm kişi ve kurum adları kurgusaldır ve
"Örnek" etiketiyle işaretlenir.
"""
import secrets
from datetime import datetime, timedelta

from . import agent, db
from .analysis import compute_metrics
from .icf import COMPETENCIES
from .llm import _mock
from .research import SAMPLE_PAPERS
from .schemas import MicroLearning

ORGS = [
    {
        "key": "tek",
        "name": "Örnek Teknoloji A.Ş.",
        "org_type": "sirket",
        "sector": "Yazılım",
        "knowledge": (
            "Değerlerimiz: şeffaflık, müşteri odaklılık, sürekli öğrenme.\n"
            "Yönetici yetkinlik modeli: geri bildirim kültürü, delegasyon, psikolojik güvenlik.\n"
            "2026 önceliği: ekip içinde düzenli ve yapıcı geri bildirim kültürünü yerleştirmek."
        ),
    },
    {
        "key": "sos",
        "name": "Örnek Belediye Sosyal Destek Birimi",
        "org_type": "sosyal_birim",
        "sector": "Kamu / sosyal hizmet",
        "knowledge": (
            "Amaç: Sosyal destek alan bireylerin öz yeterliğini artırmak ve istihdama kazandırmak.\n"
            "Programlar: İstihdam Destek Programı, Aile Destek Programı, Gençlik Programı.\n"
            "İlkeler: güçlendirme, damgalamama, gizlilik, gönüllü katılım."
        ),
    },
]

ICF_TEXT = {
    "A1": ("Koçluk sınırları korundu; terapi veya danışmanlığa kayılmadı.", "Sınırlar korundu ancak gizlilik çerçevesi seans başında hatırlatılmadı."),
    "A2": ("Danışan odaklı, meraklı ve yargısız bir tutum sergilendi.", "Yer yer çözüm önermeye yönelindi; merak tutumu güçlendirilebilir."),
    "B3": ("Seansın hedefi ve başarı ölçütü birlikte netleştirildi.", "Seans hedefi konuşuldu ama başarı ölçütü netleştirilmedi."),
    "B4": ("Danışanın duyguları kabul edildi, güvenli bir alan oluşturuldu.", "Destekleyici bir dil kullanıldı; duyguların adlandırılması sınırlı kaldı."),
    "B5": ("Sakin ve odaklı kalındı; sessizliğe alan tanındı.", "Bazı sorular arka arkaya soruldu; düşünme alanı kısa kaldı."),
    "C6": ("Danışanın kelimeleri yansıtıldı ve özetlendi.", "Yansıtma ve özetleme fırsatları kaçırıldı."),
    "C7": ("Güçlü, açık uçlu sorularla yeni bir farkındalık ortaya çıktı.", "Sorular çoğunlukla bilgi toplamaya yönelikti; derinleşme sınırlı kaldı."),
    "D8": ("Farkındalık somut, zamanlı bir eylem planına dönüştürüldü.", "Eylem adımı belirlendi ama zaman ve hesap verebilirlik netleşmedi."),
}

ELIF_S1 = [
    ("koc", "Merhaba Elif Hanım, hoş geldiniz. Bugünkü seanstan ne almak istersiniz?"),
    ("danisan", "Ekibime geri bildirim verirken zorlanıyorum. Ya hiç söylemiyorum ya da çok geç söylüyorum."),
    ("koc", "Geri bildirim vermeyi ertelediğiniz anlarda içinizde neler oluyor?"),
    ("danisan", "Kırıcı olmaktan korkuyorum. Ekipteki iyi havayı bozmak istemiyorum."),
    ("koc", "Bu iyi hava sizin için neyi temsil ediyor?"),
    ("danisan", "Sanırım sevilmek. Herkesin benimle rahat olmasını istiyorum."),
    ("koc", "Bunu fark etmek size ne hissettiriyor?"),
    ("danisan", "Şaşırdım açıkçası. Liderlik yerine sevilmeyi seçiyormuşum."),
    ("koc", "Bu seansın sonunda neyi farklı yapmak isterdiniz?"),
    ("danisan", "Bu hafta en az bir kişiye zamanında ve net bir geri bildirim vermek istiyorum."),
    ("koc", "Bunu ne zaman ve kiminle yapacaksınız?"),
    ("danisan", "Perşembe günü sprint toplantısından sonra Burak ile konuşacağım."),
]
ELIF_S2 = [
    ("koc", "Geçen hafta Burak ile konuşmayı planlamıştınız. Nasıl geçti?"),
    ("danisan", "Konuştum! Önceden üç cümle yazdım, çok işe yaradı. Burak da teşekkür etti."),
    ("koc", "Bunu yaptığınızda kendinizle ilgili neyi fark ettiniz?"),
    ("danisan", "Net olmanın aslında saygı göstermek olduğunu. Korktuğum şey olmadı."),
    ("koc", "Bu farkındalığı ekibin geri kalanına nasıl taşımak istersiniz?"),
    ("danisan", "Haftalık birebirlerde kısa bir geri bildirim bölümü açmak istiyorum."),
    ("koc", "Bunun işe yaradığını nereden anlayacaksınız?"),
    ("danisan", "Ekipten de bana geri bildirim gelmeye başlarsa. Bir ay içinde görmek istiyorum."),
]
MERT_S1 = [
    ("koc", "Merhaba Mert Bey, bugün hangi konu üzerinde çalışmak istersiniz?"),
    ("danisan", "Altı aydır iş arıyorum. Görüşmelere gidiyorum ama kendimi anlatamıyorum."),
    ("koc", "Kendinizi anlatamadığınızı düşündüğünüz anlarda ne oluyor?"),
    ("danisan", "Boşluğumu sorduklarında utanıyorum, kısa kesiyorum."),
    ("koc", "Bu altı ayda kendiniz için neler yaptınız?"),
    ("danisan", "Aslında forklift sertifikası aldım, bir de mahallede gönüllü çalıştım."),
    ("koc", "Bunları söylerken sesinizin değiştiğini fark ettim. Ne hissediyorsunuz?"),
    ("danisan", "Galiba gurur. Bunları hiç bir başarı gibi düşünmemiştim."),
    ("koc", "Bir sonraki görüşmeye kadar ne denemek istersiniz?"),
    ("danisan", "Bu iki şeyi anlatan kısa bir cümle hazırlayıp aynada prova edeceğim. Bir de her gün iki ilana başvuracağım."),
]
ZEYNEP_S1 = [
    ("koc", "Merhaba Zeynep Hanım, bugün neyi konuşmak istersiniz?"),
    ("danisan", "On beş yaşındaki oğlumla her konuşmamız kavgaya dönüyor."),
    ("koc", "Bu konuşmalar genelde nasıl başlıyor?"),
    ("danisan", "Ders sorduğumda. O odasına kapanıyor, ben de sesimi yükseltiyorum."),
    ("koc", "Oğlunuzla olan ilişkinizde en çok neyi korumak istiyorsunuz?"),
    ("danisan", "Bana güvenmesini. Küçükken her şeyi anlatırdı."),
    ("koc", "Ders dışında bir konuşma başlatsanız bu nasıl olurdu?"),
    ("danisan", "Futbolu çok seviyor. Belki maç hakkında sorabilirim."),
    ("koc", "Bunu bu hafta ne zaman denemek istersiniz?"),
    ("danisan", "Cumartesi maçı birlikte izlemeyi teklif edeceğim."),
]

REPORTS = {
    "elif1": {
        "ozet": "Elif Hanım, ekibine geri bildirim vermeyi ertelediğini ve bunun altında sevilme ihtiyacının yattığını fark etti. "
                "Liderlik rolü ile onaylanma ihtiyacı arasındaki gerilim seansın ana teması oldu. Seans, somut bir geri bildirim görüşmesi planıyla kapandı.",
        "danisan_hedefleri": ["Ekibe zamanında ve net geri bildirim vermek"],
        "ana_temalar": ["Geri bildirim", "Onaylanma ihtiyacı", "Liderlik rolü"],
        "onceki_seanslarla_baglanti": "Bu danışanla yapılan ilk seans.",
        "gelisim_alanlari": [
            {"baslik": "Yapıcı geri bildirim verme", "aciklama": "Kırıcı olma kaygısıyla geri bildirimi erteliyor; somut bir model ihtiyacı var.",
             "kanit": "Ya hiç söylemiyorum ya da çok geç söylüyorum."},
            {"baslik": "Liderlik rolü ve onay ihtiyacı", "aciklama": "Sevilme isteği liderlik kararlarını etkiliyor.",
             "kanit": "Liderlik yerine sevilmeyi seçiyormuşum."},
        ],
        "danisan_gorevleri": ["Söylenecekleri üç cümleyle önceden yazmak", "Perşembe günü Burak ile geri bildirim görüşmesi yapmak"],
        "sonraki_seans_onerileri": ["Burak ile görüşmenin nasıl geçtiğini sorun", "Onay ihtiyacı temasını derinleştirin"],
        "duygu_dili": [{"duygu": "kaygı", "alinti": "“Söylersem kırılır diye çok geriliyorum.”"},
                       {"duygu": "suçluluk", "alinti": "“Ekibe haksızlık ediyormuşum gibi hissediyorum.”"}],
        "plan_degerlendirmesi": [],
    },
    "elif2": {
        "ozet": "Elif Hanım planladığı geri bildirim görüşmesini gerçekleştirdi ve olumlu sonuç aldı. Net olmanın saygı göstermek olduğunu fark etti. "
                "Bu kazanımı ekibe yaymak için haftalık birebirlerde geri bildirim bölümü açmaya karar verdi.",
        "danisan_hedefleri": ["Ekipte iki yönlü geri bildirim kültürü oluşturmak"],
        "ana_temalar": ["Geri bildirim", "Başarı deneyimi", "Ekip kültürü"],
        "onceki_seanslarla_baglanti": "İlk seansta belirlenen görev tamamlandı. Erteleme davranışı yerini planlı ve net iletişime bıraktı; belirgin bir ilerleme var.",
        "gelisim_alanlari": [
            {"baslik": "Geri bildirim isteme", "aciklama": "Geri bildirim vermeye başladı; şimdi ekipten geri bildirim istemeyi öğrenmesi gerekiyor.",
             "kanit": "Ekipten de bana geri bildirim gelmeye başlarsa."},
        ],
        "danisan_gorevleri": ["Haftalık birebirlere 5 dakikalık geri bildirim bölümü eklemek"],
        "sonraki_seans_onerileri": ["Ekipten gelen ilk geri bildirimlere verdiği tepkiyi konuşun"],
        "duygu_dili": [{"duygu": "rahatlama", "alinti": "“Konuştuktan sonra omzumdan yük kalktı.”"},
                       {"duygu": "gurur", "alinti": "“İlk kez ertelemeden söyledim, kendimle gurur duydum.”"}],
        "plan_degerlendirmesi": [{"plan": "Eğer bir ekip üyesi teslim tarihini kaçırırsa, o zaman aynı gün 10 dakikalık birebir görüşme isterim",
                                  "bahsedildi": True, "kanit": "“Burak teslimi kaçırınca aynı gün yanına gittim.”"}],
    },
    "mert1": {
        "ozet": "Mert Bey, uzun süren iş arayışında görüşmelerde kendini ifade etmekte zorlandığını anlattı. Seansta, sertifika ve gönüllülük gibi "
                "deneyimlerini başarı olarak görmediği ortaya çıktı. Bunu fark etmek gurur duygusu yarattı ve somut bir prova planı oluşturuldu.",
        "danisan_hedefleri": ["İş görüşmelerinde kendini güvenle anlatmak", "Düzenli iş arama rutini kurmak"],
        "ana_temalar": ["Öz yeterlik", "Utanç", "İş arama motivasyonu"],
        "onceki_seanslarla_baglanti": "Bu danışanla yapılan ilk seans.",
        "gelisim_alanlari": [
            {"baslik": "Güçlü yönlerini ifade etme", "aciklama": "Deneyimlerini değersiz görüyor; kendini anlatma becerisi gelişmeli.",
             "kanit": "Bunları hiç bir başarı gibi düşünmemiştim."},
        ],
        "danisan_gorevleri": ["Sertifika ve gönüllülüğü anlatan kısa bir tanıtım cümlesi hazırlayıp prova etmek", "Her gün iki ilana başvurmak"],
        "sonraki_seans_onerileri": ["Prova deneyimini ve başvuru sayısını konuşun"],
    },
    "zeynep1": {
        "ozet": "Zeynep Hanım, ergen oğluyla konuşmalarının ders konusu yüzünden çatışmaya dönüştüğünü anlattı. İlişkideki asıl ihtiyacının güven "
                "olduğunu fark etti. Ders dışı, ortak bir ilgi alanı üzerinden bağ kurmayı denemeye karar verdi.",
        "danisan_hedefleri": ["Oğluyla tartışmadan konuşabilmek", "Güven ilişkisini yeniden kurmak"],
        "ana_temalar": ["Ebeveyn-ergen iletişimi", "Güven", "Çatışma döngüsü"],
        "onceki_seanslarla_baglanti": "Bu danışanla yapılan ilk seans.",
        "gelisim_alanlari": [
            {"baslik": "Ergenle şiddetsiz iletişim", "aciklama": "Ses yükseltme ve sorgulama döngüsü güveni zedeliyor.",
             "kanit": "O odasına kapanıyor, ben de sesimi yükseltiyorum."},
        ],
        "danisan_gorevleri": ["Cumartesi maçı oğluyla birlikte izlemeyi teklif etmek"],
        "sonraki_seans_onerileri": ["Maç deneyimini ve oğlunun tepkisini sorun"],
    },
}

ICF_SCORES = {
    "elif1": [4, 4, 4, 4, 3, 3, 5, 4], "elif2": [4, 5, 4, 4, 4, 4, 5, 5],
    "mert1": [4, 4, 3, 5, 4, 4, 4, 4], "zeynep1": [4, 3, 3, 4, 3, 3, 4, 4],
}


def _segments(lines: list[tuple[str, str]]) -> list[dict]:
    t, out = 0.0, []
    for i, (speaker, text) in enumerate(lines):
        duration = max(3.0, len(text.split()) / 2.4)
        out.append({"start": round(t, 1), "end": round(t + duration, 1), "speaker": speaker, "text": text})
        t += duration + (2.5 if i % 3 == 0 else 1.2)
    return out


def _icf(key: str) -> dict:
    scores = ICF_SCORES[key]
    items = [{
        "kod": code, "ad": name, "puan": p,
        "gerekce": ICF_TEXT[code][0 if p >= 4 else 1],
        "kanitlar": [],
        "gelistirme_onerisi": "Mevcut güçlü tutumu sürdürün." if p >= 4 else "Bu yetkinliğe bir sonraki seansta bilinçli olarak odaklanın.",
    } for (code, name, _), p in zip(COMPETENCIES, scores)]
    low = [i["ad"] for i in items if i["puan"] <= 3]
    return {
        "yetkinlikler": items,
        "guclu_yonler": [i["ad"] for i in items if i["puan"] == 5] or ["Danışan odaklı, yargısız tutum"],
        "gelisim_onerileri": [f"{n} yetkinliğini güçlendirin" for n in low] or ["Mevcut seviyeyi koruyun"],
        "genel_yorum": "(Örnek veri) Etkili ve danışan odaklı bir seans.",
        "ortalama": round(sum(scores) / len(scores), 2),
    }


def _session(client_id: int, title: str, key: str, lines, when: datetime) -> dict:
    s = db.create_session(client_id, title, "", source="ornek")
    segs = _segments(lines)
    db.update_session(
        s["id"], status="tamamlandi", transcript=segs, metrics=compute_metrics(segs),
        report=REPORTS[key], icf=_icf(key), created_at=when.isoformat(timespec="seconds"),
    )
    s = db.get_session(s["id"])
    agent.create_tasks_from_report(s, REPORTS[key])
    return s


def _checkin(client_id: int, mood: int, note: str, when: datetime) -> None:
    c = db.create_checkin(client_id, mood, note)
    db._update("checkins", c["id"], {"created_at": when.isoformat(timespec="seconds")})


DEMO_COACH_EMAIL = "demo.koc@ornek.local"
DEMO_CLIENT_EMAIL = "demo.danisan@ornek.local"
DEMO_ORG_EMAIL = "demo.kurum@ornek.local"


def ensure_demo_accounts() -> None:
    """Örnek veri varsa örnek giriş hesaplarını oluşturur (koç, danışan, kurum yöneticisi).

    Şifreleri rastgeledir ve kimseye gösterilmez; bu hesaplara yalnızca giriş ekranındaki
    "örnek hesapla gir" butonuyla girilir.
    """
    import secrets

    from . import auth

    clients = db.all_rows("SELECT id, name FROM clients WHERE name LIKE '%(Örnek)%'")
    if not clients:
        return
    coach = auth.find_by_email(DEMO_COACH_EMAIL) or auth.create_user(
        DEMO_COACH_EMAIL, "Deniz Aydın (Örnek Koç)", "koc", secrets.token_urlsafe(16), is_demo=True)
    with db.connect() as conn:
        conn.execute("UPDATE clients SET coach_id = ? WHERE name LIKE '%(Örnek)%'", (coach["id"],))
    elif_ = next((c for c in clients if c["name"].startswith("Elif Kaya")), None)
    if elif_ and not auth.find_by_email(DEMO_CLIENT_EMAIL):
        auth.create_user(DEMO_CLIENT_EMAIL, elif_["name"], "danisan", secrets.token_urlsafe(16),
                         client_id=elif_["id"], is_demo=True)
    org = db.all_rows("SELECT id FROM organizations WHERE name = ?", ("Örnek Belediye Sosyal Destek Birimi",))
    if org and not auth.find_by_email(DEMO_ORG_EMAIL):
        auth.create_user(DEMO_ORG_EMAIL, "Örnek Birim Sorumlusu", "kurum", secrets.token_urlsafe(16),
                         organization_id=org[0]["id"], is_demo=True)


def demo_user(role: str) -> dict | None:
    rows = db.all_rows("SELECT id FROM users WHERE is_demo = 1 AND role = ? ORDER BY id LIMIT 1", (role,))
    if not rows:
        return None
    from .auth import get_user

    return get_user(rows[0]["id"])


def demo_roles() -> list[str]:
    return [r["role"] for r in db.all_rows("SELECT DISTINCT role FROM users WHERE is_demo = 1")]


def seed() -> dict:
    now = datetime.now().replace(microsecond=0)
    orgs = {o["key"]: db.create_organization(**{k: v for k, v in o.items() if k != "key"}) for o in ORGS}

    elif_ = db.create_client(
        "Elif Kaya (Örnek)", "Liderlik", client_type="yonetici", organization_id=orgs["tek"]["id"],
        unit="Ürün Geliştirme", role_title="Takım Lideri", email="elif@ornek.com",
        goals="Ekibe zamanında ve net geri bildirim vermek", consent=True)
    mert = db.create_client(
        "Mert Demir (Örnek)", "Bireysel gelişim", client_type="bireysel", organization_id=orgs["sos"]["id"],
        unit="İstihdam Destek Programı", role_title="Program katılımcısı",
        goals="İş görüşmelerinde kendini ifade etmek; düzenli iş arama rutini", consent=True)
    zeynep = db.create_client(
        "Zeynep Arslan (Örnek)", "İlişkiler", client_type="bireysel", organization_id=orgs["sos"]["id"],
        unit="Aile Destek Programı", role_title="Veli",
        goals="Ergen çocuğuyla tartışmadan konuşabilmek", consent=True)

    e1 = _session(elif_["id"], "1. seans · Geri bildirim", "elif1", ELIF_S1, now - timedelta(days=9))
    _session(elif_["id"], "2. seans · İlk deneyim", "elif2", ELIF_S2, now - timedelta(days=2))
    m1 = _session(mert["id"], "1. seans · İş görüşmeleri", "mert1", MERT_S1, now - timedelta(days=4))
    z1 = _session(zeynep["id"], "1. seans · Oğlumla iletişim", "zeynep1", ZEYNEP_S1, now - timedelta(days=6))

    for t in db.list_tasks_for_session(e1["id"]):
        db.update_task(t["id"], "yapildi")
    m_tasks = db.list_tasks_for_session(m1["id"])
    db.update_task(m_tasks[0]["id"], "yapildi")

    for days, mood, note in [(8, 3, "Biraz gerginim"), (5, 4, "Burak ile konuştum, iyi geçti"), (1, 5, "Ekip toplantısı harika geçti")]:
        _checkin(elif_["id"], mood, note, now - timedelta(days=days))
    for days, mood, note in [(3, 3, "Provaya başladım"), (1, 4, "Bir görüşmeye çağrıldım")]:
        _checkin(mert["id"], mood, note, now - timedelta(days=days))
    for days, mood, note in [(5, 4, "Maçı birlikte izledik"), (1, 2, "Yine tartıştık, çok yorgunum")]:
        _checkin(zeynep["id"], mood, note, now - timedelta(days=days))

    # Örnek eğitim içeriği
    t = db.create_training(elif_["id"], e1["id"], REPORTS["elif1"]["gelisim_alanlari"][0])
    content = _mock(MicroLearning, "").model_dump()
    content["baslik"] = "Net Olmak Bir Nezakettir"
    content["kapanis"] = "Her net cümle, liderliğinize atılmış bir adım."
    db.update_training(t["id"], status="tamamlandi", query="constructive feedback workplace leaders",
                       papers=SAMPLE_PAPERS, content=content)

    # Örnek davranış döngüsü: eğer–o zaman planı -> öz-bildirim -> paydaş gözlemi -> bildirimler
    k1 = db.create_commitment(elif_["id"], t["id"], "Bir ekip üyesi teslim tarihini kaçırırsa",
                              "aynı gün 10 dakikalık birebir görüşme isterim", (now - timedelta(days=4)).date().isoformat())
    db.respond_commitment(k1["id"], "yapildi", "Burak'la aynı gün konuştum; beklediğimden rahat geçti.")
    k2 = db.create_commitment(elif_["id"], t["id"], "Toplantıda bir sorunu fark edersem",
                              "önce somut örneği, sonra beklentimi söylerim", (now + timedelta(days=2)).date().isoformat())
    o1 = db.create_observation(elif_["id"], k1["id"], secrets.token_urlsafe(16), "Ayşe", "Ekip arkadaşı")
    db.answer_observation(o1["id"], 2, "Geçen hafta sprint sonrası Burak'la kısa ve sakin bir konuşma yaptı.")
    db.create_observation(elif_["id"], k2["id"], secrets.token_urlsafe(16), "Can", "Yöneticisi")
    db.add_agent_action(elif_["id"], f"plan:k{k1['id']}", "plan", "danisan", True,
                        "Merhaba Elif Hanım, planınızı hatırlatmak istedim: “Eğer bir ekip üyesi teslimi kaçırırsa, aynı gün "
                        "birebir konuşurum.” Bu durum yaşandı mı, ne yaptınız?", "Planın kontrol günü geldi.")
    aid = db.agent_action_id(elif_["id"], f"plan:k{k1['id']}")
    msg = "Merhaba Elif Hanım, planınızı hatırlatmak istedim: bu durum yaşandı mı, ne yaptınız?"
    for ch, rcp, stt in [("uygulama", elif_["name"], "gonderildi"), ("eposta", "elif@ornek.com", "simule"),
                         ("whatsapp", "0532 111 22 33", "simule")]:
        db.add_notification(elif_["id"], aid, ch, rcp, msg, stt, "" if stt == "gonderildi" else "Örnek veri: kanal bağlı değil")
    db.update_client(elif_["id"], notify_channels="eposta,whatsapp", phone="0532 111 22 33")

    # Örnek ajan eylemleri
    actions = [
        (elif_["id"], f"takip:s{e1['id']}", "takip", "danisan", "Merhaba Elif Hanım, seansımızda Perşembe günü Burak ile konuşmayı planladınız. Bu adımı düşündüğünüzde şu an içinizden ne geçiyor?", "Seans sonrası takip ve yansıtma."),
        (elif_["id"], f"egitim:s{e1['id']}", "egitim", "koc", "Elif Hanım'ın geri bildirim erteleme eğilimi için 'Net Olmak Bir Nezakettir' eğitimini hazırladım.", "Seansta öne çıkan ilk gelişim alanı."),
        (mert["id"], f"takip:s{m1['id']}", "takip", "danisan", "Merhaba Mert Bey, sertifikanızı ve gönüllülüğünüzü anlattığınızda gurur duyduğunuzu söylemiştiniz. Provanız nasıl gidiyor?", "Seans sonrası takip."),
        (zeynep["id"], f"takip:s{z1['id']}", "takip", "danisan", "Merhaba Zeynep Hanım, Cumartesi maçı birlikte izlemeyi planlamıştınız. Oğlunuzla bu anı nasıl geçirmek istersiniz?", "Seans sonrası takip."),
        (zeynep["id"], "uyari:ornek", "uyari", "koc", "Zeynep Hanım'ın ruh hali 4'ten 2'ye düştü ve 'çok yorgunum' notunu bıraktı. Kısa bir ara görüşme planlamayı ve destek kaynaklarını konuşmayı değerlendirin.", "Ruh halinde belirgin düşüş."),
    ]
    for cid, key, kind, target, msg, reason in actions:
        db.add_agent_action(cid, key, kind, target, True, msg, reason)
    ensure_demo_accounts()
    return {"organizations": len(orgs), "clients": 3, "sessions": 4}
