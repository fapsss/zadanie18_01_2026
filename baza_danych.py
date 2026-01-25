import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from streamlit_qrcode_scanner import qrcode_scanner  # Import skanera

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro QR", layout="wide", page_icon="📦")

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-title { font-size: 40px; font-weight: bold; color: #2c3e50; text-align: center; }
    .qr-container { border: 2px dashed #1f77b4; padding: 20px; border-radius: 15px; background: white; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- POŁĄCZENIE Z SUPABASE (Identycznie jak wcześniej) ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        st.error("Błąd połączenia z bazą.")
        st.stop()

supabase = init_connection()

# --- FUNKCJE DANYCH ---
def get_products():
    res = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['kategoria_nazwa'] = df['kategorie'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Brak")
        df['wartosc'] = df['cena'] * df['liczba']
    return df

df_p = get_products()

# --- GŁÓWNY INTERFEJS ---
st.markdown('<div class="main-title">📦 Magazyn Pro + QR Scanner</div>', unsafe_allow_html=True)

# Dodajemy nową zakładkę "Skaner QR"
tab1, tab2, tab3, tab4 = st.tabs(["📊 Statystyki", "🛒 Inwentaryzacja", "🔍 Skaner QR", "⚙️ Zarządzanie"])

# === TAB 3: SKANER QR ===
with tab3:
    st.subheader("📷 Skanuj kod produktu")
    st.write("Skieruj aparat na kod QR, aby automatycznie wyszukać produkt w bazie.")
    
    col_qr, col_res = st.columns([1, 1])
    
    with col_qr:
        st.markdown('<div class="qr-container">', unsafe_allow_html=True)
        # Inicjalizacja skanera
        qr_code = qrcode_scanner(key='scanner')
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_res:
        if qr_code:
            st.success(f"Zeskanowano: **{qr_code}**")
            # Szukanie produktu po nazwie lub ID (zakładając, że QR zawiera nazwę)
            search_res = df_p[df_p['nazwa'].str.contains(qr_code, case=False, na=False)]
            
            if not search_res.empty:
                st.write("### Znaleziony produkt:")
                prod = search_res.iloc[0]
                st.info(f"**Nazwa:** {prod['nazwa']}\n\n**Stan:** {prod['liczba']} szt.\n\n**Cena:** {prod['cena']} PLN")
                
                # Szybka edycja stanu po skanowaniu
                new_qty = st.number_input("Zmień stan (szt.)", value=int(prod['liczba']), key="qr_edit")
                if st.button("Zapisz zmianę"):
                    supabase.table("produkty").update({"liczba": new_qty}).eq("id", int(prod['id'])).execute()
                    st.success("Zaktualizowano stan magazynowy!")
                    st.rerun()
            else:
                st.warning("Nie znaleziono produktu o takiej nazwie w bazie.")
        else:
            st.info("Oczekiwanie na obraz z kamery...")

# === RESZTA FUNKCJONALNOŚCI (SKRÓCONA) ===
with tab1:
    st.write("Tu znajdują się Twoje statystyki...") # (Kod z poprzedniej odpowiedzi)

with tab2:
    st.write("Tu znajduje się tabela produktów...") # (Kod z poprzedniej odpowiedzi)

with tab4:
    st.write("Tu dodajesz nowe produkty i kategorie...") # (Kod z poprzedniej odpowiedzi)
