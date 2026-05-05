"""
monitor.py  —  Financial Dashboard (PyQt6)
Dependencies: pip install PyQt6 yfinance pandas requests beautifulsoup4 lxml
"""

import sys
import datetime
import yfinance as yf
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QPushButton, QFrame, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

from yield_scraper import fetch_all_yields, YIELD_URLS
from cpi_loader import load_all as cpi_load_all, LOADERS as CPI_COUNTRIES
from eco_calendar import fetch_calendar, IMPORTANCE_COLOR, IMPORTANCE_LABEL


try:
    from config import CENTRAL_BANK_RATES, RATES_LAST_UPDATED, MACRO_DATA
except ImportError:
    CENTRAL_BANK_RATES = {}
    RATES_LAST_UPDATED = "N/A"
    MACRO_DATA = {}

# ─────────────────────────────────────────────
#  TICKER DEFINITIONS
# ─────────────────────────────────────────────

SECTIONS = {
    "FOREX": [
        ("EUR/USD",  "EURUSD=X"),
        ("GBP/USD",  "GBPUSD=X"),
        ("USD/JPY",  "JPY=X"),
    ],
    "COMMODITIES": [
        ("Gold (XAU/USD)",   "GC=F"),
        ("Silver (XAG/USD)", "SI=F"),
        ("WTI Crude",        "CL=F"),
        ("Brent Crude",      "BZ=F"),
        ("Natural Gas",      "NG=F"),
    ],
    "CRYPTO": [
        ("Bitcoin (BTC)",  "BTC-USD"),
        ("Ethereum (ETH)", "ETH-USD"),
    ],
    "EQUITIES": [
        ("S&P 500",    "^GSPC"),
        ("NASDAQ",     "^IXIC"),
        ("VIX",        "^VIX"),
        ("FTSE MIB",   "FTSEMIB.MI"),
        ("DAX",        "^GDAXI"),
        ("CAC 40",     "^FCHI"),
        ("IBEX 35",    "^IBEX"),
        ("Nikkei 225", "^N225"),
        ("FTSE 100",   "^FTSE"),
    ],
}

YIELD_NAMES = list(YIELD_URLS.keys())

SPREAD_PAIRS = [
    # 10Y
    ("BTP/Bund 10Y (IT-DE)",   "IT 10Y", "DE 10Y"),
    ("OAT/Bund 10Y (FR-DE)",   "FR 10Y", "DE 10Y"),
    ("Bonos/Bund 10Y (ES-DE)", "ES 10Y", "DE 10Y"),
    # 2Y
    ("BTP/Bund 2Y (IT-DE)",    "IT 2Y",  "DE 2Y"),
    ("OAT/Bund 2Y (FR-DE)",    "FR 2Y",  "DE 2Y"),
    ("Bonos/Bund 2Y (ES-DE)",  "ES 2Y",  "DE 2Y"),
]

CURVE_SPREADS = [
    ("US  2s10s", "US 2Y",  "US 10Y"),
    ("DE  2s10s", "DE 2Y",  "DE 10Y"),
    ("IT  2s10s", "IT 2Y",  "IT 10Y"),
    ("ES  2s10s", "ES 2Y",  "ES 10Y"),
    ("FR  2s10s", "FR 2Y",  "FR 10Y"),
    ("UK  2s10s", "UK 2Y",  "UK 10Y"),
    ("JP  2s10s", "JP 2Y",  "JP 10Y"),
]

# ─────────────────────────────────────────────
#  COLORS & STYLE
# ─────────────────────────────────────────────

BG_DARK      = "#0D1117"
BG_CARD      = "#161B22"
BG_HEADER    = "#1C2128"
ACCENT       = "#58A6FF"
TEXT_PRIMARY = "#E6EDF3"
TEXT_MUTED   = "#7D8590"
GREEN        = "#3FB950"
RED          = "#F85149"
GOLD         = "#D4A017"
BORDER       = "#30363D"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: 'Courier New', monospace;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_DARK};
}}
QTabBar::tab {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    padding: 8px 28px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    border: 1px solid {BORDER};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: {BG_DARK};
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}
QScrollArea {{
    border: none;
    background-color: {BG_DARK};
}}
QScrollBar:vertical {{
    background: {BG_CARD};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QTableWidget {{
    background-color: {BG_CARD};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-size: 12px;
    color: {TEXT_PRIMARY};
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BORDER};
}}
QHeaderView::section {{
    background-color: {BG_HEADER};
    color: {TEXT_MUTED};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid {BORDER};
}}
QPushButton {{
    background-color: {ACCENT};
    color: {BG_DARK};
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: bold;
    font-family: 'Courier New', monospace;
}}
QPushButton:hover {{ background-color: #79B8FF; }}
QPushButton:pressed {{ background-color: #388BFD; }}
QPushButton:disabled {{ background-color: {BORDER}; color: {TEXT_MUTED}; }}
QLabel {{ font-family: 'Courier New', monospace; }}
"""

# ─────────────────────────────────────────────
#  DATA FETCHER (background thread)
# ─────────────────────────────────────────────

class DataFetcher(QThread):
    data_ready      = pyqtSignal(dict)
    error_signal    = pyqtSignal(str)
    progress_signal = pyqtSignal(str)

    def run(self):
        try:
            result = {}
            today  = datetime.date.today()
            start  = (today - datetime.timedelta(days=14)).isoformat()

            # ── 1. Market tickers via yfinance ──
            self.progress_signal.emit("Fetching market prices...")
            market_items = [(name, ticker)
                            for items in SECTIONS.values()
                            for name, ticker in items]
            all_tickers = list({t for _, t in market_items})

            raw   = yf.download(all_tickers, start=start, auto_adjust=True, progress=False)
            close = raw["Close"] if hasattr(raw.columns, "levels") else raw[["Close"]]

            for name, ticker in market_items:
                result[name] = self._extract_yf(close, ticker)

            # ── 2. Yield via investing.com scraping ──
            self.progress_signal.emit("Fetching bond yields from investing.com...")

            def _prog(i, total, name):
                self.progress_signal.emit(f"Bond {i}/{total}: {name}...")

            yield_data = fetch_all_yields(progress_callback=_prog)
            result.update(yield_data)

            self.data_ready.emit(result)

        except Exception as e:
            self.error_signal.emit(str(e))

    @staticmethod
    def _extract_yf(close_df, ticker):
        try:
            if ticker not in close_df.columns:
                return None
            series = close_df[ticker].dropna()
            if len(series) < 2:
                return None
            current   = float(series.iloc[-1])
            yesterday = float(series.iloc[-2])
            cutoff    = series.index[-1] - datetime.timedelta(days=6)
            wk        = series[series.index <= cutoff]
            week_ago  = float(wk.iloc[-1]) if len(wk) > 0 else None
            return {"current": current, "yesterday": yesterday, "week_ago": week_ago}
        except Exception:
            return None

# ─────────────────────────────────────────────
#  ECO CALENDAR FETCHER (background thread)
# ─────────────────────────────────────────────

class EcoFetcher(QThread):
    data_ready   = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def run(self):
        try:
            events = fetch_calendar(importance=["1","2","3"])
            self.data_ready.emit(events)
        except Exception as e:
            self.error_signal.emit(str(e))

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def fmt_price(val, decimals=2):
    return "—" if val is None else f"{val:,.{decimals}f}"

def fmt_pct(current, reference):
    if current is None or reference is None or reference == 0:
        return "—", None
    chg = (current - reference) / abs(reference) * 100
    return f"{'+'if chg>=0 else ''}{chg:.2f}%", chg

def colored_item(text, chg=None):
    """chg > 0 = red, chg < 0 = green (lower is better for yields/spreads)."""
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if chg is not None:
        if chg > 0:
            item.setForeground(QColor(RED))
        elif chg < 0:
            item.setForeground(QColor(GREEN))
        else:
            item.setForeground(QColor(TEXT_MUTED))
    else:
        item.setForeground(QColor(TEXT_PRIMARY))
    return item

def colored_item_market(text, chg=None):
    """chg > 0 = green, chg < 0 = red (standard market convention)."""
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if chg is not None:
        if chg > 0:
            item.setForeground(QColor(GREEN))
        elif chg < 0:
            item.setForeground(QColor(RED))
        else:
            item.setForeground(QColor(TEXT_MUTED))
    else:
        item.setForeground(QColor(TEXT_PRIMARY))
    return item

def left_item(text, color=TEXT_PRIMARY):
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    item.setForeground(QColor(color))
    return item

def make_section_label(text):
    label = QLabel(text)
    label.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
    label.setStyleSheet(f"color:{ACCENT}; padding:14px 4px 4px 4px; "
                        f"letter-spacing:2px; border-bottom:1px solid {BORDER};")
    return label

def make_scroll_tab():
    """Returns (tab_widget, body_layout) — a tab with an inner scroll area."""
    tab = QWidget()
    lay = QVBoxLayout(tab)
    lay.setContentsMargins(0, 8, 8, 8)
    lay.setSpacing(0)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    body = QWidget()
    bl = QVBoxLayout(body)
    bl.setContentsMargins(0, 0, 8, 0)
    bl.setSpacing(6)
    scroll.setWidget(body)
    lay.addWidget(scroll)
    return tab, bl

def make_table(rows, headers):
    t = QTableWidget(rows, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for i in range(1, len(headers)):
        t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
    t.setFixedHeight(rows * 34 + 38)
    return t

MARKET_HEADERS = ["Instrument", "Price",     "Yesterday", "Chg 1D",  "1W Ago",   "Chg 1W"]
YIELD_HEADERS  = ["Instrument", "Yield (%)", "Yesterday", "Chg 1D (bps)", "1W Ago (%)", "Chg 1W (bps)"]
SPREAD_HEADERS = ["Spread",     "Current (bps)", "Yesterday (bps)", "Chg 1D (bps)", "1W Ago (bps)", "Chg 1W (bps)"]

# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────

class FinancialMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Financial Monitor")
        self.resize(1150, 900)
        self.setStyleSheet(STYLESHEET)
        self._data    = {}
        self._tables  = {}
        self._fetcher = None
        self._build_ui()
        self._fetch_data()

    # ── UI ────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(0)

        # Top bar
        topbar = QHBoxLayout()
        title  = QLabel("FINANCIAL MONITOR")
        title.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{ACCENT}; letter-spacing:4px;")

        self.lbl_time = QLabel()
        self.lbl_time.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        self._update_clock()

        self.lbl_status = QLabel("Loading...")
        self.lbl_status.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        self.lbl_status.setMinimumWidth(340)

        self.btn_refresh = QPushButton("REFRESH")
        self.btn_refresh.setFixedWidth(140)
        self.btn_refresh.clicked.connect(self._fetch_data)

        topbar.addWidget(title)
        topbar.addStretch()
        topbar.addWidget(self.lbl_time)
        topbar.addSpacing(16)
        topbar.addWidget(self.lbl_status)
        topbar.addSpacing(12)
        topbar.addWidget(self.btn_refresh)
        root.addLayout(topbar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER}; margin:8px 0;")
        root.addWidget(sep)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        self._build_sections()

        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(60000)

    def _build_sections(self):

        # ── TAB 1: MARKETS ────────────────────
        tab1, bl1 = make_scroll_tab()
        for sec_name, items in SECTIONS.items():
            bl1.addWidget(make_section_label(sec_name))
            t = make_table(len(items), MARKET_HEADERS)
            self._tables[sec_name] = (t, items, "market")
            bl1.addWidget(t)
            self._fill_market(t, items)
        bl1.addStretch()
        self.tabs.addTab(tab1, "MARKETS")

        # ── TAB 2: RATES & SPREADS ────────────
        tab2, bl2 = make_scroll_tab()

        bl2.addWidget(make_section_label("YIELD CURVE (%)  —  source: investing.com"))
        t = make_table(len(YIELD_NAMES), YIELD_HEADERS)
        self._tables["yield"] = (t, YIELD_NAMES, "yield")
        bl2.addWidget(t)
        self._fill_yield(t, YIELD_NAMES)

        bl2.addWidget(make_section_label("SPREADS vs BUND (bps)"))
        t = make_table(len(SPREAD_PAIRS), SPREAD_HEADERS)
        self._tables["spread"] = (t, SPREAD_PAIRS, "spread")
        bl2.addWidget(t)
        self._fill_spread(t)

        bl2.addWidget(make_section_label("2Y-10Y CURVE SPREADS (bps)"))
        t = make_table(len(CURVE_SPREADS), SPREAD_HEADERS)
        self._tables["curve"] = (t, CURVE_SPREADS, "curve")
        bl2.addWidget(t)
        self._fill_curve(t)

        bl2.addStretch()
        self.tabs.addTab(tab2, "RATES & SPREADS")

        # ── TAB 3: MACRO ──────────────────────
        tab3, bl3 = make_scroll_tab()

        bl3.addWidget(make_section_label("CENTRAL BANK RATES"))
        bl3.addWidget(self._build_rates_widget())

        bl3.addWidget(make_section_label("MACRO DATA  —  manual update (config.py)"))
        bl3.addWidget(self._build_macro_widget())

        bl3.addStretch()
        self.tabs.addTab(tab3, "MACRO")

        # ── TAB 4: CPI ────────────────────────
        self._cpi_data = {}
        tab4 = self._build_cpi_tab()
        self.tabs.addTab(tab4, "CPI")

        # ── TAB 5: ECO CALENDAR ───────────────
        tab5 = self._build_eco_tab()
        self.tabs.addTab(tab5, "ECO")

    # ── ECO CALENDAR TAB ──────────────────────

    def _build_eco_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # ── Top bar ──
        topbar = QHBoxLayout()

        title = QLabel("ECONOMIC CALENDAR")
        title.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{ACCENT}; letter-spacing:3px;")

        self.lbl_eco_date = QLabel()
        self.lbl_eco_date.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")

        self.lbl_eco_status = QLabel("—")
        self.lbl_eco_status.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        self.lbl_eco_status.setMinimumWidth(220)

        self.btn_eco_refresh = QPushButton("REFRESH")
        self.btn_eco_refresh.setFixedWidth(120)
        self.btn_eco_refresh.clicked.connect(self._fetch_eco)

        topbar.addWidget(title)
        topbar.addStretch()
        topbar.addWidget(self.lbl_eco_date)
        topbar.addSpacing(16)
        topbar.addWidget(self.lbl_eco_status)
        topbar.addSpacing(12)
        topbar.addWidget(self.btn_eco_refresh)
        layout.addLayout(topbar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER}; margin:2px 0;")
        layout.addWidget(sep)

        # ── Legend + filter buttons ──
        legend = QHBoxLayout()
        self._eco_imp_filter = {1: True, 2: True, 3: True}  # all on by default

        for imp, label in [(3, "High ●●●"), (2, "Medium ●●"), (1, "Low ●")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setFixedWidth(110)
            color = IMPORTANCE_COLOR[imp]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_CARD};
                    color: {color};
                    border: 1px solid {color};
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 10px;
                    padding: 3px 8px;
                }}
                QPushButton:checked {{
                    background-color: {color};
                    color: {BG_DARK};
                    font-weight: bold;
                }}
            """)
            btn.clicked.connect(lambda checked, i=imp, b=btn: self._eco_toggle_filter(i, b.isChecked()))
            legend.addWidget(btn)

        legend.addStretch()
        layout.addLayout(legend)

        # ── Table ──
        headers = ["Time", "Ctry", "!", "Event",
                   "Actual", "Forecast", "Previous", "Surprise"]
        self.eco_table = QTableWidget(0, len(headers))
        self.eco_table.setHorizontalHeaderLabels(headers)
        self.eco_table.verticalHeader().setVisible(False)
        self.eco_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.eco_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.eco_table.setAlternatingRowColors(False)

        hh = self.eco_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Time
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Ctry
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # !
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # Event
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Actual
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Forecast
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Previous
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Surprise

        layout.addWidget(self.eco_table)

        # Update date label
        self._eco_update_date()

        # Auto-fetch on tab creation
        self._fetch_eco()

        return tab

    def _eco_update_date(self):
        now = datetime.datetime.now()
        self.lbl_eco_date.setText(now.strftime("%A %d %B %Y"))

    def _eco_toggle_filter(self, importance: int, checked: bool):
        """Show/hide rows by importance level without refetching."""
        self._eco_imp_filter[importance] = checked
        self._eco_apply_filter()

    def _eco_apply_filter(self):
        """Show/hide table rows based on current importance filter."""
        for row in range(self.eco_table.rowCount()):
            imp_item = self.eco_table.item(row, 2)
            if imp_item is None:
                continue
            imp = len(imp_item.text().replace(" ", ""))  # count ● chars
            visible = self._eco_imp_filter.get(imp, True)
            self.eco_table.setRowHidden(row, not visible)

    def _fetch_eco(self):
        self.btn_eco_refresh.setEnabled(False)
        self.btn_eco_refresh.setText("Loading...")
        self.lbl_eco_status.setText("Fetching calendar...")
        self.lbl_eco_status.setStyleSheet(f"color:{GOLD}; font-size:11px;")
        self._eco_fetcher = EcoFetcher()
        self._eco_fetcher.data_ready.connect(self._on_eco_ready)
        self._eco_fetcher.error_signal.connect(self._on_eco_error)
        self._eco_fetcher.start()

    def _on_eco_ready(self, events: list):
        self.eco_table.setRowCount(0)

        # Group events by time for visual separation
        prev_time = None
        for ev in events:
            row = self.eco_table.rowCount()
            self.eco_table.insertRow(row)

            time_str   = ev.get("time", "")
            country    = ev.get("country", "")
            importance = ev.get("importance", 0)
            event_name = ev.get("event", "")
            actual     = ev.get("actual", "")
            forecast   = ev.get("forecast", "")
            previous   = ev.get("previous", "")
            surprise   = ev.get("surprise")

            # Separator line between time blocks
            if prev_time and time_str and time_str != prev_time:
                self.eco_table.setRowHeight(row, 32)
            if time_str:
                prev_time = time_str

            # Col 0: Time — highlight current/upcoming
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            now_time = datetime.datetime.now().strftime("%H:%M")
            if time_str and time_str <= now_time:
                time_item.setForeground(QColor(TEXT_MUTED))
            else:
                time_item.setForeground(QColor(ACCENT))
            self.eco_table.setItem(row, 0, time_item)

            # Col 1: Country
            ctry_item = QTableWidgetItem(country)
            ctry_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            ctry_item.setForeground(QColor(TEXT_PRIMARY))
            self.eco_table.setItem(row, 1, ctry_item)

            # Col 2: Importance (colored bullets)
            imp_color = IMPORTANCE_COLOR.get(importance, TEXT_MUTED)
            imp_item  = QTableWidgetItem("●" * importance)
            imp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            imp_item.setForeground(QColor(imp_color))
            self.eco_table.setItem(row, 2, imp_item)

            # Col 3: Event name
            ev_item = QTableWidgetItem(event_name)
            ev_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            # Bold for high importance
            if importance == 3:
                font = QFont("Courier New", 11, QFont.Weight.Bold)
                ev_item.setFont(font)
                ev_item.setForeground(QColor(TEXT_PRIMARY))
            else:
                ev_item.setForeground(QColor(TEXT_MUTED))
            self.eco_table.setItem(row, 3, ev_item)

            # Col 4: Actual
            act_item = QTableWidgetItem(actual)
            act_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if surprise == "beat":
                act_item.setForeground(QColor(GREEN))
                act_item.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            elif surprise == "miss":
                act_item.setForeground(QColor(RED))
                act_item.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            elif actual:
                act_item.setForeground(QColor(TEXT_PRIMARY))
            else:
                act_item.setForeground(QColor(TEXT_MUTED))
            self.eco_table.setItem(row, 4, act_item)

            # Col 5: Forecast
            fc_item = QTableWidgetItem(forecast if forecast else "—")
            fc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            fc_item.setForeground(QColor(TEXT_MUTED))
            self.eco_table.setItem(row, 5, fc_item)

            # Col 6: Previous
            pr_item = QTableWidgetItem(previous if previous else "—")
            pr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            pr_item.setForeground(QColor(TEXT_MUTED))
            self.eco_table.setItem(row, 6, pr_item)

            # Col 7: Surprise tag
            if surprise == "beat":
                surp_text, surp_color = "BEAT", GREEN
            elif surprise == "miss":
                surp_text, surp_color = "MISS", RED
            elif surprise == "inline":
                surp_text, surp_color = "IN LINE", TEXT_MUTED
            else:
                surp_text, surp_color = "", TEXT_MUTED
            surp_item = QTableWidgetItem(surp_text)
            surp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            surp_item.setForeground(QColor(surp_color))
            self.eco_table.setItem(row, 7, surp_item)

            self.eco_table.setRowHeight(row, 30)

        count = self.eco_table.rowCount()
        now_str = datetime.datetime.now().strftime("%H:%M")
        self._eco_apply_filter()
        visible = sum(1 for r in range(count) if not self.eco_table.isRowHidden(r))
        self.lbl_eco_status.setText(f"{visible}/{count} events  ·  updated {now_str}")
        self.lbl_eco_status.setStyleSheet(f"color:{GREEN}; font-size:11px;")
        self.btn_eco_refresh.setEnabled(True)
        self.btn_eco_refresh.setText("REFRESH")

    def _on_eco_error(self, msg: str):
        self.lbl_eco_status.setText(f"Error: {msg[:60]}")
        self.lbl_eco_status.setStyleSheet(f"color:{RED}; font-size:11px;")
        self.btn_eco_refresh.setEnabled(True)
        self.btn_eco_refresh.setText("REFRESH")

    # ── CPI TAB ───────────────────────────────

    def _build_cpi_tab(self):
        """Landing page: headline cards + country buttons."""
        from PyQt6.QtWidgets import QStackedWidget, QGridLayout
        self._cpi_stack_widget = QWidget()
        outer = QVBoxLayout(self._cpi_stack_widget)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._cpi_stack = QStackedWidget()
        outer.addWidget(self._cpi_stack)

        # ── Landing page ──
        landing = QWidget()
        ll = QVBoxLayout(landing)
        ll.setContentsMargins(24, 20, 24, 24)
        ll.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("CPI INFLATION MONITOR")
        title.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{ACCENT}; letter-spacing:3px;")
        btn_reload = QPushButton("RELOAD DATA")
        btn_reload.setFixedWidth(140)
        btn_reload.clicked.connect(self._reload_cpi)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(btn_reload)
        ll.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER}; margin:2px 0 8px 0;")
        ll.addWidget(sep)

        # Headline cards grid (2 rows × 3 cols)
        self._cpi_cards = {}         # country -> (val_lbl, period_lbl)
        cards_widget = QWidget()
        cards_grid = QGridLayout(cards_widget)
        cards_grid.setSpacing(12)
        cards_grid.setContentsMargins(0, 0, 0, 0)

        countries = list(CPI_COUNTRIES.keys())
        for idx, country in enumerate(countries):
            row, col = divmod(idx, 3)
            card = self._make_cpi_card(country)
            cards_grid.addWidget(card, row, col)

        ll.addWidget(cards_widget)

        subtitle = QLabel("Click a card to view detailed breakdown →")
        subtitle.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; padding-top:4px;")
        ll.addWidget(subtitle)
        ll.addStretch()

        self._cpi_stack.addWidget(landing)

        # Detail page placeholder
        self._cpi_detail_widget = QWidget()
        self._cpi_stack.addWidget(self._cpi_detail_widget)

        self._reload_cpi()
        return self._cpi_stack_widget

    def _make_cpi_card(self, country: str) -> QWidget:
        """A clickable card showing country name + headline CPI + period."""
        card = QWidget()
        card.setFixedHeight(110)
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
            QWidget:hover {{
                border: 1px solid {ACCENT};
            }}
        """)
        card.setCursor(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        lbl_country = QLabel(country.upper())
        lbl_country.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; letter-spacing:2px; border:none;")

        lbl_val = QLabel("—")
        lbl_val.setFont(QFont("Courier New", 22, QFont.Weight.Bold))
        lbl_val.setStyleSheet(f"color:{TEXT_PRIMARY}; border:none;")

        lbl_period = QLabel("no data")
        lbl_period.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; border:none;")

        layout.addWidget(lbl_country)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_period)

        # Store refs for update
        self._cpi_cards[country] = (lbl_val, lbl_period)

        # Make entire card clickable via mouse press event
        def _click(event, c=country):
            self._open_cpi_country(c)
        card.mousePressEvent = _click

        return card

    def _reload_cpi(self):
        """Load CPI data from files and refresh landing page cards."""
        try:
            self._cpi_data = cpi_load_all()
        except Exception as e:
            print(f"CPI load error: {e}")
            self._cpi_data = {}

        for country, (lbl_val, lbl_period) in self._cpi_cards.items():
            data = self._cpi_data.get(country, {})
            headline = data.get("Headline")
            if headline is not None and len(headline) > 0:
                val    = headline.iloc[-1]
                period = headline.index[-1].strftime("%b %Y")
                # Color: red if >3%, orange if 2-3%, green if ≤2%
                if val > 3.0:
                    color = RED
                elif val > 2.0:
                    color = GOLD
                else:
                    color = GREEN
                lbl_val.setText(f"{val:.1f}%")
                lbl_val.setStyleSheet(f"color:{color}; border:none; font-size:22px; font-weight:bold;")
                lbl_period.setText(f"Headline CPI  ·  {period}")
            else:
                lbl_val.setText("—")
                lbl_val.setStyleSheet(f"color:{TEXT_MUTED}; border:none; font-size:22px;")
                lbl_period.setText("no data")

    def _open_cpi_country(self, country: str):
        """Build and show the detail page for a country."""
        data = self._cpi_data.get(country, {})

        self._cpi_stack.removeWidget(self._cpi_detail_widget)
        self._cpi_detail_widget.deleteLater()

        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(16, 12, 16, 12)
        dl.setSpacing(8)

        # Top bar
        topbar = QHBoxLayout()
        btn_back = QPushButton("← BACK")
        btn_back.setFixedWidth(100)
        btn_back.setStyleSheet(f"""
            QPushButton {{
                background-color:{BG_CARD}; color:{TEXT_MUTED};
                border:1px solid {BORDER}; border-radius:4px;
                font-family:'Courier New',monospace; font-size:10px; padding:4px 12px;
            }}
            QPushButton:hover {{ color:{TEXT_PRIMARY}; border-color:{ACCENT}; }}
        """)
        btn_back.clicked.connect(lambda: self._cpi_stack.setCurrentIndex(0))

        lbl_title = QLabel(f"CPI  —  {country.upper()}")
        lbl_title.setFont(QFont("Courier New", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color:{ACCENT}; letter-spacing:3px;")

        topbar.addWidget(btn_back)
        topbar.addSpacing(16)
        topbar.addWidget(lbl_title)
        topbar.addStretch()
        dl.addLayout(topbar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER}; margin:4px 0;")
        dl.addWidget(sep)

        if "_error" in data:
            lbl = QLabel(f"Error loading data: {data['_error']}")
            lbl.setStyleSheet(f"color:{RED}; font-size:11px; padding:16px;")
            dl.addWidget(lbl)
        elif not data:
            lbl = QLabel("No data found. Check CPI_DATA folder.")
            lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; padding:16px;")
            dl.addWidget(lbl)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            chart_w = QWidget()
            chart_l = QVBoxLayout(chart_w)
            chart_l.setContentsMargins(0, 0, 8, 0)
            chart_l.setSpacing(12)
            scroll.setWidget(chart_w)
            dl.addWidget(scroll)

            long_s  = {k: v for k, v in data.items() if len(v) >= 18}
            short_s = {k: v for k, v in data.items() if 0 < len(v) < 18}

            main_keys = [k for k in ["Headline","Core","Food","Energy"] if k in long_s]
            if main_keys:
                chart_l.addWidget(self._make_cpi_chart(
                    {k: long_s[k] for k in main_keys},
                    "Headline, Core, Food & Energy  (YoY %)"))

            gs_keys = [k for k in ["Goods","Services","Shelter","OER"] if k in long_s]
            if gs_keys:
                chart_l.addWidget(self._make_cpi_chart(
                    {k: long_s[k] for k in gs_keys},
                    "Goods, Services & Shelter  (YoY %)"))

            used = set(main_keys + gs_keys)
            rem  = {k: v for k, v in long_s.items() if k not in used}
            if rem:
                chart_l.addWidget(self._make_cpi_chart(rem, "Other Components  (YoY %)"))

            if short_s:
                items = list(short_s.items())
                for i in range(0, len(items), 5):
                    chart_l.addWidget(self._make_cpi_chart(
                        dict(items[i:i+5]), "Components — Recent Months  (YoY %)"))

            chart_l.addStretch()

        self._cpi_detail_widget = detail
        self._cpi_stack.addWidget(detail)
        self._cpi_stack.setCurrentWidget(detail)

    # ── PYQTGRAPH INTERACTIVE CHART ───────────

    def _make_cpi_chart(self, series_dict: dict, title: str) -> QWidget:
        """Interactive pyqtgraph chart with hover tooltip."""
        COLORS_HEX = ["#58A6FF","#3FB950","#F85149","#D4A017",
                      "#BC8CFF","#FF7B72","#79C0FF","#56D364"]

        import pyqtgraph as pg
        from PyQt6.QtWidgets import QGraphicsProxyWidget

        container = QWidget()
        container.setStyleSheet(f"background-color:{BG_CARD}; border:1px solid {BORDER}; border-radius:6px;")
        vl = QVBoxLayout(container)
        vl.setContentsMargins(12, 8, 12, 8)
        vl.setSpacing(4)

        # Title label
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; letter-spacing:1px; border:none;")
        lbl.setFont(QFont("Courier New", 9))
        vl.addWidget(lbl)

        # Hover label
        hover_lbl = QLabel("")
        hover_lbl.setStyleSheet(f"color:{ACCENT}; font-size:10px; font-family:'Courier New'; border:none;")
        hover_lbl.setFixedHeight(16)
        vl.addWidget(hover_lbl)

        # Plot widget
        pw = pg.PlotWidget()
        pw.setFixedHeight(220)
        pw.setBackground("#161B22")
        pw.showGrid(x=False, y=True, alpha=0.15)
        pw.getAxis("bottom").setStyle(tickFont=QFont("Courier New", 7))
        pw.getAxis("left").setStyle(tickFont=QFont("Courier New", 7))
        pw.getAxis("bottom").setPen(pg.mkPen("#30363D"))
        pw.getAxis("left").setPen(pg.mkPen("#30363D"))
        pw.getAxis("bottom").setTextPen(pg.mkPen("#7D8590"))
        pw.getAxis("left").setTextPen(pg.mkPen("#7D8590"))

        # Convert dates to timestamps (seconds)
        import time as _time

        all_series = []
        for (label, series), hex_col in zip(series_dict.items(), COLORS_HEX):
            if len(series) == 0:
                continue
            ts = [s.timestamp() for s in series.index]
            vals = list(series.values)
            color = pg.mkColor(hex_col)

            min_obs = min(len(v) for v in series_dict.values())
            if min_obs < 18:
                # Bar graph for short series
                bg = pg.BarGraphItem(
                    x=ts, height=vals,
                    width=86400 * 25,
                    brush=pg.mkBrush(color),
                    pen=pg.mkPen(color)
                )
                pw.addItem(bg)
            else:
                pen = pg.mkPen(color=hex_col, width=2)
                curve = pw.plot(ts, vals, pen=pen, name=label)

            all_series.append((label, ts, vals, hex_col))

        # Zero line and 2% target
        pw.addItem(pg.InfiniteLine(pos=0,   angle=0,
                   pen=pg.mkPen("#30363D", width=1, style=__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.PenStyle.DashLine)))
        pw.addItem(pg.InfiniteLine(pos=2.0, angle=0,
                   pen=pg.mkPen("#7D8590", width=1, style=__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.PenStyle.DotLine)))

        # X axis: date ticks
        import datetime as _dt
        axis_dates = {}
        if all_series:
            all_ts = all_series[0][1]
            step = max(1, len(all_ts) // 8)
            for i in range(0, len(all_ts), step):
                ts_val = all_ts[i]
                d = _dt.datetime.fromtimestamp(ts_val)
                axis_dates[ts_val] = d.strftime("%b '%y")
        ax = pg.AxisItem(orientation="bottom")
        ax.setTicks([list(axis_dates.items())])
        pw.setAxisItems({"bottom": ax})
        pw.getAxis("bottom").setStyle(tickFont=QFont("Courier New", 7))
        pw.getAxis("bottom").setTextPen(pg.mkPen("#7D8590"))

        # Vertical hover line
        v_line = pg.InfiniteLine(angle=90, movable=False,
                                  pen=pg.mkPen("#58A6FF", width=1, style=__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.PenStyle.DashLine))
        pw.addItem(v_line, ignoreBounds=True)
        v_line.setVisible(False)

        def on_mouse_moved(pos):
            if pw.sceneBoundingRect().contains(pos):
                mouse_point = pw.getViewBox().mapSceneToView(pos)
                x_val = mouse_point.x()
                v_line.setPos(x_val)
                v_line.setVisible(True)

                # Find nearest point across all series
                parts = []
                for label, ts_list, val_list, hex_col in all_series:
                    if not ts_list:
                        continue
                    diffs = [abs(t - x_val) for t in ts_list]
                    idx = diffs.index(min(diffs))
                    d = _dt.datetime.fromtimestamp(ts_list[idx])
                    parts.append(
                        f'<span style="color:{hex_col}">'
                        f'{label}: {val_list[idx]:.2f}%  '
                        f'({d.strftime("%b %Y")})'
                        f'</span>'
                    )
                hover_lbl.setText("  |  ".join(parts))
            else:
                v_line.setVisible(False)
                hover_lbl.setText("")

        pw.scene().sigMouseMoved.connect(on_mouse_moved)

        vl.addWidget(pw)
        container.setFixedHeight(300)
        return container

    # ── FILL: MARKETS ─────────────────────────

    def _dec(self, name):
        if "BTC" in name:  return 0
        if any(x in name for x in ["EUR", "GBP", "ETH"]): return 4
        return 2

    def _fill_market(self, table, items, data=None):
        d = data or {}
        for row, (name, _) in enumerate(items):
            rec = d.get(name)
            dec = self._dec(name)
            table.setItem(row, 0, left_item(name))
            if rec:
                cur = rec["current"]
                yst = rec["yesterday"]
                wk  = rec.get("week_ago")
                pct_1d, chg_1d = fmt_pct(cur, yst)
                pct_1w, chg_1w = fmt_pct(cur, wk)
                table.setItem(row, 1, colored_item_market(fmt_price(cur, dec)))
                table.setItem(row, 2, colored_item_market(fmt_price(yst, dec)))
                table.setItem(row, 3, colored_item_market(pct_1d, chg_1d))
                table.setItem(row, 4, colored_item_market(fmt_price(wk, dec) if wk else "—"))
                table.setItem(row, 5, colored_item_market(pct_1w, chg_1w))
            else:
                for c in range(1, 6): table.setItem(row, c, colored_item("—"))

    # ── FILL: YIELDS ──────────────────────────

    def _fill_yield(self, table, names, data=None):
        d = data or {}
        for row, name in enumerate(names):
            rec = d.get(f"YIELD_{name}")
            table.setItem(row, 0, left_item(name))
            if rec:
                cur = rec["current"]
                yst = rec["yesterday"]
                wk  = rec.get("week_ago")
                d1d = (cur - yst) * 100
                d1w = (cur - wk)  * 100 if wk is not None else None
                table.setItem(row, 1, colored_item(fmt_price(cur, 3)))
                table.setItem(row, 2, colored_item(fmt_price(yst, 3)))
                table.setItem(row, 3, colored_item(f"{d1d:+.1f}", d1d))
                table.setItem(row, 4, colored_item(fmt_price(wk, 3) if wk else "—"))
                table.setItem(row, 5, colored_item(f"{d1w:+.1f}" if d1w is not None else "—", d1w))
            else:
                for c in range(1, 6): table.setItem(row, c, colored_item("—"))

    # ── FILL: SPREADS vs BUND ─────────────────

    def _fill_spread(self, table, data=None):
        d = data or {}
        for row, (label, leg1, leg2) in enumerate(SPREAD_PAIRS):
            d1 = d.get(f"YIELD_{leg1}")
            d2 = d.get(f"YIELD_{leg2}")
            table.setItem(row, 0, left_item(label, GOLD))
            if d1 and d2 and d1["current"] and d2["current"]:
                sp   = (d1["current"]              - d2["current"])              * 100
                spy  = ((d1.get("yesterday") or 0) - (d2.get("yesterday") or 0)) * 100
                sp1w = (((d1.get("week_ago") or 0) - (d2.get("week_ago") or 0))  * 100
                        if d1.get("week_ago") and d2.get("week_ago") else None)
                d1d  = sp - spy
                d1w  = sp - sp1w if sp1w is not None else None
                table.setItem(row, 1, colored_item(f"{sp:.1f}"))
                table.setItem(row, 2, colored_item(f"{spy:.1f}"))
                table.setItem(row, 3, colored_item(f"{d1d:+.1f}", d1d))
                table.setItem(row, 4, colored_item(f"{sp1w:.1f}" if sp1w is not None else "—"))
                table.setItem(row, 5, colored_item(f"{d1w:+.1f}" if d1w is not None else "—", d1w))
            else:
                for c in range(1, 6): table.setItem(row, c, colored_item("—"))

    # ── FILL: 2s10s CURVE SPREADS ─────────────

    def _fill_curve(self, table, data=None):
        d = data or {}
        for row, (label, short, long_) in enumerate(CURVE_SPREADS):
            ds = d.get(f"YIELD_{short}")
            dl = d.get(f"YIELD_{long_}")
            table.setItem(row, 0, left_item(label))
            if ds and dl and ds["current"] and dl["current"]:
                sp   = (dl["current"]              - ds["current"])              * 100
                spy  = ((dl.get("yesterday") or 0) - (ds.get("yesterday") or 0)) * 100
                sp1w = (((dl.get("week_ago") or 0) - (ds.get("week_ago") or 0))  * 100
                        if dl.get("week_ago") and ds.get("week_ago") else None)
                d1d  = sp - spy
                d1w  = sp - sp1w if sp1w is not None else None
                table.setItem(row, 1, colored_item(f"{sp:+.1f}"))
                table.setItem(row, 2, colored_item(f"{spy:+.1f}"))
                table.setItem(row, 3, colored_item(f"{d1d:+.1f}", d1d))
                table.setItem(row, 4, colored_item(f"{sp1w:+.1f}" if sp1w is not None else "—"))
                table.setItem(row, 5, colored_item(f"{d1w:+.1f}" if d1w is not None else "—", d1w))
            else:
                for c in range(1, 6): table.setItem(row, c, colored_item("—"))

    # ── STATIC WIDGETS ────────────────────────

    def _build_rates_widget(self):
        w  = QWidget()
        w.setStyleSheet(f"background-color:{BG_CARD}; border:1px solid {BORDER}; border-radius:6px;")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(12, 10, 12, 10)
        note = QLabel(f"Manual update — last updated: {RATES_LAST_UPDATED}  |  Edit config.py")
        note.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; padding-bottom:6px;")
        vl.addWidget(note)
        grid = QHBoxLayout()
        c1, c2 = QVBoxLayout(), QVBoxLayout()
        items  = list(CENTRAL_BANK_RATES.items())
        half   = (len(items) + 1) // 2
        for i, (name, rate) in enumerate(items):
            rw = QWidget()
            rl = QHBoxLayout(rw)
            rl.setContentsMargins(0, 2, 0, 2)
            ln = QLabel(name)
            ln.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
            lr = QLabel(f"{rate:.2f}%")
            lr.setStyleSheet(f"color:{ACCENT}; font-size:12px; font-weight:bold;")
            lr.setAlignment(Qt.AlignmentFlag.AlignRight)
            rl.addWidget(ln); rl.addStretch(); rl.addWidget(lr)
            (c1 if i < half else c2).addWidget(rw)
        grid.addLayout(c1); grid.addSpacing(20); grid.addLayout(c2)
        vl.addLayout(grid)
        return w

    def _build_macro_widget(self):
        if not MACRO_DATA:
            lbl = QLabel("No macro data in config.py")
            lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; padding:8px;")
            return lbl

        outer = QWidget()
        outer.setStyleSheet(f"background-color:{BG_CARD}; border:1px solid {BORDER}; border-radius:6px;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(12, 10, 12, 12)
        outer_layout.setSpacing(0)

        note = QLabel("Manual update  |  Edit config.py")
        note.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; padding-bottom:8px;")
        outer_layout.addWidget(note)

        all_indicators = []
        for country_data in MACRO_DATA.values():
            for ind in country_data:
                if ind not in all_indicators:
                    all_indicators.append(ind)

        countries = list(MACRO_DATA.keys())
        col_headers = ["Indicator"]
        for c in countries:
            col_headers.append(c)
            col_headers.append("vs prev")

        t = QTableWidget(len(all_indicators), len(col_headers))
        t.setHorizontalHeaderLabels(col_headers)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(col_headers)):
            t.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        t.setFixedHeight(len(all_indicators) * 34 + 38)

        for row, indicator in enumerate(all_indicators):
            t.setItem(row, 0, left_item(indicator))
            col = 1
            for country in countries:
                rec = MACRO_DATA[country].get(indicator)
                if rec and rec.get("value") is not None:
                    val    = rec["value"]
                    prev   = rec.get("prev")
                    unit   = rec.get("unit", "%")
                    period = rec.get("period", "")
                    val_str = f"{val:+.1f}{unit}" if val < 0 else f"{val:.1f}{unit}"
                    vi = QTableWidgetItem(val_str)
                    vi.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    vi.setToolTip(f"Period: {period}")
                    vi.setForeground(QColor(TEXT_PRIMARY))
                    t.setItem(row, col, vi)
                    if prev is not None:
                        diff = val - prev
                        sign = "+" if diff >= 0 else ""
                        di = QTableWidgetItem(f"{sign}{diff:.2f}{unit}")
                        di.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        di.setToolTip(f"Previous: {prev:.1f}{unit}")
                        is_positive_good = "GDP" in indicator
                        if diff > 0:
                            di.setForeground(QColor(GREEN if is_positive_good else RED))
                        elif diff < 0:
                            di.setForeground(QColor(RED if is_positive_good else GREEN))
                        else:
                            di.setForeground(QColor(TEXT_MUTED))
                        t.setItem(row, col + 1, di)
                    else:
                        na = QTableWidgetItem("—")
                        na.setForeground(QColor(TEXT_MUTED))
                        na.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        t.setItem(row, col + 1, na)
                else:
                    for offset in range(2):
                        na = QTableWidgetItem("—")
                        na.setForeground(QColor(TEXT_MUTED))
                        na.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                        t.setItem(row, col + offset, na)
                col += 2

        outer_layout.addWidget(t)
        return outer

    # ── FETCH ─────────────────────────────────

    def _fetch_data(self):
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Loading...")
        self.lbl_status.setText("Initializing data fetch...")
        self.lbl_status.setStyleSheet(f"color:{GOLD}; font-size:11px;")
        self._fetcher = DataFetcher()
        self._fetcher.data_ready.connect(self._on_data_ready)
        self._fetcher.error_signal.connect(self._on_error)
        self._fetcher.progress_signal.connect(self._on_progress)
        self._fetcher.start()

    def _on_progress(self, msg):
        self.lbl_status.setText(msg)
        self.lbl_status.setStyleSheet(f"color:{GOLD}; font-size:11px;")

    def _on_data_ready(self, data):
        self._data = data
        for key, (table, items, mode) in self._tables.items():
            if   mode == "market": self._fill_market(table, items, data)
            elif mode == "yield":  self._fill_yield(table, items, data)
            elif mode == "spread": self._fill_spread(table, data)
            elif mode == "curve":  self._fill_curve(table, data)
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.lbl_status.setText(f"Updated: {now}")
        self.lbl_status.setStyleSheet(f"color:{GREEN}; font-size:11px;")
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("REFRESH")

    def _on_error(self, msg):
        self.lbl_status.setText(f"Error: {msg[:70]}")
        self.lbl_status.setStyleSheet(f"color:{RED}; font-size:11px;")
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("REFRESH")

    def _update_clock(self):
        self.lbl_time.setText(
            datetime.datetime.now().strftime("%A %d %B %Y  —  %H:%M"))

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FinancialMonitor()
    window.show()
    sys.exit(app.exec())
