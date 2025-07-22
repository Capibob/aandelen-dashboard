import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
from datetime import timedelta

# Importeer de signaal-logica uit de bestaande engine
from active_trading_engine import bepaal_signaal_per_rij

def get_backtest_data(ticker, start_datum, eind_datum):
    """
    Haalt historische data op voor een specifieke periode voor de backtest.
    Haalt 300 dagen extra data op vóór de startdatum om voortschrijdende gemiddelden te initialiseren.
    """
    try:
        # We hebben extra data nodig voor de indicatoren (bv. 200d MA, 3m volume)
        start_datum_buffer = start_datum - timedelta(days=300)
        data = yf.download(ticker, start=start_datum_buffer, end=eind_datum, progress=False, auto_adjust=True)
        if data.empty:
            return pd.DataFrame()

        # FIX: Als yfinance een MultiIndex retourneert (bv. bij 1 ticker in een lijst),
        # maak er dan een enkele index van. Dit voorkomt de .str accessor fout.
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        return data
    except Exception as e:
        print(f"Fout bij ophalen data voor {ticker}: {e}")
        return pd.DataFrame()

def run_backtest(ticker, start_datum, eind_datum, start_kapitaal=10000,
                 transactie_kosten=5, signaal_vertraging=1, stop_loss_pct=0.05, take_profit_pct=0.10,
                 # Nieuwe parameters voor de signaal-engine
                 rsi_oversold=30, rsi_overbought=70, volume_drempel=1.5):
    """
    Voert de backtest uit voor een gegeven aandeel en periode.
    """
    data = get_backtest_data(ticker, start_datum, eind_datum)
    if data.empty:
        return None, "Geen data gevonden voor deze ticker en periode."

    # Bereken technische indicatoren voor de gehele periode
    data.ta.rsi(length=14, append=True)
    data.ta.macd(fast=12, slow=26, signal=9, append=True)
    data.ta.sma(length=20, append=True)

    # Volume Ratio (vergelijking 7d avg met 3m avg) - vereist extra data
    data['Volume_Avg_7d'] = data['Volume'].rolling(window=7).mean()
    data['Volume_Avg_3m'] = data['Volume'].rolling(window=63).mean()  # Approx. 3 maanden (63 handelsdagen)
    data['Volume Ratio'] = data['Volume_Avg_7d'] / data['Volume_Avg_3m']

    # Bundel de strategieparameters
    strategie_params = {
        'rsi_oversold': rsi_oversold,
        'rsi_overbought': rsi_overbought,
        'volume_drempel': volume_drempel
    }
    # Signalen genereren (met verschuiving om rekening te houden met vertraging)
    data['Signaal'] = data.apply(lambda row: bepaal_signaal_per_rij(row, **strategie_params), axis=1)
    data['Signaal_met_vertraging'] = data['Signaal'].shift(signaal_vertraging)

    # Start de simulatie
    posities = 0
    positie_type = "geen"  # "geen", "long", "short"
    kapitaal = start_kapitaal
    transacties = []

    for i in range(max(signaal_vertraging, 1), len(data)):
        vandaag = data.iloc[i]
        gesloten = False

        # --- Positiebeheer ---
        if posities > 0:  # We hebben een open positie (long of short)
            if positie_type == "long":
                # --- Check voor Stop Loss / Take Profit (Long) ---
                if vandaag['Low'] <= transacties[-1]['aankoop_prijs'] * (1 - stop_loss_pct):
                    # Stop Loss geraakt (Long)
                    kapitaal += (transacties[-1]['aankoop_prijs'] * (1 - stop_loss_pct) - transactie_kosten)
                    transacties[-1]['verkoop_prijs'] = transacties[-1]['aankoop_prijs'] * (1 - stop_loss_pct)
                    transacties[-1]['datum_uit'] = vandaag.name
                    transacties[-1]['reden'] = "Stop Loss (Long)"
                    transacties[-1]['resultaat'] = transacties[-1]['verkoop_prijs'] - transacties[-1]['aankoop_prijs'] - transactie_kosten
                    posities = 0
                    positie_type = "geen"
                    gesloten = True

                elif vandaag['High'] >= transacties[-1]['aankoop_prijs'] * (1 + take_profit_pct):
                    # Take Profit geraakt (Long)
                    kapitaal += (transacties[-1]['aankoop_prijs'] * (1 + take_profit_pct) - transactie_kosten)
                    transacties[-1]['verkoop_prijs'] = transacties[-1]['aankoop_prijs'] * (1 + take_profit_pct)
                    transacties[-1]['datum_uit'] = vandaag.name
                    transacties[-1]['reden'] = "Take Profit (Long)"
                    transacties[-1]['resultaat'] = transacties[-1]['verkoop_prijs'] - transacties[-1]['aankoop_prijs'] - transactie_kosten
                    posities = 0
                    positie_type = "geen"
                    gesloten = True

                # --- Check voor Verkoopsignaal (indien niet gesloten door SL/TP) ---
                elif "VERKOOP" in vandaag['Signaal_met_vertraging'] and not gesloten:
                    # Verkoopsignaal (Long positie sluiten)
                    kapitaal += (vandaag['Close'] - transactie_kosten)  # Verkoop tegen slotkoers
                    transacties[-1]['verkoop_prijs'] = vandaag['Close']
                    transacties[-1]['datum_uit'] = vandaag.name
                    transacties[-1]['reden'] = "Verkoopsignaal (Long sluiten)"
                    transacties[-1]['resultaat'] = transacties[-1]['verkoop_prijs'] - transacties[-1]['aankoop_prijs'] - transactie_kosten
                    posities = 0
                    positie_type = "geen"
                    gesloten = True

            elif positie_type == "short":
                # --- Check voor Stop Loss / Take Profit (Short) ---
                if vandaag['High'] >= transacties[-1]['aankoop_prijs'] * (1 + stop_loss_pct):
                    # Stop Loss geraakt (Short) - verlies wanneer koers stijgt
                    kapitaal += (transacties[-1]['aankoop_prijs'] * (1 + stop_loss_pct) - transactie_kosten) # Aangepast voor short
                    transacties[-1]['verkoop_prijs'] = transacties[-1]['aankoop_prijs'] * (1 + stop_loss_pct)
                    transacties[-1]['datum_uit'] = vandaag.name
                    transacties[-1]['reden'] = "Stop Loss (Short)"
                    transacties[-1]['resultaat'] = transacties[-1]['aankoop_prijs'] - transacties[-1]['verkoop_prijs'] - transactie_kosten # Aangepast
                    posities = 0
                    positie_type = "geen"
                    gesloten = True

                elif vandaag['Low'] <= transacties[-1]['aankoop_prijs'] * (1 - take_profit_pct):
                    # Take Profit geraakt (Short) - winst wanneer koers daalt
                    kapitaal += (transacties[-1]['aankoop_prijs'] * (1 - take_profit_pct) - transactie_kosten) # Aangepast
                    transacties[-1]['verkoop_prijs'] = transacties[-1]['aankoop_prijs'] * (1 - take_profit_pct)
                    transacties[-1]['datum_uit'] = vandaag.name
                    transacties[-1]['reden'] = "Take Profit (Short)"
                    transacties[-1]['resultaat'] = transacties[-1]['aankoop_prijs'] - transacties[-1]['verkoop_prijs'] - transactie_kosten # Aangepast
                    posities = 0
                    positie_type = "geen"
                    gesloten = True

                # --- Check voor Koopsignaal (indien niet gesloten door SL/TP) ---
                elif "KOOP" in vandaag['Signaal_met_vertraging'] and not gesloten:
                    # Koopsignaal (Short positie sluiten)
                    kapitaal += (vandaag['Close'] - transactie_kosten)  # Terugkoop tegen slotkoers
                    transacties[-1]['verkoop_prijs'] = vandaag['Close']
                    transacties[-1]['datum_uit'] = vandaag.name
                    transacties[-1]['reden'] = "Koopsignaal (Short sluiten)"
                    transacties[-1]['resultaat'] = transacties[-1]['aankoop_prijs'] - transacties[-1]['verkoop_prijs'] - transactie_kosten # Aangepast
                    posities = 0
                    positie_type = "geen"
                    gesloten = True

        # --- Check voor Nieuwe Signalen (indien geen positie open) ---
        if posities == 0:
            if "KOOP" in vandaag['Signaal_met_vertraging']:
                # Koopsignaal -> Open Long Positie
                transacties.append({
                    'datum_in': vandaag.name,
                    'aankoop_prijs': vandaag['Close'],
                    'verkoop_prijs': None,
                    'datum_uit': None,
                    'reden': "Koopsignaal (Open Long)",
                    'resultaat': None,
                    'positie_type': "long"
                })
                kapitaal -= transactie_kosten  # Kosten bij aankoop
                posities = 1
                positie_type = "long"

            elif "VERKOOP" in vandaag['Signaal_met_vertraging']:
                # Verkoopsignaal -> Open Short Positie
                transacties.append({
                    'datum_in': vandaag.name,
                    'aankoop_prijs': vandaag['Close'],  # Verkoopprijs bij short
                    'verkoop_prijs': None,
                    'datum_uit': None,
                    'reden': "Verkoopsignaal (Open Short)",
                    'resultaat': None,
                    'positie_type': "short"
                })
                kapitaal -= transactie_kosten  # Kosten bij verkoop (short)
                posities = 1
                positie_type = "short"

    # --- Afsluiten van open posities aan het einde van de periode ---
    # Dit is belangrijk om het resultaat correct te berekenen, ook al is er geen verkoopsignaal
    if posities > 0:
        transacties[-1]['verkoop_prijs'] = data.iloc[-1]['Close']  # Sluiten tegen slotkoers einddatum
        transacties[-1]['datum_uit'] = data.iloc[-1].name
        transacties[-1]['reden'] = f"Einde Periode ({positie_type})"
        if positie_type == "long":
            transacties[-1]['resultaat'] = transacties[-1]['verkoop_prijs'] - transacties[-1]['aankoop_prijs'] - transactie_kosten
        elif positie_type == "short":
            transacties[-1]['resultaat'] = transacties[-1]['aankoop_prijs'] - transacties[-1]['verkoop_prijs'] - transactie_kosten
        kapitaal += transacties[-1]['resultaat']
        posities = 0
        positie_type = "geen"

    # --- Berekening van performance en statistieken ---
    df_transacties = pd.DataFrame(transacties)
    # ... (rest van de code blijft hetzelfde, maar gebruik df_transacties) ...
    aantal_transacties = len(df_transacties)
    if aantal_transacties > 0:
        totaal_resultaat = df_transacties['resultaat'].sum()
        winstgevende_transacties = len(df_transacties[df_transacties['resultaat'] > 0])
        verlieslatende_transacties = aantal_transacties - winstgevende_transacties
        percentage_winstgevend = (winstgevende_transacties / aantal_transacties) * 100
        gemiddelde_winst = df_transacties[df_transacties['resultaat'] > 0]['resultaat'].mean() if winstgevende_transacties > 0 else 0
        gemiddelde_verlies = df_transacties[df_transacties['resultaat'] < 0]['resultaat'].mean() if verlieslatende_transacties > 0 else 0
    else:
        totaal_resultaat = 0
        percentage_winstgevend = 0
        gemiddelde_winst = 0
        gemiddelde_verlies = 0

    # Bereken eindwaarde indien nog open posities
    if posities > 0:
        transacties[-1]['verkoop_prijs'] = data.iloc[-1]['Close']
        transacties[-1]['datum_uit'] = data.iloc[-1].name
        transacties[-1]['resultaat'] = transacties[-1]['verkoop_prijs'] - transacties[-1]['aankoop_prijs'] - transactie_kosten
        kapitaal += transacties[-1]['resultaat']

    # Analyseer de resultaten
    df_transacties = pd.DataFrame(transacties)
    aantal_transacties = len(df_transacties)
    if aantal_transacties > 0:
        totaal_resultaat = df_transacties['resultaat'].sum()
        winstgevende_transacties = len(df_transacties[df_transacties['resultaat'] > 0])
        verlieslatende_transacties = aantal_transacties - winstgevende_transacties
        percentage_winstgevend = (winstgevende_transacties / aantal_transacties) * 100 if aantal_transacties > 0 else 0
        gemiddelde_winst = df_transacties[df_transacties['resultaat'] > 0]['resultaat'].mean() if winstgevende_transacties > 0 else 0
        gemiddelde_verlies = df_transacties[df_transacties['resultaat'] < 0]['resultaat'].mean() if verlieslatende_transacties > 0 else 0
    else:
        totaal_resultaat = 0
        percentage_winstgevend = 0
        gemiddelde_winst = 0
        gemiddelde_verlies = 0

    eind_waarde = kapitaal
    rendement_pct = ((eind_waarde - start_kapitaal) / start_kapitaal) * 100

    resultaten = {
        'ticker': ticker,
        'start_datum': start_datum,
        'eind_datum': eind_datum,
        'start_kapitaal': start_kapitaal,
        'eind_waarde': eind_waarde,
        'rendement_pct': rendement_pct,
        'aantal_transacties': aantal_transacties,
        'totaal_resultaat': totaal_resultaat,
        'percentage_winstgevend': percentage_winstgevend,
        'gemiddelde_winst': gemiddelde_winst,
        'gemiddelde_verlies': gemiddelde_verlies,
        'transacties': df_transacties
    }
    return resultaten, None


def optimaliseer_backtest(ticker, start_datum, eind_datum, start_kapitaal=10000, transactie_kosten=5,
                       signaal_vertraging_range=(0, 3), stop_loss_pct_range=(0.01, 0.10), take_profit_pct_range=(0.05, 0.20),
                       metriek='rendement'):
    """
    Optimaliseert de backtest parameters met een eenvoudige grid search.
    """
    beste_resultaten = None
    beste_parameters = {}

    # Genereer parameter combinaties (grid search)
    signaal_vertraging_opties = range(signaal_vertraging_range[0], signaal_vertraging_range[1] + 1)
    stop_loss_pct_opties = [round(x, 2) for x in np.arange(stop_loss_pct_range[0], stop_loss_pct_range[1] + 0.01, 0.01)]
    take_profit_pct_opties = [round(x, 2) for x in np.arange(take_profit_pct_range[0], take_profit_pct_range[1] + 0.01, 0.01)]

    aantal_combinaties = len(signaal_vertraging_opties) * len(stop_loss_pct_opties) * len(take_profit_pct_opties)
    print(f"Aantal parameter combinaties om te testen: {aantal_combinaties}")

    i = 0
    for signaal_vertraging in signaal_vertraging_opties:
        for stop_loss_pct in stop_loss_pct_opties:
            for take_profit_pct in take_profit_pct_opties:
                i += 1
                print(f"Backtest {i}/{aantal_combinaties} (vertraging={signaal_vertraging}, stop={stop_loss_pct}, take={take_profit_pct})")
                resultaten, foutmelding = run_backtest(
                    ticker=ticker,
                    start_datum=start_datum,
                    eind_datum=eind_datum,
                    start_kapitaal=start_kapitaal,
                    transactie_kosten=transactie_kosten,
                    signaal_vertraging=signaal_vertraging,
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=take_profit_pct
                )

                if foutmelding:
                    print(f"  Backtest mislukt: {foutmelding}")
                    continue

                if resultaten:
                    if metriek == 'rendement':
                        prestatie = resultaten['rendement_pct']
                    elif metriek == 'sharpe':  # Sharpe ratio (niet geïmplementeerd)
                        prestatie = 0  # Placeholder
                        print("  Sharpe Ratio optimalisatie is nog niet geïmplementeerd.")
                    else:
                        print(f"  Ongeldige metriek: {metriek}. Gebruik 'rendement'.")
                        return None, "Ongeldige optimalisatiemetriek."

                    if beste_resultaten is None or prestatie > beste_resultaten:
                        beste_resultaten = prestatie
                        beste_parameters = {
                            'signaal_vertraging': signaal_vertraging,
                            'stop_loss_pct': stop_loss_pct,
                            'take_profit_pct': take_profit_pct
                        }
                        print(f"  Nieuw beste resultaat: {beste_resultaten:.2f} (parameters: {beste_parameters})")

    if beste_resultaten is not None:
        print(f"Optimalisatie voltooid. Beste {metriek}: {beste_resultaten:.2f} met parameters: {beste_parameters}")
        return {
            'beste_resultaten': beste_resultaten,
            'beste_parameters': beste_parameters
        }, None
    else:
        print("Optimalisatie mislukt: geen geldige resultaten gevonden.")
        return None, "Optimalisatie mislukt: geen geldige resultaten gevonden."