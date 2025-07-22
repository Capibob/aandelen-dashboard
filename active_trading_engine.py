import pandas as pd


def genereer_actieve_handel_signalen(df):
    """
    Genereert koop- en verkoopsignalen op basis van actieve, technische handelsstrategieën.
    Deze engine staat los van de 'buy-and-hold' adviesmotor.
    """
    df_signalen = df.copy()

    for index, rij in df_signalen.iterrows():
        signaal = bepaal_signaal_per_rij(rij)
        df_signalen.at[index, 'Signaal'] = signaal

    return df_signalen


def bepaal_signaal_per_rij(rij_data, **kwargs):
    """
    Bepaalt een signaal voor één aandeel op basis van een combinatie van technische indicatoren.
    Strategie: Zoekt naar een cluster van koopsignalen.
    **kwargs accepteert optionele drempelwaarden, bv. rsi_oversold=30.
    """
    signalen_gevonden = []

    # Haal drempelwaarden uit kwargs, met standaardwaarden
    rsi_oversold = kwargs.get('rsi_oversold', 30)
    rsi_overbought = kwargs.get('rsi_overbought', 70)
    volume_drempel = kwargs.get('volume_drempel', 1.5)
    # --- Data veilig ophalen ---
    huidige_koers = rij_data.get('Huidige koers (EUR)')
    vorige_koers = rij_data.get('Vorige koers (EUR)')
    rsi = rij_data.get('RSI')
    rsi_prev = rij_data.get('RSI_prev')
    macd = rij_data.get('MACD')
    macd_signal = rij_data.get('MACD_signal')
    macd_prev = rij_data.get('MACD_prev')
    macd_signal_prev = rij_data.get('MACD_signal_prev')
    ma20 = rij_data.get('20d MA')
    volume_ratio = rij_data.get('Volume Ratio', 0.0)

    # --- Controleer op de aanwezigheid van de signalen ---

    # 1. RSI is recent uit de 'oversold'-zone gekomen (bv. < 30)
    if rsi is not None and rsi_prev is not None:
        if rsi > rsi_oversold and rsi_prev <= rsi_oversold:
            signalen_gevonden.append("RSI Bullish Cross")

    # 2. MACD-lijn heeft zojuist een bullish cross gemaakt
    if all(v is not None for v in [macd, macd_signal, macd_prev, macd_signal_prev]):
        if macd > macd_signal and macd_prev <= macd_signal_prev:
            signalen_gevonden.append("MACD Bullish Cross")

    # 3. Koers is net boven zijn 20-daags gemiddelde gebroken
    if all(v is not None for v in [huidige_koers, vorige_koers, ma20]):
        if huidige_koers > ma20 and vorige_koers <= ma20:
            signalen_gevonden.append("Koers > 20d MA")

    # 4. Het handelsvolume is significant hoger dan normaal (bv. > 50%)
    if volume_ratio > volume_drempel:
        signalen_gevonden.append("Hoog Volume")

    # --- Mogelijk Verkoopsignalen ---

    # 1. RSI zakt onder 70
    if rsi is not None and rsi_prev is not None:
        if rsi < rsi_overbought and rsi_prev >= rsi_overbought:
            signalen_gevonden.append("RSI Bearish Cross")

    # 2. MACD Bearish Cross
    if all(v is not None for v in [macd, macd_signal, macd_prev, macd_signal_prev]):
        if macd < macd_signal and macd_prev >= macd_signal_prev:
            signalen_gevonden.append("MACD Bearish Cross")

    # 3. Koers onder 20d MA
    if all(v is not None for v in [huidige_koers, vorige_koers, ma20]):
        if huidige_koers < ma20 and vorige_koers >= ma20:
            signalen_gevonden.append("Koers < 20d MA")

    # --- Finale Beslissing ---
    aantal_signalen = len(signalen_gevonden)
    if aantal_signalen == 0:
        return "NEUTRAAL"

    signaal_tekst = ", ".join(signalen_gevonden)
    if "Bearish" in signaal_tekst and aantal_signalen >= 2:  # Pas drempel aan voor verkoop
        return f"VERKOOP - {signaal_tekst}"
    elif aantal_signalen >= 3:
        return f"KOOP (STERK) - {signaal_tekst}"
    elif aantal_signalen >= 2:
        return f"KOOP - {signaal_tekst}"
    else:
        return f"ZWAK SIGNAAL - {signaal_tekst}"