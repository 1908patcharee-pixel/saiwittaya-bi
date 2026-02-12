import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import timedelta, datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide")

# ==================================================
# 🔄 AUTO REFRESH (10 วินาที)
# ==================================================
st_autorefresh(interval=10000, key="refresh")

# ==================================================
# 🎨 ENTERPRISE STYLE
# ==================================================
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg,#0f172a,#1e293b);
    color:white;
}
.card {
    background:#1e293b;
    padding:15px;
    border-radius:12px;
}
.kpi-number {
    font-size:28px;
    font-weight:800;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# 🟢 LIVE STATUS BAR
# ==================================================
st.markdown(f"""
<div style="
background:#16a34a;
padding:10px;
border-radius:10px;
text-align:center;
font-weight:600;
">
🟢 LIVE MODE — Real-Time Monitoring Active  
Last Updated: {datetime.now().strftime('%H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# ==================================================
# 🏫 HEADER
# ==================================================
col1, col2 = st.columns([1,4])
with col1:
    try:
        st.image("logo.png", width=80)
    except:
        pass
with col2:
    st.markdown("## 🎯 Saiwittaya Executive War Room")

st.markdown("---")

# ==================================================
# 📂 LOAD HISTORY DB (SAFE MODE)
# ==================================================
try:
    conn = sqlite3.connect("attendance_history.db")
    df = pd.read_sql("SELECT * FROM history", conn)
    conn.close()
except Exception as e:
    st.error(f"Database Error: {e}")
    st.stop()

if df.empty:
    st.warning("No attendance data yet.")
    st.stop()

# Ensure required columns exist
required_cols = ["date","class_name","status","student_id","name"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing column in database: {col}")
        st.stop()

# Safe datetime conversion
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"])

df["grade"] = df["class_name"].str.extract(r"(ม\.\d+)")

today = df["date"].max().date()
filtered = df[df["date"].dt.date == today]

# ==================================================
# 📘 LOAD STUDENT MASTER
# ==================================================
try:
    student_df = pd.read_excel("StudentData.xlsx")
except:
    st.error("StudentData.xlsx not found.")
    st.stop()

student_df["class_name"] = student_df["Class"].apply(
    lambda x: f"ม.{x}" if "/" in str(x) and not str(x).startswith("ม.") else x
)

# ==================================================
# 🔎 FILTER
# ==================================================
col_filter1, col_filter2 = st.columns(2)

grades = ["ทั้งหมด"] + sorted(df["grade"].dropna().unique())
classes = ["ทั้งหมด"] + sorted(df["class_name"].unique())

selected_grade = col_filter1.selectbox("ระดับชั้น", grades)
selected_class = col_filter2.selectbox("ห้อง", classes)

if selected_grade != "ทั้งหมด":
    filtered = filtered[filtered["grade"] == selected_grade]

if selected_class != "ทั้งหมด":
    filtered = filtered[filtered["class_name"] == selected_class]

# ==================================================
# 📊 KPI CALCULATION (SAFE)
# ==================================================
if selected_class != "ทั้งหมด":
    total_students = len(student_df[student_df["class_name"] == selected_class])
elif selected_grade != "ทั้งหมด":
    total_students = len(student_df[student_df["class_name"].str.contains(selected_grade)])
else:
    total_students = len(student_df)

late = len(filtered[filtered["status"]=="late"])
absent = len(filtered[filtered["status"]=="absent"])
ontime = len(filtered[filtered["status"]=="ontime"])

if "checkout_status" in filtered.columns:
    checked_out = len(filtered[filtered["checkout_status"]=="ออกจากโรงเรียนแล้ว"])
    not_out = len(filtered[filtered["checkout_status"]=="ยังไม่สแกนออก"])
else:
    checked_out = 0
    not_out = 0

attendance_rate = ((ontime+late)/total_students*100) if total_students else 0
checkout_rate = (checked_out/total_students*100) if total_students else 0

# ==================================================
# 📊 KPI DISPLAY
# ==================================================
k1,k2,k3,k4,k5,k6 = st.columns(6)

def kpi(col,value,label,color):
    col.markdown(f"""
    <div class='card'>
        <div class='kpi-number' style='color:{color}'>{value}</div>
        {label}
    </div>
    """, unsafe_allow_html=True)

kpi(k1,total_students,"Students","#60a5fa")
kpi(k2,f"{attendance_rate:.1f}%","Attendance","#22c55e")
kpi(k3,late,"Late","#f97316")
kpi(k4,absent,"Absent","#ef4444")
kpi(k5,f"{checkout_rate:.1f}%","Checkout %","#facc15")
kpi(k6,not_out,"Not Checkout","#eab308")

if late > 0:
    st.markdown("""
    <div style="background:#dc2626;padding:10px;border-radius:10px;text-align:center;font-weight:bold;">
    🚨 ALERT: มีนักเรียนมาสายวันนี้
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==================================================
# 📊 CHART SECTION
# ==================================================
colA,colB,colC = st.columns(3)

# PIE
with colA:
    st.markdown("### Attendance Overview")
    if not filtered.empty:
        status_counts = filtered["status"].value_counts().reset_index()
        status_counts.columns=["Status","Count"]
        fig1 = px.pie(status_counts,names="Status",values="Count",hole=0.5)
        fig1.update_layout(paper_bgcolor="#1e293b",font_color="white")
        st.plotly_chart(fig1,use_container_width=True)

# WEEKLY TREND (FIXED GROUPBY BUG)
with colB:
    st.markdown("### Weekly Late Trend")
    last7 = df[df["date"].dt.date >= today - timedelta(days=6)].copy()
    last7["day"] = last7["date"].dt.date
    trend = (
        last7[last7["status"]=="late"]
        .groupby("day")
        .size()
        .reset_index(name="Late")
    )
    if not trend.empty:
        fig_area = px.area(trend,x="day",y="Late",markers=True)
        fig_area.update_layout(paper_bgcolor="#1e293b",font_color="white")
        st.plotly_chart(fig_area,use_container_width=True)

# CHECKOUT
with colC:
    st.markdown("### Checkout Overview")
    if "checkout_status" in filtered.columns and not filtered.empty:
        checkout_counts = filtered["checkout_status"].value_counts().reset_index()
        checkout_counts.columns=["Status","Count"]
        fig2 = px.bar(checkout_counts,x="Status",y="Count",color="Status")
        fig2.update_layout(paper_bgcolor="#1e293b",font_color="white")
        st.plotly_chart(fig2,use_container_width=True)

# ==================================================
# ⚡ RECENT SCANS (SAFE SORT)
# ==================================================
st.markdown("---")
st.markdown("### ⚡ Recent Scans")

if "time" in df.columns:
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    recent = (
        df.sort_values("time", ascending=False)
        .drop_duplicates(["student_id","date"])
        .head(5)
    )
else:
    recent = df.sort_values("date", ascending=False).head(5)

st.dataframe(
    recent[["date","class_name","student_id","name","status"]],
    use_container_width=True
)
