import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Importeer de benodigde functies uit je project
from config import build_profile_sidebar
# Gebruik dezelfde data-ophaal functies als de Aandelen Screener voor consistentie
from data_processing import get_all_ticker_info, get_wisselkoers, bepaal_land_uit_markt, get_historische_data
from advice_engine import genereer_advies_per_rij
from ai_analysis import genereer_ai_analyse, AI_IS_CONFIGURED
from utils import format_euro

# --- Pagina Configuratie & Sidebar ---
st.set_page_config(layout="wide", page_title="AI Aandelen Analyse")
mijn_profiel = build_profile_sidebar()

# --- Session State Initialisatie ---
# Dit onthoudt de data van het laatst geanalyseerde aandeel
if 'analyse_data' not in st.session_state:
    st.session_state.analyse_data = None
if 'analyse_ticker' not in st.session_state:
    st.session_state.analyse_ticker = ""

# --- Hoofdpagina Applicatie ---
st.title("🤖 AI-Gedreven Aandelen Analyse")
st.markdown("Voer een ticker-symbool in om een diepgaande, gecombineerde kwantitatieve en kwalitatieve analyse te genereren. Deze tool is ideaal voor het onderzoeken van nieuwe investeringsideeën.")

if not AI_IS_CONFIGURED:
    st.error("De AI-analyse functie is niet beschikbaar. Configureer je Gemini API sleutel in `secrets.toml`.")
    st.code('[GEMINI_API_KEY]\nkey = "YOUR_API_KEY_HERE"', language="toml")
    st.stop()

# --- Input sectie ---
st.header("1. Selecteer een Aandeel")
ticker_input = st.text_input(
    "Voer een ticker-symbool in (bv. 'AAPL', 'MSFT', 'ASML.AS')",
    value=st.session_state.analyse_ticker,
    placeholder="bv. NVDA"
)

if st.button("Haal data op", key="fetch_data"):
    if ticker_input:
        st.session_state.analyse_ticker = ticker_input.upper()
        with st.spinner(f"Data voor {st.session_state.analyse_ticker} wordt opgehaald en verwerkt..."):
            # --- LOGICA GEKOPIEERD VAN AANDELEN SCREENER VOOR 100% CONSISTENTIE ---
            info = get_all_ticker_info(st.session_state.analyse_ticker)
            verwerkte_rij_data = None

            if info and info.get('regularMarketPrice') is not None:
                rij_data = {'Ticker': st.session_state.analyse_ticker,
                            'Naam': info.get('shortName', st.session_state.analyse_ticker)}

                koers_orig = info.get('regularMarketPrice')
                valuta_orig = info.get('currency', 'N/A')
                wisselkoers = get_wisselkoers(valuta_orig, 'EUR')

                if koers_orig and valuta_orig and wisselkoers:
                    koers_eur = koers_orig * wisselkoers
                    rij_data['Huidige koers (EUR)'] = koers_eur
                    koersdoel_orig = info.get('targetMeanPrice')
                    if koersdoel_orig and koers_eur > 0:
                        rij_data['Potentieel %'] = (
                            koersdoel_orig * wisselkoers / koers_eur) - 1

                    rij_data['P/E Ratio'] = info.get('trailingPE')
                    rij_data['P/B Ratio'] = info.get('priceToBook')
                    rij_data['P/S Ratio'] = info.get(
                        'priceToSalesTrailing12Months')
                    debt_equity_raw = info.get('debtToEquity')
                    rij_data['Debt/Equity'] = debt_equity_raw / \
                        100 if debt_equity_raw is not None else pd.NA
                    rij_data['Winstmarge %'] = info.get('profitMargins')
                    rij_data['Dagwijziging %'] = dagwijziging_raw / 100 if (
                        dagwijziging_raw := info.get('regularMarketChangePercent')) is not None else 0.0
                    hist_df = get_historische_data(
                        st.session_state.analyse_ticker)
                    if not hist_df.empty:
                        gemiddeld_volume_7d = hist_df['Volume'].tail(7).mean()
                        gemiddeld_volume_3m = info.get(
                            'averageDailyVolume3Month', 0)
                        if gemiddeld_volume_3m > 0:
                            rij_data['Volume Ratio'] = gemiddeld_volume_7d / \
                                gemiddeld_volume_3m
                    rij_data['Beta'] = info.get('beta')
                    rij_data['Return on Equity'] = info.get('returnOnEquity')
                    rij_data['50d MA'] = info.get('fiftyDayAverage')
                    rij_data['200d MA'] = info.get('twoHundredDayAverage')
                    # --- TOEGEVOEGD: De cruciale ontbrekende dataregel ---
                    rij_data['52w High'] = info.get('fiftyTwoWeekHigh')
                    verwerkte_rij_data = pd.Series(rij_data)

            # Controleer of de data succesvol is opgehaald
            if verwerkte_rij_data is None or pd.isna(verwerkte_rij_data.get('Naam')):
                st.error(
                    f"Kon geen data vinden voor ticker '{st.session_state.analyse_ticker}'. Controleer het symbool en probeer opnieuw.")
                st.session_state.analyse_data = None
            else:
                # Genereer het advies van de regelmotor (in 'screener' modus)
                advies_details = genereer_advies_per_rij(
                    verwerkte_rij_data, mijn_profiel, 999_999_999)
                # Sla zowel het advies als de details op
                verwerkte_rij_data['Advies'] = advies_details['advies']
                verwerkte_rij_data['advies_details'] = advies_details['details']

                # Sla de complete data op in de session state
                st.session_state.analyse_data = verwerkte_rij_data
    else:
        st.warning("Voer een ticker-symbool in.")

# --- Analyse sectie (wordt alleen getoond als er data is) ---
if st.session_state.analyse_data is not None:
    rij_data = st.session_state.analyse_data

    st.header(
        f"2. Genereer Analyse voor {rij_data.get('Naam', st.session_state.analyse_ticker)}")

    # Toon een beknopte samenvatting van de opgehaalde data
    st.subheader("Kwantitatieve Samenvatting")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Huidige Koers", format_euro(
        rij_data.get('Huidige koers (EUR)')))
    col2.metric("P/E Ratio", f"{rij_data.get('P/E Ratio', 'N/B'):.2f}" if pd.notna(
        rij_data.get('P/E Ratio')) else 'N/B')
    col3.metric("Potentieel", f"{rij_data.get('Potentieel %', 0):.2%}" if pd.notna(
        rij_data.get('Potentieel %')) else 'N/B')
    col4.metric("Regelmotor Advies", rij_data.get('Advies', 'N/B'))

    # --- NIEUW: Toon de koersgrafiek ---
    hist_df = get_historische_data(rij_data.get('Ticker'))
    if not hist_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist_df.index, y=hist_df['Close'], mode='lines', name='Koers', line=dict(color='royalblue')))
        # Voeg voortschrijdende gemiddelden toe als ze bestaan in de data
        if '50d MA' in rij_data and pd.notna(rij_data['50d MA']):
            fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'].rolling(window=50).mean(
            ), mode='lines', name='50d MA', line=dict(color='orange', dash='dash')))
        if '200d MA' in rij_data and pd.notna(rij_data['200d MA']):
            fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'].rolling(
                window=200).mean(), mode='lines', name='200d MA', line=dict(color='red', dash='dash')))

        fig.update_layout(
            title=f'Historische Koers en Voortschrijdende Gemiddelden voor {rij_data.get("Naam")}',
            xaxis_title=None,
            yaxis_title='Koers (EUR)',
            legend_title='Legenda'
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- NIEUW: Toon de details van de adviesmotor ---
    advies_details = rij_data.get('advies_details')
    if advies_details:
        with st.expander("Bekijk de details van de Regelmotor Score"):
            scores = advies_details.get('scores', {})
            checks = advies_details.get('checks', {})

            st.write("##### Scores")
            col1, col2 = st.columns(2)
            col1.metric("Kwaliteit Score", scores.get(
                'Kwaliteit Score', 'N/B'))
            col2.metric("Waarde Score", scores.get('Waarde Score', 'N/B'))

            st.write("##### Individuele Checks")
            for check_naam, resultaat in checks.items():
                st.markdown(f"- {check_naam}: {'✅' if resultaat else '❌'}")

    st.markdown("---")

    st.subheader("3. Start de AI Analyse")
    feedback = st.text_area("Geef feedback op de analyse (optioneel)",
                            placeholder="Bijvoorbeeld: 'De analyse miste het recente nieuws over de overname.'")

    if st.button(f"Genereer AI Analyse", type="primary"):
        # --- CORRECTE CONTROLE ---
        # Controleer HIER of de data overeenkomt met de input, voordat de dure AI-call wordt gemaakt.
        if ticker_input.upper() != rij_data.get('Ticker'):
            st.error(
                f"De ticker in het invoerveld ('{ticker_input.upper()}') komt niet overeen met de geladen data ('{rij_data.get('Ticker')}'). Klik eerst op **'Haal data op'** om de nieuwe ticker te analyseren.")
        else:
            with st.spinner(f"De AI-analist bestudeert {rij_data['Naam']}... Dit kan even duren."):
                # Dit is de CORRECTE aanroep van de functie
                # We converteren de pandas Series naar een dictionary (`.to_dict()`). Dit is een
                # robuustere manier om data door te geven aan een gecachte functie, omdat
                # dictionaries betrouwbaarder worden "gehasht" door Streamlit dan pandas objecten.
                # We geven de ticker expliciet mee als eerste argument om de cache te garanderen.
                analyse_tekst = genereer_ai_analyse(rij_data.get(
                    'Ticker'), rij_data.to_dict(), mijn_profiel, feedback)
                st.markdown("---")
                st.write_stream(analyse_tekst)
