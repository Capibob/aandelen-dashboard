import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="Aandelen Analyse Tool",
    page_icon="📈"
)

st.title("Welkom bij de Aandelen Analyse Tool")

st.markdown("""
Deze applicatie biedt twee krachtige tools om je te helpen bij het analyseren van aandelen.

👈 **Selecteer een van de volgende pagina's in de zijbalk:**
*   **Aandelen Screener:** Scan volledige beursindices op basis van fundamentele en technische criteria.
*   **AI Analyse:** Genereer een diepgaande, kwalitatieve analyse voor een specifiek aandeel met behulp van AI.
""")