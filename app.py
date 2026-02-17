import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. ZABEZPIECZENIE HASŁEM
# ==========================================
st.set_page_config(page_title="A/B Spread Revenue Calculator", layout="wide")

def check_password():
    """Zwraca True jeśli hasło jest poprawne."""
    def password_entered():
        # HASŁO USTAWIONE NA: Stop_Out
        if st.session_state["password"] == "Stop_Out":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Usuwamy hasło z pamięci ze względów bezpieczeństwa
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Wprowadź hasło, aby uzyskać dostęp do kalkulatora:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Wprowadź hasło, aby uzyskać dostęp do kalkulatora:", type="password", on_change=password_entered, key="password")
        st.error("❌ Niepoprawne hasło")
        return False
    return True

if not check_password():
    st.stop()  # Zatrzymuje aplikację tutaj, jeśli hasło nie zostało podane poprawnie

# ==========================================
# 2. ŁADOWANIE DANYCH (CSV)
# ==========================================
@st.cache_data
def load_distributions():
    try:
        df_Futuress = pd.read_csv("Futuress_distribution.csv")
        df_spot = pd.read_csv("spot_distribution.csv")
        return df_Futuress, df_spot
    except Exception as e:
        st.error(f"Nie znaleziono plików dystrybucji lub wystąpił błąd. Błąd: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data
def load_default_order_book():
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7],
        "Bid Size": [1.0, 6.0, 10.0, 11.0, 15.0, 19.0, 23.0],
        "Ask Size": [1.0, 6.0, 11.0, 15.0, 18.0, 19.0, 20.0],
        "Spread": [31.0, 42.0, 57.0, 84.0, 115.0, 164.0, 247.0]
    })

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
# 3. SILNIK INTERFEJSU (Jedna funkcja do rysowania tabel dla zakładek)
# ==========================================
def render_dashboard(vol_dist_df, tab_name):
    default_ob_df = load_default_order_book()
    TABLE_HEIGHT = 300 

    col_left, col_right = st.columns(2)

    with col_left:
        st.header(f"🔴 Scenariusz A ({tab_name})")
        st.markdown("**1. Edytuj Order Book A**")
        edited_ob_a = st.data_editor(
            default_ob_df.copy(), 
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True, 
            key=f"ob_a_{tab_name}",
            height=TABLE_HEIGHT
        )
        
        results_a = calculate_per_bucket_revenue(edited_ob_a, vol_dist_df)
        total_rev_a = results_a['Revenue_USD'].sum()
        
        # POPRAWIONA LINIJKA A (Czysty HTML)
        st.markdown(f"**2. Wyniki A** &mdash; Total Revenue: <span style='color:#EF553B; font-size:1.1em; font-weight:bold;'>${total_rev_a:,.2f}</span>", unsafe_allow_html=True)
        st.dataframe(results_a, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with col_right:
        st.header(f"🔵 Scenariusz B ({tab_name})")
        st.markdown("**1. Edytuj Order Book B**")
        edited_ob_b = st.data_editor(
            default_ob_df.copy(), 
            num_rows="dynamic", 
            use_container_width=True, 
            hide_index=True, 
            key=f"ob_b_{tab_name}",
            height=TABLE_HEIGHT
        )
        
        results_b = calculate_per_bucket_revenue(edited_ob_b, vol_dist_df)
        total_rev_b = results_b['Revenue_USD'].sum()
        diff_vs_a = total_rev_b - total_rev_a
        
        diff_color = "#00CC96" if diff_vs_a >= 0 else "#EF553B"
        diff_sign = "+" if diff_vs_a >= 0 else ""
        
        # POPRAWIONA LINIJKA B (Czysty HTML)
        st.markdown(f"**2. Wyniki B** &mdash; Total Revenue: <span style='color:#00CC96; font-size:1.1em; font-weight:bold;'>${total_rev_b:,.2f}</span> <span style='color:{diff_color}; font-size:0.9em; font-weight:bold;'>({diff_sign}${diff_vs_a:,.2f} vs A)</span>", unsafe_allow_html=True)
        st.dataframe(results_b, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    st.divider()

    # OBLICZENIA PROCENTOWE
    pct_diff_list = []
    for rev_a, rev_b in zip(results_a['Revenue_USD'], results_b['Revenue_USD']):
        if rev_a > 0:
            pct = ((rev_b - rev_a) / rev_a) * 100
        elif rev_a == 0 and rev_b > 0:
            pct = 100.0  
        else:
            pct = 0.0
        pct_diff_list.append(pct)

    results_b['Pct_Diff'] = pct_diff_list

    # WYKRES: PARTER
    st.header(f"📈 Porównanie Przychodów dla dystrybucji {tab_name} (z różnicą %)")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(x=results_a['Volume_Bucket'], y=results_a['Revenue_USD'], name='Scenariusz A (USD)', marker_color='#EF553B'), secondary_y=False)
    fig.add_trace(go.Bar(x=results_b['Volume_Bucket'], y=results_b['Revenue_USD'], name='Scenariusz B (USD)', marker_color='#00CC96'), secondary_y=False)
    fig.add_trace(go.Scatter(x=results_b['Volume_Bucket'], y=results_b['Pct_Diff'], name='Różnica B vs A (%)', mode='lines+markers', marker_color='#FFA15A', line=dict(width=3, dash='dot')), secondary_y=True)

    fig.update_layout(
        barmode='group', 
        xaxis_title='Przedział Wolumenu (Volume Bucket)',
        hovermode="x unified",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="Przychód (USD)", secondary_y=False)
    fig.update_yaxes(title_text="Zmiana (%)", secondary_y=True, showgrid=False, tickformat=".1f", ticksuffix="%")

    st.plotly_chart(fig, use_container_width=True)

    # Przycisk pobierania Excela (odseparowany dla każdej zakładki)
    st.write("---")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        results_a.to_excel(writer, sheet_name=f'Scenariusz A ({tab_name})', index=False)
        results_b.to_excel(writer, sheet_name=f'Scenariusz B ({tab_name})', index=False)
    output.seek(0)

    st.download_button(
        label=f"📥 Pobierz wyniki {tab_name} jako Excel",
        data=output,
        file_name=f"symulacja_ab_revenue_{tab_name.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_btn_{tab_name}"
    )

# ==========================================
# 4. GŁÓWNA STRONA I ZAKŁADKI (TABS)
# ==========================================
st.title("📊 A/B Spread & Revenue Calculator")
st.write("Wybierz rynek z zakładek poniżej, aby porównać scenariusze na odpowiednich wolumenach.")

df_Futuress, df_spot = load_distributions()

# Jeśli pliki zostały poprawnie załadowane, budujemy zakładki
if not df_Futuress.empty and not df_spot.empty:
    
    # Tworzenie dwóch zakładek na samej górze
    tab_Futures, tab_spot = st.tabs(["Futuress", "Spot"])

    # Wrzucenie całej logiki (tabel, wykresów) do pierwszej zakładki
    with tab_Futures:
        render_dashboard(df_Futuress, "Futuress")

    # Wrzucenie całej logiki do drugiej zakładki
    with tab_spot:
        render_dashboard(df_spot, "Spot")
        
else:
    st.warning("Oczekuję na pliki. Upewnij się, że wgrałeś `Futuress_distribution.csv` oraz `spot_distribution.csv`.")