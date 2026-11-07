"""LLM'den beklenen yapılandırılmış çıktılar (Pydantic modelleri)."""
from typing import Literal

from pydantic import BaseModel, Field


class SpeakerLabels(BaseModel):
    labels: list[Literal["koc", "danisan"]] = Field(
        description="Her segment için sırayla konuşmacı etiketi; segment sayısı kadar eleman."
    )


class DevelopmentArea(BaseModel):
    baslik: str
    aciklama: str
    kanit: str = Field(description="Transkriptten kısa bir alıntı veya gözlem")


class EmotionMention(BaseModel):
    duygu: str = Field(description="Danışanın KENDİ SÖZLERİYLE ifade ettiği duygu, tek kelime (ör. kaygı, umut, öfke)")
    alinti: str = Field(description="Danışanın bu duyguyu ifade ettiği kısa alıntı (transkriptten aynen)")


class PlanReview(BaseModel):
    plan: str = Field(description="Önceki 'Eğer–o zaman' planı")
    bahsedildi: bool = Field(description="Danışan bu seansta planı uyguladığından/denediğinden bahsetti mi")
    kanit: str = Field(description="Transkriptten kısa kanıt ya da 'bahsedilmedi'")


class SessionReport(BaseModel):
    ozet: str = Field(description="Seansın 4-6 cümlelik özeti")
    danisan_hedefleri: list[str]
    ana_temalar: list[str]
    onceki_seanslarla_baglanti: str = Field(
        description="Önceki seanslara göre ilerleme veya tekrar eden konular; önceki seans yoksa bunu belirt"
    )
    gelisim_alanlari: list[DevelopmentArea] = Field(
        description="Danışanda eksik görülen ve eğitim içeriğiyle desteklenebilecek alanlar"
    )
    danisan_gorevleri: list[str] = Field(description="Danışanın seansta üstlendiği somut adımlar")
    sonraki_seans_onerileri: list[str] = Field(description="Koç için bir sonraki seansa yönelik öneriler")
    duygu_dili: list[EmotionMention] = Field(
        default_factory=list,
        description="Danışanın konuşmasında AÇIKÇA SÖYLEDİĞİ duygular (metne dayalı; yüz, ses tonu veya beden "
                    "dilinden çıkarım YOK). En fazla 5; söylenmediyse boş.")
    plan_degerlendirmesi: list[PlanReview] = Field(
        default_factory=list,
        description="Verilen önceki 'Eğer–o zaman' planlarının her biri için bu seanstaki kanıt; plan verilmediyse boş")


class CompetencyScore(BaseModel):
    kod: str = Field(description="Yetkinlik kodu, ör. C7")
    ad: str
    puan: int = Field(description="1 ile 5 arasında tam sayı")
    gerekce: str
    kanitlar: list[str] = Field(description="Koçun konuşmasından 1-3 kısa alıntı")
    gelistirme_onerisi: str


class ICFEvaluation(BaseModel):
    yetkinlikler: list[CompetencyScore] = Field(description="8 yetkinliğin hepsi, rubrikteki sırayla")
    guclu_yonler: list[str]
    gelisim_onerileri: list[str]
    genel_yorum: str


# --- Eğitim modülü (Coaching -> Training) -----------------------------------


class SearchQuery(BaseModel):
    sorgu: str = Field(description="OpenAlex için 3-6 kelimelik İngilizce akademik arama sorgusu")


class LearningCard(BaseModel):
    ikon: str = Field(description="Kartı temsil eden tek bir emoji")
    baslik: str
    metin: str = Field(description="En fazla 2-3 kısa cümle, sade ve samimi dil")
    kaynak_no: list[int] = Field(description="Dayandığı kaynakların numaraları (1'den başlar); yoksa boş")


class ComicPanel(BaseModel):
    sahne: str = Field(description="Panelin kısa sahne tarifi, ör. 'Toplantı odası, akşamüstü'")
    karakter: str = Field(description="Konuşan karakterin adı")
    ikon: str = Field(description="Karakteri temsil eden tek bir emoji")
    konusma: str = Field(description="Konuşma balonundaki kısa replik")


class QuizQuestion(BaseModel):
    soru: str
    secenekler: list[str] = Field(description="3 veya 4 seçenek")
    dogru_index: int = Field(description="Doğru seçeneğin 0'dan başlayan sırası")
    aciklama: str = Field(description="Doğru cevabın neden doğru olduğu, kaynağa dayanarak")


class WeeklyExperiment(BaseModel):
    baslik: str
    adimlar: list[str] = Field(description="Danışanın bu hafta deneyeceği 3-4 somut adım")


class MythFact(BaseModel):
    ifade: str = Field(description="Yaygın bir inanış ya da bilimsel bir gerçek, tek cümle")
    gercek_mi: bool = Field(description="İfade bilimsel olarak doğruysa true, yaygın bir mit ise false")
    aciklama: str = Field(description="Neden doğru/yanlış olduğu, kaynağa dayanarak 1-2 cümle")
    kaynak_no: list[int] = Field(description="Dayandığı kaynak numaraları; yoksa boş")


class ScenarioOption(BaseModel):
    metin: str = Field(description="Danışanın yapabileceği bir davranış")
    sonuc: str = Field(description="Bu seçimin olası sonucu, 1-2 cümle, yargılamadan")
    en_iyi: bool = Field(description="En yapıcı seçenek ise true (yalnızca biri true)")


class Scenario(BaseModel):
    durum: str = Field(description="Danışanın hayatına benzeyen kısa, gerçekçi bir an (2-3 cümle)")
    secenekler: list[ScenarioOption] = Field(description="3 seçenek")


class MatchPair(BaseModel):
    kavram: str = Field(description="Kısa kavram veya ipucu (1-3 kelime)")
    anlam: str = Field(description="Kavramın günlük hayattaki karşılığı, tek kısa cümle")


class IfThenPlan(BaseModel):
    """Eğer-o zaman planı (implementation intention; Gollwitzer & Sheeran 2006)."""
    durumlar: list[str] = Field(description="'Eğer ...' ile başlayabilecek 3 gerçekçi tetikleyici durum (Eğer kelimesi olmadan, ör. 'Bir ekip üyesi teslim tarihini kaçırırsa')")
    davranislar: list[str] = Field(description="Bu durumlarda yapılabilecek 3 somut, küçük davranış (ör. 'aynı gün birebir konuşurum')")


class MicroLearning(BaseModel):
    baslik: str = Field(description="Akılda kalıcı, eğlenceli bir başlık")
    kanca: str = Field(description="Danışanın kendi durumuna dokunan 1-2 cümlelik giriş")
    kartlar: list[LearningCard] = Field(description="4-6 bilgi kartı")
    cizgi_roman: list[ComicPanel] = Field(
        description="Danışanın durumuna benzeyen bir sahnede yeni davranışı gösteren 4 panellik mini hikâye"
    )
    quiz: list[QuizQuestion] = Field(description="3 soruluk mini quiz")
    mit_gercek: list[MythFact] = Field(description="4 ifadelik 'Mit mi, gerçek mi?' oyunu; en az biri mit, en az biri gerçek")
    senaryo: Scenario = Field(description="'Sen olsan ne yapardın?' seçmeli senaryo")
    eslestirme: list[MatchPair] = Field(description="4 çiftlik eşleştirme oyunu: konunun anahtar kavramları ve günlük karşılıkları")
    eger_o_zaman: IfThenPlan = Field(description="Danışanın kendi 'Eğer ... o zaman ...' planını kuracağı seçenekler")
    haftalik_deneme: WeeklyExperiment
    kapanis: str = Field(description="Cesaretlendirici tek cümlelik kapanış")
    koc_ozeti: str = Field(default="", description="KOÇA 2-3 cümlelik not: eğitim hangi bilimsel bulgulara dayandı, "
                                                    "danışana ne önerildi, sonraki seansta neyi sormalı")


# --- Görsel analiz ----------------------------------------------------------


class ImageAnalysis(BaseModel):
    gorsel_ozeti: str = Field(description="Görselde ne olduğunun 2-3 cümlelik tarafsız özeti")
    gozlemler: list[str] = Field(description="Koçluk açısından anlamlı somut gözlemler")
    temalar: list[str] = Field(description="Görselde öne çıkan hedef, değer, kaygı veya temalar")
    koc_icin_sorular: list[str] = Field(description="Koçun bu görsel üzerinden sorabileceği açık uçlu sorular")
    gelisim_baglantisi: str = Field(description="Danışanın hedefleri ve gelişim süreciyle bağlantısı")


# --- Görsel (video) seans -----------------------------------------------------


class FrameNote(BaseModel):
    kare_no: int = Field(description="1'den başlayan kare numarası")
    gorulen: str = Field(description="Karede görünen içerik, 1-2 cümle (yüzden duygu çıkarımı yok)")


class VideoAnalysis(BaseModel):
    genel_gozlem: str = Field(description="Seansın görsel tarafının 2-3 cümlelik özeti")
    kareler: list[FrameNote] = Field(description="Her kare için bir not, sırasıyla")
    paylasilan_materyaller: list[str] = Field(description="Ekran paylaşımı, beyaz tahta, not, çizim gibi materyaller ve içerikleri; yoksa boş")
    koc_icin_notlar: list[str] = Field(description="Görsellerden koç için çıkan kısa notlar")
    konusmayla_baglanti: str = Field(description="Görsellerin konuşulanlarla bağlantısı")


# --- Kurumsal içgörü (Behavioral AI, kurum düzeyi) ----------------------------


class OrgInsight(BaseModel):
    genel_durum: str = Field(description="Kurum/birimdeki koçluk sürecinin 3-5 cümlelik değerlendirmesi")
    ortak_temalar: list[str] = Field(description="Danışanlarda tekrar eden gelişim temaları")
    riskler: list[str] = Field(description="Dikkat gerektiren örüntüler (kişi adı vermeden)")
    kurumsal_oneriler: list[str] = Field(description="Kuruma yönelik eğitim, program veya süreç önerileri")
    izlenecek_gostergeler: list[str] = Field(description="Davranış değişimini ölçmek için izlenecek göstergeler")


# --- Aktif ajan -----------------------------------------------------------


class AgentDecision(BaseModel):
    tetik_kodu: str = Field(description="Karar verilen tetiğin kodu, listede verildiği gibi")
    uygula: bool = Field(description="Bu eylem şimdi yapılmalı mı? Gereksiz/rahatsız edici ise false")
    mesaj: str = Field(description="Hedefe gidecek kısa mesaj (uygula=false ise boş bırak)")
    gerekce: str = Field(description="Kararın 1 cümlelik gerekçesi (koç bu kaydı görecek)")


class AgentPlan(BaseModel):
    kararlar: list[AgentDecision] = Field(description="Verilen her tetik için tam olarak bir karar")


class PreSessionBrief(BaseModel):
    danisan_durumu: str = Field(description="Danışanın şu ana kadarki süreci, 3-5 cümle")
    takip_edilecek_konular: list[str] = Field(description="Önceki görevler ve açık kalan konular")
    onerilen_sorular: list[str] = Field(description="Seansta sorulabilecek güçlü, açık uçlu sorular")
    dikkat_noktalari: list[str] = Field(description="Koçun dikkat etmesi gereken örüntüler veya riskler")
