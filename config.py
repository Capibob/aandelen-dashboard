import streamlit as st


def build_profile_sidebar():
    """
    Bouwt de volledige interactieve sidebar met de correcte 4 inklapbare secties en help-teksten.
    """
    st.sidebar.title("⚙️ Profiel Instellingen")
    st.sidebar.info(
        "Pas de regels aan en zie direct het effect op de adviezen.")

    # --- Sectie 1: Algemene Regels ---
    with st.sidebar.expander("1. Algemene Regels", expanded=True):
        max_aandeel_pct = st.slider(
            'Max. % per Aandeel (Herbalanceren)', 5, 25, 15, format='%d%%',
            help="Signaal om te verkopen als een positie groter wordt dan dit % van de totale portefeuille."
        )
        verkoop_boven_doel_pct = st.slider(
            'Verkoopkans % Boven Koersdoel', 0, 50, 10, format='+%d%%',
            help="Signaal om te verkopen als de koers dit % boven het analistenkoersdoel komt."
        )
        verkoop_pe_boven = st.number_input(
            'Verkoop bij P/E Ratio Boven', 0, 500, 100,
            help="Signaal om te verkopen als een aandeel een extreem hoge P/E ratio heeft (en winstgevend is)."
        )
        verkoop_de_boven = st.number_input(
            'Verkoop bij Debt/Equity Boven', 0.0, 10.0, 4.0, step=0.1,
            help="Signaal om te verkopen als de schuldgraad van een bedrijf extreem hoog is."
        )

    # --- Sectie 2: Technische Analyse & Trend ---
    with st.sidebar.expander("2. Technische Analyse & Trend", expanded=True):
        volume_ratio_drempel = st.slider(
            'Min. Volume Ratio (7d/3m)', 1.0, 5.0, 1.2, step=0.1,
            help="Hoeveel hoger moet het 7-daags gemiddelde volume zijn t.o.v. het 3-maands gemiddelde? 1.2 = 20% hoger."
        )
        trend_check_actief = st.toggle(
            'Trend-Check Activeren', value=True,
            help="Indien actief, moeten aandelen in een bewezen opwaartse trend zitten (Koers > 50d > 200d)."
        )
        max_afstand_van_top = st.slider(
            'Max. Afstand van 52w Hoogtepunt (%)', 0, 50, 15, format='%d%%',
            help="Hoe ver mag een aandeel maximaal van zijn jaarrecord verwijderd zijn? Filter voor sterke aandelen."
        ) / 100

    # --- Sectie 3: Kwaliteit & Stabiliteit ---
    with st.sidebar.expander("3. Kwaliteit & Stabiliteit Drempels", expanded=True):
        min_roe = st.slider(
            'Min. Return on Equity (ROE) %', 0, 50, 15,
            help="Rendement op Eigen Vermogen. Hoe efficiënt genereert het bedrijf winst? >15% is vaak een teken van kwaliteit."
        ) / 100
        max_beta = st.slider(
            'Max. Beta (Volatiliteit)', 0.5, 2.5, 1.2, step=0.1,
            help="Stabiliteit. <1.0 is stabieler dan de markt."
        )

    # --- Sectie 4: Waarderingsregels ---
    with st.sidebar.expander("4. Waarderingsregels (voor KOOP)", expanded=True):
        help_text = {
            'potentieel': "Minimale 'korting' t.o.v. het analistenkoersdoel.",
            'pe': "Koers/Winst. GOED: <15 (Value) of <25 (Groei). WAARSCHUWING: >25 (Value) of >40 (Groei).",
            'pb': "Koers/Boekwaarde. GOED: <1.5. WAARSCHUWING: >2.5 (Value) of >4 (Groei).",
            'ps': "Koers/Omzet. GOED: <2 (stabiele bedrijven). WAARSCHUWING: >4 (tenzij bij zeer hoge groei).",
            'de': "Schuld/Eigen Vermogen. GOED: <0.5-1.0. WAARSCHUWING: >1.5 (verhoogd risico), >2.0 (risicovol).",
            'marge': "Nettowinstmarge. Hoger is efficiënter."
        }
        potentieel_drempel = st.slider(
            'Min. Potentieel (%)', 0, 100, 25, key='pot', help=help_text['potentieel']) / 100
        pe_drempel = st.number_input(
            'Max. P/E Ratio', 0, 1000, 25, key='pe', help=help_text['pe'])
        pb_drempel = st.number_input(
            'Max. P/B Ratio', 0.0, 50.0, 2.5, step=0.1, key='pb', help=help_text['pb'])
        ps_drempel = st.number_input(
            'Max. P/S Ratio', 0.0, 50.0, 4.0, step=0.1, key='ps', help=help_text['ps'])
        de_drempel = st.number_input(
            'Max. Debt/Equity', 0.0, 5.0, 1.5, step=0.1, key='de', help=help_text['de'])
        marge_drempel = st.slider(
            'Min. Winstmarge (%)', -100, 50, 10, key='marge', help=help_text['marge']) / 100

    # Bouw het profiel dictionary
    mijn_profiel = {
        'algemeen': {
            'max_aandeel_in_portefeuille_%': max_aandeel_pct / 100,
            'verkoop_kans_boven_koersdoel_%': 1 + (verkoop_boven_doel_pct / 100),
            'verkoop_bij_pe_ratio_boven': verkoop_pe_boven,
            'verkoop_bij_schuldgraad_boven': verkoop_de_boven
        },
        'technisch': {
            'minimale_volume_ratio': volume_ratio_drempel,
            'trend_check_actief': trend_check_actief,
            'max_afstand_van_top': max_afstand_van_top,
        },
        'kwaliteit': {
            'min_return_on_equity_%': min_roe,
            'max_beta': max_beta
        },
        'waardering': {
            'koop_kans_onder_koersdoel_%': potentieel_drempel,
            'max_pe_ratio_voor_koop': pe_drempel,
            'max_pb_ratio_voor_koop': pb_drempel,
            'max_ps_ratio_voor_koop': ps_drempel,
            'max_debt_to_equity_voor_koop': de_drempel,
            'min_winstmarge_%': marge_drempel
        }
    }
    return mijn_profiel
