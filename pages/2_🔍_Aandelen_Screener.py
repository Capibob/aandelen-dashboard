import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# Importeer vanuit onze modulaire bestanden
from config import build_profile_sidebar
from data_processing import get_all_ticker_info, get_wisselkoers, bepaal_land_uit_markt, get_historische_data
from advice_engine import genereer_advies_per_rij
# Importeer de SIMPELE analysefunctie voor de screener en de configuratiecheck
from ai_analysis import genereer_simpele_ai_analyse, AI_IS_CONFIGURED
from utils import format_euro, stijl_advies_kolom


def format_dataframe_for_display(df, kolommen):
    """Formatteert een dataframe voor weergave in Streamlit."""
    df_display = df.copy()
    bestaande_kolommen = [col for col in kolommen if col in df_display.columns]

    for col in ['Potentieel %', 'Winstmarge %', 'Return on Equity', 'Dagwijziging %']:
        if col in df_display.columns:
            df_display[col] = pd.to_numeric(df_display[col], errors='coerce').apply(
                lambda x: f'{x:.2%}'.replace('.', ',') if pd.notna(x) else 'N/B')
    if 'Volume Ratio' in df_display.columns:
        df_display['Volume Ratio'] = pd.to_numeric(df_display['Volume Ratio'], errors='coerce').apply(
            lambda x: f'{x:.2f}x'.replace('.', ',') if pd.notna(x) else 'N/B')
    if 'Huidige koers (EUR)' in df_display.columns:
        df_display['Huidige koers (EUR)'] = df_display['Huidige koers (EUR)'].apply(
            format_euro)
    return df_display[bestaande_kolommen]


# --- Vaste, betrouwbare lijsten met tickers ---
indices = {
    "BEL 20 (België)": ["ABI.BR", "ACKB.BR", "AED.BR", "AGS.BR", "ARGX.BR", "BAR.BR", "COFB.BR", "ELI.BR", "GBLB.BR", "KBC.BR", "MELE.BR", "UCB.BR", "UMI.BR", "WDP.BR", "SYNT.BR", "DEXB.BR", "GLPG.AS", "LOTB.BR"],
    "AEX 25 (Nederland)": ["ADYEN.AS", "AD.AS", "AGN.AS", "AKZA.AS", "ASML.AS", "ASRNL.AS", "DSFIR.AS", "HEIA.AS", "IMCD.AS", "INGA.AS", "KPN.AS", "NN.AS", "PHIA.AS", "PRX.AS", "RAND.AS", "REN.AS", "SHELL.AS", "UNA.AS", "WKL.AS"],
    "DAX 40 (Duitsland)": ["ADS.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BEI.DE", "BMW.DE", "BNR.DE", "CON.DE", "DPW.DE", "DTE.DE", "EOAN.DE", "HEI.DE", "HEN3.DE", "IFX.DE", "MRK.DE", "RWE.DE", "SAP.DE", "SIE.DE", "VNA.DE", "1COV.DE", "AIR.DE", "DB1.DE", "DTG.DE", "DHER.DE", "HDB.DE", "QIA.DE", "SHL.DE", "ZAL.DE"],
    "Dow Jones 30 (VS)": ["AXP", "AMGN", "AAPL", "BA", "CAT", "CSCO", "CVX", "GS", "HD", "HON", "IBM", "INTC", "JNJ", "KO", "JPM", "MCD", "MMM", "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "CRM", "VZ", "V", "WBA", "WMT", "DIS", "DOW"],
    "Euro Stoxx 50": ["ADS.DE", "AD.AS", "AI.PA", "AIR.PA", "ALV.DE", "ASML.AS", "BAS.DE", "BAYN.DE", "BBVA.MC", "BMW.DE", "BN.PA", "BNP.PA", "CRG.IR", "CS.PA", "DAN.PA", "DB1.DE", "DTE.DE", "ENEL.MI", "ENI.MI", "FLTR.IR", "IBE.MC", "IFX.DE", "IND.MC", "INGA.AS", "ISP.MI", "KER.PA", "KNE.DE", "LVMH.PA", "MBG.DE", "MUV2.DE", "OR.PA", "PHIA.AS", "RACE.MI", "SAN.PA", "SAP.DE", "SIE.DE", "STLA.MI", "TTE.PA", "VOW3.DE", "VNA.DE"],
    "NASDAQ 100": ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "TSLA", "META", "AVGO", "PEP", "COST", "ASML", "AZN", "AMD", "CSCO", "TMUS", "INTC", "ADBE", "CMCSA", "TXN", "QCOM", "HON", "INTU", "AMGN", "ISRG", "SBUX", "MDLZ", "GILD", "PYPL", "ADI", "BKNG", "REGN", "VRTX", "LRCX", "AMAT", "MU", "CSX", "PANW", "SNPS", "CDNS", "MAR", "KLAC", "EXC", "AEP", "FTNT", "MNST", "ORLY", "CTAS", "PCAR", "DXCM", "CPRT", "PAYX", "ROST", "IDXX", "LULU", "WDAY", "FAST", "CEG", "DDOG", "XEL", "MCHP", "MRVL", "WBD", "KDP", "SIRI", "BKR", "CTSH", "EA", "KHC", "OKTA", "ZM", "ILMN", "BIIB", "CRWD", "MELI", "PYPL", "TEAM"],
    "WIG20 (Polen)": ["PKO.WA", "PKN.WA", "PZU.WA", "PEO.WA", "LPP.WA", "DNP.WA", "SPL.WA", "ALE.WA", "KGH.WA", "CDR.WA", "ALR.WA", "KRU.WA", "MBK.WA", "KTY.WA", "BDX.WA", "PGE.WA", "OPL.WA", "CPS.WA", "PCO.WA", "JSW.WA"],
    "OMXS30 (Zweden)": ["ATCO-A.ST", "ALFA.ST", "AZN.ST", "BOL.ST", "ELUX-B.ST", "ERIC-B.ST", "ESSITY-B.ST", "EVO.ST", "GETI-B.ST", "HEXA-B.ST", "HM-B.ST", "INVE-B.ST", "KINV-B.ST", "NDA-SE.ST", "SAND.ST", "SCA-B.ST", "SEB-A.ST", "SHB-A.ST", "SKF-B.ST", "SWED-A.ST", "TELIA.ST", "VOLV-B.ST", "ALIV-SDB.ST", "SINCH.ST", "NIBE-B.ST"],
    "OMXC25 (Denemarken)": ["MAERSK-B.CO", "NOVO-B.CO", "DSV.CO", "ORSTED.CO", "PNDORA.CO", "GN.CO", "VWS.CO", "NZYM-B.CO", "GMAB.CO", "COLO-B.CO", "CHR.CO", "CARL-B.CO", "TRYG.CO", "ROCK-B.CO", "DANSKE.CO", "DEMANT.CO", "ISS.CO", "BAVA.CO", "AMBU-B.CO"],
    "OMXH25 (Finland)": ["NESTE.HE", "NOKIA.HE", "SAMPO.HE", "KNEBV.HE", "UPM.HE", "FORTUM.HE", "ORNBV.HE", "TELIA.HE", "WRT1V.HE", "ELISA.HE", "NDA-FI.HE", "OUT1V.HE", "KCR.HE", "MOCORP.HE"],
    "OBX 25 (Noorwegen)": ["EQNR.OL", "DNB.OL", "TGS.OL", "NHY.OL", "ORK.OL", "MOWI.OL", "AKRBP.OL", "TEL.OL", "SUBC.OL", "YAR.OL", "FRO.OL", "STB.OL", "AKER.OL", "SCHA.OL", "PGS.OL", "NOD.OL", "OTL.OL"],
    "S&P 500 (Volledig)": [
        'A', 'AAL', 'AAP', 'AAPL', 'ABBV', 'ABC', 'ABT', 'ACGL', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEE', 'AEP', 'AES', 'AFL', 'AIG', 'AIZ',
        'AJG', 'AKAM', 'ALB', 'ALGN', 'ALK', 'ALL', 'ALLE', 'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN', 'AMP', 'AMT', 'AMZN', 'ANET', 'ANSS', 'AON', 'AOS',
        'APA', 'APD', 'APH', 'APTV', 'ARE', 'ATO', 'AVB', 'AVGO', 'AVY', 'AWK', 'AXON', 'AXP', 'AZO', 'BA', 'BAC', 'BALL', 'BAX', 'BBWI', 'BBY', 'BDX',
        'BEN', 'BF-B', 'BG', 'BIIB', 'BIO', 'BK', 'BKNG', 'BKR', 'BLK', 'BMY', 'BR', 'BRK-B', 'BRO', 'BSX', 'BWA', 'BX', 'BXP', 'C', 'CAG', 'CAH',
        'CAT', 'CB', 'CBOE', 'CBRE', 'CDNS', 'CDW', 'CE', 'CEG', 'CF', 'CFG', 'CHD', 'CHRW', 'CHTR', 'CI', 'CINF', 'CL', 'CLX', 'CMA', 'CMCSA', 'CME',
        'CMG', 'CMI', 'CMS', 'CNC', 'CNP', 'COF', 'COO', 'COP', 'COR', 'COST', 'CPAY', 'CPB', 'CPRT', 'CPT', 'CRL', 'CRM', 'CSCO', 'CSGP', 'CSX', 'CTAS',
        'CTLT', 'CTRA', 'CTSH', 'CVS', 'CVX', 'D', 'DAL', 'DD', 'DE', 'DECK', 'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DLR', 'DLTR', 'DOV', 'DOW', 'DPZ',
        'DRI', 'DTE', 'DUK', 'DVA', 'DVN', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX', 'EIX', 'EL', 'ELV', 'EMN', 'EMR', 'ENPH', 'EOG', 'EPAM', 'EQIX',
        'EQR', 'EQT', 'ES', 'ESS', 'ETN', 'ETR', 'ETSY', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG', 'FAST', 'FCX', 'FDS', 'FDX', 'FE',
        'FFIV', 'FI', 'FICO', 'FIS', 'FITB', 'FMC', 'FOX', 'FOXA', 'FRT', 'FSLR', 'FTNT', 'FTV', 'GD', 'GE', 'GEHC', 'GEN', 'GILD', 'GIS', 'GL', 'GLW',
        'GM', 'GNRC', 'GOOG', 'GOOGL', 'GPC', 'GPN', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HD', 'HES', 'HIG', 'HII', 'HLT', 'HOLX', 'HON',
        'HPE', 'HPQ', 'HRL', 'HSIC', 'HSY', 'HUBB', 'HUM', 'HWM', 'IBM', 'ICE', 'IDXX', 'IEX', 'IFF', 'ILMN', 'INCY', 'INTC', 'INTU', 'INVH', 'IP', 'IPG',
        'IQV', 'IR', 'IRM', 'ISRG', 'IT', 'ITW', 'IVZ', 'J', 'JBHT', 'JCI', 'JKHY', 'JNJ', 'JNPR', 'JPM', 'K', 'KDP', 'KEY', 'KEYS', 'KHC', 'KIM',
        'KLAC', 'KMB', 'KMI', 'KMX', 'KO', 'KR', 'KVUE', 'L', 'LDOS', 'LEN', 'LH', 'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNT', 'LOW', 'LRCX', 'LULU',
        'LVS', 'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MGM', 'MHK', 'MKC', 'MKTX',
        'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOS', 'MPC', 'MPWR', 'MRK', 'MRNA', 'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTD', 'MU', 'NCLH', 'NDAQ',
        'NEE', 'NEM', 'NFLX', 'NI', 'NKE', 'NOC', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWS', 'NWSA', 'NXPI', 'O', 'ODFL', 'OKE',
        'OMC', 'ON', 'ORCL', 'ORLY', 'OXY', 'PANW', 'PARA', 'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEAK', 'PEG', 'PEP', 'PFE', 'PFG', 'PG', 'PGR', 'PH', 'PHM',
        'PKG', 'PLD', 'PM', 'PNC', 'PNR', 'PNW', 'PODD', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PWR', 'PXD', 'PYPL', 'QCOM', 'QRVO', 'RCL',
        'REG', 'REGN', 'RF', 'RHI', 'RJF', 'RL', 'RMD', 'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX', 'RVTY', 'SBAC', 'SBUX', 'SCHW', 'SEDG', 'SEE', 'SHW',
        'SJM', 'SLB', 'SNA', 'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STT', 'STX', 'STZ', 'SWK', 'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TDG',
        'TDY', 'TECH', 'TEL', 'TER', 'TFC', 'TFX', 'TGT', 'TJX', 'TMO', 'TMUS', 'TPR', 'TRGP', 'TRMB', 'TROW', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTWO',
        'TXN', 'TXT', 'UA', 'UAA', 'UAL', 'UDR', 'UHS', 'ULTA', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V', 'VFC', 'VICI', 'VLO', 'VMC', 'VRSK', 'VRSN',
        'VRTX', 'VTR', 'VTRS', 'VZ', 'WAB', 'WAT', 'WBD', 'WCN', 'WDC', 'WEC', 'WELL', 'WFC', 'WHR', 'WM', 'WMB', 'WMT', 'WRB', 'WRK', 'WST', 'WY', 'WYNN',
        'XEL', 'XOM', 'XRAY', 'XYL', 'YUM', 'ZBH', 'ZBRA', 'ZTS'
    ]
}

# --- Streamlit Pagina ---
st.set_page_config(layout="wide", page_title="Aandelen Screener")
mijn_profiel = build_profile_sidebar()
st.title("🔍 Aandelen Screener")
st.info("Scan een index en vind nieuwe koopkansen op basis van jouw actieve profielinstellingen in de zijbalk.")

# --- Session State Initialisatie ---
# Dit zorgt ervoor dat de resultaten bewaard blijven, zelfs als je op een andere knop klikt.
if 'screener_results' not in st.session_state:
    st.session_state.screener_results = None

index_keuze = st.selectbox(
    "Kies een aandelenuniversum om te scannen:", indices.keys())

if st.button(f"Start screener voor {index_keuze}"):
    tickers_to_scan = list(dict.fromkeys(indices[index_keuze]))

    resultaten = []  # Hernoemd van 'koopkansen' naar 'resultaten'
    progress_bar = st.progress(0, text="Screener gestart...")

    for i, ticker in enumerate(tickers_to_scan):
        progress_text = f"Analyse van {ticker}... ({i+1}/{len(tickers_to_scan)})"
        progress_bar.progress(
            (i + 1) / len(tickers_to_scan), text=progress_text)

        info = get_all_ticker_info(ticker)
        if info and info.get('regularMarketPrice') is not None:
            rij_data = {'Ticker': ticker,
                        'Naam': info.get('shortName', ticker)}

            koers_orig = info.get('regularMarketPrice')
            valuta_orig = info.get('currency', 'N/A')
            wisselkoers = get_wisselkoers(valuta_orig, 'EUR')
            if not (koers_orig and valuta_orig and wisselkoers):
                continue

            koers_eur = koers_orig * wisselkoers
            rij_data['Huidige koers (EUR)'] = koers_eur
            koersdoel_orig = info.get('targetMeanPrice')
            if koersdoel_orig and koers_eur > 0:
                rij_data['Potentieel %'] = (
                    koersdoel_orig * wisselkoers / koers_eur) - 1

            rij_data['P/E Ratio'] = info.get('trailingPE')
            rij_data['P/B Ratio'] = info.get('priceToBook')
            rij_data['P/S Ratio'] = info.get('priceToSalesTrailing12Months')
            debt_equity_raw = info.get('debtToEquity')
            rij_data['Debt/Equity'] = debt_equity_raw / \
                100 if debt_equity_raw is not None else pd.NA
            rij_data['Winstmarge %'] = info.get('profitMargins')
            rij_data['Dagwijziging %'] = dagwijziging_raw / 100 if (
                dagwijziging_raw := info.get('regularMarketChangePercent')) is not None else 0.0  # noqa: E203
            hist_df = get_historische_data(ticker)
            if not hist_df.empty:
                gemiddeld_volume_7d = hist_df['Volume'].tail(7).mean()
                gemiddeld_volume_3m = info.get('averageDailyVolume3Month', 0)
                if gemiddeld_volume_3m > 0:
                    rij_data['Volume Ratio'] = gemiddeld_volume_7d / \
                        gemiddeld_volume_3m
            rij_data['Beta'] = info.get('beta')
            rij_data['Return on Equity'] = info.get('returnOnEquity')
            rij_data['50d MA'] = info.get('fiftyDayAverage')
            rij_data['200d MA'] = info.get('twoHundredDayAverage')
            # --- TOEGEVOEGD: De cruciale ontbrekende dataregel ---
            rij_data['52w High'] = info.get('fiftyTwoWeekHigh')

            # We genereren altijd een advies
            advies_details = genereer_advies_per_rij(
                rij_data, mijn_profiel, 999_999_999)

            # --- AANGEPAST: De filter is verwijderd ---
            # We voegen nu elk aandeel toe aan de resultatenlijst
            # We slaan alleen de advies-tekst op, niet de hele dictionary
            rij_data['Advies'] = advies_details['advies']
            rij_data['Sector'] = info.get('sector', 'Onbekend')
            rij_data['Regio'] = info.get('country') or bepaal_land_uit_markt(
                info.get('exchangeName', ''))
            resultaten.append(rij_data)

    progress_bar.empty()  # Verberg de progress bar

    # Sla de resultaten op in de session state
    st.session_state.screener_results = pd.DataFrame(
        resultaten) if resultaten else pd.DataFrame()

# --- Resultaten Weergeven (buiten de 'if st.button' block) ---
# We controleren of er resultaten in de session state zijn om weer te geven.
if st.session_state.screener_results is not None:
    result_df = st.session_state.screener_results

    # Als de screener nog niet is gedraaid, tonen we niks.
    if result_df.empty and len(st.session_state.screener_results.columns) == 0:
        st.stop()

    st.success(f"Analyse voltooid voor {len(result_df)} aandelen!")

    # Definieer de kolommen die we willen tonen
    relevante_kolommen_screener = ['Naam', 'Ticker', 'Advies', 'Sector', 'Regio',
                                   'Huidige koers (EUR)', 'Potentieel %', 'P/E Ratio', 'P/B Ratio', 'P/S Ratio', 'Debt/Equity', 'Winstmarge %', 'Return on Equity', 'Beta']

    # Splits de resultaten op in koopkansen en de rest
    koopkansen_df = result_df[result_df['Advies'].str.contains(
        'KOOP', na=False)]
    andere_resultaten_df = result_df[~result_df['Advies'].str.contains(
        'KOOP', na=False)]

    # Toon de koopkansen prominent
    st.subheader(f"✅ {len(koopkansen_df)} Koopkansen Gevonden")
    if not koopkansen_df.empty:
        koopkansen_display = format_dataframe_for_display(
            koopkansen_df, relevante_kolommen_screener)
        st.dataframe(koopkansen_display.style.applymap(
            stijl_advies_kolom, subset=['Advies']))
    else:
        st.write("Geen aandelen voldeden aan je 'KOOP'-criteria.")

    # --- AI Analyse Sectie ---
    if not koopkansen_df.empty:
        st.subheader("🤖 AI-Gedreven Kwalitatieve Analyse")
        st.info("Selecteer een van de koopkansen hierboven om een diepgaandere analyse door Gemini te laten uitvoeren.")

        if not AI_IS_CONFIGURED:
            st.warning(
                "Voeg je `GEMINI_API_KEY` toe aan je `.streamlit/secrets.toml` bestand om deze functie te gebruiken.")
        else:
            koopkansen_namen = koopkansen_df['Naam'].tolist()
            geselecteerd_aandeel_naam = st.selectbox(
                "Kies een aandeel voor analyse:",
                options=koopkansen_namen
            )

            if st.button(f"Genereer AI analyse voor {geselecteerd_aandeel_naam}"):
                geselecteerd_aandeel_rij = koopkansen_df[koopkansen_df['Naam']
                                                         == geselecteerd_aandeel_naam].iloc[0]
                ticker = geselecteerd_aandeel_rij['Ticker']
                with st.spinner(f"Gemini analyseert {geselecteerd_aandeel_naam}... Dit kan even duren."):
                    st.markdown(genereer_simpele_ai_analyse(ticker))

    # Toon de overige resultaten in een inklapbare sectie
    with st.expander(f"Bekijk de overige {len(andere_resultaten_df)} geanalyseerde aandelen"):
        andere_display = format_dataframe_for_display(
            andere_resultaten_df, relevante_kolommen_screener)
        st.dataframe(andere_display.style.applymap(
            stijl_advies_kolom, subset=['Advies']))
