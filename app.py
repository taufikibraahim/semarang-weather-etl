import os
import sqlite3
import urllib.request

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.pipeline.queries import (
    daily_rain,
    daily_temperature,
    data_overview,
    hottest_days,
    most_humid_days,
    open_readonly,
    rain_by_hour,
    temperature_vs_daily_average,
)

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
            labels={"value": "Suhu (°C)", "date": "Waktu"},
            markers=True,
        )

        # Mengubah nama teks legenda secara langsung
        new_names = {
            "temperature_c": "Suhu Udara (°C)",
            "apparent_temperature_c": "Terasa Seperti (°C)",
        }
        fig_temp.for_each_trace(lambda t: t.update(name=new_names.get(t.name, t.name)))

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

    st.markdown("---")
    st.header("📊 Analisis Cuaca Mendalam (Insights)")

    # 1. DATA OVERVIEW (Ringkasan Data)
    conn = open_readonly(DB_PATH)
    df_overview = data_overview(conn)
    if not df_overview.empty:
        st.subheader("Ringkasan Data Historis")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Baris Data", f"{df_overview['row_count'].iloc[0]} Jam")
        col2.metric("Tanggal Mulai", df_overview["first_date"].iloc[0][:10])
        col3.metric("Tanggal Akhir", df_overview["last_date"].iloc[0][:10])

    st.markdown("---")

    # 2. DAILY TEMPERATURE (Suhu Harian)
    st.subheader("Tren Suhu Harian (Min, Rata-rata, Max)")
    df_daily_temp = daily_temperature(conn)
    fig_temp_trend = px.line(
        df_daily_temp,
        x="day",
        y=["min_temp_c", "avg_temp_c", "max_temp_c"],
        labels={"day": "Tanggal", "value": "Suhu (°C)"},
        markers=True,
        color_discrete_map={
            "min_temp_c": "#1f77b4",
            "avg_temp_c": "#2ca02c",
            "max_temp_c": "#d62728",
        },
    )
    # Ubah nama legenda
    temp_names = {
        "min_temp_c": "Suhu Minimum",
        "avg_temp_c": "Suhu Rata-rata",
        "max_temp_c": "Suhu Maksimum",
    }
    fig_temp_trend.for_each_trace(
        lambda t: t.update(name=temp_names.get(t.name, t.name))
    )
    fig_temp_trend.update_layout(legend_title_text="", hovermode="x unified")
    st.plotly_chart(fig_temp_trend, use_container_width=True)

    st.markdown("---")

    # 3. RAIN BY HOUR & DAILY RAIN (Layout 2 Kolom)
    col_rain1, col_rain2 = st.columns(2)
    with col_rain1:
        st.subheader("Jam Paling Sering Hujan")
        df_rain_hour = rain_by_hour(conn)
        fig_rain_hour = px.bar(
            df_rain_hour,
            x="hour",
            y="avg_rain_mm",
            labels={"hour": "Jam (WIB)", "avg_rain_mm": "Rata-rata Hujan (mm)"},
            color="avg_rain_mm",
            color_continuous_scale="Blues",
        )
        fig_rain_hour.update_xaxes(type="category")  # Format jam agar tidak ada desimal
        fig_rain_hour.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_rain_hour, use_container_width=True)

    with col_rain2:
        st.subheader("Total Hujan Harian")
        df_daily_rain = daily_rain(conn)
        fig_daily_rain = px.bar(
            df_daily_rain,
            x="day",
            y="total_rain_mm",
            labels={"day": "Tanggal", "total_rain_mm": "Total Hujan (mm)"},
            color="total_rain_mm",
            color_continuous_scale="Teal",
        )
        fig_daily_rain.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_daily_rain, use_container_width=True)

    st.markdown("---")

    # 4. HOTTEST DAYS & MOST HUMID DAYS (Layout 2 Kolom)
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        st.subheader("5 Hari Terpanas")
        df_hottest = hottest_days(conn, limit=5)
        df_hottest.rename(
            columns={
                "day": "Tanggal",
                "max_temp_c": "Suhu Max (°C)",
                "avg_temp_c": "Suhu Rata-rata (°C)",
            },
            inplace=True,
        )
        st.dataframe(df_hottest, use_container_width=True, hide_index=True)

    with col_top2:
        st.subheader("5 Hari Paling Lembap")
        df_humid = most_humid_days(conn, limit=5)
        df_humid.rename(
            columns={"day": "Tanggal", "avg_humidity_pct": "Kelembapan Rata-rata (%)"},
            inplace=True,
        )
        st.dataframe(df_humid, use_container_width=True, hide_index=True)

    st.markdown("---")

    # 5. TEMPERATURE VS DAILY AVERAGE (Selisih Suhu)
    st.subheader("Fluktuasi Suhu vs Rata-rata Harian")
    st.write(
        "Grafik ini menunjukkan seberapa jauh suhu pada jam tertentu menyimpang dari rata-rata suhu di hari tersebut (Merah = Lebih Panas, Biru = Lebih Dingin)."
    )
    df_temp_vs_avg = temperature_vs_daily_average(conn)
    fig_diff = px.bar(
        df_temp_vs_avg,
        x="date",
        y="diff_from_avg_c",
        labels={
            "date": "Waktu (Jam)",
            "diff_from_avg_c": "Selisih dari Rata-rata (°C)",
        },
        color="diff_from_avg_c",
        color_continuous_scale="RdBu_r",  # Skala Red-Blue reversed (merah panas, biru dingin)
    )
    fig_diff.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig_diff, use_container_width=True)

    # Tutup koneksi
    conn.close()

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
