import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. KONFIGURACJA STRONY
# ==========================================
st.set_page_config(page_title="A/B Spread Revenue Calculator", layout="wide")

# ==========================================
# UKRYCIE ELEMENTOW STREAMLIT COMMUNITY CLOUD
# ==========================================
st.markdown("""
    <style>
        [data-testid="stActionButtonIcon"]      { display: none !important; }
        button[data-testid="baseButton-header"] { display: none !important; }
        .stActionButton                         { display: none !important; }
        #MainMenu                               { visibility: hidden !important; }
        footer                                  { visibility: hidden !important; }
        .stAppDeployButton                      { display: none !important; }
        [data-testid="stToolbar"]               { display: none !important; }
        [data-testid="collapsedControl"]        { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# STAŁE — WARTOŚĆ 1 LOTA
# ==========================================
LOT_PRICE_XAUUSD = 500_000.0   # 1 Lot XAUUSD = 500 000 USD
LOT_PRICE_XAGUSD = 400_000.0   # 1 Lot XAGUSD = 400 000 USD

# ==========================================
# 2. ŁADOWANIE DANYCH (CSV)
# ==========================================
@st.cache_data
def load_csv_auto_sep(path: str) -> pd.DataFrame:
    """Ładuje CSV automatycznie wykrywając separator (; lub ,)."""
    try:
        df = pd.read_csv(path, sep=";")
        if len(df.columns) >= 2:
            return df
    except Exception:
        pass
    return pd.read_csv(path, sep=",")


@st.cache_data
def load_distributions_xauusd() -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        df_futures = load_csv_auto_sep("futures_distribution.csv")
        df_spot    = load_csv_auto_sep("spot_distribution.csv")
        for name, df in [("futures_distribution.csv", df_futures), ("spot_distribution.csv", df_spot)]:
            if "volume_range" not in df.columns or "filled_volume" not in df.columns:
                st.error(f"Plik {name} nie zawiera wymaganych kolumn: 'volume_range', 'filled_volume'.")
                return pd.DataFrame(), pd.DataFrame()
        return df_futures, df_spot
    except FileNotFoundError as e:
        st.error(f"Nie znaleziono pliku dystrybucji XAUUSD: {e}")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Nieoczekiwany błąd (XAUUSD): {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data
def load_distributions_xagusd() -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        df_futures = load_csv_auto_sep("futures_distribution_XAGUSD.csv")
        df_spot    = load_csv_auto_sep("spot_distribution_XAGUSD.csv")
        for name, df in [("futures_distribution_XAGUSD.csv", df_futures), ("spot_distribution_XAGUSD.csv", df_spot)]:
            if "volume_range" not in df.columns or "filled_volume" not in df.columns:
                st.error(f"Plik {name} nie zawiera wymaganych kolumn: 'volume_range', 'filled_volume'.")
                return pd.DataFrame(), pd.DataFrame()
        return df_futures, df_spot
    except FileNotFoundError as e:
        st.error(f"Nie znaleziono pliku dystrybucji XAGUSD: {e}")
        return pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        st.error(f"Nieoczekiwany błąd (XAGUSD): {e}")
        return pd.DataFrame(), pd.DataFrame()


# ==========================================
# DOMYŚLNE ORDER BOOKI — XAUUSD
# ==========================================
@st.cache_data
def load_default_ob_xauusd_futures() -> pd.DataFrame:
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7],
        "Bid Size": [1.0,  6.0, 10.0, 11.0, 15.0, 19.0, 23.0],
        "Ask Size": [1.0,  6.0, 11.0, 15.0, 18.0, 19.0, 20.0],
        "Spread":   [31.0, 42.0, 57.0, 84.0, 115.0, 164.0, 247.0],
    })

@st.cache_data
def load_default_ob_xauusd_spot_a() -> pd.DataFrame:
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "Bid Size": [1.0, 4.5, 6.0, 9.0, 11.5, 14.0, 16.5, 23.5, 35.0, 44.0],
        "Ask Size": [1.0, 4.5, 6.0, 9.0, 11.5, 14.0, 16.5, 23.5, 35.0, 44.0],
        "Spread":   [20.0, 44.0, 65.0, 82.0, 112.0, 145.0, 180.0, 211.0, 241.0, 270.0],
    })

@st.cache_data
def load_default_ob_xauusd_spot_b() -> pd.DataFrame:
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "Bid Size": [1.0, 4.5, 6.0, 9.0, 11.5, 14.0, 16.5, 23.5, 35.0, 44.0],
        "Ask Size": [1.0, 4.5, 6.0, 9.0, 11.5, 14.0, 16.5, 23.5, 35.0, 44.0],
        "Spread":   [20.0, 44.0, 65.0, 82.0, 112.0, 145.0, 180.0, 211.0, 241.0, 270.0],
    })


# ==========================================
# DOMYŚLNE ORDER BOOKI — XAGUSD
# Futures: z OB_Futures_XAGUSD.xlsx (7 linii)
# Spot:    z OB_Spot_XAGUSD.xlsx    (5 linii)
# ==========================================
@st.cache_data
def load_default_ob_xagusd_futures() -> pd.DataFrame:
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7],
        "Bid Size": [2.4, 3.0, 4.5, 6.0, 7.5, 9.0, 11.5],
        "Ask Size": [2.4, 3.0, 4.5, 6.0, 7.5, 9.0, 11.5],
        "Spread":   [46.0, 52.0, 66.0, 80.0, 96.0, 110.0, 132.0],
    })

@st.cache_data
def load_default_ob_xagusd_spot_a() -> pd.DataFrame:
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5],
        "Bid Size": [1.0, 2.0, 5.0, 10.0, 20.0],
        "Ask Size": [1.0, 2.0, 5.0, 10.0, 20.0],
        "Spread":   [22.0, 40.0, 60.0, 82.0, 112.0],
    })

@st.cache_data
def load_default_ob_xagusd_spot_b() -> pd.DataFrame:
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5],
        "Bid Size": [1.0, 2.0, 5.0, 10.0, 20.0],
        "Ask Size": [1.0, 2.0, 5.0, 10.0, 20.0],
        "Spread":   [22.0, 40.0, 60.0, 82.0, 112.0],
    })


# ==========================================
# 3. WALIDACJA ORDER BOOK
# ==========================================
def validate_order_book(ob: pd.DataFrame) -> list[str]:
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


def calculate_per_bucket_revenue(order_book: pd.DataFrame, volume_distribution: pd.DataFrame, lot_price: float) -> pd.DataFrame:
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

        revenue      = round((filled_volume * assigned_spread) / 2, 2)
        turnover_usd = filled_volume * lot_price
        rpm          = (revenue / turnover_usd * 1_000_000) if turnover_usd > 0 else 0.0

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


def calculate_fill_rate_per_line(results: pd.DataFrame, order_book: pd.DataFrame, lot_price: float) -> pd.DataFrame:
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

    total_volume = sum(fill_volumes.values())

    rows = []
    for line in lines:
        count  = fill_counts[line]
        volume = fill_volumes[line]
        rev    = fill_revenues[line]
        turnover = volume * lot_price
        rpm      = (rev / turnover * 1_000_000) if turnover > 0 else 0.0

        rows.append({
            "OB Line":         line,
            "Fill Count":      count,
            "Fill Volume":     round(volume, 2),
            "Fill Volume (%)": round((volume / total_volume * 100), 1) if total_volume > 0 else 0.0,
            "RPM":             round(rpm, 2),
        })

    return pd.DataFrame(rows)

# ==========================================
# 5. SILNIK INTERFEJSU
# ==========================================
def render_dashboard(vol_dist_df: pd.DataFrame, tab_name: str, default_ob_df: pd.DataFrame,
                     lot_price: float, default_ob_df_b: pd.DataFrame = None) -> None:
    """Renderuje pełny dashboard dla jednego rynku (zakładki)."""

    TABLE_HEIGHT = 300
    col_left, col_right = st.columns(2)

    # --- Scenariusz A (Current) ---
    with col_left:
        st.header(f"Scenariusz A — {tab_name} (Current)")
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

        results_a = calculate_per_bucket_revenue(edited_ob_a, vol_dist_df, lot_price)

        if results_a.empty:
            st.warning("Brak wyników dla Scenariusza A. Sprawdź dane wejściowe.")
            return

        total_rev_a      = results_a["Revenue_USD"].sum()
        total_turnover_a = results_a["Turnover_USD"].sum()
        rpm_a            = (total_rev_a / total_turnover_a * 1_000_000) if total_turnover_a > 0 else 0.0

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
        st.header(f"Scenariusz B — {tab_name} (Optimized)")
        st.markdown("**1. Edytuj Order Book B**")

        edited_ob_b = st.data_editor(
            (default_ob_df_b if default_ob_df_b is not None else default_ob_df).copy(),
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

        results_b = calculate_per_bucket_revenue(edited_ob_b, vol_dist_df, lot_price)

        if results_b.empty:
            st.warning("Brak wyników dla Scenariusza B. Sprawdź dane wejściowe.")
            return

        total_rev_b      = results_b["Revenue_USD"].sum()
        total_turnover_b = results_b["Turnover_USD"].sum()
        rpm_b            = (total_rev_b / total_turnover_b * 1_000_000) if total_turnover_b > 0 else 0.0

        diff_vs_a  = total_rev_b - total_rev_a
        diff_color = "#00CC96" if diff_vs_a >= 0 else "#EF553B"
        diff_sign  = "+" if diff_vs_a >= 0 else ""

        diff_rpm  = rpm_b - rpm_a
        rpm_color = "#00CC96" if diff_rpm >= 0 else "#EF553B"
        rpm_sign  = "+" if diff_rpm >= 0 else ""

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

    fill_a = calculate_fill_rate_per_line(results_a, edited_ob_a, lot_price)
    fill_b = calculate_fill_rate_per_line(results_b, edited_ob_b, lot_price)

    col_fill_left, col_fill_right = st.columns(2)

    with col_fill_left:
        st.markdown("**Scenariusz A (Current)**")
        st.dataframe(fill_a, use_container_width=True, hide_index=True)

    with col_fill_right:
        st.markdown("**Scenariusz B (Optimized)**")
        st.dataframe(fill_b, use_container_width=True, hide_index=True)

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

    n = min(len(ob_lines), len(ask_a), len(ask_b), len(spr_a), len(spr_b))
    ob_lines_str = [str(x) for x in ob_lines[:n]]

    fig_ob = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Lot Sizes: Current vs Optimized", "Spreads: Current vs Optimized"),
        horizontal_spacing=0.10,
    )

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

    fixed_lines_count = min(2, n)
    max_spr = max(max(spr_a[:n]), max(spr_b[:n])) * 1.1

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
    # SEKCJA: PRZYCHOD — porownanie A vs B
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
        file_name=f"symulacja_ab_revenue_{tab_name.lower().replace(' ', '_').replace(':', '')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_btn_{tab_name}",
    )

# ==========================================
# 6. INSTRUKCJA
# ==========================================
def render_instruction_tab() -> None:
    st.header("Metodologia i opis kalkulatora")

    st.markdown("""
---

### Dane wejściowe — skąd pochodzi wolumen?

Kalkulator wczytuje pliki CSV z dystrybucjami wolumenu dla poszczególnych instrumentów i rynków. Każdy wiersz opisuje:

- **volume_range** — przedział wielkości zlecenia w lotach, np. `(6, 11]` oznacza zlecenia większe niż 6 i nie większe niż 11 lotów.
- **filled_volume** — łączny wolumen (w lotach) który historycznie wpadł w ten przedział. To zagregowana liczba z danych transakcyjnych.

Dane te są stałe — odzwierciedlają historyczne zachowanie klientów i nie zmieniają się w zależności od konfiguracji Order Booka.

---

### Obsługiwane instrumenty

| Instrument | Rynki | Wartość 1 Lota |
|------------|-------|----------------|
| **XAUUSD** | Futures, Spot | 500 000 USD |
| **XAGUSD** | Futures, Spot | 400 000 USD |

---

### Logika przypisania zlecenia do linii OB

Dla każdego bucketu kalkulator sprawdza, na którą linię Order Booka wpadłoby zlecenie o wielkości równej górnej granicy tego przedziału. Robi to przez porównanie górnej granicy bucketu ze **skumulowanym Ask Size** Order Booka.

Przykład: jeśli OB wygląda tak:

| OB Line | Ask Size | Cum. Ask Size |
|---------|----------|---------------|
| 1       | 1        | 1             |
| 2       | 6        | 7             |
| 3       | 11       | 18            |

Zlecenie z bucketu `(6, 11]` (górna granica = 11) trafi w **linię 3**, bo dopiero tam skumulowany Ask Size osiąga wartość >= 11. Do tego bucketu zostaje przypisany spread z linii 3.

---

### Jak wyliczany jest Revenue?

```
Revenue = (Filled_Volume x Assigned_Spread) / 2
```

Dzielenie przez 2 wynika z tego, że spread jest kwotowany jako różnica bid-ask, a LP zarabia połowę spreadu na każdej stronie transakcji.

---

### Jak wyliczany jest Turnover?

```
Turnover_USD = Filled_Volume x LOT_PRICE_USD
```

Wartość LOT_PRICE_USD zależy od instrumentu:
- **XAUUSD**: 1 Lot = 500 000 USD notional
- **XAGUSD**: 1 Lot = 400 000 USD notional

---

### Jak wyliczany jest RPM?

```
RPM = (Revenue_USD / Turnover_USD) x 1 000 000
```

RPM (Revenue per Million) to przychód w dolarach na każdy 1 milion dolarów obrotu. Jest to kluczowy wskaźnik efektywności — uniezależnia ocenę od rozmiaru wolumenu i pozwala porównywać różne konfiguracje Order Booka oraz różne rynki na jednej skali. RPM jest liczony zarówno per bucket (tabela wyników), jak i per linia OB (tabela Fill Rate).

---

### Fill Rate per OB Line — co pokazują tabele?

Dla każdej linii OB kalkulator zlicza na podstawie przypisanych bucketów:

- **Fill Count** — ile bucketów zostało przypisanych do tej linii, czyli ile razy ta linia obsłużyła zlecenie.
- **Fill Volume** — łączny wolumen (w lotach) ze wszystkich bucketów przypisanych do tej linii.
- **Fill Volume (%)** — udział tej linii w całkowitym wolumenie. Najważniejsza kolumna — pokazuje gdzie realnie koncentruje się obrót klientów.
- **RPM** — efektywność przychodu liczona wyłącznie dla wolumenu który przeszedł przez tę linię.

Fill Rate pozwala ocenić które linie OB mają realne znaczenie biznesowe. Jeśli linie 5-7 mają Fill Volume (%) bliskie zeru, zmiany ich spreadów nie wpłyną na przychód.

---

### Wykres Fill Rate — jak czytać?

**Słupki (lewa oś Y)** — procentowy udział wolumenu per linia. Im wyższy słupek, tym więcej realnego obrotu klientów przeszło przez tę linię.

**Linia ciągła (prawa oś Y)** — Fill Count, czyli liczba użyć danej linii. Duży Fill Count przy małym Fill Volume wskazuje na wiele małych zleceń — typowy sygnał flow retailowego.

Porównanie Scenariusza A i B na tym wykresie pokazuje czy zmiana grubości linii w OB realnie przesunęła wolumen między liniami.

---

### Wykres Current vs Optimized — jak czytać?

**Lewy panel (Lot Sizes)** — porównuje grubość linii (Ask Size) między Scenariuszem A i B. Pokazuje gdzie dodajesz lub zabierasz płynność.

**Prawy panel (Spreads)** — porównuje spready per linia. Różowe tło na liniach 1-2 oznacza, że są traktowane jako "Fixed" — competitive tier, który zazwyczaj nie powinien być agresywnie zmieniany bez analizy wpływu na fill rate.

---

### Wykres Porównanie Przychodów — jak czytać?

Słupki pokazują Revenue per bucket dla Scenariusza A (czerwony) i B (zielony). Linia przerywana (prawa oś) pokazuje procentową zmianę B względem A dla każdego bucketu z osobna. Pozwala zidentyfikować które przedziały wolumenowe zyskują lub tracą najbardziej na zmianie konfiguracji OB.

---

### Dane zakodowane na stałe w aplikacji

| Parametr | Wartość | Opis |
|----------|---------|------|
| `LOT_PRICE_XAUUSD` | 500 000 USD | Wartość notional 1 lota XAUUSD |
| `LOT_PRICE_XAGUSD` | 400 000 USD | Wartość notional 1 lota XAGUSD |
| Fixed Lines (wykres) | Linie 1-2 | Competitive tier oznaczony różowym tłem |
| Domyślny OB XAUUSD Futures | 7 linii | Ask: 1, 6, 11, 15, 18, 19, 20 / Spready: 31, 42, 57, 84, 115, 164, 247 |
| Domyślny OB XAUUSD Spot | 10 linii | Ask: 1, 4.5, 6, 9, 11.5, 14, 16, 23, 35, 44 / Spready: 20, 44, 65, 82, 112, 145, 180, 211, 241, 270 |
| Domyślny OB XAGUSD Futures | 7 linii | Ask: 2, 3, 4, 6, 7, 9, 11 / Spready: 46, 52, 66, 80, 96, 110, 132 |
| Domyślny OB XAGUSD Spot | 5 linii | Ask: 1, 2, 5, 10, 20 / Spready: 22, 40, 60, 82, 112 |

---

### Eksport danych

Przycisk "Pobierz wyniki jako Excel" na dole każdej zakładki generuje plik z czterema arkuszami: wyniki per bucket dla Scenariusza A i B oraz tabele Fill Rate dla obu scenariuszy.
    """)

# ==========================================
# 7. GŁÓWNA STRONA I ZAKŁADKI
# ==========================================
st.title("A/B Spread & Revenue Calculator")
st.write("Wybierz instrument i rynek z zakładek poniżej, aby porównać scenariusze na odpowiednich wolumenach.")

# Ładowanie danych
df_xau_futures, df_xau_spot = load_distributions_xauusd()
df_xag_futures, df_xag_spot = load_distributions_xagusd()

# Domyślne Order Booki — XAUUSD
ob_xau_futures   = load_default_ob_xauusd_futures()
ob_xau_spot_a    = load_default_ob_xauusd_spot_a()
ob_xau_spot_b    = load_default_ob_xauusd_spot_b()

# Domyślne Order Booki — XAGUSD
ob_xag_futures   = load_default_ob_xagusd_futures()
ob_xag_spot_a    = load_default_ob_xagusd_spot_a()
ob_xag_spot_b    = load_default_ob_xagusd_spot_b()

# Sprawdzenie dostępności danych
xau_ok = not df_xau_futures.empty and not df_xau_spot.empty
xag_ok = not df_xag_futures.empty and not df_xag_spot.empty

if xau_ok or xag_ok:
    tab_names = []
    if xau_ok:
        tab_names += ["Rynek Futures XAUUSD", "Rynek Spot XAUUSD"]
    if xag_ok:
        tab_names += ["Rynek Futures XAGUSD", "Rynek Spot XAGUSD"]
    tab_names.append("Instrukcja")

    tabs = st.tabs(tab_names)

    idx = 0

    if xau_ok:
        with tabs[idx]:
            render_dashboard(df_xau_futures, "Futures XAUUSD", ob_xau_futures, LOT_PRICE_XAUUSD)
        idx += 1

        with tabs[idx]:
            render_dashboard(df_xau_spot, "Spot XAUUSD", ob_xau_spot_a, LOT_PRICE_XAUUSD, ob_xau_spot_b)
        idx += 1

    if xag_ok:
        with tabs[idx]:
            render_dashboard(df_xag_futures, "Futures XAGUSD", ob_xag_futures, LOT_PRICE_XAGUSD)
        idx += 1

        with tabs[idx]:
            render_dashboard(df_xag_spot, "Spot XAGUSD", ob_xag_spot_a, LOT_PRICE_XAGUSD, ob_xag_spot_b)
        idx += 1

    with tabs[idx]:
        render_instruction_tab()

else:
    st.warning(
        "Oczekuję na pliki. Upewnij się, że wgrałeś pliki dystrybucji "
        "(`futures_distribution.csv`, `spot_distribution.csv` dla XAUUSD i/lub "
        "`futures_distribution_XAGUSD.csv`, `spot_distribution_XAGUSD.csv` dla XAGUSD)."
    )
