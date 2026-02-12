import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from PIL import Image

st.set_page_config(layout="wide")

# ==================================================
# 🎨 ENTERPRISE STYLE
# ==================================================
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    color:white;
}
.block-container { padding-top:0.5rem; }
.card {
    background:#1e293b;
    padding:12px;
    border-radius:12px;
}
.kpi-number {
    font-size:26px;
    font-weight:800;
}
.ribbon {
    background:#2563eb;
    padding:8px;
    border-radius:8px;
    text-align:center;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# 🏫 HEADER
# ==================================================
col_logo, col_title, col_filter = st.columns([1,4,2])

with col_logo:
    try:
        st.image("logo.png", width=80)
    except:
        pass

with col_title:
    st.markdown("## Saiwittaya BI Control Room")

# ==================================================
# 📂 LOAD DATA
# ==================================================
conn = sqlite3.connect("attendance.db")
df = pd.read_sql("SELECT * FROM attendance", conn)
conn.close()

if df.empty:
    st.warning("No data available")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
df["grade"] = df["class_name"].str.extract(r"(ม\.\d+)")

today = df["date"].max().date()
filtered = df[df["date"].dt.date == today]

# ==================================================
# 🔎 FILTER
# ==================================================
grades = ["ทั้งหมด"] + sorted(filtered["grade"].dropna().unique())
classes = ["ทั้งหมด"] + sorted(filtered["class_name"].unique())

selected_grade = col_filter.selectbox("ระดับชั้น", grades)

if selected_grade != "ทั้งหมด":
    filtered = filtered[filtered["grade"] == selected_grade]

selected_class = col_filter.selectbox("ห้อง", classes)

if selected_class != "ทั้งหมด":
    filtered = filtered[filtered["class_name"] == selected_class]

# ==================================================
# 📊 KPI
# ==================================================
total = len(filtered)
late = len(filtered[filtered["status"]=="late"])
absent = len(filtered[filtered["status"]=="absent"])
ontime = len(filtered[filtered["status"]=="ontime"])
checked_out = len(filtered[filtered["checkout_status"]=="ออกจากโรงเรียนแล้ว"])
not_out = len(filtered[filtered["checkout_status"]=="ยังไม่สแกนออก"])

attendance_rate = ((ontime+late)/total*100) if total else 0
checkout_rate = (checked_out/total*100) if total else 0

k1,k2,k3,k4,k5,k6 = st.columns(6)

def kpi(col,value,label,color):
    col.markdown(f"""
    <div class='card'>
        <div class='kpi-number' style='color:{color}'>{value}</div>
        {label}
    </div>
    """, unsafe_allow_html=True)

kpi(k1,total,"Students","#60a5fa")
kpi(k2,f"{attendance_rate:.1f}%","Attendance","#22c55e")
kpi(k3,late,"Late","#f97316")
kpi(k4,absent,"Absent","#ef4444")
kpi(k5,f"{checkout_rate:.1f}%","Checkout %","#facc15")
kpi(k6,not_out,"Not Checkout","#eab308")

st.markdown("---")

# ==================================================
# 📊 MAIN GRID
# ==================================================
col1,col2,col3 = st.columns([1.2,1.5,1.2])

# ==================================================
# LEFT – ATTENDANCE
# ==================================================
with col1:
    st.markdown("### Attendance Overview")

    status_counts = filtered["status"].value_counts().reset_index()
    status_counts.columns=["Status","Count"]

    fig1 = px.pie(
        status_counts,
        names="Status",
        values="Count",
        hole=0.5,
        color_discrete_sequence=px.colors.qualitative.Bold
    )

    fig1.update_layout(
        paper_bgcolor="#1e293b",
        font_color="white",
        height=320
    )

    st.plotly_chart(fig1, use_container_width=True)

# ==================================================
# CENTER – TREND
# ==================================================
with col2:
    st.markdown("### Weekly Late Trend")

    last7 = df[df["date"].dt.date >= today - timedelta(days=6)]

    trend = (
        last7[last7["status"]=="late"]
        .groupby(last7["date"].dt.date)
        .size()
        .reset_index(name="Late")
    )

    fig_area = go.Figure()

    fig_area.add_trace(go.Scatter(
        x=trend["date"],
        y=trend["Late"],
        fill='tozeroy',
        mode='lines+markers',
        line=dict(width=4,color="#22c55e")
    ))

    fig_area.update_layout(
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font_color="white",
        height=320
    )

    st.plotly_chart(fig_area,use_container_width=True)

# ==================================================
# RIGHT – CHECKOUT
# ==================================================
with col3:
    st.markdown("### Checkout Overview")

    checkout_counts = filtered["checkout_status"].value_counts().reset_index()
    checkout_counts.columns=["Status","Count"]

    fig2 = px.bar(
        checkout_counts,
        x="Status",
        y="Count",
        color="Status"
    )

    fig2.update_layout(
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font_color="white",
        height=320
    )

    st.plotly_chart(fig2,use_container_width=True)

# ==================================================
# 🔍 DRILLDOWN 2 LEVEL
# ==================================================
st.markdown("---")
st.markdown("### 🔍 Drilldown Explorer")

selected_status = st.multiselect(
    "เลือกสถานะ",
    filtered["status"].unique()
)

if selected_status:
    level1 = filtered[filtered["status"].isin(selected_status)]

    selected_class2 = st.multiselect(
        "เลือกห้อง (Level 2)",
        level1["class_name"].unique()
    )

    if selected_class2:
        level2 = level1[level1["class_name"].isin(selected_class2)]
    else:
        level2 = level1

    st.dataframe(
        level2[["class_name","student_id","name","status","checkout_status","time"]],
        height=250,
        use_container_width=True
    )

    csv_selected = level2.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Export Selected",
        data=csv_selected,
        file_name="drilldown_export.csv",
        mime="text/csv"
    )

# ==================================================
# 📊 HEATMAP
# ==================================================
st.markdown("### Heatmap (Late by Class)")

heat = (
    filtered[filtered["status"]=="late"]
    .groupby(["grade","class_name"])
    .size()
    .reset_index(name="Late")
)

if not heat.empty:
    pivot = heat.pivot(index="grade",
                       columns="class_name",
                       values="Late").fillna(0)

    fig_heat = px.imshow(
        pivot,
        text_auto=True,
        color_continuous_scale="YlOrBr"
    )

    fig_heat.update_layout(
        paper_bgcolor="#1e293b",
        font_color="white",
        height=350
    )

    st.plotly_chart(fig_heat,use_container_width=True)

