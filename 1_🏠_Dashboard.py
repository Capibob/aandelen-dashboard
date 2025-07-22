import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path

# Importeer vanuit onze modulaire bestanden
from config import build_profile_sidebar
from data_processing import laad_en_analyseer_data, sla_historische_data_op
from advice_engine import genereer_adviezen
from utils import format_euro, stijl_advies_kolom


def toon_visuele_samenvatting(df):
    """Toont de visuele samenvatting met pie charts voor Sector en Regio."""
    st.subheader("Visuele Samenvatting")
    col1, col2 = st.columns(2)
    with col1:
        st.write("##### Verdeling per Sector")
        st.plotly_chart(px.pie(df, names='Sector', values='Huidige Waarde (EUR)', hole=.3), use_container_width=True)
    with col2:
        st.write("##### Verdeling per Regio")
        st.plotly_chart(px.pie(df, names='Regio', values='Huidige Waarde (EUR)', hole=.3), use_container_width=True)

# --- Pagina Configuratie & Sidebar ---
st.set_page_config(layout="wide", page_title="Portefeuille Dashboard")
mijn_profiel = build_profile_sidebar()

# --- Hoofdpagina Applicatie ---
st.title("📈 Persoonlijke Portefeuille Analyse")
st.caption(
    f"Laatste data opgehaald op: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

portfolio_basis_df = laad_en_analyseer_data()

if not portfolio_basis_df.empty:
    portfolio_met_advies_df = genereer_adviezen(
        portfolio_basis_df, mijn_profiel)

    # Importeer plotly express lokaal voor de grafieken
    import plotly.express as px
    toon_visuele_samenvatting(portfolio_met_advies_df)

    st.subheader("Details van je Portefeuille")

    # De definitieve, complete lijst met kolommen
    relevante_kolommen = [
        'Naam', 'Type Asset', 'Strategie Type', 'Sector', 'Regio',
        'Aankoopprijs (EUR)', 'Huidige koers (EUR)', 'Winst/Verlies (EUR)', 'Rendement %',
        'Huidige Waarde (EUR)', 'Analist Koersdoel (EUR)', 'Potentieel %',
        'P/E Ratio', 'P/B Ratio', 'P/S Ratio', 'Debt/Equity', 'Winstmarge %',
        'Return on Equity', 'Beta', 'Advies'
    ]
    bestaande_relevante_kolommen = [
        col for col in relevante_kolommen if col in portfolio_met_advies_df.columns]

    portfolio_df_display = portfolio_met_advies_df.copy()

    # Formatteer de kolommen voor een nette, Europese weergave
    for col in ['Potentieel %', 'Winstmarge %', 'Insider Eigendom %', 'Dagwijziging %', 'Return on Equity', 'Rendement %']:
        if col in portfolio_df_display.columns:
            portfolio_df_display[col] = pd.to_numeric(portfolio_df_display[col], errors='coerce').apply(
                lambda x: f'{x:+.2%}'.replace('.', ',') if col == 'Dagwijziging %' and pd.notna(
                    x) else (f'{x:.2%}'.replace('.', ',') if pd.notna(x) else 'N/B')
            )
    if 'Volume Ratio' in portfolio_df_display.columns:
        portfolio_df_display['Volume Ratio'] = pd.to_numeric(portfolio_df_display['Volume Ratio'], errors='coerce').apply(
            lambda x: f'{x:.2f}x'.replace('.', ',') if pd.notna(x) else 'N/B'
        )

    euro_kolommen = ['Aankoopprijs (EUR)', 'Huidige koers (EUR)',
                     'Winst/Verlies (EUR)', 'Huidige Waarde (EUR)', 'Analist Koersdoel (EUR)']
    for col in euro_kolommen:
        if col in portfolio_df_display.columns:
            portfolio_df_display[col] = portfolio_df_display[col].apply(
                format_euro)

    # Toon het dataframe met de conditionele styling
    st.dataframe(
        portfolio_df_display[bestaande_relevante_kolommen].style.map(
            stijl_advies_kolom, subset=['Advies']), use_container_width=True)

    # Toon het totaaloverzicht
    st.subheader("Totaaloverzicht")
    totale_waarde_portfolio = portfolio_met_advies_df['Huidige Waarde (EUR)'].sum(
    )
    totale_winst_verlies = portfolio_met_advies_df['Winst/Verlies (EUR)'].sum()

    totale_aankoopwaarde = totale_waarde_portfolio - totale_winst_verlies
    totaal_rendement_pct = (
        totale_winst_verlies / totale_aankoopwaarde) if totale_aankoopwaarde > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Totale Waarde Portefeuille",
                value=format_euro(totale_waarde_portfolio))
    col2.metric(label="Totale Aankoopwaarde",
                value=format_euro(totale_aankoopwaarde))
    col3.metric(label="Totaal Winst/Verlies",
                value=format_euro(totale_winst_verlies))
    col4.metric(label="Totaal Rendement",
                value=f"{totaal_rendement_pct:.2%}".replace('.', ','))

    if st.sidebar.button('Historische data vandaag opslaan'):
        try:
            SCRIPT_MAP = Path(__file__).resolve().parent
        except NameError:
            SCRIPT_MAP = Path.cwd()
        sla_historische_data_op(
            date.today(), totale_waarde_portfolio, SCRIPT_MAP)
else:
    st.info(
        "Start met het vullen van je 'portefeuille.xlsx' bestand om de analyse te zien.")
