import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Pro", layout="wide", page_icon="📦")

# --- POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        st.error("Błąd: Brak danych logowania do Supabase w Secrets!")
        st.stop()

supabase = init_connection()

# --- FUNKCJE POBIERANIA DANYCH ---
def get_categories():
    res = supabase.table("kategorie").select("*").execute()
    return pd.DataFrame(res.data)

def get_products():
    res = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['kategoria_nazwa'] = df['kategorie'].apply(lambda x: x['nazwa'] if isinstance(x, dict) else "Brak")
        df['wartosc'] = df['cena'] * df['liczba']
    return df

# --- GŁÓWNY INTERFEJS ---
st.title("📦 System Zarządzania Magazynem")

tab1, tab2, tab3 = st.tabs(["📊 Statystyki", "🛒 Produkty", "📂 Kategorie"])

df_p = get_products()
df_c = get_categories()

# === TAB 1: STATYSTYKI ===
with tab1:
    if not df_p.empty:
        st.subheader("Analityka Magazynowa")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Suma sztuk", int(df_p['liczba'].sum()))
        col_m2.metric("Łączna wartość", f"{df_p['wartosc'].sum():,.2f} PLN")
        col_m3.metric("Liczba pozycji", len(df_p))

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.write("📈 **Stan ilościowy produktów**")
            st.bar_chart(df_p, x="nazwa", y="liczba", color="#0072B2")
        
        with c2:
            st.write("🍕 **Wartościowy udział kategorii**")
            fig = px.pie(df_p, values='wartosc', names='kategoria_nazwa', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Baza jest pusta. Dodaj kategorie i produkty, aby zobaczyć wykresy.")

# === TAB 2: PRODUKTY ===
with tab2:
    st.header("🛒 Zarządzanie Produktami")
    
    # Formularz dodawania
    with st.expander("➕ Dodaj nowy produkt"):
        if df_c.empty:
            st.warning("Najpierw dodaj kategorię!")
        else:
            with st.form("form_prod"):
                nazwa = st.text_input("Nazwa produktu")
                c_l, c_c = st.columns(2)
                liczba = c_l.number_input("Sztuk", min_value=0, step=1)
                cena = c_c.number_input("Cena (PLN)", min_value=0.0, step=0.01)
                kat = st.selectbox("Kategoria", df_c['nazwa'])
                if st.form_submit_button("Zapisz produkt"):
                    kat_id = df_c[df_c['nazwa'] == kat]['id'].values[0]
                    supabase.table("produkty").insert({
                        "nazwa": nazwa, "liczba": liczba, "cena": cena, "kategoria_id": int(kat_id)
                    }).execute()
                    st.success("Dodano produkt!")
                    st.rerun()

    # Tabela i usuwanie
    if not df_p.empty:
        st.dataframe(df_p[['id', 'nazwa', 'liczba', 'cena', 'kategoria_nazwa']], use_container_width=True)
        to_del = st.selectbox("Usuń produkt:", df_p['nazwa'], key="del_p")
        if st.button("Usuń produkt"):
            id_del = df_p[df_p['nazwa'] == to_del]['id'].values[0]
            supabase.table("produkty").delete().eq("id", int(id_del)).execute()
            st.rerun()

# === TAB 3: KATEGORIE ===
with tab3:
    st.header("📂 Kategorie")
    with st.expander("➕ Dodaj kategorię"):
        with st.form("form_kat"):
            n_kat = st.text_input("Nazwa kategorii")
            o_kat = st.text_area("Opis")
            if st.form_submit_button("Dodaj"):
                supabase.table("kategorie").insert({"nazwa": n_kat, "opis": o_kat}).execute()
                st.rerun()

    if not df_c.empty:
        st.table(df_c[['id', 'nazwa', 'opis']])
        kat_del = st.selectbox("Usuń kategorię:", df_c['nazwa'], key="del_k")
        if st.button("Usuń kategorię"):
            k_id = df_c[df_c['nazwa'] == kat_del]['id'].values[0]
            try:
                supabase.table("kategorie").delete().eq("id", int(k_id)).execute()
                st.rerun()
            except:
                st.error("Nie można usunąć kategorii, która zawiera produkty!")
