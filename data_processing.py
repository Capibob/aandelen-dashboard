import pandas as pd
import yfinance as yf
import streamlit as st
from pathlib import Path
from datetime import date, timedelta
import pandas_ta as ta

engels_naar_nederlands_land = {
    'Netherlands': 'Nederland',
    'Belgium': 'België',
    'Germany': 'Duitsland',
    'United States': 'Verenigde Staten',
    'Norway': 'Noorwegen',
    'France': 'Frankrijk',
    'United Kingdom': 'Verenigd Koninkrijk',
    'Switzerland': 'Zwitserland',
    'Ireland': 'Ierland',
    'Canada': 'Canada',
    'Japan': 'Japan',
    'China': 'China',
}

markt_naar_land_mapping = {'BRU': 'België', 'AMS': 'Nederland', 'ETR': 'Duitsland',
                           'XETRA': 'Duitsland', 'NAS': 'Verenigde Staten', 'NYS': 'Verenigde Staten', 'ARC': 'Verenigde Staten', 'OSL': 'Noorwegen'}

def vertaal_land(engelse_naam):
    """
    Vertaalt een Engelse landnaam naar het Nederlands, case-insensitief.
    Geeft None terug als er geen vertaling is, zodat de fallback-logica kan werken.
    """
    if not engelse_naam:
        return None

    # Normaliseer de input naar kleine letters voor een betrouwbare vergelijking
    engelse_naam_lower = engelse_naam.lower()
    for key_eng, val_ned in engels_naar_nederlands_land.items():
        if key_eng.lower() == engelse_naam_lower:
            return val_ned  # Gevonden, geef de Nederlandse waarde terug
    return None  # Niet gevonden in de dictionary


@st.cache_data
def get_wisselkoers(valuta_van, valuta_naar='EUR'):
    if valuta_van == valuta_naar:
        return 1.0
    paar = f"{valuta_van}{valuta_naar}=X"
    try:
        return yf.Ticker(paar).info.get('regularMarketPrice')
    except Exception:
        return None


@st.cache_data
def get_all_ticker_info(ticker):
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}


@st.cache_data
def get_historische_data(ticker, periode="1y"):
    """Haalt historische data op voor een ticker voor de technische analyse."""
    try:
        aandeel = yf.Ticker(ticker)
        # We halen iets meer data op om zeker te zijn van de berekeningen
        eind_datum = date.today()
        start_datum = eind_datum - timedelta(days=400)
        return aandeel.history(start=start_datum, end=eind_datum)
    except Exception:
        return pd.DataFrame()


def bepaal_land_uit_markt(markt_string):
    markt_upper = str(markt_string).upper()
    for code, land in markt_naar_land_mapping.items():
        if code in markt_upper:
            return land
    return markt_string


def _verwerk_enkele_rij(rij, **kwargs):
    """
    Verwerkt de data voor een enkele rij (aandeel, ETF of cash).
    Deze functie wordt toegepast op elke rij van het DataFrame.
    """
    ticker = str(rij.get('Ticker', '')).upper()
    aantal = rij.get('Aantal')

    if not ticker or pd.isna(aantal):
        return rij

    # --- Speciale verwerking voor CASH posities ---
    if 'CASH-' in ticker:
        valuta = ticker.split('-')[1]
        wisselkoers = get_wisselkoers(valuta, 'EUR')
        if wisselkoers:
            rij['Sector'] = 'Cash'
            rij['Regio'] = 'Cash'
            rij['Huidige Waarde (EUR)'] = aantal * wisselkoers
        return rij

    # --- Algemene verwerking voor Aandelen en ETFs - Gebruik meegegeven 'info' ---
    info = kwargs.get('info')
    info = get_all_ticker_info(ticker)
    if not info:
        return rij  # Geen info gevonden, retourneer originele rij

    # Vul basisinformatie aan
    rij['Naam'] = info.get('shortName', ticker)
    rij['Regio'] = vertaal_land(info.get('country')) or bepaal_land_uit_markt(
        rij.get('Markt', 'Onbekend'))
    rij['Sector'] = info.get(
        'category', 'ETF') if rij.get('Type') == 'ETF' else info.get('sector', 'Onbekend')

    # Vul financiële ratio's en metrics
    rij['P/E Ratio'] = info.get('trailingPE')
    rij['P/B Ratio'] = info.get('priceToBook')
    rij['P/S Ratio'] = info.get('priceToSalesTrailing12Months')
    debt_equity_raw = info.get('debtToEquity')
    # yfinance geeft D/E als percentage (bv. 55.3), dus delen door 100
    rij['Debt/Equity'] = debt_equity_raw / 100 if debt_equity_raw is not None else pd.NA
    rij['Winstmarge %'] = info.get('profitMargins')
    rij['Insider Eigendom %'] = info.get('heldPercentInsiders')
    dagwijziging_raw = info.get('regularMarketChangePercent')
    rij['Dagwijziging %'] = dagwijziging_raw if dagwijziging_raw is not None else 0.0
    rij['Beta'] = info.get('beta')
    rij['Return on Equity'] = info.get('returnOnEquity')
    rij['50d MA'] = info.get('fiftyDayAverage')
    rij['200d MA'] = info.get('twoHundredDayAverage')
    rij['52w High'] = info.get('fiftyTwoWeekHigh')

    # Volume Ratio berekening
    hist_df = get_historische_data(ticker)
    if not hist_df.empty:
        # --- NIEUW: Bereken technische indicatoren met pandas_ta ---
        # Zorg ervoor dat de index een datetime object is, wat het al zou moeten zijn
        hist_df.ta.rsi(length=14, append=True)  # Voegt 'RSI_14' kolom toe
        hist_df.ta.macd(fast=12, slow=26, signal=9,
                        append=True)  # Voegt MACD kolommen toe
        hist_df.ta.sma(length=20, append=True)  # Voegt 'SMA_20' kolom toe

        # Haal de meest recente waarden op
        latest_data = hist_df.iloc[-1]
        previous_data = hist_df.iloc[-2] if len(hist_df) > 1 else latest_data

        rij['RSI'] = latest_data.get('RSI_14')
        rij['RSI_prev'] = previous_data.get('RSI_14')  # Voor cross-detectie
        rij['MACD'] = latest_data.get('MACD_12_26_9')
        rij['MACD_signal'] = latest_data.get('MACDs_12_26_9')
        rij['MACD_prev'] = previous_data.get('MACD_12_26_9')
        rij['MACD_signal_prev'] = previous_data.get('MACDs_12_26_9')
        rij['20d MA'] = latest_data.get('SMA_20')

        gemiddeld_volume_3m = info.get('averageDailyVolume3Month', 0)
        gemiddeld_volume_7d = hist_df['Volume'].tail(7).mean()
        if gemiddeld_volume_3m > 0:
            rij['Volume Ratio'] = gemiddeld_volume_7d / gemiddeld_volume_3m

    # Koers, waarde en rendementsberekening
    koers_orig = info.get('regularMarketPrice') or info.get('currentPrice')
    valuta_orig = info.get('currency', 'N/A')
    if koers_orig and valuta_orig:
        wisselkoers_naar_eur = get_wisselkoers(valuta_orig, 'EUR')
        if wisselkoers_naar_eur:
            koers_eur = koers_orig * wisselkoers_naar_eur
            rij['Huidige koers (EUR)'] = koers_eur
            # --- NIEUW: Voeg vorige koers toe voor MA cross-detectie ---
            if not hist_df.empty and len(hist_df) > 1:
                prev_koers_orig = hist_df.iloc[-2].get('Close')
                if prev_koers_orig:
                    rij['Vorige koers (EUR)'] = prev_koers_orig * wisselkoers_naar_eur
            waarde_eur = aantal * koers_eur
            rij['Huidige Waarde (EUR)'] = waarde_eur

            # VERNIEUWDE, CORRECTE LOGICA: Gebruik 'Aankoopprijs (EUR)' uit Excel
            aankoopprijs_eur = rij.get('Aankoopprijs (EUR)', 0)
            if aankoopprijs_eur and aankoopprijs_eur > 0:
                totale_aankoopwaarde = aantal * aankoopprijs_eur
                winst_verlies_eur = waarde_eur - totale_aankoopwaarde
                rij['Winst/Verlies (EUR)'] = winst_verlies_eur
                rij['Rendement %'] = winst_verlies_eur / totale_aankoopwaarde if totale_aankoopwaarde > 0 else 0

            koersdoel_orig = info.get('targetMeanPrice')
            if koersdoel_orig:
                koersdoel_eur = koersdoel_orig * wisselkoers_naar_eur
                rij['Analist Koersdoel (EUR)'] = koersdoel_eur
                if koers_eur > 0:
                    rij['Potentieel %'] = (koersdoel_eur / koers_eur - 1)
    return rij


@st.cache_data
def laad_en_analyseer_data():
    try:
        SCRIPT_MAP = Path(__file__).resolve().parent
    except NameError:
        SCRIPT_MAP = Path.cwd()
    bestandsnaam = SCRIPT_MAP / 'portefeuille.xlsx'
    try:
        df = pd.read_excel(bestandsnaam, sheet_name='Portfolio')
        if df.empty:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ FOUT bij het lezen van '{bestandsnaam}': {e}")  
        st.stop()

    # Definieer alle kolommen die we willen hebben, met hun standaardwaarden
    kolommen = {'Type Asset': '', 'Strategie Type': '', 'Sector': '', 'Regio': '', 'Originele Valuta': '', 'Aankoopprijs (EUR)': 0.0, 'Huidige koers (EUR)': 0.0, 'Huidige Waarde (EUR)': 0.0, 'Winst/Verlies (EUR)': 0.0, 'Rendement %': 0.0, 'Analist Koersdoel (EUR)': 0.0,
                'Potentieel %': 0.0, 'P/E Ratio': pd.NA, 'P/B Ratio': pd.NA, 'P/S Ratio': pd.NA, 'Debt/Equity': pd.NA, 'Winstmarge %': pd.NA, 'Insider Eigendom %': pd.NA, 'Dagwijziging %': 0.0, 'Volume Ratio': 0.0, 'Advies': 'N/B', 'Beta': pd.NA, 'Return on Equity': pd.NA}
    for col, default in kolommen.items():
        if col not in df.columns:
            df[col] = default

    # Waarschuw de gebruiker als de cruciale kolom voor winstberekening ontbreekt
    if 'Aankoopprijs (EUR)' not in df.columns:
        st.warning(
            "Kolom 'Aankoopprijs (EUR)' niet gevonden in Excel. Winst/Verlies en Rendement kunnen niet berekend worden.")

    # Pas de verwerkingsfunctie toe op elke rij van het DataFrame
    # De 'axis=1' zorgt ervoor dat we per rij werken
    df_verwerkt = df.apply(lambda x: _verwerk_enkele_rij(x), axis=1)

    return df_verwerkt


def sla_historische_data_op(datum, totale_waarde, script_pad):
    """Slaat de totale waarde van de portefeuille op voor een specifieke datum."""
    historiek_bestandsnaam = script_pad / 'historiek.csv'
    try:
        historiek_df = pd.read_csv(historiek_bestandsnaam, index_col='Datum')
    except FileNotFoundError:
        historiek_df = pd.DataFrame(columns=['Totale Waarde (EUR)'])
        historiek_df.index.name = 'Datum'
    datum_str = datum.strftime('%Y-%m-%d')
    historiek_df.loc[datum_str] = totale_waarde
    # --- GECORRIGEERD: Sla op naar het juiste bestand ---
    historiek_df.to_csv(historiek_bestandsnaam)
    st.toast(f"Historische data opgeslagen voor {datum_str}")
