# ============================================================
#  config.py  —  Dati Macro & Tassi Banche Centrali
#
#  Aggiorna manualmente questi valori quando escono i nuovi dati.
#  Ogni voce include il dato e il mese/periodo di riferimento.
#
#  Struttura:
#    CENTRAL_BANK_RATES  → tassi ufficiali
#    MACRO_DATA          → indicatori macro per paese
# ============================================================


# ─────────────────────────────────────────────
#  TASSI BANCHE CENTRALI
# ─────────────────────────────────────────────
# Formato: "Nome tasso": valore (float, %)

CENTRAL_BANK_RATES = {
    # Federal Reserve (US)
    "Fed Funds Rate (upper)":  3.50,
    "Fed Funds Rate (lower)":  3.75,

    # Banca Centrale Europea (BCE)
    "BCE – Deposit Facility":  2.00,
    "BCE – Main Refi Rate":    2.15,
    "BCE – Marginal Lending":  2.40,

    # Bank of England (BoE)
    "BoE Bank Rate":           3.75,

    # Bank of Japan (BoJ)
    "BoJ Policy Rate":         0.75,
}

RATES_LAST_UPDATED = "2025-04-24"  # Data ultimo aggiornamento manuale


# ─────────────────────────────────────────────
#  DATI MACRO
# ─────────────────────────────────────────────
#
#  Struttura per ogni indicatore:
#    "value"  : float  — il dato (es. 3.2 per 3.2%)
#    "prev"   : float  — dato del mese/trimestre precedente
#    "period" : str    — periodo di riferimento (es. "Feb 2026")
#    "unit"   : str    — unità di misura mostrata nel monitor
#
#  Se un dato non è disponibile, usa None.

MACRO_DATA = {

    # ──────────────────────────────────────────
    #  🇺🇸  UNITED STATES
    # ──────────────────────────────────────────
    "USA": {
        "CPI Headline (YoY %)": {
            "value":  2.9,
            "prev":   2.7,
            "period": "Jan 2026",
            "unit":   "%",
        },
        "CPI Core (YoY %)": {
            "value":  3.2,
            "prev":   3.2,
            "period": "Jan 2026",
            "unit":   "%",
        },
        "Disoccupazione (%)": {
            "value":  4.1,
            "prev":   4.1,
            "period": "Jan 2026",
            "unit":   "%",
        },
        "GDP Growth (QoQ ann. %)": {
            "value":  2.3,
            "prev":   3.1,
            "period": "Q4 2025",
            "unit":   "%",
        },
        "Deficit / GDP (%)": {
            "value":  -6.4,
            "prev":   -6.2,
            "period": "FY 2025",
            "unit":   "%",
        },
        "Debt / GDP (%)": {
            "value":  122.3,
            "prev":   120.1,
            "period": "2025",
            "unit":   "%",
        },
    },

    # ──────────────────────────────────────────
    #  🇪🇺  EUROZONA
    # ──────────────────────────────────────────
    "Eurozona": {
        "CPI Headline (YoY %)": {
            "value":  2.5,
            "prev":   2.4,
            "period": "Jan 2026",
            "unit":   "%",
        },
        "CPI Core (YoY %)": {
            "value":  2.7,
            "prev":   2.7,
            "period": "Jan 2026",
            "unit":   "%",
        },
        "Disoccupazione (%)": {
            "value":  6.3,
            "prev":   6.3,
            "period": "Dec 2025",
            "unit":   "%",
        },
        "GDP Growth (QoQ %)": {
            "value":  0.1,
            "prev":   0.4,
            "period": "Q4 2025",
            "unit":   "%",
        },
        "Deficit / GDP (%)": {
            "value":  -3.6,
            "prev":   -3.5,
            "period": "2025 est.",
            "unit":   "%",
        },
        "Debt / GDP (%)": {
            "value":  89.2,
            "prev":   88.7,
            "period": "2025 est.",
            "unit":   "%",
        },
    },

    # ──────────────────────────────────────────
    #  🇮🇹  ITALIA
    # ──────────────────────────────────────────
    "Italia": {
        "CPI Headline (YoY %)": {
            "value":  1.5,
            "prev":   1.4,
            "period": "Jan 2026",
            "unit":   "%",
        },
        "CPI Core (YoY %)": {
            "value":  1.8,
            "prev":   1.9,
            "period": "Jan 2026",
            "unit":   "%",
        },
        "Disoccupazione (%)": {
            "value":  5.7,
            "prev":   5.8,
            "period": "Dec 2025",
            "unit":   "%",
        },
        "GDP Growth (QoQ %)": {
            "value":  0.1,
            "prev":   0.0,
            "period": "Q4 2025",
            "unit":   "%",
        },
        "Deficit / GDP (%)": {
            "value":  -3.8,
            "prev":   -3.4,
            "period": "2025 est.",
            "unit":   "%",
        },
        "Debt / GDP (%)": {
            "value":  137.3,
            "prev":   134.8,
            "period": "2025 est.",
            "unit":   "%",
        },
    },

    # ──────────────────────────────────────────
    #  🇬🇧  UNITED KINGDOM
    # ──────────────────────────────────────────
    "UK": {
        "CPI Headline (YoY %)": {
            "value":  2.5,
            "prev":   2.6,
            "period": "Dec 2025",
            "unit":   "%",
        },
        "CPI Core (YoY %)": {
            "value":  3.2,
            "prev":   3.5,
            "period": "Dec 2025",
            "unit":   "%",
        },
        "Disoccupazione (%)": {
            "value":  4.4,
            "prev":   4.3,
            "period": "Nov 2025",
            "unit":   "%",
        },
        "GDP Growth (QoQ %)": {
            "value":  0.1,
            "prev":   0.1,
            "period": "Q3 2025",
            "unit":   "%",
        },
        "Deficit / GDP (%)": {
            "value":  -4.5,
            "prev":   -4.4,
            "period": "FY 2024-25",
            "unit":   "%",
        },
        "Debt / GDP (%)": {
            "value":  98.8,
            "prev":   97.5,
            "period": "2025 est.",
            "unit":   "%",
        },
    },

    # ──────────────────────────────────────────
    #  🇯🇵  GIAPPONE
    # ──────────────────────────────────────────
    "Giappone": {
        "CPI Headline (YoY %)": {
            "value":  3.6,
            "prev":   2.9,
            "period": "Dec 2025",
            "unit":   "%",
        },
        "CPI Core (YoY %)": {
            "value":  3.0,
            "prev":   2.7,
            "period": "Dec 2025",
            "unit":   "%",
        },
        "Disoccupazione (%)": {
            "value":  2.4,
            "prev":   2.5,
            "period": "Dec 2025",
            "unit":   "%",
        },
        "GDP Growth (QoQ ann. %)": {
            "value":  1.2,
            "prev":  -0.4,
            "period": "Q3 2025",
            "unit":   "%",
        },
        "Deficit / GDP (%)": {
            "value":  -3.9,
            "prev":   -3.8,
            "period": "FY 2025",
            "unit":   "%",
        },
        "Debt / GDP (%)": {
            "value":  255.2,
            "prev":   252.4,
            "period": "2025 est.",
            "unit":   "%",
        },
    },
}


# ─────────────────────────────────────────────
#  NOTE PER L'AGGIORNAMENTO
# ─────────────────────────────────────────────
#
#  Fonti consigliate per aggiornare i dati:
#
#  CPI / Inflazione:
#    US   → https://www.bls.gov/cpi/
#    EZ   → https://ec.europa.eu/eurostat (HICP)
#    IT   → https://www.istat.it
#    UK   → https://www.ons.gov.uk
#    JP   → https://www.stat.go.jp
#
#  Disoccupazione:
#    US   → https://www.bls.gov
#    EZ   → https://ec.europa.eu/eurostat
#    UK   → https://www.ons.gov.uk
#    JP   → https://www.stat.go.jp
#
#  GDP:
#    US   → https://www.bea.gov (BEA, advance/second/third estimate)
#    EZ   → https://ec.europa.eu/eurostat
#    UK   → https://www.ons.gov.uk
#    JP   → https://www.esri.cao.go.jp
#
#  Deficit / Debito:
#    US   → https://fiscaldata.treasury.gov
#    EZ   → https://ec.europa.eu/eurostat
#    UK   → https://www.ons.gov.uk / OBR
#    JP   → https://www.mof.go.jp
#    IT   → https://www.mef.gov.it / ISTAT
#
#  Calendario rilascio dati (tutti i paesi):
#    → https://www.investing.com/economic-calendar/
# ─────────────────────────────────────────────
