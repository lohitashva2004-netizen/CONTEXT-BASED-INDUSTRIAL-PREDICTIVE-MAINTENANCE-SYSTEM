import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# =========================
# APP CONFIG
# =========================
st.set_page_config(
    page_title="Context Based Industrial Predictive Maintenance System",
    page_icon="⚙️",
    layout="wide"
)

# =========================
# TITLE
# =========================
st.title("⚙️ CONTEXT BASED INDUSTRIAL PREDICTIVE MAINTENANCE SYSTEM")
st.caption("Multi-Sensor Monitoring • Fault Classification • GNSS-Enabled Alerting")

# =========================
# SESSION STORAGE
# =========================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["time","vibration","temperature","current","fault","severity"]
    )

# =========================
# GNSS LOCATION (Simulated)
# =========================
GNSS_LAT = 13.0827
GNSS_LON = 80.2707

# =========================
# FAULT CLASSIFICATION
# =========================
def classify(vib, temp, curr):

    if vib > 75 and temp > 70:
        return "Bearing Fault", "Critical"

    if vib > 80 and curr < 50:
        return "Rotor Imbalance", "Warning"

    if temp > 80:
        return "Thermal Overload", "Warning"

    if curr > 85:
        return "Electrical Overload", "Warning"

    if curr > 70 and temp > 70:
        return "Winding Fault", "Critical"

    return "Normal Operation", "Normal"

# =========================
# SIDEBAR SENSOR INPUTS
# =========================
st.sidebar.header("Sensor Inputs")

vibration = st.sidebar.slider("Vibration", 0, 100, 30)
temperature = st.sidebar.slider("Temperature", 0, 100, 35)
current = st.sidebar.slider("Current", 0, 100, 25)

fault, severity = classify(vibration, temperature, current)

# =========================
# STORE DATA
# =========================
new_row = {
    "time": datetime.now(),
    "vibration": vibration,
    "temperature": temperature,
    "current": current,
    "fault": fault,
    "severity": severity
}

st.session_state.data = pd.concat(
    [st.session_state.data, pd.DataFrame([new_row])]
)

df = st.session_state.data.copy()

# =========================
# VIEW MODE
# =========================
mode = st.radio("View Mode", ["Real-Time", "Historical"])

if mode == "Historical":
    st.subheader("Historical Data")
    window = st.selectbox(
        "Time Window",
        ["Last 50","Last 100","All"]
    )
    if window == "Last 50":
        df = df.tail(50)
    elif window == "Last 100":
        df = df.tail(100)

# =========================
# METRICS
# =========================
c1,c2,c3,c4 = st.columns(4)

c1.metric("Vibration", vibration)
c2.metric("Temperature", temperature)
c3.metric("Current", current)

if severity == "Normal":
    c4.success("NORMAL")
elif severity == "Warning":
    c4.warning("WARNING")
else:
    c4.error("CRITICAL")

st.divider()

# =========================
# GAUGES
# =========================
def gauge(val,title,color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        title={"text":title},
        gauge={"axis":{"range":[0,100]},
               "bar":{"color":color}}
    ))
    fig.update_layout(height=250)
    return fig

g1,g2,g3 = st.columns(3)
g1.plotly_chart(gauge(vibration,"Vibration","orange"),use_container_width=True)
g2.plotly_chart(gauge(temperature,"Temperature","red"),use_container_width=True)
g3.plotly_chart(gauge(current,"Current","blue"),use_container_width=True)

st.divider()

# =========================
# SENSOR TRENDS
# =========================
col1,col2,col3 = st.columns(3)

def trend(series,title,color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=series,
        mode="lines",
        line=dict(color=color,width=3)
    ))
    fig.update_layout(title=title,height=300)
    return fig

col1.plotly_chart(trend(df["vibration"],"Vibration Trend","orange"),use_container_width=True)
col2.plotly_chart(trend(df["temperature"],"Temperature Trend","red"),use_container_width=True)
col3.plotly_chart(trend(df["current"],"Current Trend","blue"),use_container_width=True)

st.divider()

# =========================
# FAULT DISTRIBUTION
# =========================
st.subheader("Fault Distribution")

fault_counts = df["fault"].value_counts()

pie = go.Figure(data=[go.Pie(
    labels=fault_counts.index,
    values=fault_counts.values
)])
pie.update_layout(height=350)

st.plotly_chart(pie,use_container_width=True)

# =========================
# GNSS ALERT PANEL
# =========================
st.subheader("GNSS Fault Alert")

if severity in ["Critical","Warning"]:
    st.error(f"""
🚨 FAULT ALERT  
Fault: {fault}  
Severity: {severity}  
Location: {GNSS_LAT}, {GNSS_LON}  
Maintenance Required
""")
else:
    st.success("System Operating Normally")

# =========================
# GNSS MAP
# =========================
st.subheader("Machine Location (GNSS)")

map_df = pd.DataFrame({
    "lat":[GNSS_LAT],
    "lon":[GNSS_LON]
})

st.map(map_df, zoom=12)

# =========================
# SEVERITY TIMELINE
# =========================
sev_map={"Normal":1,"Warning":2,"Critical":3}
sev=df["severity"].map(sev_map)

sev_fig=go.Figure()
sev_fig.add_trace(go.Scatter(
    x=df["time"],
    y=sev,
    mode="lines+markers"
))
sev_fig.update_layout(
    title="Severity Timeline",
    height=300,
    yaxis=dict(
        tickvals=[1,2,3],
        ticktext=["Normal","Warning","Critical"]
    )
)

st.plotly_chart(sev_fig,use_container_width=True)
