"""ICF Temel Yetkinlik Modeli (2019 güncellemesi, 8 yetkinlik) ve puanlama rubriği.

Not: Bu, akreditasyon değerlendirmesinin yerine geçmez; koça gelişim amaçlı
ön değerlendirme sunar. Rubrik ileride ICF PCC Markers ile ayrıntılandırılabilir.
"""

COMPETENCIES = [
    ("A1", "Etik Uygulama Sergiler",
     "Gizlilik, sınırlar ve koçluk etiğine uyum; koçluğu terapi/danışmanlıktan ayırır."),
    ("A2", "Koçluk Zihniyetini Benimser",
     "Açık, meraklı, esnek ve danışan odaklı tutum; danışanın kendi seçimlerinden sorumlu olduğunu kabul eder."),
    ("B3", "Anlaşmaları Belirler ve Sürdürür",
     "Seansın hedefini, başarı ölçütünü ve odak konusunu danışanla birlikte netleştirir."),
    ("B4", "Güven ve Güvenlik Ortamı Oluşturur",
     "Danışanın kimliğine, algısına ve duygularına saygı gösterir; destekleyici, güvenli bir alan yaratır."),
    ("B5", "Varlığını Sürdürür",
     "Odaklı, dikkatli ve sakin kalır; sessizliğe ve belirsizliğe alan tanır, acele etmez."),
    ("C6", "Aktif Dinler",
     "Danışanın söylediğine ve söylemediğine odaklanır; yansıtır, özetler, danışanın kelimelerini kullanır."),
    ("C7", "Farkındalık Uyandırır",
     "Güçlü ve açık uçlu sorular, metafor ve meydan okuma ile yeni bakış açıları ortaya çıkarır; tavsiye vermek yerine keşfettirir."),
    ("D8", "Danışanın Gelişimini Kolaylaştırır",
     "Farkındalığı eyleme dönüştürür; somut adımlar, hesap verebilirlik ve kapanış konusunda danışanla birlikte çalışır."),
]

SCALE = """Puan ölçeği (1-5):
1 = Gözlenmedi veya yetkinliğe aykırı davranış var
2 = Zayıf / tutarsız
3 = Yeterli (temel düzeyde gözlendi)
4 = İyi (tutarlı ve etkili)
5 = Örnek düzeyde (ustalıkla, derinlikli)"""


def rubric_text() -> str:
    lines = [f"{code} - {name}: {desc}" for code, name, desc in COMPETENCIES]
    return "\n".join(lines) + "\n\n" + SCALE
