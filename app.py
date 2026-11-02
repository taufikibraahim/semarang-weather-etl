import os
import sqlite3
import urllib.request

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# URL rilis publik tempat weather.db disimpan oleh GitHub Actions
DB_URL = "https://github.com/taufikibraahim/semarang-weather-etl/releases/download/data-latest/weather.db"
DB_PATH = "data/weather.db"

# 1. Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Dashboard Cuaca Semarang", page_icon="🌤️", layout="wide")


# 2. Fungsi Pembaca Data dari SQLite dengan Caching 5 Menit
# Cache data selama 1 jam (3600 detik) agar tidak terlalu sering melakukan HTTP Request
@st.cache_data(ttl=3600)
def load_data():
    # Buat folder data jika belum ada di server cloud
    os.makedirs("data", exist_ok=True)

    # Unduh file weather.db terbaru dari GitHub Release
    try:
        urllib.request.urlretrieve(DB_URL, DB_PATH)
    except Exception as e:
        # Jika gagal unduh, gunakan file lokal yang ada jika ada
        if not os.path.exists(DB_PATH):
            raise e

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM hourly_weather ORDER BY date ASC", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


st.title("Dashboard Pemantauan Cuaca Semarang")
st.caption("Data dikumpulkan otomatis via Open-Meteo API & GitHub Actions")

try:
    df = load_data()

    # 3. Sidebar Filter Tanggal
    st.sidebar.header("Filter Rentang Tanggal")
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    date_range = st.sidebar.date_input(
        "Pilih Tanggal:",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date,
    )

    # Validasi input tanggal (mencegah error jika pengguna baru memilih 1 tanggal)
    if isinstance(date_range, (list, tuple)):
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = end_date = date_range[0]
    else:
        start_date = end_date = date_range

    # Saring data berdasarkan tanggal
    filtered_df = df[
        (df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)
    ]

    if filtered_df.empty:
        st.warning("Tidak ada data pada rentang tanggal yang dipilih.")
        st.stop()

    # Ambil baris data terbaru dari rentang yang disaring
    latest_data = filtered_df.iloc[-1]

    # 4. Ringkasan Kartu Indikator KPI (2 Baris x 3 Kolom)
    st.subheader("Kondisi Cuaca Terkini")

    # Baris 1: Suhu & Kelembaban
    col1, col2, col3 = st.columns(3)
    col1.metric("Suhu Udara", f"{latest_data['temperature_c']:.1f} °C")
    col2.metric("Terasa Seperti", f"{latest_data['apparent_temperature_c']:.1f} °C")
    col3.metric("Kelembaban", f"{latest_data['humidity_pct']:.0f} %")

    # Baris 2: Angin & Hujan
    col4, col5, col6 = st.columns(3)
    col4.metric("Kecepatan Angin", f"{latest_data['wind_speed_kmh']:.1f} km/h")
    col5.metric("Peluang Hujan", f"{latest_data['precip_probability_pct']:.0f} %")
    col6.metric("Curah Hujan", f"{latest_data['rain_mm']:.1f} mm")

    st.divider()

    # 5. Visualisasi Baris 1: Suhu & Curah Hujan
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Perbandingan Suhu vs Real Feel")
        fig_temp = px.line(
            filtered_df,
            x="date",
            y=["temperature_c", "apparent_temperature_c"],
            labels={"value": "Suhu (°C)", "date": "Waktu", "variable": "Metrik"},
            markers=True,
        )
        fig_temp.update_layout(legend_title_text="", hovermode="x unified")
        st.plotly_chart(fig_temp, use_container_width=True)

    with chart_col2:
        st.subheader("Curah Hujan & Peluang Hujan")
        fig_rain = go.Figure()
        fig_rain.add_trace(
            go.Bar(
                x=filtered_df["date"],
                y=filtered_df["rain_mm"],
                name="Curah Hujan (mm)",
                marker_color="#636EFA",
            )
        )
        fig_rain.add_trace(
            go.Scatter(
                x=filtered_df["date"],
                y=filtered_df["precip_probability_pct"],
                name="Peluang Hujan (%)",
                mode="lines+markers",
                yaxis="y2",
                line=dict(color="#EF553B", width=2),
            )
        )
        fig_rain.update_layout(
            yaxis=dict(title="Curah Hujan (mm)"),
            yaxis2=dict(title="Peluang Hujan (%)", overlaying="y", side="right"),
            legend=dict(x=0, y=1.15, orientation="h"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_rain, use_container_width=True)

    # 6. Visualisasi Baris 2: Kecepatan Angin & Kelembaban
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.subheader("Tren Kecepatan Angin")
        fig_wind = px.line(
            filtered_df,
            x="date",
            y="wind_speed_kmh",
            labels={"wind_speed_kmh": "Kecepatan (km/h)", "date": "Waktu"},
            markers=True,
            color_discrete_sequence=["#00CC96"],
        )
        fig_wind.update_layout(hovermode="x unified")
        st.plotly_chart(fig_wind, use_container_width=True)

    with chart_col4:
        st.subheader("Tren Kelembaban Udara")
        fig_hum = px.area(
            filtered_df,
            x="date",
            y="humidity_pct",
            labels={"humidity_pct": "Kelembaban (%)", "date": "Waktu"},
            color_discrete_sequence=["#AB63FA"],
        )
        fig_hum.update_layout(hovermode="x unified")
        st.plotly_chart(fig_hum, use_container_width=True)

    st.divider()

    # 7. Tabel Eksplorasi Data Mentah
    with st.expander("Lihat Detail Data Mentah"):
        st.dataframe(filtered_df, use_container_width=True)

except Exception as e:
    st.error(f"Gagal memuat data dari `data/weather.db`: {e}")
