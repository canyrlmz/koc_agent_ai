"""Farkora'nın 4 yapay zekâ ajanı: görev tanımları, girdi/çıktıları ve çalışma istatistikleri.

Ajanlar birbirine zincir gibi bağlıdır:
  1. Seans Analiz ve Metrik Ajanı  ──(gelişim alanı)──▶  2. Müfredat ve Mikro-Öğrenme Tasarım Ajanı
  2. ──(eğitim + eğer–o zaman planı)──▶  3. Davranış Takip ve Proaktif Eylem Ajanı
  1+3 ──(anonim toplu veri)──▶  4. Kurumsal İçgörü ve Anonimleştirme Ajanı
"""
from . import db

AGENTS = [
    {
        "key": "analiz", "no": 1, "ikon": "🎧", "ad": "Seans Analiz ve Metrik Ajanı",
        "temel": "ICF 8 temel yetkinlik göstergeleri, konuşma analizi",
        "gorev": [
            "Transkripti, ses metriklerini (konuşma payı, hız, düşünme süresi) ve görselleri inceler",
            "Koçun performansını ICF göstergelerine göre transkriptten alıntılarla puanlar",
            "Danışanın kendi sözleriyle ifade ettiği duyguları (duygu dili) ve önceki planların kanıtını çıkarır",
        ],
        "girdi": "Ses / video / ekran kaydı, fotoğraf, yazışma",
        "cikti": "Seans raporu, koç değerlendirme raporu, gelişim alanlarının ham verisi",
        "modul": "analysis.py · video.py · transcribe.py",
    },
    {
        "key": "mufredat", "no": 2, "ikon": "🎓", "ad": "Müfredat ve Mikro-Öğrenme Tasarım Ajanı",
        "temel": "Aralıklı tekrar, geri getirme pratiği, oyunlaştırma",
        "gorev": [
            "Analiz ajanından danışanın zorlandığı “kası” alır (ör. hayır diyememe, delegasyon, geri bildirim)",
            "OpenAlex akademik veri tabanında o konudaki en çok atıf alan çalışmaları tarar",
            "Bulguları Mit mi gerçek mi, eşleştirme, senaryo ve eğer–o zaman planı oyunlarına dönüştürür",
        ],
        "girdi": "Gelişim alanı + danışan profili + bilimsel makaleler",
        "cikti": "Danışanın ekranına otomatik düşen atıflı mikro-eğitim; koça kısa rapor",
        "modul": "training.py · research.py",
    },
    {
        "key": "davranis", "no": 3, "ikon": "🎯", "ad": "Davranış Takip ve Proaktif Eylem Ajanı",
        "temel": "Eğer–o zaman planları (Gollwitzer & Sheeran), dürtme (nudge)",
        "gorev": [
            "Görevleri ve “Eğer [durum] olursa, o zaman [aksiyon]” planlarını hafızaya alır",
            "Planın günü gelince veya ruh hali düşünce kendiliğinden tetiklenir",
            "İzin verilen kanallardan (uygulama, e-posta, WhatsApp) mesaj gönderir, eylemi doğrular, koça raporlar",
        ],
        "girdi": "Görevler, planlar, check-in'ler, paydaş gözlemleri",
        "cikti": "Gerçek zamanlı mesajlar, koç paneli uyarıları, davranış kanıtı",
        "modul": "agent.py · notify.py",
    },
    {
        "key": "kurum", "no": 4, "ikon": "🏢", "ad": "Kurumsal İçgörü ve Anonimleştirme Ajanı",
        "temel": "k-anonimlik (en az 3 kişi), tema kümeleme",
        "gorev": [
            "Kurum içindeki seanslardan ve geri bildirimlerden gelen veriyi süzer",
            "Kişi adlarını, olay ayrıntılarını ve transkripti tamamen çıkarır; 3 kişiden küçük grupları gizler",
            "Benzer temaları kümeleyip birim bazında ortak kültürel riskleri ve program önerilerini çıkarır",
        ],
        "girdi": "Anonim toplu metrikler ve tema listeleri",
        "cikti": "Kurum yöneticisinin gördüğü isimsiz içgörü ve program önerisi paneli",
        "modul": "insights.py",
    },
]


def overview(coach_id: int | None = None) -> list[dict]:
    """Her ajan için son çalışma istatistikleri (koç yalnızca kendi danışanlarını görür)."""
    f, p = ("AND c.coach_id = ?", (coach_id,)) if coach_id is not None else ("", ())

    def n(sql: str) -> int:
        return db.all_rows(sql + f" {f}", p)[0]["n"]

    stats = {
        "analiz": [
            ("Analiz edilen seans", n("SELECT COUNT(*) AS n FROM sessions s JOIN clients c ON c.id = s.client_id "
                                      "WHERE s.status = 'tamamlandi'")),
            ("ICF puanlanan", n("SELECT COUNT(*) AS n FROM sessions s JOIN clients c ON c.id = s.client_id "
                                "WHERE s.icf_json IS NOT NULL")),
        ],
        "mufredat": [
            ("Hazırlanan eğitim", n("SELECT COUNT(*) AS n FROM trainings t JOIN clients c ON c.id = t.client_id "
                                    "WHERE t.status = 'tamamlandi'")),
            ("Kurulan plan", n("SELECT COUNT(*) AS n FROM commitments k JOIN clients c ON c.id = k.client_id WHERE 1=1")),
        ],
        "davranis": [
            ("Proaktif eylem", n("SELECT COUNT(*) AS n FROM agent_actions a JOIN clients c ON c.id = a.client_id "
                                 "WHERE a.applied = 1")),
            ("Gönderilen bildirim", n("SELECT COUNT(*) AS n FROM notifications x JOIN clients c ON c.id = x.client_id "
                                      "WHERE x.channel <> 'uygulama'")),
            ("Paydaş gözlemi", n("SELECT COUNT(*) AS n FROM observations o JOIN clients c ON c.id = o.client_id "
                                 "WHERE o.status = 'yanitlandi'")),
        ],
        "kurum": [
            ("Kurum / birim", n("SELECT COUNT(DISTINCT c.organization_id) AS n FROM clients c "
                                "WHERE c.organization_id IS NOT NULL")),
            ("Kurumdaki danışan", n("SELECT COUNT(*) AS n FROM clients c WHERE c.organization_id IS NOT NULL")),
        ],
    }
    return [{**a, "istatistik": [{"ad": k, "deger": v} for k, v in stats[a["key"]]]} for a in AGENTS]
