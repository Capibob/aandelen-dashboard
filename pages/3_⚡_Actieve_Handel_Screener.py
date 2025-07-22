import streamlit as st
import pandas as pd
from datetime import datetime

# Importeer onze eigen modules
# Let op: we importeren hier de NIEUWE active_trading_engine
from data_processing import _verwerk_enkele_rij
from active_trading_engine import genereer_actieve_handel_signalen
from utils import format_euro, stijl_advies_kolom

# Voorbeeldlijsten van tickers om te screenen. Je kunt deze zelf uitbreiden.
TICKER_LIJSTEN = {
    "Tech (Voorbeeld)": ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'ASML.AS', 'ADYEN.AS'],
    "BEL 20 (Voorbeeld)": ['ABI.BR', 'ACKB.BR', 'AED.BR', 'AGS.BR', 'APAM.AS', 'ARGX.BR', 'BAR.BR', 'COFB.BR', 'ELI.BR', 'GBLB.BR', 'KBC.BR', 'PROX.BR', 'SOF.BR', 'SOLB.BR', 'UCB.BR', 'UMI.BR', 'WDP.BR'],
    "AEX (Voorbeeld)": ['ADYEN.AS', 'AD.AS', 'AKZA.AS', 'ASML.AS', 'ASRNL.AS', 'DSFIR.AS', 'HEIA.AS', 'IMCD.AS', 'INGA.AS', 'KPN.AS', 'NN.AS', 'PHIA.AS', 'PRX.AS', 'RAND.AS', 'REN.AS', 'SHELL.AS', 'UNA.AS', 'WKL.AS'],
    "Mijn Eigen Lijst": ['BPOST.BR', 'OR.PA', 'SIE.DE', 'VOW3.DE']  # Voeg hier je eigen tickers toe
}

# --- Pagina Configuratie ---
st.set_page_config(layout="wide", page_title="Actieve Handel Screener")

# --- Hoofdpagina Applicatie ---
st.title("⚡ Actieve Handel Screener")
st.markdown("""
Deze screener is ontworpen voor **korte-termijn handel** en zoekt naar een **cluster van technische koopsignalen**.
De engine controleert op de volgende condities:
- **RSI Bullish Cross:** De RSI is recent boven de 'oversold' grens van 30 gekomen.
- **MACD Bullish Cross:** De MACD-lijn heeft zojuist de signaallijn naar boven gekruist.
- **Koers > 20d MA:** De koers is recent boven het 20-daags voortschrijdend gemiddelde gebroken.
- **Hoog Volume:** Het handelsvolume is significant hoger dan normaal (bv. >1.5x).

Een aandeel krijgt een **KOOP** signaal als het aan **minimaal 2** van deze criteria voldoet.
""")
st.caption(
    f"Laatste run: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

# Selectie van de te screenen lijst
gekozen_lijst_naam = st.selectbox(
    "Kies een lijst om te screenen:", options=TICKER_LIJSTEN.keys())
tickers_om_te_screenen = TICKER_LIJSTEN[gekozen_lijst_naam]

if st.button(f"Scan {len(tickers_om_te_screenen)} aandelen op handelssignalen", type="primary"):
    verwerkte_rijen = []
    progress_bar = st.progress(0, text="Starten van de analyse...")

    for i, ticker in enumerate(tickers_om_te_screenen):
        progress_bar.progress((i + 1) / len(tickers_om_te_screenen),
                              text=f"Analyseren van {ticker}...")
        dummy_rij = pd.Series(
            {'Ticker': ticker, 'Aantal': 1, 'Type Asset': 'Aandeel'})
        verwerkte_rij = _verwerk_enkele_rij(dummy_rij)
        verwerkte_rijen.append(verwerkte_rij)

    progress_bar.empty()

    if not verwerkte_rijen:
        st.warning("Geen data gevonden voor de geselecteerde tickers.")
        st.stop()

    df_resultaat = pd.DataFrame(verwerkte_rijen)
    df_signalen = genereer_actieve_handel_signalen(df_resultaat)

    st.subheader(f"📊 {len(df_signalen)} Actieve Handelssignalen Gevonden")

    if df_signalen.empty:
        st.info(
            "Geen aandelen voldeden aan de criteria voor een KOOP-signaal (minimaal 2 indicatoren).")
    else:
        kolommen = ['Naam', 'Ticker', 'Sector', 'Huidige koers (EUR)',
                    'RSI', '20d MA', 'Volume Ratio', 'Signaal']

        # Filter de 'kolommen' lijst om alleen kolommen te bevatten die daadwerkelijk bestaan in de dataframe.
        # Dit voorkomt een KeyError als data voor een indicator niet kon worden opgehaald.
        bestaande_kolommen = [
            col for col in kolommen if col in df_signalen.columns]

        for col in ['Huidige koers (EUR)', '20d MA']:
            if col in df_signalen.columns:
                df_signalen[col] = df_signalen[col].apply(format_euro)
        if 'RSI' in df_signalen.columns:
            df_signalen['RSI'] = pd.to_numeric(df_signalen['RSI'], errors='coerce').apply(
                lambda x: f'{x:.2f}'.replace('.', ',') if pd.notna(x) else 'N/B')
        if 'Volume Ratio' in df_signalen.columns:
            df_signalen['Volume Ratio'] = pd.to_numeric(df_signalen['Volume Ratio'], errors='coerce').apply(
                lambda x: f'{x:.2f}x'.replace('.', ',') if pd.notna(x) else 'N/B')

        st.dataframe(df_signalen[bestaande_kolommen].sort_values(by='Signaal', ascending=False).style.applymap(
            stijl_advies_kolom, subset=['Signaal']), use_container_width=True)