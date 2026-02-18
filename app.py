import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. KONFIGURACJA STRONY
# ==========================================
st.set_page_config(page_title="A/B Spread Revenue Calculator", layout="wide")

LOT_PRICE_USD = 500_000.0  # Stała wartość 1 Lota dla XAUUSD

# ==========================================
# 2. ŁADOWANIE DANYCH (CSV)
# ==========================================
@st.cache_data
def load_distributions() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ładuje dystrybucje wolumenu dla rynków Futures i Spot.
    Oczekiwane kolumny CSV: volume_range (string), filled_volume (float).
    """
    try:
        df_futures = pd.read_csv("futures_distribution.csv")
        df_spot    = pd.read_csv("spot_distribution.csv")

        for name, df in [("futures_distribution.csv", df_futures), ("spot_distribution.csv", df_spot)]:
            if "volume_range" not in df.columns or "filled_volume" not in df.columns:
                st.error(f"Plik {name} nie zawiera wymaganych kolumn: 'volume_range', 'filled_volume'.")
                return pd.DataFrame(), pd.DataFrame()

        return df_futures, df_spot

    except FileNotFoundError as e:
        st.error(f"Nie znaleziono pliku dystrybucji: {e}")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Nieoczekiwany błąd podczas ładowania danych: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data
def load_default_order_book_futures() -> pd.DataFrame:
    """Domyślny Order Book dla zakładki Futures"""
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7],
        "Bid Size": [1.0,  6.0, 10.0, 11.0, 15.0, 19.0, 23.0],
        "Ask Size": [1.0,  6.0, 11.0, 15.0, 18.0, 19.0, 20.0],
        "Spread":   [31.0, 42.0, 57.0, 84.0, 115.0, 164.0, 247.0],
    })

@st.cache_data
def load_default_order_book_spot() -> pd.DataFrame:
    """Nowy, domyślny Order Book wczytany z pliku OB.xlsx dla zakładki Spot"""
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "Bid Size": [1.0, 6.0, 10.0, 13.0, 18.0, 19.0, 22.0, 32.0, 36.0, 42.0],
        "Ask Size": [1.0, 6.0, 10.0, 15.0, 17.0, 18.0, 18.0, 25.0, 35.0, 44.0],
        "Spread":   [21.0, 41.0, 62.0, 88.0, 112.0, 145.0, 180.0, 211.0, 241.0, 270.0],
    })

# ==========================================
# 3. WALIDACJA ORDER BOOK
# ==========================================
def validate_order_book(ob: pd.DataFrame) -> list[str]:
    """
    Sprawdza poprawność danych Order Book.
    Zwraca listę komunikatów o błędach (pusta = dane prawidłowe).
    """
    errors = []

    for col in ["Ask Size", "Spread"]:
        if col not in ob.columns:
            errors.append(f"Brak kolumny: {col}")
            return errors

    if ob["Ask Size"].isnull().any():
        errors.append("Kolumna 'Ask Size' zawiera puste wartości.")
    elif (ob["Ask Size"] <= 0).any():
        errors.append("Wartości 'Ask Size' muszą być większe od zera.")

    if ob["Spread"].isnull().any():
        errors.append("Kolumna 'Spread' zawiera puste wartości.")
    elif (ob["Spread"] <= 0).any():
        errors.append("Wartości 'Spread' muszą być większe od zera.")

    return errors

# ==========================================
# 4. SILNIK KALKULACJI
# ==========================================
def parse_bucket_end(vol_range_str: str) -> float | None:
    try:
        cleaned = str(vol_range_str).replace('"', "").replace("'", "").strip()
        end_str = cleaned.split(",")[1].strip(" )]")
        return float(end_str)
    except (IndexError, ValueError):
        return None

def calculate_per_bucket_revenue(order_book: pd.DataFrame, volume_distribution: pd.DataFrame) -> pd.DataFrame:
    ob = order_book.copy()
    ob["Ask Size"] = pd.to_numeric(ob["Ask Size"], errors="coerce")
    ob["Spread"]   = pd.to_numeric(ob["Spread"],   errors="coerce")
    ob["Cum_Ask_Size"] = ob["Ask Size"].cumsum()

    if "OB Line" not in ob.columns:
        ob["OB Line"] = range(1, len(ob) + 1)

    results = []

    for _, row in volume_distribution.iterrows():
        bucket_end = parse_bucket_end(row["volume_range"])

        if bucket_end is None:
            st.warning(f"Nie można sparsować przedziału: '{row['volume_range']}' — pominięto.")
            continue

        filled_volume = float(row["filled_volume"])
        valid_lines   = ob[ob["Cum_Ask_Size"] >= bucket_end]

        if not valid_lines.empty:
            assigned_spread = float(valid_lines.iloc[0]["Spread"])
            ob_line_used    = int(valid_lines.iloc[0]["OB Line"])
        else:
            assigned_spread = float(ob.iloc[-1]["Spread"])
            ob_line_used    = int(ob.iloc[-1]["OB Line"])

        revenue = round((filled_volume * assigned_spread) / 2, 2)
        
        # Wyliczenie Turnoveru i RPM
        turnover_usd = filled_volume * LOT_PRICE_USD
        rpm = (revenue / turnover_usd * 1_000_000) if turnover_usd > 0 else 0.0

        results.append({
            "Volume_Bucket":   row["volume_range"],
            "Filled_Volume":   round(filled_volume, 2),
            "OB_Line_Used":    ob_line_used,
            "Assigned_Spread": round(assigned_spread, 2),
            "Turnover_USD":    round(turnover_usd, 2),
            "Revenue_USD":     revenue,
            "RPM":             round(rpm, 2),
        })

    return pd.DataFrame(results)

def calculate_fill_rate_per_line(results: pd.DataFrame, order_book: pd.DataFrame) -> pd.DataFrame:
    ob = order_book.copy()
    if "OB Line" not in ob.columns:
        ob["OB Line"] = range(1, len(ob) + 1)

    lines = ob["OB Line"].tolist()

    fill_counts   = {line: 0   for line in lines}
    fill_volumes  = {line: 0.0 for line in lines}
    fill_revenues = {line: 0.0 for line in lines}

    for _, row in results.iterrows():
        line = row["OB_Line_Used"]
        if line in fill_counts:
            fill_counts[line]   += 1
            fill_volumes[line]  += float(row["Filled_Volume"])
            fill_revenues[line] += float(row["Revenue_USD"])

    total_count  = sum(fill_counts.values())
    total_volume = sum(fill_volumes.values())

    rows = []
    for line in lines:
        count  = fill_counts[line]
        volume = fill_volumes[line]
        rev    = fill_revenues[line]
        
        # RPM per konkretna linia
        turnover = volume * LOT_PRICE_USD
        rpm = (rev / turnover * 1_000_000) if turnover > 0 else 0.0
        
        rows.append({
            "OB Line":         line,
            "Fill Count":      count,
            "Fill Volume":     round(volume, 2),
            "Fill Volume (%)": round((volume / total_volume * 100), 1) if total_volume > 0 else 0.0,
            "RPM":             round(rpm, 2),
        })

    return pd.DataFrame(rows)

# ==========================================
# 5. ZAKŁADKA Z INSTRUKCJĄ (Po ludzku)
# ==========================================
def render_instruction_tab():
    st.header("📖 Jak korzystać z tego kalkulatora?")
    
    st.markdown("""
    Cześć! Ten kalkulator to symulator, który pozwala Ci sprawdzić: **„Ile kasy byśmy zarobili, gdybyśmy zmienili spready i wielkość lotów w naszym Order Booku?”**
    
    Bierze on twarde, historyczne dane o tym, jak duże zlecenia składali klienci, a następnie "przepuszcza" je przez nasz Order Book, żeby sprawdzić rentowność.

    ---

    ### 🛠️ Instrukcja krok po kroku:
    1. **Wybierz rynek** na górze (Futures lub Spot).
    2. Zobaczysz podzielony ekran. 
       - **Lewa strona (Scenariusz A)** to Twój punkt wyjścia (Obecny Order Book).
       - **Prawa strona (Scenariusz B)** to Twój plac zabaw do optymalizacji.
    3. **Zmień wartości** w tabeli po prawej stronie (np. podnieś spread na 3 linii, albo zmniejsz Ask Size na pierwszej).
    4. Wszystkie wykresy i tabele poniżej zaktualizują się od razu i pokażą Ci, **ile zyskujesz lub tracisz** w stosunku do punktu wyjścia.

    ---

    ### 💡 Słowniczek najważniejszych pojęć:
    * **Ask Size:** Wielkość (w lotach) płynności dostępnej na danym poziomie Order Booka.
    * **Spread:** Ile punktów zapłaci klient, jeśli "wpadnie" w tę linię.
    * **Total Revenue:** Całkowity wygenerowany zysk (wzór: `Wolumen * Spread / 2`).
    * **RPM (Revenue per Million):** Najważniejszy wskaźnik do oceny! Mówi o tym, ile dolarów czystego zysku generujesz z każdego 1 miliona dolarów obrotu, jaki zrobi klient. Przyjęliśmy tu rynkowy standard: **1 Lot XAUUSD = 500 000 USD obrotu**. RPM pozwala świetnie porównywać różne rynki niezależnie od ich rozmiaru.
    * **Fill Rate (Dolne tabele):** Pokazuje, jak mocno obciążona jest każda z linii. Jeśli widzisz, że 90% wolumenu idzie po pierwszych dwóch liniach, to wiesz, że zmiany spreadów na linii nr 8 nie zrobią dla biznesu żadnej różnicy.
    """)

# ==========================================
# 6. SILNIK INTERFEJSU
# ==========================================
def render_dashboard(vol_dist_df: pd.DataFrame, tab_name: str, default_ob_df: pd.DataFrame) -> None:
    """Renderuje pełny dashboard dla jednego rynku (zakładki)."""

    TABLE_HEIGHT = 300
    col_left, col_right = st.columns(2)

    # --- Scenariusz A (Current) ---
    with col_left:
        st.header(f"Scenariusz A — {tab_name}  (Current)")
        st.markdown("**1. Edytuj Order Book A**")

        edited_ob_a = st.data_editor(
            default_ob_df.copy(),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"ob_a_{tab_name}",
            height=TABLE_HEIGHT,
        )

        errors_a = validate_order_book(edited_ob_a)
        if errors_a:
            for err in errors_a:
                st.error(f"Order Book A — {err}")
            return

        results_a = calculate_per_bucket_revenue(edited_ob_a, vol_dist_df)

        if results_a.empty:
            st.warning("Brak wyników dla Scenariusza A. Sprawdź dane wejściowe.")
            return

        total_rev_a = results_a["Revenue_USD"].sum()
        total_turnover_a = results_a["Turnover_USD"].sum()
        rpm_a = (total_rev_a / total_turnover_a * 1_000_000) if total_turnover_a > 0 else 0.0

        st.markdown(
            f"<div style='margin-bottom:0.5rem;'><b>2. Wyniki A</b> &mdash; "
            f"Total Revenue: <span style='color:#EF553B;font-size:1.1em;font-weight:bold;'>"
            f"${total_rev_a:,.2f}</span> "
            f"<span style='color:#888;font-size:0.9em;margin-left:10px;'>| RPM: <b>${rpm_a:,.2f}</b></span></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(results_a, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    # --- Scenariusz B (Optimized) ---
    with col_right:
        st.header(f"Scenariusz B — {tab_name}  (Optimized)")
        st.markdown("**1. Edytuj Order Book B**")

        edited_ob_b = st.data_editor(
            default_ob_df.copy(),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"ob_b_{tab_name}",
            height=TABLE_HEIGHT,
        )

        errors_b = validate_order_book(edited_ob_b)
        if errors_b:
            for err in errors_b:
                st.error(f"Order Book B — {err}")
            return

        results_b = calculate_per_bucket_revenue(edited_ob_b, vol_dist_df)

        if results_b.empty:
            st.warning("Brak wyników dla Scenariusza B. Sprawdź dane wejściowe.")
            return

        total_rev_b = results_b["Revenue_USD"].sum()
        total_turnover_b = results_b["Turnover_USD"].sum()
        rpm_b = (total_rev_b / total_turnover_b * 1_000_000) if total_turnover_b > 0 else 0.0

        diff_vs_a   = total_rev_b - total_rev_a
        diff_color  = "#00CC96" if diff_vs_a >= 0 else "#EF553B"
        diff_sign   = "+" if diff_vs_a >= 0 else ""
        
        diff_rpm    = rpm_b - rpm_a
        rpm_color   = "#00CC96" if diff_rpm >= 0 else "#EF553B"
        rpm_sign    = "+" if diff_rpm >= 0 else ""

        st.markdown(
            f"<div style='margin-bottom:0.5rem;'><b>2. Wyniki B</b> &mdash; "
            f"Total Revenue: <span style='color:#00CC96;font-size:1.1em;font-weight:bold;'>"
            f"${total_rev_b:,.2f}</span> "
            f"<span style='color:{diff_color};font-size:0.9em;font-weight:bold;'>"
            f"({diff_sign}${diff_vs_a:,.2f} vs A)</span><br>"
            f"<span style='color:#888;font-size:0.9em;'>RPM: <b>${rpm_b:,.2f}</b></span> "
            f"<span style='color:{rpm_color};font-size:0.8em;font-weight:bold;'>({rpm_sign}${diff_rpm:,.2f})</span></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(results_b, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    st.divider()

    # ==========================================
    # SEKCJA: FILL RATE PER LINE
    # ==========================================
    st.header(f"Fill Rate per OB Line — {tab_name}")

    fill_a = calculate_fill_rate_per_line(results_a, edited_ob_a)
    fill_b = calculate_fill_rate_per_line(results_b, edited_ob_b)

    col_fill_left, col_fill_right = st.columns(2)

    with col_fill_left:
        st.markdown("**Scenariusz A (Current)**")
        st.dataframe(fill_a, use_container_width=True, hide_index=True)

    with col_fill_right:
        st.markdown("**Scenariusz B (Optimized)**")
        st.dataframe(fill_b, use_container_width=True, hide_index=True)

    # Wykres fill rate — słupki grouped per linia
    fig_fill = make_subplots(specs=[[{"secondary_y": True}]])

    fig_fill.add_trace(go.Bar(
        x=fill_a["OB Line"].astype(str),
        y=fill_a["Fill Volume (%)"],
        name="Fill Volume % — A (Current)",
        marker_color="#5B9BD5",
        opacity=0.85,
    ), secondary_y=False)

    fig_fill.add_trace(go.Bar(
        x=fill_b["OB Line"].astype(str),
        y=fill_b["Fill Volume (%)"],
        name="Fill Volume % — B (Optimized)",
        marker_color="#70AD47",
        opacity=0.85,
    ), secondary_y=False)

    fig_fill.add_trace(go.Scatter(
        x=fill_a["OB Line"].astype(str),
        y=fill_a["Fill Count"],
        name="Fill Count — A",
        mode="lines+markers",
        marker_color="#EF553B",
        line=dict(width=2, dash="dot"),
    ), secondary_y=True)

    fig_fill.add_trace(go.Scatter(
        x=fill_b["OB Line"].astype(str),
        y=fill_b["Fill Count"],
        name="Fill Count — B",
        mode="lines+markers",
        marker_color="#FFA15A",
        line=dict(width=2, dash="dash"),
    ), secondary_y=True)

    fig_fill.update_layout(
        title="Udział wolumenu (%) i liczba użyć per linia OB",
        barmode="group",
        xaxis_title="OB Line",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_fill.update_yaxes(title_text="Fill Volume (%)", secondary_y=False)
    fig_fill.update_yaxes(title_text="Fill Count (liczba bucketów)", secondary_y=True, showgrid=False)

    st.plotly_chart(fig_fill, use_container_width=True, key=f"chart_fill_{tab_name}")

    st.divider()

    # ==========================================
    # SEKCJA: CURRENT vs OPTIMIZED — Lot Sizes & Spreads
    # ==========================================
    st.header(f"Order Book — Current vs Optimized — {tab_name}")

    ob_lines = edited_ob_a["OB Line"].tolist() if "OB Line" in edited_ob_a.columns else list(range(1, len(edited_ob_a) + 1))

    ask_a = pd.to_numeric(edited_ob_a["Ask Size"], errors="coerce").tolist()
    ask_b = pd.to_numeric(edited_ob_b["Ask Size"], errors="coerce").tolist()
    spr_a = pd.to_numeric(edited_ob_a["Spread"],   errors="coerce").tolist()
    spr_b = pd.to_numeric(edited_ob_b["Spread"],   errors="coerce").tolist()

    # Wyrównujemy długości na wypadek gdyby OB miały różną liczbę linii
    n = min(len(ob_lines), len(ask_a), len(ask_b), len(spr_a), len(spr_b))
    ob_lines_str = [str(x) for x in ob_lines[:n]]

    fig_ob = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Lot Sizes: Current vs Optimized", "Spreads: Current vs Optimized"),
        horizontal_spacing=0.10,
    )

    # Panel lewy — Lot Sizes (Ask Size)
    fig_ob.add_trace(go.Bar(
        x=ob_lines_str,
        y=ask_a[:n],
        name="Current (Ask Size)",
        marker_color="#5B9BD5",
        opacity=0.85,
    ), row=1, col=1)

    fig_ob.add_trace(go.Bar(
        x=ob_lines_str,
        y=ask_b[:n],
        name="Optimized (Ask Size)",
        marker_color="#70AD47",
        opacity=0.85,
    ), row=1, col=1)

    # Panel prawy — Spreads
    fixed_lines_count = min(2, n)
    max_spr  = max(max(spr_a[:n]), max(spr_b[:n])) * 1.1

    fig_ob.add_trace(go.Scatter(
        x=ob_lines_str[:fixed_lines_count] + ob_lines_str[:fixed_lines_count][::-1],
        y=[max_spr] * fixed_lines_count + [0] * fixed_lines_count,
        fill="toself",
        fillcolor="rgba(255, 182, 193, 0.25)",
        line=dict(color="rgba(255,182,193,0)"),
        name="Fixed (Lines 1-2)",
        showlegend=True,
        hoverinfo="skip",
    ), row=1, col=2)

    fig_ob.add_trace(go.Scatter(
        x=ob_lines_str,
        y=spr_a[:n],
        name="Current (Spread)",
        mode="lines+markers",
        marker=dict(symbol="circle", size=8, color="#5B9BD5"),
        line=dict(color="#5B9BD5", width=2),
    ), row=1, col=2)

    fig_ob.add_trace(go.Scatter(
        x=ob_lines_str,
        y=spr_b[:n],
        name="Optimized (Spread)",
        mode="lines+markers",
        marker=dict(symbol="square", size=8, color="#375623"),
        line=dict(color="#375623", width=2),
    ), row=1, col=2)

    fig_ob.update_layout(
        barmode="group",
        hovermode="x unified",
        height=420,
        margin=dict(l=0, r=0, t=60, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    )

    fig_ob.update_xaxes(title_text="OB Line", row=1, col=1)
    fig_ob.update_xaxes(title_text="OB Line", row=1, col=2)
    fig_ob.update_yaxes(title_text="Lot Capacity", row=1, col=1)
    fig_ob.update_yaxes(title_text="Spread (points)", row=1, col=2)

    st.plotly_chart(fig_ob, use_container_width=True, key=f"chart_ob_{tab_name}")

    # ==========================================
    # SEKCJA: PRZYCHÓD — porównanie A vs B
    # ==========================================
    st.header(f"Porównanie Przychodów — {tab_name}")

    pct_diff_list = []
    for rev_a, rev_b in zip(results_a["Revenue_USD"], results_b["Revenue_USD"]):
        if rev_a > 0:
            pct = round(((rev_b - rev_a) / rev_a) * 100, 2)
        elif rev_a == 0 and rev_b > 0:
            pct = 100.0
        else:
            pct = 0.0
        pct_diff_list.append(pct)

    results_b = results_b.copy()
    results_b["Pct_Diff"] = pct_diff_list

    fig_rev = make_subplots(specs=[[{"secondary_y": True}]])

    fig_rev.add_trace(go.Bar(
        x=results_a["Volume_Bucket"], y=results_a["Revenue_USD"],
        name="Scenariusz A — Current (USD)", marker_color="#EF553B",
    ), secondary_y=False)

    fig_rev.add_trace(go.Bar(
        x=results_b["Volume_Bucket"], y=results_b["Revenue_USD"],
        name="Scenariusz B — Optimized (USD)", marker_color="#00CC96",
    ), secondary_y=False)

    fig_rev.add_trace(go.Scatter(
        x=results_b["Volume_Bucket"],
        y=results_b["Pct_Diff"],
        name="Różnica B vs A (%)",
        mode="lines+markers",
        marker_color="#FFA15A",
        line=dict(width=3, dash="dot"),
    ), secondary_y=True)

    fig_rev.update_layout(
        barmode="group",
        xaxis_title="Przedział Wolumenu (Volume Bucket)",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig_rev.update_yaxes(title_text="Przychód (USD)", secondary_y=False)
    fig_rev.update_yaxes(
        title_text="Zmiana (%)", secondary_y=True,
        showgrid=False, tickformat=".1f", ticksuffix="%",
    )

    st.plotly_chart(fig_rev, use_container_width=True, key=f"chart_rev_{tab_name}")

    # ==========================================
    # EKSPORT DO EXCELA
    # ==========================================
    st.write("---")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        results_a.to_excel(writer, sheet_name=f"Scenariusz A ({tab_name})", index=False)
        results_b.to_excel(writer, sheet_name=f"Scenariusz B ({tab_name})", index=False)
        fill_a.to_excel(writer,    sheet_name=f"Fill Rate A ({tab_name})",  index=False)
        fill_b.to_excel(writer,    sheet_name=f"Fill Rate B ({tab_name})",  index=False)
    output.seek(0)

    st.download_button(
        label=f"Pobierz wyniki {tab_name} jako Excel",
        data=output,
        file_name=f"symulacja_ab_revenue_{tab_name.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_btn_{tab_name}",
    )

# ==========================================
# 7. GŁÓWNA STRONA I ZAKŁADKI
# ==========================================
st.title("A/B Spread & Revenue Calculator")
st.write("Skorzystaj z zakładek poniżej, aby przeczytać instrukcję lub przejść do analizy.")

df_futures, df_spot = load_distributions()
default_ob_futures = load_default_order_book_futures()
default_ob_spot    = load_default_order_book_spot()

if not df_futures.empty and not df_spot.empty:
    tab_instrukcja, tab_future, tab_spot = st.tabs(["📖 Instrukcja", "📈 Rynek: Futures", "📉 Rynek: Spot"])

    with tab_instrukcja:
        render_instruction_tab()

    with tab_future:
        render_dashboard(df_futures, "Futures", default_ob_futures)

    with tab_spot:
        render_dashboard(df_spot, "Spot", default_ob_spot)

else:
    st.warning(
        "Oczekuję na pliki. Upewnij się, że wgrałeś "
        "`futures_distribution.csv` oraz `spot_distribution.csv`."
    )