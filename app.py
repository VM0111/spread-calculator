import streamlit as st
import pandas as pd
import io

# 1. ZASZYTA NA SZTYWNO DYSTRYBUCJA WOLUMENU
# Skopiowana dokładnie z Twojego pliku Volume_Distribution.csv
@st.cache_data
def load_volume_distribution():
    data = [
        {"volume_range": "(0, 1]", "filled_volume": 5217.78},
        {"volume_range": "(1, 2]", "filled_volume": 2818.88},
        {"volume_range": "(2, 3]", "filled_volume": 1296.56},
        {"volume_range": "(3, 4]", "filled_volume": 1040.58},
        {"volume_range": "(4, 5]", "filled_volume": 680.59},
        {"volume_range": "(5, 6]", "filled_volume": 133.23},
        {"volume_range": "(6, 7]", "filled_volume": 66.40},
        {"volume_range": "(7, 8]", "filled_volume": 59.35},
        {"volume_range": "(8, 9]", "filled_volume": 53.00},
        {"volume_range": "(9, 10]", "filled_volume": 51.60},
        {"volume_range": "(10, 11]", "filled_volume": 7.00},
        {"volume_range": "(11, 12]", "filled_volume": 7.00},
        {"volume_range": "(12, 13]", "filled_volume": 5.80},
        {"volume_range": "(13, 14]", "filled_volume": 5.00},
        {"volume_range": "(14, 15]", "filled_volume": 4.00},
        {"volume_range": "(15, 16]", "filled_volume": 4.00},
        {"volume_range": "(16, 17]", "filled_volume": 4.00},
        {"volume_range": "(17, 18]", "filled_volume": 4.00},
        {"volume_range": "(18, 19]", "filled_volume": 4.00},
        {"volume_range": "(19, 20]", "filled_volume": 4.00},
        {"volume_range": "(20, 21]", "filled_volume": 1.00},
        {"volume_range": "(21, 22]", "filled_volume": 1.00},
        {"volume_range": "(22, 23]", "filled_volume": 1.00},
        {"volume_range": "(23, 24]", "filled_volume": 1.00},
        {"volume_range": "(24, 25]", "filled_volume": 1.00},
        {"volume_range": "(25, 26]", "filled_volume": 0.00},
    ]
    return pd.DataFrame(data)

# 2. DOMYŚLNY ORDER BOOK (Do edycji przez użytkownika)
@st.cache_data
def load_default_order_book():
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7],
        "Bid Size": [1.0, 6.0, 10.0, 11.0, 15.0, 19.0, 23.0],
        "Ask Size": [1.0, 6.0, 11.0, 15.0, 18.0, 19.0, 20.0],
        "Spread": [31.0, 42.0, 57.0, 84.0, 115.0, 164.0, 247.0]
    })

# 3. GŁÓWNA LOGIKA OBLICZENIOWA (Ta sama co wcześniej)
def calculate_per_bucket_revenue(order_book, volume_distribution):
    ob = order_book.copy()
    ob['Ask Size'] = pd.to_numeric(ob['Ask Size'], errors='coerce')
    ob['Spread'] = pd.to_numeric(ob['Spread'], errors='coerce')
    ob['Cum_Ask_Size'] = ob['Ask Size'].cumsum()
    
    results = []
    
    for idx, row in volume_distribution.iterrows():
        try:
            vol_str = str(row['volume_range']).replace('"', '').replace("'", "")
            end_str = vol_str.split(',')[1].strip(')] ')
            bucket_end = float(end_str)
        except Exception:
            continue
            
        filled_volume = float(row['filled_volume'])
        valid_lines = ob[ob['Cum_Ask_Size'] >= bucket_end]
        
        if not valid_lines.empty:
            assigned_spread = valid_lines.iloc[0]['Spread']
        else:
            assigned_spread = ob.iloc[-1]['Spread']
            
        revenue = (filled_volume * assigned_spread) / 2
        
        results.append({
            'Volume_Bucket': row['volume_range'],
            'Filled_Volume': round(filled_volume, 2),
            'Assigned_Spread': round(assigned_spread, 2),
            'Revenue_USD': round(revenue, 2)
        })
    
    return pd.DataFrame(results)

# ==========================================
# INTERFEJS APLIKACJI WEBOWEJ
# ==========================================
st.set_page_config(page_title="Spread Revenue Calculator", layout="wide")

st.title("📊 Spread & Revenue Calculator")
st.write("Skonfiguruj płynność w arkuszu (Order Book), aby zobaczyć, jak wpłynie to na przychody z historycznych wolumenów.")

# Wczytanie danych
vol_dist_df = load_volume_distribution()
default_ob_df = load_default_order_book()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Edytuj Order Book")
    st.info("Zmień wartości 'Ask Size' lub 'Spread' w tabeli poniżej. Zmiany przeliczą się automatycznie.")
    
    # INTERAKTYWNA TABELA - Tutaj dzieje się magia
    edited_ob_df = st.data_editor(
        default_ob_df,
        num_rows="dynamic", # Pozwala na dodawanie nowych wierszy!
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.subheader("2. Wyniki (Per-Bucket Revenue)")
    
    # Wywołanie kalkulacji na żywo z edytowanego Order Booka
    results_df = calculate_per_bucket_revenue(edited_ob_df, vol_dist_df)
    total_revenue = results_df['Revenue_USD'].sum()
    
    # Wyświetlanie łącznego zarobku na ładnym kafelku
    st.metric(label="Total Revenue (USD)", value=f"${total_revenue:,.2f}")
    
    # Tabela z wynikami
    st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    # Generowanie pliku Excel do pobrania (w pamięci, bez zapisywania na dysku)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        results_df.to_excel(writer, sheet_name='Per-Bucket Revenue', index=False)
    output.seek(0)
    
    st.download_button(
        label="📥 Pobierz wyniki jako Excel",
        data=output,
        file_name="final_calculations.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )