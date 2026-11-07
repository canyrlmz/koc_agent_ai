"""LLM katmanı. Uygulamanın geri kalanı sadece `structured()` fonksiyonunu çağırır.

- claude: Anthropic API (ANTHROPIC_API_KEY gerekir)
- gemini: Google AI Studio (GEMINI_API_KEY; ücretsiz katman var, ama ücretsiz katmanda
          veriler Google tarafından kullanılabilir: gerçek danışan verisi göndermeyin)
- mock:   API anahtarı olmadan sahte ama şemaya uygun cevaplar (geliştirme/test için)
"""
from typing import TypeVar

from pydantic import BaseModel

from . import schemas
from .config import CLAUDE_MODEL, GEMINI_API_KEY, GEMINI_FALLBACK_MODELS, GEMINI_MODEL, LLM_PROVIDER

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


Image = tuple[bytes, str]  # (dosya içeriği, mime türü)


def structured(system: str, prompt: str, schema: type[T], effort: str = "medium",
               images: list[Image] | None = None) -> T:
    if LLM_PROVIDER == "mock":
        return _mock(schema, prompt)
    if LLM_PROVIDER == "claude":
        return _claude(system, prompt, schema, effort, images or [])
    if LLM_PROVIDER == "gemini":
        return _gemini(system, prompt, schema, images or [])
    raise LLMError(f"Bilinmeyen LLM_PROVIDER: {LLM_PROVIDER}")


# --- Gemini (Google AI Studio; ücretsiz katman var) ---------------------------

_gemini_client = None
_exhausted: dict = {}  # bugün kotası dolan modeller


def _gemini(system: str, prompt: str, schema: type[T], images: list[Image]) -> T:
    import time

    from google import genai
    from google.genai import errors, types

    global _gemini_client
    if _gemini_client is None:
        if not GEMINI_API_KEY:
            raise LLMError("GEMINI_API_KEY boş. Anahtarı .env dosyasına ekleyin.")
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)

    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=schema,
    )
    contents = [types.Part.from_bytes(data=data, mime_type=mime) for data, mime in images] + [prompt]

    # Ücretsiz katmanda her modelin kendi günlük kotası var: ana model dolunca sıradakine geçilir.
    today = time.strftime("%Y-%m-%d")
    if _exhausted.get("day") != today:
        _exhausted.clear()
        _exhausted["day"] = today
    models = [m for m in [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS] if m not in _exhausted]
    if not models:
        raise LLMError("Bugünkü ücretsiz Gemini kotası tüm modellerde doldu; yarın sıfırlanır.")

    response, last_error = None, None
    for model in models:
        for attempt in range(3):
            try:
                response = _gemini_client.models.generate_content(model=model, contents=contents, config=config)
                break
            except errors.ClientError as e:
                text = str(e)
                if e.code in (400, 401, 403) and "API key" in text:
                    raise LLMError("Gemini API anahtarı geçersiz (GEMINI_API_KEY).") from e
                if e.code == 429 and "PerDay" not in text and "per day" not in text and attempt < 2:
                    time.sleep(15 * (attempt + 1))  # dakikalık sınır: kısa bekle, aynı modeli dene
                    continue
                if e.code in (404, 429):  # model yok ya da günlük kotası doldu: sıradaki modele geç
                    _exhausted[model] = True
                    last_error = e
                    break
                raise LLMError(f"Gemini API hatası ({e.code}): {e.message}") from e
            except errors.ServerError as e:
                last_error = e
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                break  # yoğunluk sürüyorsa sıradaki modeli dene
        if response is not None:
            break
    if response is None:
        if isinstance(last_error, errors.ServerError):
            raise LLMError("Gemini şu an çok yoğun; biraz sonra tekrar deneyin.") from last_error
        raise LLMError("Bugünkü ücretsiz Gemini kotası tüm modellerde doldu; yarın sıfırlanır.") from last_error

    if isinstance(response.parsed, schema):
        return response.parsed
    if not response.text:
        raise LLMError("Gemini boş cevap döndürdü (içerik filtresine takılmış olabilir).")
    try:
        return schema.model_validate_json(response.text)
    except ValueError as e:
        raise LLMError("Gemini şemaya uygun çıktı döndürmedi.") from e


# --- Claude ---------------------------------------------------------------

_client = None


def _claude_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def _claude(system: str, prompt: str, schema: type[T], effort: str, images: list[Image]) -> T:
    import base64

    import anthropic

    content = [
        {"type": "image", "source": {"type": "base64", "media_type": mime,
                                     "data": base64.standard_b64encode(data).decode("utf-8")}}
        for data, mime in images
    ] + [{"type": "text", "text": prompt}]
    try:
        # Uzun transkriptlerde zaman aşımı olmasın diye streaming kullanılır.
        # fallbacks="default": güvenlik sınıflandırıcısı reddederse istek sunucu tarafında
        # uygun bir modele yönlendirilir (koçluk konuşmaları bazen hassas konular içerir).
        with _claude_client().beta.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=32000,
            system=system,
            messages=[{"role": "user", "content": content}],
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
            output_format=schema,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError as e:
        raise LLMError("API anahtarı geçersiz veya eksik (ANTHROPIC_API_KEY).") from e
    except anthropic.RateLimitError as e:
        raise LLMError("API hız sınırına takıldı, biraz sonra tekrar deneyin.") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude API hatası ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Claude API'ye bağlanılamadı (internet bağlantısını kontrol edin).") from e

    if message.stop_reason == "refusal":
        raise LLMError("Model bu içeriği analiz etmeyi reddetti.")
    if message.stop_reason == "max_tokens":
        raise LLMError("Model çıktısı uzunluk sınırına takıldı.")
    if message.parsed_output is None:
        raise LLMError("Model yapılandırılmış çıktı döndürmedi.")
    return message.parsed_output


# --- Mock -----------------------------------------------------------------


def _mock(schema: type[T], prompt: str) -> T:
    if schema is schemas.SpeakerLabels:
        n = prompt.count("\n[")  # her segment "[i] ..." satırı olarak gönderilir
        return schemas.SpeakerLabels(labels=["koc" if i % 2 == 0 else "danisan" for i in range(n)])

    if schema is schemas.SessionReport:
        has_history = "ÖNCEKİ SEANS" in prompt
        return schemas.SessionReport(
            ozet="(Örnek) Danışan, ekibine geri bildirim vermekte zorlandığını ve bunun altında "
                 "sevilme ihtiyacının yattığını fark etti. Seans somut bir eylem planıyla kapandı.",
            danisan_hedefleri=["Ekibe zamanında ve net geri bildirim vermek"],
            ana_temalar=["Geri bildirim", "Onaylanma ihtiyacı", "Liderlik"],
            onceki_seanslarla_baglanti=(
                "(Örnek) Önceki seansta da çatışmadan kaçınma teması görülmüştü; bu seansta "
                "danışan bunu ilk kez kendisi adlandırdı."
                if has_history else "Bu danışanla yapılan ilk seans."
            ),
            gelisim_alanlari=[
                schemas.DevelopmentArea(
                    baslik="Yapıcı geri bildirim verme",
                    aciklama="Geri bildirimi ertelemek ekip performansını ve güveni etkiliyor.",
                    kanit="“ya hiç söylemiyorum ya da çok geç söylüyorum”",
                )
            ],
            danisan_gorevleri=["Perşembe günü Ayşe'ye net bir geri bildirim vermek"],
            sonraki_seans_onerileri=["Geri bildirim deneyiminin nasıl geçtiğini sorun"],
            duygu_dili=[
                schemas.EmotionMention(duygu="kaygı", alinti="“söylersem kırılır diye çok geriliyorum”"),
                schemas.EmotionMention(duygu="suçluluk", alinti="“ekibe haksızlık ediyormuşum gibi hissediyorum”"),
                schemas.EmotionMention(duygu="umut", alinti="“bu sefer deneyebilirim gibi geliyor”"),
            ],
            plan_degerlendirmesi=[
                schemas.PlanReview(plan=m.split(" |")[0].strip(), bahsedildi=True,
                                   kanit="(Örnek) “Burak teslimi kaçırınca aynı gün konuştum.”")
                for m in prompt.split("PLAN: ")[1:2]
            ] if "PLAN: " in prompt else [],
        )

    if schema is schemas.ICFEvaluation:
        from .icf import COMPETENCIES

        demo_scores = [4, 4, 4, 4, 3, 4, 5, 4]
        return schemas.ICFEvaluation(
            yetkinlikler=[
                schemas.CompetencyScore(
                    kod=code, ad=name, puan=score,
                    gerekce="(Örnek) Mock modda üretilmiş açıklama.",
                    kanitlar=["“Bu korku size neyi koruyormuş gibi geliyor?”"],
                    gelistirme_onerisi="(Örnek) Danışanın kelimelerini daha sık yansıtın.",
                )
                for (code, name, _), score in zip(COMPETENCIES, demo_scores)
            ],
            guclu_yonler=["Açık uçlu, farkındalık yaratan sorular"],
            gelisim_onerileri=["Seans başında başarı ölçütünü daha net belirleyin"],
            genel_yorum="(Örnek) Mock mod. Gerçek değerlendirme için LLM_PROVIDER=claude yapın.",
        )

    if schema is schemas.PreSessionBrief:
        return schemas.PreSessionBrief(
            danisan_durumu="(Örnek) Danışan geri bildirim konusunda çalışıyor.",
            takip_edilecek_konular=["Ayşe ile yapılacak geri bildirim görüşmesi"],
            onerilen_sorular=["Geri bildirimi verdiğinizde kendinizde neyi fark ettiniz?"],
            dikkat_noktalari=["Onaylanma ihtiyacı teması tekrar ediyor"],
        )

    if schema is schemas.AgentPlan:
        import re

        templates = {
            "takip": "(Örnek) Merhaba! Seansımızda net bir adım belirlediniz. Bu adımı düşündüğünüzde "
                     "şu an içinizden ne geçiyor?",
            "hatirlatma": "(Örnek) Küçük bir hatırlatma: üstlendiğiniz görevin zamanı yaklaşıyor. "
                          "Bunu gerçekleştirmek için neye ihtiyacınız var?",
            "checkin": "(Örnek) Bir haftadır haberleşmedik. Bu hafta kendinizi 1-5 arası nasıl hissediyorsunuz?",
            "uyari": "(Örnek) Danışanın ruh hali belirgin şekilde düştü. Seansı öne almayı veya kısa bir "
                     "görüşme yapmayı değerlendirin.",
            "egitim": "(Örnek) Seanstaki gelişim alanı için kişiye özel bir eğitim hazırladım.",
            "plan": "(Örnek) Planınızı hatırlatmak istedim: “Eğer bir ekip üyesi teslimi kaçırırsa, o zaman aynı gün "
                    "birebir konuşurum.” Bu durum yaşandı mı, ne yaptınız? Farkora'daki Planlarım bölümüne kısaca yazabilirsiniz.",
        }
        found = re.findall(r"tetik_kodu=(\S+) \| tür=(\w+)", prompt)
        return schemas.AgentPlan(kararlar=[
            schemas.AgentDecision(tetik_kodu=key, uygula=True, mesaj=templates[kind],
                                  gerekce="(Örnek) Mock modda tüm tetikler uygulanır.")
            for key, kind in found
        ])

    if schema is schemas.VideoAnalysis:
        import re

        n = int((re.search(r"(\d+) kare var", prompt) or [0, 1])[1])
        return schemas.VideoAnalysis(
            genel_gozlem="(Örnek) Seansın ortasında danışan, kameraya el yazısıyla hazırladığı haftalık planı gösterdi.",
            kareler=[schemas.FrameNote(kare_no=i + 1, gorulen="(Örnek) Kamera görüntüsü; masada bir defter görünüyor.")
                     for i in range(n)],
            paylasilan_materyaller=["(Örnek) El yazısı haftalık plan: uyku saati, yürüyüş günleri"],
            koc_icin_notlar=["Planı bir sonraki seansta birlikte gözden geçirin"],
            konusmayla_baglanti="(Örnek) Plan, danışanın seansta üstlendiği görevlerle örtüşüyor.",
        )

    if schema is schemas.ImageAnalysis:
        return schemas.ImageAnalysis(
            gorsel_ozeti="(Örnek) Danışanın hazırladığı, kariyer ve aile hedeflerini içeren bir hedef panosu.",
            gozlemler=["Panonun büyük kısmı iş hedeflerine ayrılmış", "Dinlenme ve sağlıkla ilgili tek bir görsel var"],
            temalar=["Kariyer ilerlemesi", "İş-yaşam dengesi"],
            koc_icin_sorular=["Panoya baktığınızda en çok hangi parçası size enerji veriyor?",
                              "Panoda eksik olduğunu düşündüğünüz bir şey var mı?"],
            gelisim_baglantisi="(Örnek) Liderlik hedefleriyle uyumlu; denge teması seansta ele alınabilir.",
        )

    if schema is schemas.OrgInsight:
        return schemas.OrgInsight(
            genel_durum="(Örnek) Birimdeki danışanlar düzenli seanslara katılıyor; görev tamamlama orta düzeyde.",
            ortak_temalar=["Geri bildirim verme", "Öz-güven"],
            riskler=["Bir danışanın ruh hali son iki check-in'de düştü"],
            kurumsal_oneriler=["Yöneticilere yönelik yapıcı geri bildirim atölyesi düzenlenmesi"],
            izlenecek_gostergeler=["Görev tamamlama oranı", "Check-in ruh hali ortalaması"],
        )

    if schema is schemas.SearchQuery:
        return schemas.SearchQuery(sorgu="constructive feedback leadership")

    if schema is schemas.MicroLearning:
        return schemas.MicroLearning(
            baslik="(Örnek) Geri Bildirim Bir Hediyedir 🎁",
            kanca="Söylemediğin her geri bildirim, ekibinden esirgediğin bir gelişim fırsatı olabilir.",
            kartlar=[
                schemas.LearningCard(ikon="🎯", baslik="Göreve odaklan, kişiye değil",
                                     metin="Kişiliğe değil, davranışa ve işe yönelik geri bildirim daha etkilidir.",
                                     kaynak_no=[2]),
                schemas.LearningCard(ikon="⏱️", baslik="Zamanlama her şeydir",
                                     metin="Geri bildirim olaydan kısa süre sonra verildiğinde öğrenmeyi daha çok destekler.",
                                     kaynak_no=[1]),
                schemas.LearningCard(ikon="🧭", baslik="Üç soru",
                                     metin="Nereye gidiyoruz? Ne durumdayız? Sırada ne var? İyi geri bildirim bu üçünü yanıtlar.",
                                     kaynak_no=[1]),
                schemas.LearningCard(ikon="🤝", baslik="Netlik bir nezakettir",
                                     metin="Belirsiz mesajlar ilişkiyi korumaz; kafa karışıklığı yaratır.",
                                     kaynak_no=[]),
            ],
            cizgi_roman=[
                schemas.ComicPanel(sahne="Toplantı sonrası koridor", karakter="Elif", ikon="👩‍💼",
                                   konusma="Can, iki dakikan var mı? Raporla ilgili konuşmak istiyorum."),
                schemas.ComicPanel(sahne="Küçük toplantı odası", karakter="Can", ikon="👨‍💻",
                                   konusma="Tabii... Bir sorun mu var?"),
                schemas.ComicPanel(sahne="Elif sakin ve net", karakter="Elif", ikon="👩‍💼",
                                   konusma="Rapor iki gün gecikti ve müşteri bekledi. Bir dahakine nasıl önleyebiliriz?"),
                schemas.ComicPanel(sahne="Can rahatlamış", karakter="Can", ikon="👨‍💻",
                                   konusma="Haklısın. Ara teslim tarihi koyalım, ben de takvimi paylaşırım."),
            ],
            quiz=[
                schemas.QuizQuestion(
                    soru="Hangisi daha etkili bir geri bildirimdir?",
                    secenekler=["Sen hep dağınıksın.", "Bu raporda iki tablo eksikti.", "Biraz daha dikkat et."],
                    dogru_index=1,
                    aciklama="Somut ve göreve odaklı geri bildirim performansı daha çok artırır [2].",
                ),
            ],
            mit_gercek=[
                schemas.MythFact(ifade="Geri bildirimi ertelemek ilişkiyi korur.", gercek_mi=False,
                                 aciklama="Ertelenen geri bildirim çoğu zaman sorunu büyütür ve güveni azaltır.", kaynak_no=[1]),
                schemas.MythFact(ifade="Göreve odaklanan geri bildirim, kişiye odaklanandan daha etkilidir.", gercek_mi=True,
                                 aciklama="Meta-analizler, kişiliğe yönelik geri bildirimin performansı düşürebildiğini gösteriyor.", kaynak_no=[2]),
                schemas.MythFact(ifade="Her geri bildirim performansı artırır.", gercek_mi=False,
                                 aciklama="Geri bildirim müdahalelerinin üçte birinden fazlası performansı düşürmüş.", kaynak_no=[2]),
                schemas.MythFact(ifade="Zamanında verilen geri bildirim öğrenmeyi güçlendirir.", gercek_mi=True,
                                 aciklama="Olaydan kısa süre sonra verilen geri bildirim daha kolay uygulanır.", kaynak_no=[1]),
            ],
            senaryo=schemas.Scenario(
                durum="(Örnek) Toplantıda Burak sunumunu yine son dakika hazırladı ve müşteri sorulara yanıt alamadı. Toplantıdan çıkıyorsunuz.",
                secenekler=[
                    schemas.ScenarioOption(metin="Hiçbir şey söylemem, bir dahakine düzelir.", sonuc="Sorun tekrar eder; Burak neyin eksik olduğunu bilmez.", en_iyi=False),
                    schemas.ScenarioOption(metin="Ekibin önünde hemen uyarırım.", sonuc="Mesaj net ama Burak kendini savunmaya geçebilir.", en_iyi=False),
                    schemas.ScenarioOption(metin="Aynı gün birebir konuşur, somut örnek verip ne yapabileceğini sorarım.", sonuc="Net, zamanında ve saygılı; Burak çözümün parçası olur. 🎯", en_iyi=True),
                ],
            ),
            eslestirme=[
                schemas.MatchPair(kavram="Zamanında", anlam="Olaydan sonraki 48 saat içinde konuşmak"),
                schemas.MatchPair(kavram="Somut", anlam="“Raporda iki tablo eksikti” gibi örnek vermek"),
                schemas.MatchPair(kavram="Göreve odaklı", anlam="Kişiyi değil davranışı konuşmak"),
                schemas.MatchPair(kavram="İleriye dönük", anlam="“Bir dahakine ne yapabiliriz?” diye sormak"),
            ],
            eger_o_zaman=schemas.IfThenPlan(
                durumlar=["Bir ekip üyesi teslim tarihini kaçırırsa", "Toplantıda bir sorun fark edersem",
                          "Geri bildirim vermeyi ertelemek istediğimi fark edersem"],
                davranislar=["aynı gün 10 dakikalık birebir görüşme isterim",
                             "önce somut örneği, sonra beklentimi söylerim",
                             "“Bir dahakine ne yapabiliriz?” diye sorarım"],
            ),
            haftalik_deneme=schemas.WeeklyExperiment(
                baslik="48 saat kuralı",
                adimlar=["Geri bildirim vereceğin durumu seç", "Ne söyleyeceğini 3 cümleyle yaz",
                         "48 saat içinde, sakin bir anda konuş", "Sonrasında ne hissettiğini not al"],
            ),
            kapanis="(Örnek) Mock mod. Her net cümle, liderliğine atılmış bir adım. 🚀",
            koc_ozeti="(Örnek) Eğitim, göreve odaklı ve zamanında geri bildirimin performansı artırdığını gösteren "
                      "meta-analizlere [1][2] dayanıyor. Danışana 48 saat kuralı ve bir eğer–o zaman planı önerildi. "
                      "Sonraki seansta planın ilk denemesinin nasıl geçtiğini sorun.",
        )

    raise LLMError(f"Mock cevap tanımlı değil: {schema.__name__}")
