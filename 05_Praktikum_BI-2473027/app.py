
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================
# KONFIGURASI DASHBOARD
# =========================
st.set_page_config(
    page_title="Coffee Shop Sales",
    layout="wide"
)

st.title("Dashboard Coffee Shop Sales")
st.caption(
    "Januari-Juni 2023. "
    "Mata uang belum dinyatakan pada file."
)


# =========================
# MEMUAT DATA
# =========================
folder = Path(__file__).resolve().parent
file_data = (
    folder / "data_prepared" / "coffee_sales_prepared.csv"
)


@st.cache_data
def load_data(path, modified_time):
    data = pd.read_csv(path)
    data["transaction_date"] = pd.to_datetime(
        data["transaction_date"]
    )
    return data


if not file_data.exists():
    st.error(
        "Jalankan audit terlebih dahulu. "
        "File coffee_sales_prepared.csv belum tersedia."
    )
    st.stop()


df = load_data(
    str(file_data),
    file_data.stat().st_mtime_ns
)


# =========================
# FILTER GERAI
# =========================
st.sidebar.header("Filter Data")

stores = sorted(
    df["store_location"].dropna().unique().tolist()
)

selected = st.sidebar.multiselect(
    "Pilih gerai",
    stores,
    default=stores
)

if not selected:
    st.info("Pilih minimal satu gerai.")
    st.stop()

data_filter = df[
    df["store_location"].isin(selected)
].copy()

st.sidebar.caption(
    "Semua indikator dan grafik mengikuti pilihan gerai."
)


# =========================
# RINGKASAN BULANAN
# =========================
months = pd.period_range(
    df["transaction_date"].min().to_period("M"),
    df["transaction_date"].max().to_period("M"),
    freq="M"
).astype(str).tolist()

monthly = (
    data_filter.groupby("month")
    .agg(
        total_sales=("sales", "sum"),
        total_transactions=("transaction_id", "nunique"),
        total_units=("transaction_qty", "sum")
    )
    .reindex(months)
)

previous = monthly["total_sales"].shift(1)

monthly["growth_pct"] = (
    (monthly["total_sales"] - previous)
    / previous * 100
).where(
    previous.notna() & previous.ne(0)
)

monthly["average_transaction_value"] = (
    monthly["total_sales"]
    / monthly["total_transactions"]
)

monthly = monthly.reset_index().rename(
    columns={"index": "month"}
)


# =========================
# FORMAT ANGKA
# =========================
def format_angka(value, decimals=2):
    if pd.isna(value):
        return "Belum tersedia"

    return (
        f"{value:,.{decimals}f}"
        .replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )


# =========================
# INDIKATOR UTAMA
# =========================
total_sales = data_filter["sales"].sum()

total_transactions = data_filter[
    "transaction_id"
].nunique()

total_units = data_filter[
    "transaction_qty"
].sum()

average = (
    total_sales / total_transactions
    if total_transactions
    else None
)

growth = monthly["growth_pct"].iloc[-1]
last_month = pd.Period(months[-1], freq="M")

st.subheader("Ringkasan Penjualan")

st.caption(
    "Total penjualan, transaksi, rata-rata, dan unit terjual "
    "mencakup seluruh periode. Pertumbuhan membandingkan "
    f"{last_month} dengan {last_month - 1}."
)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Total Penjualan",
    format_angka(total_sales)
)

col2.metric(
    "Transaksi Tercatat",
    format_angka(total_transactions, 0)
)

col3.metric(
    "Rata-rata Nilai Transaksi",
    format_angka(average)
    if average is not None
    else "Belum tersedia"
)

col4.metric(
    "Total Unit Terjual",
    format_angka(total_units, 0)
)

col5.metric(
    "Pertumbuhan Penjualan",
    f"{format_angka(growth)}%"
    if pd.notna(growth)
    else "Belum tersedia",
    help=(
        f"Perbandingan {last_month} "
        f"dengan {last_month - 1}"
    )
)


# =========================
# TREN PENJUALAN BULANAN
# =========================
st.subheader("Tren Penjualan Bulanan")

fig = px.line(
    monthly,
    x="month",
    y="total_sales",
    markers=True,
    labels={
        "month": "Bulan",
        "total_sales": "Nilai Penjualan"
    }
)

fig.update_traces(
    line_color="#087F8C",
    connectgaps=False
)

fig.update_layout(
    xaxis_type="category",
    yaxis_rangemode="tozero"
)

st.plotly_chart(
    fig,
    use_container_width=True,
    key="trend"
)


# =========================
# TABEL RINGKASAN BULANAN
# =========================
with st.expander("Lihat Angka Ringkasan Bulanan"):
    table = monthly.rename(
        columns={
            "month": "Bulan",
            "total_sales": "Total Penjualan",
            "total_transactions": "Transaksi Tercatat",
            "total_units": "Unit Terjual",
            "growth_pct": "Pertumbuhan (%)",
            "average_transaction_value":
                "Rata-rata Nilai Transaksi"
        }
    )

    st.dataframe(
        table.style.format(
            {
                "Total Penjualan": "{:,.2f}",
                "Transaksi Tercatat": "{:,.0f}",
                "Unit Terjual": "{:,.0f}",
                "Pertumbuhan (%)": "{:,.2f}",
                "Rata-rata Nilai Transaksi": "{:,.2f}"
            },
            na_rep="Belum tersedia",
            decimal=",",
            thousands="."
        ),
        use_container_width=True,
        hide_index=True
    )


st.divider()


# =========================
# PERBANDINGAN GERAI DAN KATEGORI
# =========================
st.header("Perbandingan Gerai dan Kategori")

left, right = st.columns(2)


# =========================
# PENJUALAN PER GERAI
# =========================
with left:
    st.subheader("Penjualan per Gerai")

    sales_by_store = (
        data_filter.groupby(
            "store_location",
            as_index=False
        )
        .agg(total_sales=("sales", "sum"))
        .sort_values(
            "total_sales",
            ascending=False
        )
    )

    # Ringkasan gerai dengan penjualan tertinggi
    if not sales_by_store.empty:
        best_store = sales_by_store.iloc[0]

        st.info(
            f"Gerai dengan penjualan tertinggi: "
            f"**{best_store['store_location']}**, "
            f"dengan total penjualan sebesar "
            f"**{format_angka(best_store['total_sales'])}**."
        )

    fig_store = px.bar(
        sales_by_store,
        x="store_location",
        y="total_sales",
        color="store_location",
        text_auto=".2s",
        labels={
            "store_location": "Gerai",
            "total_sales": "Nilai Penjualan"
        },
        color_discrete_sequence=[
            "#087F8C",
            "#7656B5",
            "#D98B39"
        ]
    )

    fig_store.update_layout(
        showlegend=False,
        height=400
    )

    st.plotly_chart(
        fig_store,
        use_container_width=True,
        key="stores"
    )

    st.caption(
        "Hanya gerai yang dipilih muncul pada grafik."
    )


# =========================
# KONTRIBUSI PENJUALAN KATEGORI
# =========================
with right:
    st.subheader("Kontribusi Penjualan Kategori")

    sales_by_category = (
        data_filter.groupby(
            "product_category",
            as_index=False
        )
        .agg(total_sales=("sales", "sum"))
        .sort_values(
            "total_sales",
            ascending=False
        )
    )

    fig_category = px.pie(
        sales_by_category,
        names="product_category",
        values="total_sales",
        hole=0.55
    )

    fig_category.update_traces(
        textinfo="none",
        hovertemplate=(
            "%{label}<br>"
            "Penjualan: %{value:,.2f}<br>"
            "Kontribusi: %{percent}"
            "<extra></extra>"
        )
    )

    fig_category.update_layout(
        height=400,
        legend_title_text="Kategori"
    )

    st.plotly_chart(
        fig_category,
        use_container_width=True,
        key="categories"
    )

    st.caption(
        "Kontribusi terhadap total penjualan "
        "dalam pilihan gerai yang sama."
    )


# =========================
# PRODUK DAN POLA WAKTU
# =========================
st.header("Produk dan Pola Waktu Transaksi")

left, right = st.columns(2)


# =========================
# 10 PRODUK DENGAN PENJUALAN TERTINGGI
# =========================
with left:
    st.subheader("10 Produk dengan Penjualan Tertinggi")

    top_products = (
        data_filter.groupby(
            ["product_id", "product_detail"],
            as_index=False
        )
        .agg(total_sales=("sales", "sum"))
        .nlargest(10, "total_sales")
        .sort_values(
            "total_sales",
            ascending=True
        )
    )

    top_products["label"] = (
        top_products["product_detail"]
        + " ("
        + top_products["product_id"].astype(str)
        + ")"
    )

    fig_products = px.bar(
        top_products,
        x="total_sales",
        y="label",
        orientation="h",
        color_discrete_sequence=["#7656B5"],
        labels={
            "total_sales": "Nilai Penjualan",
            "label": "Produk"
        }
    )

    fig_products.update_layout(
        height=470,
        yaxis={
            "categoryorder": "array",
            "categoryarray": top_products["label"].tolist()
        }
    )

    st.plotly_chart(
        fig_products,
        use_container_width=True,
        key="products"
    )

    st.caption(
        "Peringkat berdasarkan nilai penjualan, "
        "bukan jumlah unit atau keuntungan."
    )


# =========================
# TRANSAKSI MENURUT JAM
# =========================
with right:
    st.subheader("Transaksi Tercatat Menurut Jam")

    by_hour = (
        data_filter.groupby(
            "hour",
            as_index=False
        )
        .agg(
            total_transactions=(
                "transaction_id",
                "nunique"
            )
        )
        .sort_values("hour")
    )

    by_hour["label"] = (
        by_hour["hour"]
        .astype(int)
        .astype(str)
        .str.zfill(2)
        + ":00"
    )

    fig_hour = px.bar(
        by_hour,
        x="label",
        y="total_transactions",
        color_discrete_sequence=["#D98B39"],
        labels={
            "label": "Jam",
            "total_transactions": "Transaksi Tercatat"
        }
    )

    fig_hour.update_layout(
        height=470,
        xaxis_type="category"
    )

    st.plotly_chart(
        fig_hour,
        use_container_width=True,
        key="hours"
    )

    st.caption(
        "Akumulasi sepanjang periode, "
        "belum mengukur antrean layanan."
    )


# =========================
# INSIGHT BISNIS OTOMATIS
# =========================
st.divider()
st.header("Insight Bisnis")

insight1, insight2, insight3 = st.columns(3)


# Insight 1: Kategori teratas
with insight1:
    st.subheader("Kategori Teratas")

    category_insight = (
        data_filter.groupby("product_category")["sales"]
        .sum()
        .sort_values(ascending=False)
    )

    if not category_insight.empty:
        best_category = category_insight.index[0]
        category_sales = category_insight.iloc[0]

        st.write(
            f"Kategori **{best_category}** mencatat "
            f"penjualan tertinggi sebesar "
            f"**{format_angka(category_sales)}**."
        )
    else:
        st.write("Data kategori belum tersedia.")


# Insight 2: Jam tersibuk
with insight2:
    st.subheader("Jam Tersibuk")

    hour_insight = (
        data_filter.groupby("hour")["transaction_id"]
        .nunique()
        .sort_values(ascending=False)
    )

    if not hour_insight.empty:
        busiest_hour = int(hour_insight.index[0])
        busiest_count = int(hour_insight.iloc[0])

        st.write(
            f"Jam **{busiest_hour:02d}:00** mencatat "
            f"transaksi terbanyak, yaitu "
            f"**{format_angka(busiest_count, 0)} transaksi**."
        )
    else:
        st.write("Data jam transaksi belum tersedia.")


# Insight 3: Bulan dengan penjualan tertinggi
with insight3:
    st.subheader("Bulan Terbaik")

    month_insight = monthly.dropna(
        subset=["total_sales"]
    )

    if not month_insight.empty:
        best_month = month_insight.loc[
            month_insight["total_sales"].idxmax()
        ]

        st.write(
            f"Bulan **{best_month['month']}** mencatat "
            f"penjualan tertinggi sebesar "
            f"**{format_angka(best_month['total_sales'])}**."
        )
    else:
        st.write("Data penjualan bulanan belum tersedia.")


# =========================
# CATATAN DASHBOARD
# =========================
st.caption(
    "Transaksi tercatat dihitung berdasarkan transaction_id unik, "
    "bukan pelanggan unik. Rata-rata nilai transaksi belum "
    "dipastikan mewakili seluruh isi struk pelanggan. "
    "Insight mengikuti filter gerai yang dipilih. "
    "Penjualan tertinggi tidak selalu berarti keuntungan tertinggi."
)
