"""
yield_scraper.py  —  Scraping yield bond da investing.com
Dipendenze: pip install requests beautifulsoup4 lxml
"""

import time
import datetime
import requests
from bs4 import BeautifulSoup

# ── Headers che simulano un browser reale ──────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.investing.com/",
}

# ── Mappa nome → slug URL investing.com ───────────────────
YIELD_URLS = {
    # Italia
    "IT 2Y":  "italy-2-year-bond-yield",
    "IT 10Y": "italy-10-year-bond-yield",
    # Germania
    "DE 2Y":  "germany-2-year-bond-yield",
    "DE 10Y": "germany-10-year-bond-yield",
    # Spagna
    "ES 2Y":  "spain-2-year-bond-yield",       
    "ES 10Y": "spain-10-year-bond-yield",
    # Francia
    "FR 2Y":  "france-2-year-bond-yield",
    "FR 10Y": "france-10-year-bond-yield",
    # UK
    "UK 2Y":  "uk-2-year-bond-yield",  
    "UK 10Y": "uk-10-year-bond-yield",
    # US
    "US 2Y":  "u.s.-2-year-bond-yield",
    "US 10Y": "u.s.-10-year-bond-yield",
    # Giappone
    "JP 2Y":  "japan-2-year-bond-yield",        
    "JP 10Y": "japan-10-year-bond-yield",
}

BASE_URL = "https://www.investing.com/rates-bonds/{slug}-historical-data"


def _parse_table(html: str) -> list[dict]:
    """Estrae le righe dalla tabella historical data di investing.com."""
    soup = BeautifulSoup(html, "lxml")

    # La tabella ha id 'curr_table' oppure è la prima tabella con dati
    table = soup.find("table", {"id": "curr_table"})
    if not table:
        # Fallback: cerca la tabella con colonna 'Price'
        for t in soup.find_all("table"):
            headers = [th.get_text(strip=True) for th in t.find_all("th")]
            if "Price" in headers:
                table = t
                break

    if not table:
        return []

    rows = []
    for tr in table.find("tbody").find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) >= 2:
            try:
                date_str = cells[0]   # es. "Mar 09, 2026"
                price    = float(cells[1].replace(",", ""))
                rows.append({"date": date_str, "price": price})
            except (ValueError, IndexError):
                continue
    return rows


def fetch_yield(slug: str, retries: int = 3, delay: float = 1.5) -> dict | None:
    """
    Fetcha la pagina historical-data e restituisce:
      { "current": float, "yesterday": float, "week_ago": float | None }
    oppure None in caso di errore.
    """
    url = BASE_URL.format(slug=slug)
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                rows = _parse_table(resp.text)
                if len(rows) < 2:
                    return None
                current   = rows[0]["price"]
                yesterday = rows[1]["price"]
                # 1 settimana fa: cerca la riga con data >= 5 giorni fa
                today_dt  = datetime.date.today()
                cutoff    = today_dt - datetime.timedelta(days=5)
                week_ago  = None
                for r in rows[2:]:
                    try:
                        d = datetime.datetime.strptime(r["date"], "%b %d, %Y").date()
                        if d <= cutoff:
                            week_ago = r["price"]
                            break
                    except ValueError:
                        continue
                return {"current": current, "yesterday": yesterday, "week_ago": week_ago}
            elif resp.status_code == 429:
                time.sleep(delay * 3)
            else:
                time.sleep(delay)
        except Exception:
            time.sleep(delay)
    return None


def fetch_all_yields(progress_callback=None) -> dict:
    """
    Fetcha tutti i bond in YIELD_URLS con un piccolo delay tra le richieste.
    Ritorna dict: { "YIELD_IT 2Y": {...}, "YIELD_DE 10Y": {...}, ... }
    """
    result = {}
    total  = len(YIELD_URLS)
    for i, (name, slug) in enumerate(YIELD_URLS.items()):
        if progress_callback:
            progress_callback(i + 1, total, name)
        data = fetch_yield(slug)
        result[f"YIELD_{name}"] = data
        # Piccolo delay per non stressare il server
        time.sleep(1.2)
    return result
