"""
eco_calendar.py  —  Fetches economic calendar from investing.com
Dependencies: pip install requests beautifulsoup4 lxml

HTML structure (from inspection):
  <tr id="eventRowId_545672" class="js-event-item" data-event-datetime="2026/04/27 06:00:00">
    <td class="first left time js-time">06:00</td>
    <td class="left flagCur noWrap">
      <span title="Germany" class="ceFlags Germany" data-img_key="Germany">&nbsp;</span> EUR
    </td>
    <td class="left textNum sentiment noWrap" title="Moderate Volatility Expected">
      <i class="grayFullBullishIcon"></i>
      <i class="grayFullBullishIcon"></i>
      <i class="grayEmptyBullishIcon"></i>
    </td>
    <td class="left event" title="..."><a href="...">GfK German Consumer Climate (May)</a></td>
    <td class="bold act redFont event-545672-actual" id="eventActual_545672">-33.3</td>
    <td class="fore event-545672-forecast"          id="eventForecast_545672">-30.2</td>
    <td class="prev redFont event-545672-previous"  id="eventPrevious_545672">
      <span title="Revised From -28.0">-28.1</span>
    </td>
  </tr>
"""

import re
import datetime
import requests
from bs4 import BeautifulSoup

# ── Country flag title → ISO code ────────────────────────────────────
FLAG_TITLE_MAP = {
    "United States":    "US",
    "United Kingdom":   "UK",
    "Euro Zone":        "EU",
    "European Union":   "EU",
    "Germany":          "DE",
    "France":           "FR",
    "Italy":            "IT",
    "Spain":            "ES",
    "Japan":            "JP",
    "China":            "CN",
    "Switzerland":      "CH",
    "Australia":        "AU",
    "Canada":           "CA",
    "New Zealand":      "NZ",
    "India":            "IN",
    "Brazil":           "BR",
    "South Korea":      "KR",
    "Sweden":           "SE",
    "Norway":           "NO",
    "Denmark":          "DK",
    "Singapore":        "SG",
    "Hong Kong":        "HK",
    "Mexico":           "MX",
    "South Africa":     "ZA",
    "Portugal":         "PT",
    "Netherlands":      "NL",
    "Belgium":          "BE",
    "Austria":          "AT",
    "Greece":           "GR",
    "Finland":          "FI",
    "Ireland":          "IE",
    "Czech Republic":   "CZ",
    "Poland":           "PL",
    "Hungary":          "HU",
    "Turkey":           "TR",
    "Russia":           "RU",
    "Indonesia":        "ID",
}

COUNTRY_CODES     = ["5","17","6","4","12","11","26","25","35","39","14","72","43","37"]
IMPORTANCE_FILTER = ["1","2","3"]

IMPORTANCE_COLOR = {0: "#7D8590", 1: "#7D8590", 2: "#D4A017", 3: "#F85149"}
IMPORTANCE_LABEL = {0: "", 1: "Low", 2: "Medium", 3: "High"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer":          "https://www.investing.com/economic-calendar/",
    "Content-Type":     "application/x-www-form-urlencoded",
    "Origin":           "https://www.investing.com",
    "Accept":           "application/json, text/javascript, */*; q=0.01",
    "Accept-Language":  "en-US,en;q=0.9",
}

API_URL = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"


# ─────────────────────────────────────────────
#  FETCH
# ─────────────────────────────────────────────

def fetch_calendar(
    date: datetime.date | None = None,
    country_codes: list | None = None,
    importance: list | None = None,
    timezone: str = "55",
    debug: bool = False,
) -> list:
    if date is None:
        date = datetime.date.today()

    payload = [
        ("timeZone",      timezone),
        ("timeFilter",    "timeOnly"),
        ("currentTab",    "today"),
        ("submitFilters", "1"),
        ("limit_from",    "0"),
    ]
    for c in (country_codes or COUNTRY_CODES):
        payload.append(("country[]", c))
    for i in (importance or IMPORTANCE_FILTER):
        payload.append(("importance[]", i))

    if date != datetime.date.today():
        payload.append(("currentTab", "custom"))
        payload.append(("dateFrom",   date.strftime("%Y-%m-%d")))
        payload.append(("dateTo",     date.strftime("%Y-%m-%d")))

    r = requests.post(API_URL, headers=HEADERS, data=payload, timeout=20)
    r.raise_for_status()

    html = r.json().get("data", "")

    if debug:
        print("=== RAW HTML (first 3000 chars) ===")
        print(html[:3000])
        print("===\n")

    return _parse_html(html)


# ─────────────────────────────────────────────
#  PARSE
# ─────────────────────────────────────────────

def _parse_html(html: str) -> list:
    soup   = BeautifulSoup(html, "lxml")
    events = []

    for row in soup.find_all("tr", id=re.compile(r"^eventRowId_")):
        ev = _parse_row(row)
        if ev:
            events.append(ev)

    return events


def _parse_row(row) -> dict | None:
    row_id = row.get("id", "")
    # Extract numeric event ID from row id e.g. "eventRowId_545672" -> "545672"
    event_num = row_id.replace("eventRowId_", "")

    # ── Time ──────────────────────────────────────────────────────────
    time_td  = row.find("td", class_="js-time")
    time_str = time_td.get_text(strip=True) if time_td else ""

    # ── Country ───────────────────────────────────────────────────────
    # <span title="Germany" class="ceFlags Germany">
    flag_span    = row.find("span", class_=re.compile(r"ceFlags"))
    country_name = ""
    if flag_span:
        title = flag_span.get("title", "").strip()
        country_name = FLAG_TITLE_MAP.get(title, title[:2].upper() if title else "")

    # ── Importance ────────────────────────────────────────────────────
    # Count <i class="grayFullBullishIcon"> — filled = counts toward importance
    sent_td    = row.find("td", class_="sentiment")
    importance = 0
    if sent_td:
        filled = sent_td.find_all("i", class_="grayFullBullishIcon")
        importance = len(filled)

    # ── Event name ────────────────────────────────────────────────────
    event_td   = row.find("td", class_="event")
    event_name = ""
    if event_td:
        a_tag = event_td.find("a")
        if a_tag:
            event_name = a_tag.get_text(strip=True)
        else:
            event_name = event_td.get_text(strip=True)

    if not event_name:
        return None

    # ── Actual ────────────────────────────────────────────────────────
    # id="eventActual_545672"
    actual_tag = row.find(id=f"eventActual_{event_num}")
    actual     = _clean_val(actual_tag)

    # ── Forecast ──────────────────────────────────────────────────────
    forecast_tag = row.find(id=f"eventForecast_{event_num}")
    forecast     = _clean_val(forecast_tag)

    # ── Previous ──────────────────────────────────────────────────────
    # Value is inside a <span title="Revised From ..."> child
    previous_tag = row.find(id=f"eventPrevious_{event_num}")
    previous     = ""
    if previous_tag:
        span = previous_tag.find("span")
        if span:
            previous = span.get_text(strip=True)
        else:
            previous = _clean_val(previous_tag)

    # ── Surprise ──────────────────────────────────────────────────────
    surprise = None
    if actual_tag and actual:
        classes = " ".join(actual_tag.get("class", []))
        if "greenFont" in classes or "better" in classes.lower():
            surprise = "beat"
        elif "redFont" in classes or "worse" in classes.lower():
            surprise = "miss"
        elif "blackFont" in classes or "bold" in classes:
            surprise = "inline"

    return {
        "time":       time_str,
        "country":    country_name,
        "importance": importance,
        "event":      event_name,
        "actual":     actual,
        "forecast":   forecast,
        "previous":   previous,
        "surprise":   surprise,
    }


def _clean_val(tag) -> str:
    if tag is None:
        return ""
    text = tag.get_text(strip=True)
    if text in ("", "\xa0", "&nbsp;"):
        return ""
    return text


# ─────────────────────────────────────────────
#  DEBUG RUNNER
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Fetching today's calendar...\n")
    try:
        events = fetch_calendar(debug=False)
        print(f"Parsed {len(events)} events:\n")
        print(f"{'TIME':<6} {'CTRY':<5} {'IMP':<4} {'EVENT':<45} {'ACTUAL':<10} {'FCST':<10} {'PREV':<10} SURPRISE")
        print("-" * 110)
        for ev in events:
            imp_str = "●" * ev["importance"]
            print(
                f"{ev['time']:<6} "
                f"{ev['country']:<5} "
                f"{imp_str:<4} "
                f"{ev['event'][:44]:<45} "
                f"{ev['actual']:<10} "
                f"{ev['forecast']:<10} "
                f"{ev['previous']:<10} "
                f"{ev['surprise'] or ''}"
            )
    except Exception as e:
        print(f"Error: {e}")
