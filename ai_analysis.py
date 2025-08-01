import streamlit as st
import google.generativeai as genai
import pandas as pd
import logging
from utils import format_euro

# Importeer specifiek de functie die nodig is voor de simpele analyse
from data_processing import get_all_ticker_info

try:
    # De API key moet expliciet naar een string worden geconverteerd.
    # st.secrets geeft een speciaal object terug, geen pure string, wat een TypeError kan veroorzaken
    # in de onderliggende gRPC-bibliotheek.
    api_key = str(st.secrets["GEMINI_API_KEY"])
    genai.configure(api_key=api_key)
    AI_IS_CONFIGURED = True
except (KeyError, FileNotFoundError):
    AI_IS_CONFIGURED = False


def _format_metric(value, format_spec):
    """Helper to format a metric, returning 'N/B' for null values."""
    if pd.isna(value):
        return "N/B"
    try:
        return f"{value:{format_spec}}"
    except (ValueError, TypeError):
        return "N/B"

# De @st.cache_data decorator wordt verwijderd om streaming mogelijk te maken.
# Caching wordt nu afgehandeld op de pagina zelf met st.session_state.
def genereer_ai_analyse(ticker, _rij_data, _profiel, _feedback=None):
    """
    Genereert een geavanceerde, context-bewuste analyse van een aandeel met Google Gemini.
    Deze functie is nu "slimmer" omdat het de volledige data, het gebruikersprofiel en
    het advies van de regelmotor meekrijgt.

    Deze functie retourneert nu een generator die de tekst chunk-voor-chunk streamt,
    wat een directe weergave in de UI mogelijk maakt.
    """
    if not AI_IS_CONFIGURED:
        yield "Fout: Gemini AI is niet geconfigureerd. Voeg je `GEMINI_API_KEY` toe aan het `secrets.toml` bestand."
        return

    # --- 1. Verzamel alle benodigde data uit de input ---
    bedrijfsnaam = _rij_data.get("Naam", ticker)
    huidig_advies = _rij_data.get("Advies", "N/B")

    # Formatteer de kwantitatieve data voor de prompt
    kwantitatieve_data = {
        "Huidige koers": format_euro(_rij_data.get("Huidige koers (EUR)")),
        "Analist Koersdoel": format_euro(_rij_data.get("Analist Koersdoel (EUR)")),
        "Potentieel": _format_metric(_rij_data.get("Potentieel %"), ".2%"),
        "Rendement (in portefeuille)": _format_metric(_rij_data.get("Rendement %"), ".2%"),
        "P/E Ratio": _format_metric(_rij_data.get("P/E Ratio"), ".2f"),
        "P/B Ratio": _format_metric(_rij_data.get("P/B Ratio"), ".2f"),
        "Debt/Equity": _format_metric(_rij_data.get("Debt/Equity"), ".2f"),
        "Winstmarge": _format_metric(_rij_data.get("Winstmarge %"), ".2%"),
        "Prestatie 1j": _format_metric(_rij_data.get("Prestatie 1j"), "+.2%"),
        "Prestatie S&P500 1j": _format_metric(_rij_data.get("Prestatie S&P500 1j"), "+.2%"),
        "Return on Equity": _format_metric(_rij_data.get("Return on Equity"), ".2%"),
        "RSI (14d)": _format_metric(_rij_data.get("RSI"), ".2f"),
        "Trend (Koers vs 50d & 200d MA)": "Positief" if _rij_data.get('Huidige koers (EUR)', 0) > _rij_data.get('50d MA', 0) > _rij_data.get('200d MA', 0) else "Neutraal/Negatief"
    }
    # Maak een nette string van de kwantitatieve data
    kwantitatieve_tekst = "\n".join(
        [f"*   **{k}:** {v}" for k, v in kwantitatieve_data.items() if 'N/B' not in str(v)])

    # --- 2. Bouw de geavanceerde prompt ---
    model = genai.GenerativeModel("gemini-1.5-flash")
    feedback_tekst = f"\n\n**Belangrijk:** Houd rekening met de volgende feedback op eerdere analyses:\n_{_feedback}_" if _feedback else ""

    prompt = f"""
Je bent een zeer ervaren, objectieve en data-gedreven beursanalist. Je taak is om een diepgaande analyse te schrijven voor {bedrijfsnaam} ({ticker}) voor een specifieke belegger.

**CONTEXT:**
1.  **Kwantitatieve Data:** Hieronder staan de belangrijkste financiële en technische metrics voor het aandeel.
{kwantitatieve_tekst}

2.  **Advies Regelmotor:** Mijn interne, op regels gebaseerde analyse-engine geeft momenteel het advies: **"{huidig_advies}"**.

3.  **Beleggersprofiel:** De analyse is voor een belegger met een focus op **{_profiel.get('focus', 'gebalanceerde groei')}** en een **{_profiel.get('risico', 'gemiddeld')}** risicoprofiel.

**JOUW OPDRACHT:**
Schrijf een gestructureerde, professionele analyse in het Nederlands. Gebruik de verstrekte context om je analyse te onderbouwen. Wees kritisch en gebalanceerd.

Structureer je antwoord in het Nederlands met de volgende secties, gebruikmakend van Markdown (gebruik ### voor de hoofdtitels):

### Executive Summary
*   Geef een zeer beknopte samenvatting (2-3 zinnen) van de investeringscase voor **deze specifieke belegger**.

### Scorekaart
*   Geef een score op 10 voor **Waardering**, **Kwaliteit (Moat)**, en **Momentum**. Geef per score een ultrakorte (1 zin) onderbouwing.

### Bedrijfsmodel & Strategie
*   **Kernactiviteit:** Beschrijf de belangrijkste activiteiten van het bedrijf en hoe het inkomsten genereert.
*   **Strategie:** Wat is de uitgesproken strategie van het management voor toekomstige groei?

### Concurrentieanalyse (Moat)
*   **Concurrenten:** Wie zijn de belangrijkste concurrenten?
*   **Concurrentievoordeel (Moat):** Wat is het belangrijkste concurrentievoordeel van dit bedrijf? (bv. merknaam, netwerkeffecten, patenten, schaalvoordeel, etc.)

### Marktanalyse & Trends
*   Wat zijn de belangrijkste trends en ontwikkelingen in de markt waarin het bedrijf opereert? Is de markt groeiend, consoliderend, of onderhevig aan disruptie?

### Kansen
*   Identificeer en beschrijf de 2-3 belangrijkste groeikansen voor de komende jaren.

### Risico's
*   Identificeer en beschrijf de 2-3 voornaamste risico's (zowel bedrijfsspecifiek als marktgerelateerd).

### Management & Leiderschap
*   Wie is de CEO? Wat is zijn/haar reputatie of track record?

### Geïntegreerde Conclusie & Advies
*   **Synthese:** Verbind de kwalitatieve analyse (bedrijf, markt, risico's) met de kwantitatieve data. Is de huidige waardering (P/E, etc.) gerechtvaardigd gezien de groeivooruitzichten en risico's?
*   **Validatie Regelmotor:** Reflecteer op het advies van de regelmotor ("{huidig_advies}"). Ondersteunt jouw diepgaande analyse dit advies, of zie je redenen om ervan af te wijken? Leg uit waarom.
*   **Finale Aanbeveling:** Geef een afsluitende, gewogen aanbeveling (bv. Kopen, Houden, Verkopen, Overwegen) specifiek voor de belegger met het gegeven profiel. Onderbouw dit kort en krachtig.

### Kritische Zelfreflectie
*   Identificeer de grootste onzekerheid of het zwakste punt in je eigen analyse hierboven. Welke informatie zou je analyse significant kunnen veranderen?

{feedback_tekst}
"""

    # Genereer de AI-inhoud
    try:
        # Gebruik stream=True om een generator terug te krijgen
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        logging.error(
            f"Fout bij het aanroepen van de Gemini API voor {ticker}: {e}")
        yield f"### Fout\n\nEr is een onverwachte fout opgetreden bij het genereren van de AI-analyse: `{e}`"


@st.cache_data(show_spinner=False)
def genereer_simpele_ai_analyse(ticker):
    """
    Genereert een eenvoudigere, kwalitatieve analyse op basis van alleen een ticker.
    Deze versie haalt zelf de benodigde data op en wordt gebruikt in de Aandelen Screener.
    """
    if not AI_IS_CONFIGURED:
        return "Fout: Gemini AI is niet geconfigureerd."

    # --- Data ophalen ---
    info = get_all_ticker_info(ticker)
    if not info or info.get('regularMarketPrice') is None:
        return f"Fout: Kon data voor ticker {ticker} niet ophalen."

    # --- Basis data verwerken ---
    bedrijfsnaam = info.get('shortName', ticker)
    sector = info.get('sector', 'N/B')
    samenvatting_raw = info.get('longBusinessSummary', 'Geen samenvatting beschikbaar.')

    # --- NIEUW: Beperk de lengte van de samenvatting om timeouts te voorkomen ---
    # Een te lange 'longBusinessSummary' kan de API-call vertragen en een 504-fout veroorzaken.
    max_len = 1500
    if len(samenvatting_raw) > max_len:
        samenvatting = samenvatting_raw[:max_len] + "..."
    else:
        samenvatting = samenvatting_raw
    # --- Prompt bouwen ---
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
Je bent een beursanalist. Schrijf een beknopte, kwalitatieve analyse voor het bedrijf {bedrijfsnaam} ({ticker}).
Focus op de volgende punten en gebruik de meegeleverde informatie.

**Bedrijfsinformatie:**
*   **Sector:** {sector}
*   **Bedrijfsomschrijving:** {samenvatting}

**Jouw Opdracht:**
Schrijf een korte analyse in het Nederlands met de volgende secties (gebruik ### voor titels):

### Korte Samenvatting
*   Vat de kernactiviteit en de marktpositie van het bedrijf in 2-3 zinnen samen.

### Belangrijkste Kansen & Risico's
*   Noem 1-2 belangrijke groeikansen en 1-2 belangrijke risico's.

Houd de analyse objectief en to-the-point.
"""

    # --- Genereer de AI-inhoud ---
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(
            f"Fout bij het aanroepen van de Gemini API voor {ticker}: {e}")
        return f"Er is een fout opgetreden bij het genereren van de simpele AI-analyse: {e}"
