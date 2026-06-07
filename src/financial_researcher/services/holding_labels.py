"""Italian labels for ETF holding synopses in generated reports."""

YAHOO_SECTOR_IT: dict[str, str] = {
    "Technology": "Tecnologia",
    "Communication Services": "Telecomunicazioni",
    "Financial Services": "Servizi finanziari",
    "Consumer Cyclical": "Consumi ciclici",
    "Consumer Defensive": "Consumi difensivi",
    "Healthcare": "Sanità",
    "Industrials": "Industriali",
    "Basic Materials": "Materie prime",
    "Energy": "Energia",
    "Utilities": "Utilities",
    "Real Estate": "Immobiliare",
}

INDUSTRY_IT: dict[str, str] = {
    "Semiconductors": "Semiconduttori",
    "Semiconductor Equipment & Materials": "Apparecchiature e materiali per semiconduttori",
    "Software—Infrastructure": "Software e infrastrutture cloud",
    "Software - Infrastructure": "Software e infrastrutture cloud",
    "Software—Application": "Software applicativo",
    "Software - Application": "Software applicativo",
    "Internet Content & Information": "Contenuti e servizi internet",
    "Internet Retail": "Commercio elettronico",
    "Consumer Electronics": "Elettronica di consumo",
    "Communication Equipment": "Apparecchiature per telecomunicazioni",
    "Telecom Services": "Servizi di telecomunicazione",
    "Auto Manufacturers": "Produzione automobilistica",
    "Biotechnology": "Biotecnologie",
    "Drug Manufacturers—General": "Farmaceutica",
    "Drug Manufacturers - General": "Farmaceutica",
    "Medical Devices": "Dispositivi medicali",
    "Banks—Regional": "Banche regionali",
    "Banks - Regional": "Banche regionali",
    "Banks—Diversified": "Banche diversificate",
    "Banks - Diversified": "Banche diversificate",
    "Capital Markets": "Mercati dei capitali",
    "Asset Management": "Gestione patrimoniale",
    "Oil & Gas Integrated": "Petrolio e gas integrato",
    "Utilities—Regulated Electric": "Utility elettriche regolamentate",
    "Utilities - Regulated Electric": "Utility elettriche regolamentate",
    "Aerospace & Defense": "Aerospazio e difesa",
    "Specialty Industrial Machinery": "Macchinari industriali specializzati",
    "Electronic Components": "Componenti elettronici",
    "Information Technology Services": "Servizi IT",
    "Scientific & Technical Instruments": "Strumenti scientifici e tecnici",
}

_INDUSTRY_KEYWORDS_IT: list[tuple[str, str]] = [
    ("semiconductor", "Semiconduttori"),
    ("software", "Software"),
    ("internet", "Servizi internet"),
    ("cloud", "Cloud e infrastrutture digitali"),
    ("artificial intelligence", "Intelligenza artificiale"),
    ("communication", "Telecomunicazioni"),
    ("optical", "Tecnologie ottiche e fotonica"),
    ("connectivity", "Soluzioni di connettività ad alta velocità"),
    ("memory", "Memorie e chip embedded"),
    ("integrated circuit", "Circuiti integrati"),
    ("multimedia", "Soluzioni multimediali e chip"),
    ("edge", "Semiconduttori e software per edge AI"),
]


def _industry_label(industry: str | None) -> str | None:
    if not industry:
        return None
    if industry in INDUSTRY_IT:
        return INDUSTRY_IT[industry]
    lower = industry.lower()
    for keyword, label in _INDUSTRY_KEYWORDS_IT:
        if keyword in lower:
            return label
    return None


def _sector_label(sector: str | None) -> str | None:
    if not sector:
        return None
    return YAHOO_SECTOR_IT.get(sector, sector)


def holding_synopsis(
    sector: str | None,
    industry: str | None,
    language: str | None = None,
) -> str:
    """Build a one-line holding description in the requested language."""
    report_language = language or "English"
    if not report_language.lower().startswith("it"):
        parts = [p for p in (industry, sector) if p]
        return ", ".join(parts) if parts else "—"

    industry_it = _industry_label(industry)
    sector_it = _sector_label(sector)

    if industry_it and sector_it:
        return f"Società attiva in {industry_it} ({sector_it})."
    if industry_it:
        return f"Società attiva in {industry_it}."
    if sector_it:
        return f"Società del settore {sector_it}."
    return "Società internazionale quotata."
