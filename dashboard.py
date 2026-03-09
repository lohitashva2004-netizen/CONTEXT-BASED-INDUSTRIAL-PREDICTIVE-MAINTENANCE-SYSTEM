import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import paho.mqtt.client as mqtt
import json
import threading
from collections import deque

# =========================================================
# GLOBAL DATA
# =========================================================

latest_data = {
    "vibration": 0,
    "temperature": 0,
    "current": 0,
    "status": "Waiting"
}

vibration = deque(maxlen=200)
temperature = deque(maxlen=200)
current = deque(maxlen=200)

vibration.append(0)
temperature.append(0)
current.append(0)

# =========================================================
# ANALYTICS FUNCTIONS
# =========================================================

def calculate_health(v,t,c):

    score = 100 - ((v+t+c)/150)

    if score < 0:
        score = 0

    if score > 100:
        score = 100

    return round(score,1)


def detect_fault(v,t,c):

    if v > 2500:
        return "Bearing Fault"

    if t > 2500:
        return "Thermal Fault"

    if c > 2500:
        return "Electrical Overload"

    return "Normal"


def predict_rul(v,t,c):

    degradation = (v+t+c)/3

    rul = max(0,5000-degradation)

    return round(rul/100,1)


def maintenance_advice(fault):

    if fault == "Bearing Fault":
        return "Inspect bearings and lubrication"

    if fault == "Thermal Fault":
        return "Check cooling system"

    if fault == "Electrical Overload":
        return "Reduce motor load"

    return "No maintenance required"


# =========================================================
# MQTT CALLBACK
# =========================================================

def on_message(client,userdata,msg):

    global latest_data

    try:

        payload = json.loads(msg.payload.decode())

        v = payload.get("vibration",0)
        t = payload.get("temperature",0)
        c = payload.get("current",0)

        latest_data["vibration"] = v
        latest_data["temperature"] = t
        latest_data["current"] = c

        vibration.append(v)
        temperature.append(t)
        current.append(c)

        print("MQTT:",payload)

    except Exception as e:

        print("MQTT ERROR:",e)


# =========================================================
# START MQTT THREAD
# =========================================================

def start_mqtt():

    client = mqtt.Client()

    client.on_message = on_message

    client.connect("broker.hivemq.com",1883,60)

    client.subscribe("machine/sensors")

    client.loop_forever()


thread = threading.Thread(target=start_mqtt)
thread.daemon = True
thread.start()


# =========================================================
# DASH APP
# =========================================================

app = dash.Dash(__name__,external_stylesheets=[dbc.themes.CYBORG])
server = app.server


# =========================================================
# LAYOUT
# =========================================================

app.layout = dbc.Container([

html.H1("⚙ Industrial Predictive Maintenance Dashboard",
style={"textAlign":"center","marginBottom":"40px"}),

dbc.Row([

dbc.Col(dbc.Card(dcc.Graph(id="vibration-gauge"),body=True),width=4),
dbc.Col(dbc.Card(dcc.Graph(id="temperature-gauge"),body=True),width=4),
dbc.Col(dbc.Card(dcc.Graph(id="current-gauge"),body=True),width=4)

]),

html.Br(),

dbc.Row([

dbc.Col(dbc.Card(dcc.Graph(id="health-gauge"),body=True),width=4),

dbc.Col(dbc.Card(html.H3(id="fault-display",
style={"textAlign":"center"}),body=True),width=4),

dbc.Col(dbc.Card(html.H3(id="alarm-display",
style={"textAlign":"center"}),body=True),width=4)

]),

html.Br(),

dbc.Row([

dbc.Col(dbc.Card(dcc.Graph(id="trend-graph"),body=True),width=12)

]),

html.Br(),

dbc.Row([

dbc.Col(dbc.Card(dcc.Graph(id="fault-chart"),body=True),width=6),

dbc.Col(dbc.Card(html.H4(id="rul-display"),body=True),width=3),

dbc.Col(dbc.Card(html.H4(id="maintenance-display"),body=True),width=3)

]),

html.Br(),

dbc.Row([

dbc.Col(html.H4("Recent Sensor Data")),
dbc.Col(html.Div(id="data-table"))

]),

dcc.Interval(id="interval-update",interval=2000,n_intervals=0)

],fluid=True)


# =========================================================
# DASH CALLBACK
# =========================================================

@app.callback(

[
Output("vibration-gauge","figure"),
Output("temperature-gauge","figure"),
Output("current-gauge","figure"),
Output("health-gauge","figure"),
Output("trend-graph","figure"),
Output("fault-chart","figure"),
Output("rul-display","children"),
Output("maintenance-display","children"),
Output("fault-display","children"),
Output("alarm-display","children"),
Output("data-table","children")
],

[Input("interval-update","n_intervals")]

)

def update_dashboard(n):

    v = latest_data["vibration"]
    t = latest_data["temperature"]
    c = latest_data["current"]

    health = calculate_health(v,t,c)

    fault = detect_fault(v,t,c)

    rul = predict_rul(v,t,c)

    maintenance = maintenance_advice(fault)

    alarm = "🟢 SYSTEM NORMAL"

    if fault != "Normal":
        alarm = "🔴 ALARM ACTIVE"


    # -------------------------
    # GAUGES
    # -------------------------

    vib = go.Figure(go.Indicator(
    mode="gauge+number",
    value=v,
    title={"text":"Vibration"},
    gauge={"axis":{"range":[0,4095]}}
    ))

    temp = go.Figure(go.Indicator(
    mode="gauge+number",
    value=t,
    title={"text":"Temperature"},
    gauge={"axis":{"range":[0,4095]}}
    ))

    curr = go.Figure(go.Indicator(
    mode="gauge+number",
    value=c,
    title={"text":"Current"},
    gauge={"axis":{"range":[0,4095]}}
    ))

    health_g = go.Figure(go.Indicator(
    mode="gauge+number",
    value=health,
    title={"text":"Machine Health %"},
    gauge={"axis":{"range":[0,100]}}
    ))


    # -------------------------
    # TREND GRAPH
    # -------------------------

    trend = go.Figure()

    trend.add_trace(go.Scatter(y=list(vibration),mode="lines",name="Vibration"))
    trend.add_trace(go.Scatter(y=list(temperature),mode="lines",name="Temperature"))
    trend.add_trace(go.Scatter(y=list(current),mode="lines",name="Current"))

    trend.update_layout(title="Sensor Trend Analysis")


    # -------------------------
    # FAULT PROBABILITY
    # -------------------------

    fault_chart = go.Figure()

    fault_chart.add_bar(
    x=["Bearing","Thermal","Electrical"],
    y=[v/40,t/40,c/40]
    )

    fault_chart.update_layout(title="Fault Probability")


    # -------------------------
    # TABLE
    # -------------------------

    df = pd.DataFrame({

    "Vibration":list(vibration)[-10:],
    "Temperature":list(temperature)[-10:],
    "Current":list(current)[-10:]

    })

    table = dbc.Table.from_dataframe(df,striped=True,bordered=True,hover=True)


    return(

    vib,
    temp,
    curr,
    health_g,
    trend,
    fault_chart,
    f"Remaining Useful Life: {rul} hours",
    f"Maintenance Advice: {maintenance}",
    f"Detected Fault: {fault}",
    alarm,
    table

    )


# =========================================================
# RUN SERVER
# =========================================================

if __name__=="__main__":

    app.run(host="0.0.0.0",port=10000)
