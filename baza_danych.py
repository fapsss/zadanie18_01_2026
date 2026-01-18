import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- Konfiguracja połączenia z Supabase ---
# Upewnij się, że w pliku .streamlit/secrets.toml masz ustawione:
# SUPABASE_URL = "twoj-url"
# SUPABASE_KEY = "twoj-klucz"
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji sekretów. Upewnij się, że SUPABASE_URL i SUPABASE_KEY są ustawione.")
    st.stop()

st.title("📦 Zarządzanie Magazynem")

# --- Funkcje pomocnicze ---
def load_categories():
    response = supabase.table('kategorie').select("*").execute()
    return pd.DataFrame(response.data)

def load_products():
    # Pobieramy produkty i łączymy z nazwami kategorii dla czytelności
    response = supabase.table('produkty').select("*, kategorie(nazwa)").execute()
    data = response.data
    # Spłaszczamy strukturę dla DataFrame (wyciągamy nazwę kategorii)
    for item in data:
        if item.get('kategorie'):
            item['kategoria_nazwa'] = item['kategorie']['nazwa']
        else:
            item['kategoria_nazwa'] = 'Brak'
    return pd.DataFrame(data)

# --- Interfejs Użytkownika ---
tab1, tab2 = st.tabs(["📂 Kategorie", "🛒 Produkty"])

# === ZAKŁADKA 1: KATEGORIE ===
with tab1:
    st.header("Zarządzaj Kategoriami")
    
    # 1. Dodawanie kategorii
    with st.expander("➕ Dodaj nową kategorię"):
        with st.form("add_category_form"):
            cat_name = st.text_input("Nazwa kategorii")
            cat_desc = st.text_area("Opis")
            submitted_cat = st.form_submit_button("Dodaj kategorię")
            
            if submitted_cat:
                if cat_name:
                    try:
                        supabase.table('kategorie').insert({"nazwa": cat_name, "opis": cat_desc}).execute()
                        st.success(f"Dodano kategorię: {cat_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd podczas dodawania: {e}")
                else:
                    st.warning("Nazwa kategorii jest wymagana.")

    # 2. Wyświetlanie i Usuwanie
    st.subheader("Lista Kategorii")
    df_cat = load_categories()
    
    if not df_cat.empty:
        # Wyświetlenie tabeli
        st.dataframe(df_cat[['id', 'nazwa', 'opis']], use_container_width=True)
        
        # Usuwanie
        st.write("🗑️ **Usuń kategorię**")
        cat_to_delete = st.selectbox("Wybierz kategorię do usunięcia", df_cat['nazwa'], key="del_cat_select")
        if st.button("Usuń wybraną kategorię"):
            cat_id = df_cat[df_cat['nazwa'] == cat_to_delete]['id'].values[0]
            try:
                # Uwaga: Jeśli istnieją produkty w tej kategorii, baza może zwrócić błąd (chyba że jest CASCADE)
                supabase.table('kategorie').delete().eq('id', int(cat_id)).execute()
                st.success("Usunięto kategorię.")
                st.rerun()
            except Exception as e:
                st.error(f"Nie można usunąć (sprawdź czy kategoria nie ma przypisanych produktów): {e}")
    else:
        st.info("Brak kategorii w bazie.")

# === ZAKŁADKA 2: PRODUKTY ===
with tab2:
    st.header("Zarządzaj Produktami")

    # Pobierz aktualne kategorie do listy rozwijanej
    df_categories_ref = load_categories()
    
    # 1. Dodawanie produktu
    with st.expander("➕ Dodaj nowy produkt"):
        if df_categories_ref.empty:
            st.warning("Najpierw dodaj przynajmniej jedną kategorię w zakładce 'Kategorie'.")
        else:
            with st.form("add_product_form"):
                prod_name = st.text_input("Nazwa produktu")
                col1, col2 = st.columns(2)
                with col1:
                    prod_count = st.number_input("Liczba sztuk", min_value=0, step=1, format="%d")
                with col2:
                    prod_price = st.number_input("Cena", min_value=0.0, step=0.01, format="%.2f")
                
                # Wybór kategorii (mapowanie nazwy na ID)
                cat_choice = st.selectbox("Kategoria", df_categories_ref['nazwa'])
                
                submitted_prod = st.form_submit_button("Dodaj produkt")
                
                if submitted_prod:
                    if prod_name and cat_choice:
                        # Znajdź ID wybranej kategorii
                        selected_cat_id = df_categories_ref[df_categories_ref['nazwa'] == cat_choice]['id'].values[0]
                        
                        try:
                            data_payload = {
                                "nazwa": prod_name,
                                "liczba": int(prod_count),
                                "cena": float(prod_price),
                                "kategoria_id": int(selected_cat_id)
                            }
                            supabase.table('produkty').insert(data_payload).execute()
                            st.success(f"Dodano produkt: {prod_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Błąd bazy danych: {e}")
                    else:
                        st.warning("Uzupełnij nazwę produktu.")

    # 2. Wyświetlanie i Usuwanie
    st.subheader("Stan Magazynowy")
    df_prod = load_products()
    
    if not df_prod.empty:
        # Wyświetlanie
        st.dataframe(
            df_prod[['id', 'nazwa', 'liczba', 'cena', 'kategoria_nazwa']], 
            column_config={
                "cena": st.column_config.NumberColumn("Cena", format="%.2f PLN"),
                "kategoria_nazwa": "Kategoria"
            },
            use_container_width=True
        )
        
        # Usuwanie
        st.write("🗑️ **Usuń produkt**")
        # Tworzymy listę etykiet do selectboxa (ID + Nazwa dla unikalności)
        product_options = {f"{row['nazwa']} (ID: {row['id']})": row['id'] for index, row in df_prod.iterrows()}
        
        selected_prod_label = st.selectbox("Wybierz produkt do usunięcia", options=list(product_options.keys()))
        
        if st.button("Usuń wybrany produkt"):
            prod_id_to_del = product_options[selected_prod_label]
            try:
                supabase.table('produkty').delete().eq('id', int(prod_id_to_del)).execute()
                st.success("Usunięto produkt.")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd usuwania: {e}")
    else:
        st.info("Brak produktów w magazynie.")
