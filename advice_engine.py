import pandas as pd


def genereer_adviezen(df, profiel):
    """Loopt door een dataframe en past de adviesmotor toe op elk aandeel."""
    df_advies = df.copy()
    totale_waarde = df_advies['Huidige Waarde (EUR)'].sum()
    if totale_waarde > 0:
        for index, rij in df_advies.iterrows():
            # Verbeterde, flexibele check: gebruik 'Type Asset' of val terug op 'Type'
            asset_type = rij.get('Type Asset') or rij.get('Type')
            if str(asset_type or '').strip().lower() == 'aandeel':
                # We vangen nu de volledige dictionary op
                advies_details = genereer_advies_per_rij(rij, profiel, totale_waarde)
                # We slaan alleen het advies op in de hoofd-dataframe
                df_advies.at[index, 'Advies'] = advies_details['advies']
    return df_advies


def genereer_advies_per_rij(rij_data, profiel, totale_portefeuille_waarde):
    """
    De finale, robuuste 'regelmotor'. Genereert een advies voor één aandeel.
    Retourneert nu een dictionary met het advies en de onderliggende details.
    """
    advies = "HOUDEN"
    algemene_regels = profiel['algemeen']
    kwaliteit_regels = profiel['kwaliteit']
    technische_regels = profiel['technisch']
    waarderings_regels = profiel['waardering']

    # --- Data veilig ophalen ---
    winstmarge = rij_data.get('Winstmarge %')
    winstmarge = 0.0 if pd.isna(winstmarge) else winstmarge
    debt_equity = rij_data.get('Debt/Equity')
    debt_equity = float('inf') if pd.isna(debt_equity) else debt_equity
    pe_ratio = rij_data.get('P/E Ratio')
    pe_ratio = float('inf') if pd.isna(pe_ratio) else pe_ratio
    huidige_koers = rij_data.get('Huidige koers (EUR)', 0)

    # --- Technische data (eenmalig ophalen) ---
    ma50 = rij_data.get('50d MA', 0)
    ma200 = rij_data.get('200d MA', 0)
    is_in_dalende_trend = (huidige_koers < ma50) and (huidige_koers < ma200)

    # --- Verkoopregels (hebben voorrang) ---
    is_screener_run = totale_portefeuille_waarde > 999_999_000
    if not is_screener_run:
        # Regel 1: Slechte fundamentals (minstens 2 van de 4 rode vlaggen)
        is_verlieslatend = winstmarge < 0
        heeft_extreme_schuld = debt_equity > algemene_regels.get(
            'verkoop_bij_schuldgraad_boven', 4.0)
        heeft_extreme_waardering = (pe_ratio > algemene_regels.get(
            'verkoop_bij_pe_ratio_boven', 100.0)) and (pe_ratio > 0)

        rode_vlaggen = sum([is_verlieslatend, heeft_extreme_schuld,
                           heeft_extreme_waardering, is_in_dalende_trend])
        if rode_vlaggen >= 2:
            return {'advies': "VERKOOP (SLECHTE FUNDAMENTALS)", 'details': {}}

        # Regel 2: Positie is te groot geworden
        huidige_waarde_positie = rij_data.get('Huidige Waarde (EUR)', 0)
        percentage_in_portefeuille = huidige_waarde_positie / totale_portefeuille_waarde
        if percentage_in_portefeuille > algemene_regels['max_aandeel_in_portefeuille_%']:
            return {'advies': f"VERKOOP (HERBALANCEER)", 'details': {}}

        # Regel 3: Aandeel is overgewaardeerd
        koersdoel = rij_data.get('Analist Koersdoel (EUR)', 0)
        if koersdoel > 0 and huidige_koers > 0 and (huidige_koers / koersdoel) > algemene_regels['verkoop_kans_boven_koersdoel_%']:
            return {'advies': "VERKOOP (OVERGEWAARDEERD)", 'details': {}}

    # --- Koopregels ---
    # Kwaliteits-checks
    voldoet_aan_winstmarge = pd.notna(
        winstmarge) and winstmarge > waarderings_regels.get('min_winstmarge_%', -999)
    heeft_gezonde_schuldgraad = pd.notna(debt_equity) and debt_equity < waarderings_regels.get(
        'max_debt_to_equity_voor_koop', 999)
    roe = rij_data.get('Return on Equity', 0.0)
    heeft_goede_roe = pd.notna(
        roe) and roe > kwaliteit_regels['min_return_on_equity_%']
    beta = rij_data.get('Beta')
    is_stabiel_genoeg = pd.notna(beta) and beta < kwaliteit_regels['max_beta']

    # Technische Kwaliteits-checks
    is_in_uptrend = (huidige_koers > ma50 >
                     ma200) if ma50 > 0 and ma200 > 0 else False
    high52w = rij_data.get('52w High', 0)
    is_dicht_bij_top = (huidige_koers / high52w) > (1 -
                                                    technische_regels['max_afstand_van_top']) if high52w > 0 else False

    # Waarderings-checks
    potentieel = rij_data.get('Potentieel %', 0.0)
    is_ondergewaardeerd = potentieel > waarderings_regels.get(
        'koop_kans_onder_koersdoel_%', 0)
    heeft_gezonde_pe = pd.notna(pe_ratio) and (pe_ratio < waarderings_regels.get(
        'max_pe_ratio_voor_koop', 999)) and (pe_ratio > 0)
    pb_ratio = rij_data.get('P/B Ratio')
    heeft_gezonde_pb = pd.notna(pb_ratio) and (pb_ratio < waarderings_regels.get(
        'max_pb_ratio_voor_koop', 999)) and (pb_ratio > 0)
    ps_ratio = rij_data.get('P/S Ratio')
    heeft_gezonde_ps = pd.notna(ps_ratio) and (ps_ratio < waarderings_regels.get(
        'max_ps_ratio_voor_koop', 999)) and (ps_ratio > 0)

    # Momentum-check
    volume_ratio = rij_data.get('Volume Ratio', 0.0)
    dagwijziging = rij_data.get('Dagwijziging %', 0.0)
    heeft_positief_momentum = volume_ratio > technische_regels[
        'minimale_volume_ratio'] and dagwijziging > 0

    # --- Finale Score Berekening ---
    # Groepeer de checks voor maximale duidelijkheid
    fundamental_quality_checks = [
        voldoet_aan_winstmarge,
        heeft_gezonde_schuldgraad,
        heeft_goede_roe,
        is_stabiel_genoeg
    ]
    technical_quality_checks = [
        is_in_uptrend,
        is_dicht_bij_top
    ]
    valuation_checks = [
        is_ondergewaardeerd,
        heeft_gezonde_pe,
        heeft_gezonde_pb,
        heeft_gezonde_ps
    ]

    # Bereken de scores op basis van de gegroepeerde checks
    kwaliteit_score = sum(fundamental_quality_checks)
    waarde_score = sum(valuation_checks)

    # Bepaal de drempel voor kwaliteit, afhankelijk van de trend-check
    kwaliteit_drempel = 3  # Minimaal 3 van de 4 fundamentele checks
    if technische_regels['trend_check_actief']:
        kwaliteit_score += sum(technical_quality_checks)
        kwaliteit_drempel = 5  # Minimaal 5 van de 6 totale checks

    # De finale beslissing
    WAARDE_DREMPEL = 3  # Minimaal 3 van de 4 waarderingschecks moeten slagen
    is_koopwaardig = (kwaliteit_score >= kwaliteit_drempel and waarde_score >= WAARDE_DREMPEL)

    if is_koopwaardig:
        if heeft_positief_momentum:
            advies = "KOOP (STERK SIGNAAL + MOMENTUM)"
        else:
            advies = "KOOP (STERK SIGNAAL)"

    # Stel de dictionary met details samen voor transparantie
    details = {
        'scores': {
            'Kwaliteit Score': f"{kwaliteit_score} / {kwaliteit_drempel}",
            'Waarde Score': f"{waarde_score} / {WAARDE_DREMPEL}",
        },
        'checks': {
            'Voldoet aan Winstmarge': voldoet_aan_winstmarge,
            'Heeft Gezonde Schuldgraad': heeft_gezonde_schuldgraad,
            'Heeft Goede ROE': heeft_goede_roe,
            'Is Stabiel Genoeg (Beta)': is_stabiel_genoeg,
            'Is in Uptrend': is_in_uptrend,
            'Is Dicht bij Top': is_dicht_bij_top,
            'Is Ondergewaardeerd': is_ondergewaardeerd,
            'Heeft Gezonde P/E': heeft_gezonde_pe,
            'Heeft Gezonde P/B': heeft_gezonde_pb,
            'Heeft Gezonde P/S': heeft_gezonde_ps,
            'Heeft Positief Momentum': heeft_positief_momentum
        }
    }

    return {'advies': advies, 'details': details}
