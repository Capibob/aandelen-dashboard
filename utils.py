import pandas as pd

def format_euro(value):
    """
    Formatteert een numerieke waarde als een Euro-bedrag in Europees formaat.
    Voorbeeld: 1234.56 -> "€ 1.234,56"
    Handelt None of niet-numerieke waarden af door 'N/B' terug te geven.
    """
    if pd.isna(value):
        return 'N/B'
    # Formatteer met duizendtalscheidingsteken (punt) en decimaal (komma)
    return f"€ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def stijl_advies_kolom(val):
    """
    Geeft een CSS-stijl terug om de achtergrondkleur van een cel aan te passen
    op basis van de adviestekst.
    """
    color_map = {
        'Kopen': 'lightgreen',
        'Verkopen': 'lightcoral',
        'Houden': 'lightgrey',
        'Overwegen': 'orange'
    }
    color = color_map.get(val, '') # Default naar geen kleur als advies niet in map staat
    return f'background-color: {color}'