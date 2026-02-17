import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go

# 1. ZASZYTA NA SZTYWNO DYSTRYBUCJA WOLUMENU
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

# 2. DOMYŚLNY ORDER BOOK
@st.cache_data
def load_default_order_book():
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7],
        "Bid Size": [1.0, 6.0, 10.0, 11.0, 15.0, 19.0, 23.0],
        "Ask Size": [1.0, 6.0, 11.0, 15.0, 18.0, 19.0, 20.0],
        "Spread": [31.0, 42.0, 57.0, 84.0, 115.0, 164.0, 247.0]
    })

# 3. GŁÓWNA LOGIKA OBLICZENIOWA (Bez zmian)
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
st.set_page_config(page_title="A/B Spread Revenue Calculator", layout="wide")

st.title("📊 A/B Spread & Revenue Calculator")
st.write("Porównaj dwa różne scenariusze płynności w Order Booku na tych samych wolumenach historycznych.")

vol_dist_df = load_volume_distribution()
default_ob_df = load_default_order_book()

# --- PIĘTRO 1: SCENARIUSZ A ---
st.header("🔴 Scenariusz A")
colA1, colA2 = st.columns([1, 2])

with colA1:
    st.caption("Edytuj Order Book A")
    # Zwróć uwagę na unikalny key="ob_a", żeby Streamlit nie pomieszał tabelek
    edited_ob_a = st.data_editor(default_ob_df.copy(), num_rows="dynamic", use_container_width=True, hide_index=True, key="ob_a")

with colA2:
    results_a = calculate_per_bucket_revenue(edited_ob_a, vol_dist_df)
    total_rev_a = results_a['Revenue_USD'].sum()
    st.metric(label="Total Revenue A (USD)", value=f"${total_rev_a:,.2f}")
    # Pokazujemy tylko kilka wierszy w podglądzie, żeby nie wydłużać strony (użytkownik może scrollować)
    st.dataframe(results_a, use_container_width=True, hide_index=True, height=200)

st.divider() # Szara linia oddzielająca

# --- PIĘTRO 2: SCENARIUSZ B ---
st.header("🔵 Scenariusz B")
colB1, colB2 = st.columns([1, 2])

with colB1:
    st.caption("Edytuj Order Book B")
    # Jako domyślny wrzucamy kopię, można sobie go zmienić
    edited_ob_b = st.data_editor(default_ob_df.copy(), num_rows="dynamic", use_container_width=True, hide_index=True, key="ob_b")

with colB2:
    results_b = calculate_per_bucket_revenue(edited_ob_b, vol_dist_df)
    total_rev_b = results_b['Revenue_USD'].sum()
    
    # Liczymy różnicę do ładnego wyświetlenia
    diff_vs_a = total_rev_b - total_rev_a
    st.metric(label="Total Revenue B (USD)", value=f"${total_rev_b:,.2f}", delta=f"{diff_vs_a:,.2f} vs Scenariusz A")
    st.dataframe(results_b, use_container_width=True, hide_index=True, height=200)

st.divider()

# --- PARTER: INTERAKTYWNY WYKRES PORÓWNAWCZY ---
st.header("📈 Porównanie Przychodów (Revenue per Bucket)")

# Tworzenie wykresu z biblioteki Plotly
fig = go.Figure()

# Dodajemy słupki dla Scenariusza A (Kolor: Czerwony/Koralowy)
fig.add_trace(go.Bar(
    x=results_a['Volume_Bucket'],
    y=results_a['Revenue_USD'],
    name='Scenariusz A',
    marker_color='#EF553B' 
))

# Dodajemy słupki dla Scenariusza B (Kolor: Niebieski)
fig.add_trace(go.Bar(
    x=results_b['Volume_Bucket'],
    y=results_b['Revenue_USD'],
    name='Scenariusz B',
    marker_color='#00CC96'
))

# Ustawienia wyglądu wykresu
fig.update_layout(
    barmode='group', # Słupki stoją obok siebie (zgrupowane)
    xaxis_title='Przedział Wolumenu (Volume Bucket)',
    yaxis_title='Przychód (USD)',
    hovermode="x unified", # Super funkcja: jak najedziesz myszką, pokazuje dane z obu słupków naraz w jednej chmurce!
    margin=dict(l=0, r=0, t=30, b=0)
)

# Wyświetlenie wykresu na cały ekran
st.plotly_chart(fig, use_container_width=True)

# Przycisk pobierania na samym dole (łączy oba scenariusze w jeden plik Excel)
st.write("---")
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    results_a.to_excel(writer, sheet_name='Scenariusz A', index=False)
    results_b.to_excel(writer, sheet_name='Scenariusz B', index=False)
output.seek(0)

st.download_button(
    label="📥 Pobierz wyniki obu scenariuszy jako Excel",
    data=output,
    file_name="symulacja_ab_revenue.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)