import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import timedelta, datetime
import os
import time

st.set_page_config(layout="wide")

# ==================================================
# 🔄 SAFE AUTO REFRESH (ไม่กระพริบ / ไม่ crash)
# ==================================================
REFRESH_SECONDS = 10

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if time.time() - st.session_state.last_refresh > REFRESH_SECONDS:
    st.session_state.last_refresh = time.time()
    st.rerun()

# ==================================================
# 🎨 STYLE
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
font-weight:600;">
🟢 LIVE MODE — Real-Time Monitoring  
Last Updated: {datetime.now().strftime('%H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# ==================================================
# 🏫 HEADER
# ==================================================
col1, col2 = st.columns([1,4])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with col1:
    logo_path = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=80)

with col2:
    st.markdown("## 🎯 Saiwittaya Executive War Room")

st.markdown("---")

# ==================================================
# 📂 LOAD DATABASE
# ==================================================
db_path = os.path.join(BASE_DIR, "attendance_history.db")

if not os.path.exists(db_path):
    st.error("attendance_history.db not found")
    st.stop()

conn = sqlite3.connect(db_path)
df = pd.read_sql("SELECT * FROM history", conn)
conn.close()

if df.empty:
    st.warning("No attendance data yet.")
    st.stop()

required_cols = ["date","class_name","status","student_id","name"]
for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing column: {col}")
        st.stop()

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"])
df["grade"] = df["class_name"].str.extract(r"(ม\.\d+)")

today = df["date"].max().date()
filtered = df[df["date"].dt.date == today]

# ==================================================
# 📘 LOAD STUDENT MASTER
# ==================================================
excel_path = os.path.join(BASE_DIR, "StudentData.xlsx")

if not os.path.exists(excel_path):
    st.error("StudentData.xlsx not found")
    st.stop()

student_df = pd.read_excel(excel_path)

if "Class" not in student_df.columns:
    st.error("Column 'Class' missing in StudentData.xlsx")
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
# 📊 KPI CALCULATION (EXECUTIVE)
# ==================================================
if selected_class != "ทั้งหมด":
    total_students = len(student_df[student_df["class_name"] == selected_class])
elif selected_grade != "ทั้งหมด":
    total_students = len(student_df[student_df["class_name"].str.contains(selected_grade)])
else:
    total_students = len(student_df)

today_records = filtered.copy()

late = len(today_records[today_records["status"]=="late"])
absent = len(today_records[today_records["status"]=="absent"])
ontime = len(today_records[today_records["status"]=="ontime"])

scanned = ontime + late
not_scanned = total_students - len(today_records)
if not_scanned < 0:
    not_scanned = 0

attendance_rate = (scanned/total_students*100) if total_students else 0

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

kpi(k1,total_students,"👥 Total","#60a5fa")
kpi(k2,scanned,"✅ Scanned","#22c55e")
kpi(k3,not_scanned,"❌ Not Scanned","#ef4444")
kpi(k4,late,"⏰ Late","#f97316")
kpi(k5,absent,"🚫 Absent","#dc2626")
kpi(k6,f"{attendance_rate:.1f}%","📊 Attendance","#facc15")

if late > 0:
    st.markdown("""
    <div style="background:#dc2626;padding:10px;border-radius:10px;text-align:center;font-weight:bold;">
    🚨 ALERT: มีนักเรียนมาสายวันนี้
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ==================================================
# 📊 STATUS SUMMARY PIE
# ==================================================
summary_df = pd.DataFrame({
    "Status":["Scanned","Not Scanned","Late","Absent"],
    "Count":[scanned,not_scanned,late,absent]
})

fig_summary = px.pie(summary_df,names="Status",values="Count",hole=0.4)
st.plotly_chart(fig_summary,use_container_width=True)

# ==================================================
# 📈 WEEKLY LATE TREND
# ==================================================
st.subheader("📈 Weekly Late Trend")

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
    st.plotly_chart(fig_area,use_container_width=True)

# ==================================================
# ⚡ RECENT SCANS
# ==================================================
st.subheader("⚡ Recent Scans")

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

st.dataframe(
    recent[["date","class_name","student_id","name","status"]],
    use_container_width=True
)
