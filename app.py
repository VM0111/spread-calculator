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

# 3. GŁÓWNA LOGIKA OBLICZENIOWA
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

TABLE_HEIGHT = 300 

# DZIELIMY GŁÓWNY EKRAN NA PÓŁ 
col_left, col_right = st.columns(2)

# ==========================================
# LEWA STRONA: SCENARIUSZ A
# ==========================================
with col_left:
    st.header("🔴 Scenariusz A")
    
    st.markdown("**1. Edytuj Order Book A**")
    edited_ob_a = st.data_editor(
        default_ob_df.copy(), 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True, 
        key="ob_a",
        height=TABLE_HEIGHT
    )
    
    results_a = calculate_per_bucket_revenue(edited_ob_a, vol_dist_df)
    total_rev_a = results_a['Revenue_USD'].sum()
    
    st.markdown(f"**2. Wyniki A** &mdash; Total Revenue: <span style='color:#EF553B; font-size:1.1em'>**${total_rev_a:,.2f}**</span>", unsafe_allow_html=True)
    st.dataframe(results_a, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

# ==========================================
# PRAWA STRONA: SCENARIUSZ B
# ==========================================
with col_right:
    st.header("🔵 Scenariusz B")
    
    st.markdown("**1. Edytuj Order Book B**")
    edited_ob_b = st.data_editor(
        default_ob_df.copy(), 
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True, 
        key="ob_b",
        height=TABLE_HEIGHT
    )
    
    results_b = calculate_per_bucket_revenue(edited_ob_b, vol_dist_df)
    total_rev_b = results_b['Revenue_USD'].sum()
    diff_vs_a = total_rev_b - total_rev_a
    
    diff_color = "#00CC96" if diff_vs_a >= 0 else "#EF553B"
    diff_sign = "+" if diff_vs_a >= 0 else ""
    
    st.markdown(f"**2. Wyniki B** &mdash; Total Revenue: <span style='color:#00CC96; font-size:1.1em'>**${total_rev_b:,.2f}**</span> <span style='color:{diff_color}; font-size:0.9em'>({diff_sign}${diff_vs_a:,.2f} vs A)</span>", unsafe_allow_html=True)
    st.dataframe(results_b, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

st.divider()

# ==========================================
# WYKRESY NA DOLE (Również podzielone na pół)
# ==========================================
col_chart_left, col_chart_right = st.columns(2)

with col_chart_left:
    st.subheader("📊 Porównanie: Słupki (Bar Chart)")
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=results_a['Volume_Bucket'], y=results_a['Revenue_USD'],
        name='Scenariusz A', marker_color='#EF553B' 
    ))
    fig_bar.add_trace(go.Bar(
        x=results_b['Volume_Bucket'], y=results_b['Revenue_USD'],
        name='Scenariusz B', marker_color='#00CC96'
    ))
    fig_bar.update_layout(
        barmode='group', 
        xaxis_title='Przedział Wolumenu',
        yaxis_title='Przychód (USD)',
        hovermode="x unified",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_chart_right:
    st.subheader("📈 Trend Przychodów: Linie (Line Chart)")
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=results_a['Volume_Bucket'], y=results_a['Revenue_USD'],
        name='Scenariusz A', mode='lines+markers', marker_color='#EF553B',
        line=dict(width=3)
    ))
    fig_line.add_trace(go.Scatter(
        x=results_b['Volume_Bucket'], y=results_b['Revenue_USD'],
        name='Scenariusz B', mode='lines+markers', marker_color='#00CC96',
        line=dict(width=3)
    ))
    fig_line.update_layout(
        xaxis_title='Przedział Wolumenu',
        yaxis_title='Przychód (USD)',
        hovermode="x unified",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# POBIERANIE WYNIKÓW
# ==========================================
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