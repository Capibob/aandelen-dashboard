import streamlit as st
import pandas as pd
from datetime import date, timedelta
import plotly.graph_objects as go

# Importeer de backtesting engine
from backtesting_engine import run_backtest, get_backtest_data, optimaliseer_backtest
from utils import format_euro

# --- Pagina Configuratie ---
st.set_page_config(layout="wide", page_title="Strategie Backtester")

# --- Hoofdpagina Applicatie ---
st.title("📈 Strategie Backtester")
st.markdown("""
Hier kunt u de **actieve handelsstrategie** testen op historische data.
U kunt de impact van transactiekosten en de vertraging tussen een signaal en de daadwerkelijke transactie simuleren.
De strategie is gebaseerd op de signalen van de 'Actieve Handel Screener'.
""")

# --- Input sectie ---
st.subheader("1. Stel de Backtest in")
col1, col2 = st.columns(2)

with col1:
    ticker = st.text_input("Ticker Symbol (bv. 'AAPL', 'MSFT', 'ASML.AS')", "NVDA")
    start_kapitaal = st.number_input("Startkapitaal (€)", min_value=100, max_value=100000, value=10000, step=100)
    transactie_kosten = st.number_input("Transactiekosten per transactie (€)", min_value=0.0, value=1.0, step=0.5)

with col2:
    default_start_datum = date.today() - timedelta(days=365 * 2) # Standaard 2 jaar
    start_datum = st.date_input("Startdatum", default_start_datum)
    eind_datum = st.date_input("Einddatum", date.today())

st.subheader("2. Parameters voor de Strategie")
col1, col2, col3 = st.columns(3)
with col1:
    signaal_vertraging = st.slider("Signaal Vertraging (dagen)", 0, 5, 1, help="De vertraging tussen het genereren van een signaal en de uitvoering van de transactie. 1 dag is realistisch voor een bot.")
    stop_loss_pct = st.slider("Stop-Loss (%)", 1, 20, 5, help="Verkoopt automatisch als de koers dit percentage daalt onder de aankoopprijs.") / 100
    take_profit_pct = st.slider("Take-Profit (%)", 5, 50, 15, help="Verkoopt automatisch als de koers dit percentage stijgt boven de aankoopprijs.") / 100
with col2:
    rsi_oversold = st.slider("RSI 'Oversold' Drempel (Koop)", 20, 50, 30, help="Een koopsignaal wordt overwogen als de RSI boven deze waarde kruist.")
    rsi_overbought = st.slider("RSI 'Overbought' Drempel (Verkoop)", 50, 80, 70, help="Een verkoopsignaal wordt overwogen als de RSI onder deze waarde kruist.")
with col3:
    volume_drempel = st.slider("Min. Volume Ratio (Koop)", 1.0, 3.0, 1.5, step=0.1, help="Het 7-daags volume moet X keer hoger zijn dan het 3-maands gemiddelde.")
    
# --- Optimalisatie optie ---
optimaliseren = st.checkbox("Optimaliseer parameters voor beste rendement")
if optimaliseren:
    st.info("De backtest wordt herhaald met verschillende combinaties van parameters om de beste instellingen te vinden.")
    optimalisatie_metriek = st.selectbox("Optimalisatie Metriek", options=['rendement'], index=0, help="Momenteel wordt enkel optimalisatie op basis van 'rendement' ondersteund.")
    signaal_vertraging_opties = st.slider("Optimalisatie: Signaal Vertraging (dagen)", 0, 3, (0, 1))
    stop_loss_pct_opties = st.slider("Optimalisatie: Stop-Loss (%)", 1, 10, (3, 7), help="Minimum en maximum stop-loss percentage.")
    take_profit_pct_opties = st.slider("Optimalisatie: Take-Profit (%)", 5, 20, (10, 20), help="Minimum en maximum take-profit percentage.")

# --- Backtest uitvoeren ---
if st.button(f"Start Backtest voor {ticker}", type="primary"):
    with st.spinner(f"Bezig met het backtesten van {ticker} van {start_datum} tot {eind_datum}..."):
        resultaten, foutmelding = run_backtest(
            ticker=ticker,
            start_datum=start_datum,
            eind_datum=eind_datum,
            start_kapitaal=start_kapitaal,
            transactie_kosten=transactie_kosten,
            signaal_vertraging=signaal_vertraging,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            rsi_oversold=rsi_oversold,
            rsi_overbought=rsi_overbought,
            volume_drempel=volume_drempel
        )

        if optimaliseren:
            # Pas de ranges aan voor de optimalisatiefunctie
            stop_loss_pct_range = (stop_loss_pct_opties[0] / 100, stop_loss_pct_opties[1] / 100)
            take_profit_pct_range = (take_profit_pct_opties[0] / 100, take_profit_pct_opties[1] / 100)

            optimalisatie_resultaten, optimalisatie_foutmelding = optimaliseer_backtest(
                ticker=ticker,
                start_datum=start_datum,
                eind_datum=eind_datum,
                start_kapitaal=start_kapitaal,
                transactie_kosten=transactie_kosten,
                signaal_vertraging_range=signaal_vertraging_opties,
                stop_loss_pct_range=stop_loss_pct_range,
                take_profit_pct_range=take_profit_pct_range,
                metriek=optimalisatie_metriek
            )

            if optimalisatie_foutmelding:
                st.error(f"Optimalisatie mislukt: {optimalisatie_foutmelding}")
            elif optimalisatie_resultaten:
                st.success("Optimalisatie succesvol voltooid!")
                beste_parameters = optimalisatie_resultaten['beste_parameters']
                st.write(f"Beste parameters gevonden:")
                st.write(f"- Signaalvertraging: {beste_parameters['signaal_vertraging']} dag(en)")
                st.write(f"- Stop-Loss: {beste_parameters['stop_loss_pct'] * 100:.0f}%")
                st.write(f"- Take-Profit: {beste_parameters['take_profit_pct'] * 100:.0f}%")

                # Voer een backtest uit met de optimale parameters en toon de resultaten
                resultaten, foutmelding = run_backtest(ticker=ticker, start_datum=start_datum, eind_datum=eind_datum, start_kapitaal=start_kapitaal, transactie_kosten=transactie_kosten, signaal_vertraging=beste_parameters['signaal_vertraging'], stop_loss_pct=beste_parameters['stop_loss_pct'], take_profit_pct=beste_parameters['take_profit_pct'])
                if resultaten:
                    st.session_state['backtest_results'] = resultaten
        else:  # Standaard backtest
            if foutmelding:
                st.error(foutmelding)
            elif resultaten:
                st.session_state['backtest_results'] = resultaten
            else:
                st.warning("De backtest kon niet worden uitgevoerd. Controleer de ticker en de periode.")


# --- Resultaten weergeven (indien beschikbaar in session state) ---
if 'backtest_results' in st.session_state:
    resultaten = st.session_state['backtest_results']
    st.subheader("2. Resultaten van de Backtest")

    # Samenvatting
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Eindwaarde", format_euro(resultaten['eind_waarde']), f"{resultaten['rendement_pct']:.2f}% Rendement")
    col2.metric("Aantal Transacties", resultaten['aantal_transacties'])
    col3.metric("Winstgevende Trades", f"{resultaten['percentage_winstgevend']:.1f}%")
    col4.metric("Gem. Winst / Verlies", f"{format_euro(resultaten['gemiddelde_winst'])} / {format_euro(resultaten['gemiddelde_verlies'])}")

    # Grafiek
    df_transacties = resultaten['transacties']
    if not df_transacties.empty:
        hist_data = get_backtest_data(resultaten['ticker'], resultaten['start_datum'], resultaten['eind_datum'])
        hist_data = hist_data[hist_data.index >= pd.to_datetime(resultaten['start_datum'])] # Filter op de daadwerkelijke startdatum

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_data.index, y=hist_data['Close'], mode='lines', name=f'Koers {resultaten["ticker"]}'))

        # Voeg koop- en verkooppunten toe
        koop_datums = df_transacties['datum_in'].dropna()
        koop_prijzen = df_transacties['aankoop_prijs'].dropna()
        verkoop_datums = df_transacties['datum_uit'].dropna()
        verkoop_prijzen = df_transacties['verkoop_prijs'].dropna()

        fig.add_trace(go.Scatter(x=koop_datums, y=koop_prijzen, mode='markers', name='Koopmomenten',
                                 marker=dict(color='green', size=10, symbol='triangle-up')))
        fig.add_trace(go.Scatter(x=verkoop_datums, y=verkoop_prijzen, mode='markers', name='Verkoopmomenten',
                                 marker=dict(color='red', size=10, symbol='triangle-down')))

        fig.update_layout(
            title=f'Transactiemomenten voor {resultaten["ticker"]}',
            xaxis_title='Datum',
            yaxis_title='Koers (EUR)',
            legend_title='Legenda'
        )
        st.plotly_chart(fig, use_container_width=True)

    # Transactielogboek
    with st.expander("Gedetailleerd Transactielogboek"):
        if not df_transacties.empty:
            df_display = df_transacties.copy()
            # Formatteer kolommen voor weergave
            for col in ['aankoop_prijs', 'verkoop_prijs', 'resultaat']:
                df_display[col] = df_display[col].apply(format_euro)
            df_display.rename(columns={
                'datum_in': 'Datum Aankoop',
                'aankoop_prijs': 'Aankoopprijs',
                'datum_uit': 'Datum Verkoop',
                'verkoop_prijs': 'Verkoopprijs',
                'resultaat': 'Resultaat'
            }, inplace=True)
            st.dataframe(df_display)
        else:
            st.info("Er zijn geen transacties uitgevoerd tijdens deze periode.")
