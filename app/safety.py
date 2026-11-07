"""Koçsuz mod için güvenlik kuralları.

Arada insan koç olmadığı için iki katmanlı kontrol yapılır:
  1. Kural tabanlı (hızlı, yapay zekâya bağlı değil): kendine zarar verme / intihar ifadeleri.
  2. Yapay zekâ: her cevapta risk düzeyi ("yuksek" ise aynı kriz akışı).

Kriz anında ajan plan veya tavsiye vermez; sabit, önceden yazılmış bir destek mesajı gösterilir
(acil durumda 112, güvenilen bir yakın, ruh sağlığı uzmanı). Tanı koymaz, ilaç konuşmaz.
"""
import re

_PATTERNS = [
    r"intihar", r"kendimi (?:öldür|oldur|asa|as\b|kes)", r"kendime zarar", r"kendime kıy", r"canıma kıy",
    r"ölmek ist", r"olmek ist", r"ölsem\b", r"ölsem daha", r"yaşamak istemiyor", r"yasamak istemiyor",
    r"yaşamanın (?:bir )?anlamı yok", r"hayatıma son", r"hayatima son", r"bilek(?:ler)?imi kes",
    r"bu dünyadan gitmek", r"herkes bensiz daha iyi", r"artık var olmak istemiyor", r"uyuyup uyanmamak",
    r"birini öldür", r"onu öldür", r"zarar vereceğim",
]
_RE = re.compile("|".join(_PATTERNS))


def _norm(text: str) -> str:
    return (text or "").replace("I", "ı").replace("İ", "i").lower()


def is_crisis(text: str) -> bool:
    return bool(_RE.search(_norm(text)))


CRISIS_MESSAGE = (
    "Bunu paylaştığın için teşekkür ederim. Şu an en önemli şey güvende olman; bu konuda tek başıma yardım edemem:\n"
    "• Tehlikedeysen hemen 112'yi ara ya da en yakın acil servise git.\n"
    "• Güvendiğin birine şimdi ulaş.\n"
    "• Bir psikolog, psikiyatrist ya da aile hekimiyle görüş.\n"
    "Hazır olduğunda buradayım."
)

DISCLAIMER = "Farkora terapi değildir. Acil durumda 112'yi arayın."
