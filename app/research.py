"""Bilimsel kaynak tarama: OpenAlex (ücretsiz, API anahtarı gerektirmez, 250M+ akademik yayın).

Akış: gelişim alanı -> (LLM) İngilizce akademik arama sorgusu -> OpenAlex -> en çok atıf
alan ilgili makaleler -> özetleri eğitim içeriği üretimine kaynak olarak verilir.
"""
import time

import httpx

from .config import OPENALEX_API_KEY, RESEARCH_MODE

OPENALEX_URL = "https://api.openalex.org/works"

SAMPLE_PAPERS = [
    {
        "title": "The power of feedback",
        "year": 2007,
        "authors": "J. Hattie, H. Timperley",
        "url": "https://doi.org/10.3102/003465430298487",
        "cited_by": 15000,
        "abstract": "Feedback is one of the most powerful influences on learning and achievement, "
                    "but this impact can be either positive or negative depending on its type and timing.",
    },
    {
        "title": "The effects of feedback interventions on performance: A historical review, "
                 "a meta-analysis, and a preliminary feedback intervention theory",
        "year": 1996,
        "authors": "A. N. Kluger, A. DeNisi",
        "url": "https://doi.org/10.1037/0033-2909.119.2.254",
        "cited_by": 9000,
        "abstract": "Feedback interventions improved performance on average, but over one-third "
                    "of them decreased performance; feedback directed at the task is more effective "
                    "than feedback directed at the self.",
    },
]


def search_papers(query: str, limit: int = 5) -> list[dict]:
    if RESEARCH_MODE == "mock":
        return SAMPLE_PAPERS[:limit]

    params = {
        "search": query,
        "filter": "has_abstract:true,from_publication_date:1990-01-01",
        "per-page": 25,
        "select": "id,title,publication_year,doi,cited_by_count,authorships,abstract_inverted_index",
    }
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY

    response = None
    for attempt in range(3):
        try:
            response = httpx.get(OPENALEX_URL, params=params, timeout=30)
        except httpx.HTTPError:
            response = None
        if response is not None and response.status_code == 200:
            break
        time.sleep(3 * (attempt + 1))  # 429 (kota) veya geçici hata: kısa bekle, tekrar dene
    if response is None or response.status_code != 200:
        # Kaynak bulunamazsa eğitim yine üretilir (kaynaksız, temkinli içerik)
        print(f"OpenAlex'e ulaşılamadı ({response.status_code if response else 'bağlantı hatası'}). "
              "Ücretsiz anahtar için: https://openalex.org/settings/api -> OPENALEX_API_KEY")
        return []
    works = [w for w in response.json().get("results", []) if w.get("title")]
    # Alakaya göre gelen ilk 25 sonuçtan en çok atıf alanları seç (kalite filtresi)
    works.sort(key=lambda w: w.get("cited_by_count") or 0, reverse=True)
    return [_paper(w) for w in works[:limit]]


def _paper(work: dict) -> dict:
    authors = [a["author"]["display_name"] for a in work.get("authorships", [])[:3] if a.get("author")]
    if len(work.get("authorships", [])) > 3:
        authors.append("vd.")
    return {
        "title": work["title"],
        "year": work.get("publication_year"),
        "authors": ", ".join(authors),
        "url": work.get("doi") or work.get("id"),
        "cited_by": work.get("cited_by_count") or 0,
        "abstract": _abstract(work.get("abstract_inverted_index"))[:1500],
    }


def _abstract(inverted: dict | None) -> str:
    """OpenAlex özetleri 'kelime -> pozisyonlar' biçiminde verir; düz metne çevir."""
    if not inverted:
        return ""
    positions = [(pos, word) for word, poss in inverted.items() for pos in poss]
    return " ".join(word for _, word in sorted(positions))
