import math
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import altair as alt
import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

API_URL = "https://danepubliczne.imgw.pl/api/data/synop"
REFRESH_SECONDS = 300
IMGW_MEASUREMENT_INTERVAL_HOURS = 1
HISTORY_FILE = Path(__file__).with_name("imgw_station_history.csv")

STATIONS = [
    {"name": "Białystok", "lat": 53.1325, "lon": 23.1688},
    {"name": "Bielsko Biała", "lat": 49.8224, "lon": 19.0584},
    {"name": "Chojnice", "lat": 53.6955, "lon": 17.5570},
    {"name": "Częstochowa", "lat": 50.8118, "lon": 19.1203},
    {"name": "Elbląg", "lat": 54.1522, "lon": 19.4088},
    {"name": "Gdańsk", "lat": 54.3520, "lon": 18.6466},
    {"name": "Gdynia", "lat": 54.5189, "lon": 18.5305},
    {"name": "Gorzów Wielkopolski", "lat": 52.7368, "lon": 15.2288},
    {"name": "Hel", "lat": 54.6081, "lon": 18.8013},
    {"name": "Jelenia Góra", "lat": 50.9044, "lon": 15.7194},
    {"name": "Kalisz", "lat": 51.7611, "lon": 18.0910},
    {"name": "Kasprowy Wierch", "lat": 49.2310, "lon": 19.9810},
    {"name": "Katowice", "lat": 50.2649, "lon": 19.0238},
    {"name": "Kętrzyn", "lat": 54.0760, "lon": 21.3753},
    {"name": "Kielce", "lat": 50.8661, "lon": 20.6286},
    {"name": "Kłodzko", "lat": 50.4340, "lon": 16.6619},
    {"name": "Koło", "lat": 52.2002, "lon": 18.6386},
    {"name": "Kołobrzeg", "lat": 54.1760, "lon": 15.5760},
    {"name": "Koszalin", "lat": 54.1944, "lon": 16.1722},
    {"name": "Kraków", "lat": 50.0647, "lon": 19.9450},
    {"name": "Krosno", "lat": 49.6880, "lon": 21.7700},
    {"name": "Legnica", "lat": 51.2070, "lon": 16.1550},
    {"name": "Lesko", "lat": 49.4700, "lon": 22.3300},
    {"name": "Leszno", "lat": 51.8406, "lon": 16.5749},
    {"name": "Lublin", "lat": 51.2465, "lon": 22.5684},
    {"name": "Łeba", "lat": 54.7600, "lon": 17.5550},
    {"name": "Łódź", "lat": 51.7592, "lon": 19.4560},
    {"name": "Mikołajki", "lat": 53.8020, "lon": 21.5710},
    {"name": "Mława", "lat": 53.1128, "lon": 20.3841},
    {"name": "Nowy Sącz", "lat": 49.6244, "lon": 20.6972},
    {"name": "Olsztyn", "lat": 53.7784, "lon": 20.4801},
    {"name": "Opole", "lat": 50.6751, "lon": 17.9213},
    {"name": "Ostrołęka", "lat": 53.0862, "lon": 21.5753},
    {"name": "Piła", "lat": 53.1510, "lon": 16.7380},
    {"name": "Poznań", "lat": 52.4064, "lon": 16.9252},
    {"name": "Przemyśl", "lat": 49.7838, "lon": 22.7673},
    {"name": "Racibórz", "lat": 50.0919, "lon": 18.2193},
    {"name": "Rzeszów", "lat": 50.0412, "lon": 21.9991},
    {"name": "Sandomierz", "lat": 50.6820, "lon": 21.7480},
    {"name": "Siedlce", "lat": 52.1677, "lon": 22.2901},
    {"name": "Słubice", "lat": 52.3509, "lon": 14.5607},
    {"name": "Suwałki", "lat": 54.1118, "lon": 22.9309},
    {"name": "Szczecin", "lat": 53.4285, "lon": 14.5528},
    {"name": "Śnieżka", "lat": 50.7360, "lon": 15.7390},
    {"name": "Świnoujście", "lat": 53.9100, "lon": 14.2470},
    {"name": "Tarnów", "lat": 50.0121, "lon": 20.9858},
    {"name": "Terespol", "lat": 52.0760, "lon": 23.6160},
    {"name": "Toruń", "lat": 53.0138, "lon": 18.5984},
    {"name": "Ustka", "lat": 54.5800, "lon": 16.8600},
    {"name": "Warszawa", "lat": 52.2297, "lon": 21.0122},
    {"name": "Włodawa", "lat": 51.5490, "lon": 23.5470},
    {"name": "Wrocław", "lat": 51.1079, "lon": 17.0385},
    {"name": "Zakopane", "lat": 49.2992, "lon": 19.9496},
    {"name": "Zamość", "lat": 50.7231, "lon": 23.2519},
    {"name": "Zielona Góra", "lat": 51.9356, "lon": 15.5062},
]

EXTRA_ALIASES = {
    "bielsko": "Bielsko Biała",
    "bielskobiala": "Bielsko Biała",
    "gorzow": "Gorzów Wielkopolski",
    "gorzowwlkp": "Gorzów Wielkopolski",
    "gorzowwielkopolski": "Gorzów Wielkopolski",
    "nowysacz": "Nowy Sącz",
    "kasprowywierch": "Kasprowy Wierch",
    "zielonagora": "Zielona Góra",
}

st.set_page_config(page_title="Mapa stacji IMGW", page_icon="🌦️", layout="wide", initial_sidebar_state="collapsed")


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def fetch_synop_data() -> list[dict]:
    response = requests.get(API_URL, timeout=20)
    response.raise_for_status()
    return response.json()


def normalize(text: str = "") -> str:
    normalized = unicodedata.normalize("NFD", str(text).strip())
    without_diacritics = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    without_diacritics = without_diacritics.replace("ł", "l").replace("Ł", "L")
    return "".join(ch.lower() for ch in without_diacritics if ch.isalnum())


CANONICAL_STATION_BY_KEY = {normalize(station["name"]): station["name"] for station in STATIONS}
COORDS_BY_KEY = {normalize(station["name"]): station for station in STATIONS}


def normalize_station_name(name: str = "") -> str:
    key = normalize(name)
    return EXTRA_ALIASES.get(key) or CANONICAL_STATION_BY_KEY.get(key) or name


def parse_number(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def freshness_label(date_str: str | None, hour_value) -> str:
    if not date_str or hour_value in (None, ""):
        return "brak czasu pomiaru"
    try:
        measurement = datetime.fromisoformat(f"{date_str}T{int(hour_value):02d}:00:00")
    except ValueError:
        return "nieznany czas"

    diff_minutes = int((datetime.now() - measurement).total_seconds() // 60)
    if diff_minutes < 0:
        return "czas pomiaru w przyszłości"
    if diff_minutes <= 90:
        return f"świeże: {diff_minutes} min temu"
    if diff_minutes <= 240:
        return f"opóźnione: {diff_minutes} min temu"
    return f"stare dane: {diff_minutes // 60} h temu"


def merge_station_data(raw_data: list[dict]) -> pd.DataFrame:
    rows: list[dict] = []
    for item in raw_data:
        normalized_name = normalize_station_name(item.get("stacja", ""))
        coords = COORDS_BY_KEY.get(normalize(normalized_name))
        if not coords:
            continue

        temperature = parse_number(item.get("temperatura"))
        row = {
            "id": item.get("id_stacji") or normalized_name,
            "name": coords["name"],
            "original_name": item.get("stacja", ""),
            "lat": coords["lat"],
            "lon": coords["lon"],
            "temperature": temperature,
            "pressure": parse_number(item.get("cisnienie")),
            "humidity": parse_number(item.get("wilgotnosc_wzgledna")),
            "wind": parse_number(item.get("predkosc_wiatru")),
            "rain": parse_number(item.get("suma_opadu")),
            "date": item.get("data_pomiaru"),
            "hour": item.get("godzina_pomiaru"),
            "freshness": freshness_label(item.get("data_pomiaru"), item.get("godzina_pomiaru")),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("name", kind="stable").reset_index(drop=True)
    return df


def get_extremes(df: pd.DataFrame):
    valid = df[df["temperature"].notna()] if not df.empty else df
    if valid.empty:
        return None, None
    coldest = valid.loc[valid["temperature"].idxmin()]
    hottest = valid.loc[valid["temperature"].idxmax()]
    return coldest, hottest


def build_measurement_time(date_value, hour_value):
    if pd.isna(date_value) or pd.isna(hour_value):
        return pd.NaT
    try:
        return pd.Timestamp(datetime.fromisoformat(f"{date_value}T{int(hour_value):02d}:00:00"))
    except (TypeError, ValueError):
        return pd.NaT


def build_history_signature(df: pd.DataFrame) -> str:
    if df.empty:
        return "empty"
    signature_parts = df[["name", "date", "hour", "temperature"]].fillna("na").astype(str).agg("|".join, axis=1)
    return "#".join(signature_parts.tolist())


def append_history_snapshot(df: pd.DataFrame) -> None:
    if df.empty:
        return

    history_df = df[["name", "temperature", "date", "hour"]].copy()
    history_df["measurement_time"] = history_df.apply(
        lambda row: build_measurement_time(row["date"], row["hour"]), axis=1
    )
    history_df = history_df.dropna(subset=["temperature", "measurement_time"])
    if history_df.empty:
        return

    history_df = history_df[["name", "temperature", "measurement_time"]]

    if HISTORY_FILE.exists():
        existing = pd.read_csv(HISTORY_FILE)
        merged = pd.concat([existing, history_df], ignore_index=True)
    else:
        merged = history_df

    merged["measurement_time"] = pd.to_datetime(merged["measurement_time"], errors="coerce")
    merged["temperature"] = pd.to_numeric(merged["temperature"], errors="coerce")
    merged = merged.dropna(subset=["measurement_time", "temperature"])
    merged = merged.drop_duplicates(subset=["name", "measurement_time"], keep="last")
    cutoff = pd.Timestamp.now() - timedelta(hours=24)
    merged = merged[merged["measurement_time"] >= cutoff].sort_values(["name", "measurement_time"])
    merged.to_csv(HISTORY_FILE, index=False)


def load_station_history(station_name: str) -> pd.DataFrame:
    if HISTORY_FILE.exists():
        history = pd.read_csv(HISTORY_FILE)
        history["measurement_time"] = pd.to_datetime(history["measurement_time"], errors="coerce")
        history["temperature"] = pd.to_numeric(history["temperature"], errors="coerce")
        history = history[
            (history["name"] == station_name)
            & history["measurement_time"].notna()
            & history["temperature"].notna()
        ]
    else:
        history = pd.DataFrame(columns=["name", "temperature", "measurement_time"])

    cutoff = pd.Timestamp.now().floor("h") - timedelta(hours=23)
    history = history[history["measurement_time"] >= cutoff].copy()
    if not history.empty:
        history["measurement_time"] = history["measurement_time"].dt.floor("h")
        history = history.sort_values("measurement_time").drop_duplicates(subset=["measurement_time"], keep="last")

    hourly_grid = pd.DataFrame(
        {
            "measurement_time": pd.date_range(
                start=cutoff,
                end=pd.Timestamp.now().floor("h"),
                freq=f"{IMGW_MEASUREMENT_INTERVAL_HOURS}h",
            )
        }
    )
    hourly_grid["name"] = station_name
    history = hourly_grid.merge(history[["measurement_time", "temperature"]], on="measurement_time", how="left")
    history["time_label"] = history["measurement_time"].dt.strftime("%H:%M")
    history["has_value"] = history["temperature"].notna()
    return history


def render_metric_card(title: str, station_row, accent: str, badge: str):
    st.markdown(
        f"""
        <div style="padding:20px;border-radius:26px;background:{accent};border:1px solid rgba(255,255,255,0.65);box-shadow:0 16px 40px rgba(15,23,42,0.09);backdrop-filter:blur(12px);min-height:190px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
            <div style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:#475569;">{title}</div>
            <div style="font-size:11px;padding:5px 10px;border-radius:999px;background:rgba(255,255,255,0.82);color:#0f172a;font-weight:700;">{badge}</div>
          </div>
        """,
        unsafe_allow_html=True,
    )
    if station_row is None:
        st.markdown("<div style='color:#64748b;font-size:15px;'>Brak danych</div></div>", unsafe_allow_html=True)
        return

    st.markdown(
        f"""
          <div style="font-size:28px;font-weight:800;color:#0f172a;line-height:1.15;">{station_row['name']}</div>
          <div style="margin-top:16px;font-size:52px;font-weight:900;color:#0f172a;line-height:1;">{station_row['temperature']:.1f}°C</div>
          <div style="margin-top:14px;font-size:12px;color:#475569;">Pomiar: {station_row['date']} {int(station_row['hour']):02d}:00</div>
          <div style="margin-top:6px;font-size:12px;color:#64748b;">{station_row['freshness']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_station_details(station_row, title: str):
    if station_row is None:
        st.info("Brak danych stacji do wyświetlenia.")
        return

    temperature_text = f"{station_row['temperature']:.1f}" if pd.notna(station_row["temperature"]) else "—"
    hour_text = f"{int(station_row['hour']):02d}" if pd.notna(station_row["hour"]) else "—"

    st.markdown(f"### {title}")
    st.markdown(
        f"""
        <div style="padding:18px;border-radius:24px;background:linear-gradient(135deg,#0f172a,#1e293b);color:white;box-shadow:0 18px 40px rgba(15,23,42,0.18);margin-bottom:14px;">
          <div style="font-size:14px;color:#cbd5e1;">{station_row['name']}</div>
          <div style="margin-top:8px;font-size:54px;font-weight:800;line-height:1;">{temperature_text}°C</div>
          <div style="margin-top:10px;font-size:13px;color:#cbd5e1;">{station_row['date']} {hour_text}:00 • {station_row['freshness']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    c1.metric("Ciśnienie", f"{station_row['pressure']:.1f} hPa" if pd.notna(station_row['pressure']) else "—")
    c2.metric("Wilgotność", f"{station_row['humidity']:.0f}%" if pd.notna(station_row['humidity']) else "—")
    c3, c4 = st.columns(2)
    c3.metric("Wiatr", f"{station_row['wind']:.1f} m/s" if pd.notna(station_row['wind']) else "—")
    c4.metric("Opad", f"{station_row['rain']:.1f} mm" if pd.notna(station_row['rain']) else "—")


def build_station_popup(station_row) -> str:
    temperature_text = f"{station_row['temperature']:.1f}" if pd.notna(station_row["temperature"]) else "—"
    hour_text = f"{int(station_row['hour']):02d}" if pd.notna(station_row["hour"]) else "—"
    pressure_text = f"{station_row['pressure']:.1f} hPa" if pd.notna(station_row["pressure"]) else "—"
    humidity_text = f"{station_row['humidity']:.0f}%" if pd.notna(station_row["humidity"]) else "—"
    return f"""
    <div style="min-width:220px;font-family:Arial,sans-serif;">
      <div style="font-size:16px;font-weight:700;margin-bottom:8px;">{station_row['name']}</div>
      <div><b>Temperatura:</b> {temperature_text}°C</div>
      <div><b>Pomiar:</b> {station_row['date']} {hour_text}:00</div>
      <div><b>Świeżość:</b> {station_row['freshness']}</div>
      <div><b>Ciśnienie:</b> {pressure_text}</div>
      <div><b>Wilgotność:</b> {humidity_text}</div>
    </div>
    """


def render_temperature_history_chart(station_name: str, history_df: pd.DataFrame):
    st.markdown('<div class="section-title" style="margin-top:18px;">Wykres temperatury z ostatniej doby</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="muted-text" style="margin-bottom:12px;">Stacja: <b>{station_name}</b>. Oś X ma stałą siatkę godzinową dla ostatnich 24 godzin. Punkty z temperaturą pojawiają się tylko tam, gdzie aplikacja ma zapisany rzeczywisty godzinowy odczyt IMGW.</div>',
        unsafe_allow_html=True,
    )

    if history_df.empty or not history_df["has_value"].any():
        st.info("Brak zapisanych godzinowych danych IMGW dla tej stacji z ostatnich 24 godzin. Po kolejnych odświeżeniach aplikacja uzupełni wykres prawdziwymi punktami pomiarowymi.")
        return

    base = alt.Chart(history_df)

    line_chart = base.mark_line(interpolate="monotone", strokeWidth=3).encode(
        x=alt.X(
            "measurement_time:T",
            title="Czas pomiaru (godziny)",
            axis=alt.Axis(format="%H:%M", labelAngle=0, tickCount=24, grid=True),
        ),
        y=alt.Y("temperature:Q", title="Temperatura [°C]"),
        tooltip=[
            alt.Tooltip("name:N", title="Stacja"),
            alt.Tooltip("measurement_time:T", title="Czas pomiaru", format="%d-%m %H:%M"),
            alt.Tooltip("temperature:Q", title="Temperatura", format=".1f"),
        ],
    )

    points_chart = base.transform_filter(alt.datum.has_value == True).mark_point(size=85, filled=True).encode(
        x="measurement_time:T",
        y="temperature:Q",
        tooltip=[
            alt.Tooltip("name:N", title="Stacja"),
            alt.Tooltip("measurement_time:T", title="Czas pomiaru", format="%d-%m %H:%M"),
            alt.Tooltip("temperature:Q", title="Temperatura", format=".1f"),
        ],
    )

    chart = (line_chart + points_chart).properties(height=300).configure_view(strokeOpacity=0)
    st.altair_chart(chart, width="stretch" )


def get_station_tests() -> pd.DataFrame:
    tests = [
        {"input": "Łódź", "expected": "lodz", "actual": normalize("Łódź")},
        {"input": "BIAŁYSTOK", "expected": "bialystok", "actual": normalize("BIAŁYSTOK")},
        {"input": "KĘTRZYN", "expected": "ketrzyn", "actual": normalize("KĘTRZYN")},
        {"input": "Bielsko-Biała", "expected": "Bielsko Biała", "actual": normalize_station_name("Bielsko-Biała")},
        {"input": "Nowy Sącz", "expected": "Nowy Sącz", "actual": normalize_station_name("Nowy Sącz")},
        {"input": "Świnoujście", "expected": "Świnoujście", "actual": normalize_station_name("Świnoujście")},
        {"input": "Zielona Gora", "expected": "Zielona Góra", "actual": normalize_station_name("Zielona Gora")},
    ]
    df = pd.DataFrame(tests)
    df["passed"] = df["expected"] == df["actual"]
    return df


def main():
    st.markdown(
        """
        <style>
          .stApp {
            background:
              radial-gradient(circle at top left, rgba(56,189,248,0.18), transparent 28%),
              radial-gradient(circle at top right, rgba(129,140,248,0.16), transparent 26%),
              linear-gradient(180deg, #f8fbff 0%, #f4f7fb 44%, #eef3f9 100%);
          }
          .block-container {
            padding-top: 1.1rem;
            padding-bottom: 1.4rem;
            max-width: 1600px;
          }
          div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.74);
            border: 1px solid rgba(226,232,240,0.95);
            border-radius: 22px;
            padding: 16px;
            box-shadow: 0 12px 30px rgba(15,23,42,0.06);
          }
          div[data-testid="stSelectbox"] > div {
            border-radius: 18px;
          }
          .glass-card {
            background: rgba(255,255,255,0.70);
            border: 1px solid rgba(255,255,255,0.72);
            box-shadow: 0 20px 60px rgba(15,23,42,0.08);
            backdrop-filter: blur(16px);
            border-radius: 32px;
          }
          .hero-wrap {
            padding: 28px 30px;
            position: relative;
            overflow: hidden;
            margin-bottom: 18px;
          }
          .hero-wrap::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(14,165,233,0.12), transparent 34%, rgba(99,102,241,0.11));
            pointer-events: none;
          }
          .map-shell {
            background: rgba(255,255,255,0.76);
            border: 1px solid rgba(255,255,255,0.82);
            box-shadow: 0 20px 60px rgba(15,23,42,0.08);
            border-radius: 30px;
            padding: 18px 18px 12px 18px;
          }
          .section-title {
            font-size: 1.45rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: .55rem;
          }
          .muted-text {
            color: #64748b;
            font-size: .95rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="glass-card hero-wrap">
          <div style="position:relative;z-index:2;display:flex;justify-content:space-between;gap:20px;align-items:flex-start;flex-wrap:wrap;">
            <div>
              <div style="display:inline-flex;gap:8px;align-items:center;padding:7px 13px;border-radius:999px;background:#eff6ff;border:1px solid #bfdbfe;color:#1d4ed8;font-size:12px;font-weight:800;letter-spacing:.04em;">
                🌦️ IMGW • LIVE WEATHER • POLSKA
              </div>
              <div style="margin-top:16px;font-size:42px;font-weight:900;line-height:1.02;color:#0f172a;">Mapa temperatur stacji meteo</div>
              <div style="margin-top:10px;font-size:16px;color:#475569;max-width:900px;line-height:1.55;">
                Klikalna, nowoczesna mapa Polski z bieżącymi danymi IMGW, szybkim podglądem ekstremów temperatur i panelem szczegółów dla wybranej stacji.
              </div>
            </div>
            <div style="position:relative;z-index:2;min-width:230px;background:rgba(255,255,255,0.7);border:1px solid rgba(255,255,255,0.82);padding:16px 18px;border-radius:22px;box-shadow:0 14px 30px rgba(15,23,42,0.06);">
              <div style="font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748b;">Status danych</div>
              <div style="margin-top:10px;font-size:15px;color:#0f172a;font-weight:700;">Aktualizacja co godzinę w danych SYNOP</div>
              <div style="margin-top:6px;font-size:13px;color:#64748b;">Mapa jest klikalna, a wykres pod mapą używa godzin pomiaru z IMGW.</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_info = st.empty()

    try:
        raw_data = fetch_synop_data()
        df = merge_station_data(raw_data)
    except requests.RequestException as exc:
        st.error(f"Nie udało się pobrać danych z API IMGW: {exc}")
        return

    history_signature = build_history_signature(df)
    if st.session_state.get("last_history_signature") != history_signature:
        append_history_snapshot(df)
        st.session_state.last_history_signature = history_signature

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    top_info.markdown(
        f"""
        <div style="margin:4px 0 16px 0;padding:14px 16px;border-radius:20px;background:rgba(255,255,255,0.74);border:1px solid rgba(226,232,240,0.9);box-shadow:0 10px 25px rgba(15,23,42,0.05);color:#334155;font-size:14px;">
          <span style="font-weight:800;color:#0f172a;">Ostatnie pobranie:</span> {now_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    coldest, hottest = get_extremes(df)

    if "selected_station_name" not in st.session_state:
        st.session_state.selected_station_name = None

    default_name = hottest["name"] if hottest is not None else (df.iloc[0]["name"] if not df.empty else None)
    if st.session_state.selected_station_name is None:
        st.session_state.selected_station_name = default_name

    if not df.empty:
        station_names = df["name"].tolist()
        current_name = (
            st.session_state.selected_station_name
            if st.session_state.selected_station_name in station_names
            else default_name
        )
        selected_name = st.selectbox(
            "Wybierz stację",
            options=station_names,
            index=station_names.index(current_name),
        )
        if selected_name != st.session_state.selected_station_name:
            st.session_state.selected_station_name = selected_name

    selected_row = (
        df[df["name"] == st.session_state.selected_station_name].iloc[0]
        if st.session_state.selected_station_name and not df.empty
        else (hottest if hottest is not None else coldest)
    )
    history_df = load_station_history(selected_row["name"]) if selected_row is not None else pd.DataFrame()

    left, right = st.columns([1.72, 0.98], gap="large")

    with left:
        st.markdown('<div class="map-shell">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Mapa Polski</div>', unsafe_allow_html=True)
        st.markdown('<div class="muted-text">Kliknij marker, aby od razu zaktualizować panel szczegółów po prawej stronie.</div>', unsafe_allow_html=True)

        if df.empty:
            st.warning("Brak danych do wyświetlenia na mapie.")
        else:
            weather_map = folium.Map(
                location=[52.1, 19.4],
                zoom_start=6,
                tiles="CartoDB positron",
                control_scale=True,
            )

            for _, station in df.iterrows():
                fill_color = "#ef4444" if hottest is not None and station["name"] == hottest["name"] else (
                    "#3b82f6" if coldest is not None and station["name"] == coldest["name"] else "#22c55e"
                )
                folium.CircleMarker(
                    location=[station["lat"], station["lon"]],
                    radius=9 if station["name"] == st.session_state.selected_station_name else 7,
                    color="white",
                    weight=2,
                    fill=True,
                    fill_color=fill_color,
                    fill_opacity=0.92,
                    tooltip=station["name"],
                    popup=folium.Popup(build_station_popup(station), max_width=320),
                ).add_to(weather_map)

            map_data = st_folium(
                weather_map,
                width=None,
                height=620,
                returned_objects=["last_object_clicked_tooltip"],
                key="imgw_clickable_map",
            )

            clicked_station = (map_data or {}).get("last_object_clicked_tooltip")
            if clicked_station and clicked_station != st.session_state.selected_station_name:
                st.session_state.selected_station_name = clicked_station
                st.rerun()

            st.markdown('<div style="padding:8px 4px 2px 4px;color:#64748b;font-size:13px;">Mapa jest klikalna: kliknij marker stacji, aby od razu wyświetlić jej szczegóły po prawej stronie.</div>', unsafe_allow_html=True)

        if selected_row is not None:
            render_temperature_history_chart(selected_row["name"], history_df)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-title">Przegląd temperatur</div>', unsafe_allow_html=True)
        st.markdown('<div class="muted-text" style="margin-bottom:10px;">Najcieplejsza i najzimniejsza stacja są wyróżnione także na mapie.</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            render_metric_card("Najwyższa temperatura", hottest, "linear-gradient(135deg,#fff1f2,#ffedd5)", "TOP")
        with c2:
            render_metric_card("Najniższa temperatura", coldest, "linear-gradient(135deg,#ecfeff,#e0f2fe)", "MIN")

        a, b, c = st.columns(3)
        a.metric("Liczba stacji", int(len(df)))
        b.metric("Min", f"{df['temperature'].min():.1f}°C" if not df.empty and df['temperature'].notna().any() else "—")
        c.metric("Max", f"{df['temperature'].max():.1f}°C" if not df.empty and df['temperature'].notna().any() else "—")

        render_station_details(selected_row, "Szczegóły stacji")

    with st.expander("Testy dopasowania nazw stacji"):
        tests_df = get_station_tests()
        st.dataframe(tests_df, width="stretch", hide_index=True)
        if tests_df["passed"].all():
            st.success("Wszystkie testy nazw przeszły poprawnie.")
        else:
            st.error("Część testów nie przeszła poprawnie.")

    st.markdown(
        """
        <div style="margin-top:18px;padding:14px 16px;border-radius:18px;background:rgba(255,255,255,0.68);border:1px solid rgba(226,232,240,0.9);color:#64748b;font-size:13px;">
          Dane pochodzą z publicznego API IMGW. Cache aplikacji odświeża się co 5 minut, ale same dane SYNOP są aktualizowane godzinowo. Do działania klikalnej mapy potrzebne są biblioteki <b>folium</b> i <b>streamlit-folium</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
