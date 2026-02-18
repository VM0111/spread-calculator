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
        df_spot = pd.read_csv("spot_distribution.csv")

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
def load_default_order_book() -> pd.DataFrame:
    return pd.DataFrame({
        "OB Line": [1, 2, 3, 4, 5, 6, 7],
        "Bid Size": [1.0, 6.0, 10.0, 11.0, 15.0, 19.0, 23.0],
        "Ask Size": [1.0, 6.0, 11.0, 15.0, 18.0, 19.0, 20.0],
        "Spread":   [31.0, 42.0, 57.0, 84.0, 115.0, 164.0, 247.0],
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
    """
    Parsuje górną granicę przedziału wolumenu ze stringa w formacie '(a, b]'.
    Zwraca float lub None przy błędzie parsowania.
    """
    try:
        cleaned = str(vol_range_str).replace('"', "").replace("'", "").strip()
        end_str = cleaned.split(",")[1].strip(" )]")
        return float(end_str)
    except (IndexError, ValueError):
        return None


def calculate_per_bucket_revenue(order_book: pd.DataFrame, volume_distribution: pd.DataFrame) -> pd.DataFrame:
    """
    Dla każdego przedziału wolumenu wyznacza spread z Order Book
    i oblicza przychód: (filled_volume * spread) / 2.
    """
    ob = order_book.copy()
    ob["Ask Size"] = pd.to_numeric(ob["Ask Size"], errors="coerce")
    ob["Spread"]   = pd.to_numeric(ob["Spread"],   errors="coerce")
    ob["Cum_Ask_Size"] = ob["Ask Size"].cumsum()

    results = []

    for _, row in volume_distribution.iterrows():
        bucket_end = parse_bucket_end(row["volume_range"])

        if bucket_end is None:
            st.warning(f"Nie można sparsować przedziału: '{row['volume_range']}' — pominięto.")
            continue

        filled_volume = float(row["filled_volume"])
        valid_lines = ob[ob["Cum_Ask_Size"] >= bucket_end]

        assigned_spread = (
            float(valid_lines.iloc[0]["Spread"])
            if not valid_lines.empty
            else float(ob.iloc[-1]["Spread"])
        )

        revenue = round((filled_volume * assigned_spread) / 2, 2)

        results.append({
            "Volume_Bucket":   row["volume_range"],
            "Filled_Volume":   round(filled_volume, 2),
            "Assigned_Spread": round(assigned_spread, 2),
            "Revenue_USD":     revenue,
        })

    return pd.DataFrame(results)

# ==========================================
# 5. SILNIK INTERFEJSU
# ==========================================
def render_dashboard(vol_dist_df: pd.DataFrame, tab_name: str, default_ob_df: pd.DataFrame) -> None:
    """Renderuje pełny dashboard dla jednego rynku (zakładki)."""

    TABLE_HEIGHT = 300
    col_left, col_right = st.columns(2)

    # --- Scenariusz A ---
    with col_left:
        st.header(f"Scenariusz A — {tab_name}")
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

        st.markdown(
            f"<div style='margin-bottom:0.5rem;'><b>2. Wyniki A</b> &mdash; "
            f"Total Revenue: <span style='color:#EF553B;font-size:1.1em;font-weight:bold;'>"
            f"${total_rev_a:,.2f}</span></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(results_a, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    # --- Scenariusz B ---
    with col_right:
        st.header(f"Scenariusz B — {tab_name}")
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
        diff_vs_a   = total_rev_b - total_rev_a
        diff_color  = "#00CC96" if diff_vs_a >= 0 else "#EF553B"
        diff_sign   = "+" if diff_vs_a >= 0 else ""

        st.markdown(
            f"<div style='margin-bottom:0.5rem;'><b>2. Wyniki B</b> &mdash; "
            f"Total Revenue: <span style='color:#00CC96;font-size:1.1em;font-weight:bold;'>"
            f"${total_rev_b:,.2f}</span> "
            f"<span style='color:{diff_color};font-size:0.9em;font-weight:bold;'>"
            f"({diff_sign}${diff_vs_a:,.2f} vs A)</span></div>",
            unsafe_allow_html=True,
        )
        st.dataframe(results_b, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    st.divider()

    # --- Obliczenia procentowe ---
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

    # --- Wykres ---
    st.header(f"Porównanie Przychodów — {tab_name} (z różnicą %)")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(x=results_a["Volume_Bucket"], y=results_a["Revenue_USD"],
               name="Scenariusz A (USD)", marker_color="#EF553B"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(x=results_b["Volume_Bucket"], y=results_b["Revenue_USD"],
               name="Scenariusz B (USD)", marker_color="#00CC96"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=results_b["Volume_Bucket"],
            y=results_b["Pct_Diff"],
            name="Różnica B vs A (%)",
            mode="lines+markers",
            marker_color="#FFA15A",
            line=dict(width=3, dash="dot"),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        barmode="group",
        xaxis_title="Przedział Wolumenu (Volume Bucket)",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Przychód (USD)", secondary_y=False)
    fig.update_yaxes(
        title_text="Zmiana (%)", secondary_y=True,
        showgrid=False, tickformat=".1f", ticksuffix="%",
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Eksport do Excela ---
    st.write("---")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        results_a.to_excel(writer, sheet_name=f"Scenariusz A ({tab_name})", index=False)
        results_b.to_excel(writer, sheet_name=f"Scenariusz B ({tab_name})", index=False)
    output.seek(0)

    st.download_button(
        label=f"Pobierz wyniki {tab_name} jako Excel",
        data=output,
        file_name=f"symulacja_ab_revenue_{tab_name.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_btn_{tab_name}",
    )

# ==========================================
# 6. GŁÓWNA STRONA I ZAKŁADKI
# ==========================================
st.title("A/B Spread & Revenue Calculator")
st.write("Wybierz rynek z zakładek poniżej, aby porównać scenariusze na odpowiednich wolumenach.")

df_futures, df_spot = load_distributions()
default_ob_df = load_default_order_book()

if not df_futures.empty and not df_spot.empty:
    tab_future, tab_spot = st.tabs(["Rynek: Futures", "Rynek: Spot"])

    with tab_future:
        render_dashboard(df_futures, "Futures", default_ob_df)

    with tab_spot:
        render_dashboard(df_spot, "Spot", default_ob_df)

else:
    st.warning(
        "Oczekuję na pliki. Upewnij się, że wgrałeś "
        "`futures_distribution.csv` oraz `spot_distribution.csv`."
    )
