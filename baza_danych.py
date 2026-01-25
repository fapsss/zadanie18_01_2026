import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro v2.0", layout="wide", page_icon="📦")

# --- STYLIZACJA CSS (Zdjęcie w tle i estetyka) ---
st.markdown("""
    <style>
    /* Gradientowe tło dla całej aplikacji */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Stylizacja kart metryk */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #1f77b4;
    }
    
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Nagłówek strony */
    .main-title {
        font-size: 45px;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        st.error("Skonfiguruj połączenie z Supabase w Secrets!")
        st.stop()

supabase = init_connection()

# --- FUNKCJE DANYCH ---
def get_categories():
    try:
        res = supabase.table("kategorie").select("*").order("nazwa").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["id", "nazwa", "opis"])

def get_products():
    try:
        res = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['kategoria_nazwa'] = df['kategorie'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Brak")
            df['wartosc'] = df['cena'] * df['liczba']
        return df
    except:
        return pd.DataFrame(columns=["id", "nazwa", "liczba", "cena", "kategoria_id"])

# Pobranie danych
df_p = get_products()
df_c = get_categories()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2271/2271062.png", width=100) # Ikona magazynu
    st.title("Magazyn Pro")
    st.markdown("---")
    st.info("Zalogowany jako: **Administrator**")
    
    search_query = st.text_input("🔍 Szukaj produktu...", "")
    selected_kat = st.multiselect("📂 Filtruj kategorię", options=df_c['nazwa'].tolist() if not df_c.empty else [])

# Filtrowanie
df_filtered = df_p.copy()
if search_query:
    df_filtered = df_filtered[df_filtered['nazwa'].str.contains(search_query, case=False)]
if selected_kat:
    df_filtered = df_filtered[df_filtered['kategoria_nazwa'].isin(selected_kat)]

# --- GŁÓWNY INTERFEJS ---
# Baner graficzny na górze
st.image("https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?ixlib=rb-1.2.1&auto=format&fit=crop&w=1600&q=80", 
         use_container_width=True, caption="Centrum Zarządzania Logistyką")

st.markdown('<div class="main-title">📦 Panel Kontrolny Magazynu</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Statystyki i Wykresy", "🛒 Inwentaryzacja", "⚙️ Konfiguracja"])

# === TAB 1: STATYSTYKI ===
with tab1:
    if not df_p.empty:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1: st.metric("Suma towarów", int(df_p['liczba'].sum()))
        with col_m2: st.metric("Wycena (PLN)", f"{df_p['wartosc'].sum():,.2f}")
        with col_m3: st.metric("Liczba SKU", len(df_p))
        with col_m4: st.metric("Kategorie", len(df_c))

        st.markdown("---")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_bar = px.bar(df_p, x="nazwa", y="liczba", color="kategoria_nazwa", 
                             title="Poziom zapasów", template="plotly_white")
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_pie = px.pie(df_p, values='wartosc', names='kategoria_nazwa', hole=0.4, 
                             title="Struktura wartościowa")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("Dodaj pierwsze produkty, aby zobaczyć statystyki.")

# === TAB 2: INWENTARYZACJA ===
with tab2:
    st.subheader("📋 Lista Produktów")
    if not df_filtered.empty:
        # Tabela z kolorowaniem zapasów
        st.dataframe(
            df_filtered[['id', 'nazwa', 'liczba', 'cena', 'wartosc', 'kategoria_nazwa']],
            column_config={
                "liczba": st.column_config.NumberColumn("Ilość", format="%d szt."),
                "cena": st.column_config.NumberColumn("Cena", format="%.2f PLN"),
                "wartosc": st.column_config.ProgressColumn("Wartość", format="%.2f PLN", min_value=0, max_value=float(df_p['wartosc'].max() if not df_p.empty else 100))
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Brak wyników wyszukiwania.")

# === TAB 3: KONFIGURACJA (DODAWANIE/USUWANIE) ===
with tab3:
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("🆕 Nowy Produkt")
        with st.form("form_add"):
            name = st.text_input("Nazwa")
            kat = st.selectbox("Kategoria", df_c['nazwa']) if not df_c.empty else st.error("Brak kategorii!")
            c1, c2 = st.columns(2)
            qty = c1.number_input("Sztuk", min_value=0)
            prc = c2.number_input("Cena", min_value=0.0)
            if st.form_submit_button("Dodaj produkt") and name:
                k_id = df_c[df_c['nazwa'] == kat]['id'].values[0]
                supabase.table("produkty").insert({"nazwa": name, "liczba": qty, "cena": prc, "kategoria_id": int(k_id)}).execute()
                st.success("Produkt dodany!")
                st.rerun()

    with col_r:
        st.subheader("📂 Nowa Kategoria")
        with st.form("form_kat"):
            k_name = st.text_input("Nazwa kategorii")
            k_desc = st.text_area("Opis")
            if st.form_submit_button("Dodaj kategorię") and k_name:
                supabase.table("kategorie").insert({"nazwa": k_name, "opis": k_desc}).execute()
                st.success("Kategoria dodana!")
                st.rerun()
