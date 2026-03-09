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
# SENSOR STORAGE
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
# ANALYTICS
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


def maintenance_advice(f):

    if f=="Bearing Fault":
        return "Inspect bearing lubrication"

    if f=="Thermal Fault":
        return "Check cooling system"

    if f=="Electrical Overload":
        return "Inspect motor load"

    return "No maintenance required"

# =========================================================
# MQTT
# =========================================================

def on_message(client,userdata,msg):

    global latest_data

    data = json.loads(msg.payload.decode())

    v=data["vibration"]
    t=data["temperature"]
    c=data["current"]

    latest_data["vibration"]=v
    latest_data["temperature"]=t
    latest_data["current"]=c

    vibration.append(v)
    temperature.append(t)
    current.append(c)


def start_mqtt():

    client=mqtt.Client()

    client.on_message=on_message

    client.connect("broker.hivemq.com",1883,60)

    client.subscribe("machine/sensors")

    client.loop_forever()


thread=threading.Thread(target=start_mqtt)
thread.daemon=True
thread.start()

# =========================================================
# DASH APP
# =========================================================

app=dash.Dash(__name__,external_stylesheets=[dbc.themes.CYBORG])
server=app.server

# =========================================================
# LAYOUT
# =========================================================

app.layout=dbc.Container([

html.H1("⚙ AI Predictive Maintenance Dashboard",
style={"textAlign":"center","marginBottom":"30px"}),

dbc.Row([

dbc.Col(dcc.Graph(id="vib"),width=4),
dbc.Col(dcc.Graph(id="temp"),width=4),
dbc.Col(dcc.Graph(id="curr"),width=4)

]),

dbc.Row([

dbc.Col(dcc.Graph(id="health"),width=4),

dbc.Col(html.Div(id="fault-card",
style={"fontSize":"24px","padding":"20px"}),width=4),

dbc.Col(html.Div(id="alarm",
style={"fontSize":"24px","padding":"20px"}),width=4)

]),

dbc.Row([

dbc.Col(dcc.Graph(id="trend"),width=12)

]),

dbc.Row([

dbc.Col(dcc.Graph(id="faultprob"),width=6),

dbc.Col(html.Div(id="rul"),width=3),

dbc.Col(html.Div(id="maint"),width=3)

]),

dbc.Row([

dbc.Col(html.Div(id="table"))

]),

dcc.Interval(id="update",interval=2000)

],fluid=True)

# =========================================================
# CALLBACK
# =========================================================

@app.callback(

[
Output("vib","figure"),
Output("temp","figure"),
Output("curr","figure"),
Output("health","figure"),
Output("trend","figure"),
Output("faultprob","figure"),
Output("rul","children"),
Output("maint","children"),
Output("fault-card","children"),
Output("alarm","children"),
Output("table","children")
],

[Input("update","n_intervals")]

)

def update(n):

    v=latest_data["vibration"]
    t=latest_data["temperature"]
    c=latest_data["current"]

    health=calculate_health(v,t,c)

    fault=detect_fault(v,t,c)

    rul=predict_rul(v,t,c)

    maintenance=maintenance_advice(fault)

    alarm="🟢 SYSTEM NORMAL"

    if fault!="Normal":

        alarm="🔴 ALARM ACTIVE"


    vib=go.Figure(go.Indicator(
    mode="gauge+number",
    value=v,
    title={"text":"Vibration"},
    gauge={"axis":{"range":[0,4095]},
    "bar":{"color":"orange"}}
    ))

    temp=go.Figure(go.Indicator(
    mode="gauge+number",
    value=t,
    title={"text":"Temperature"},
    gauge={"axis":{"range":[0,4095]},
    "bar":{"color":"red"}}
    ))

    curr=go.Figure(go.Indicator(
    mode="gauge+number",
    value=c,
    title={"text":"Current"},
    gauge={"axis":{"range":[0,4095]},
    "bar":{"color":"cyan"}}
    ))

    healthg=go.Figure(go.Indicator(
    mode="gauge+number",
    value=health,
    title={"text":"Health %"},
    gauge={"axis":{"range":[0,100]},
    "bar":{"color":"green"}}
    ))


    trend=go.Figure()

    trend.add_trace(go.Scatter(y=list(vibration),mode="lines",name="Vibration"))
    trend.add_trace(go.Scatter(y=list(temperature),mode="lines",name="Temperature"))
    trend.add_trace(go.Scatter(y=list(current),mode="lines",name="Current"))

    trend.update_layout(title="Sensor Trend Analysis")


    faultchart=go.Figure()

    faultchart.add_bar(
    x=["Bearing","Thermal","Electrical"],
    y=[v/40,t/40,c/40]
    )

    faultchart.update_layout(title="Fault Probability")


    df=pd.DataFrame({

    "Vibration":list(vibration)[-10:],
    "Temperature":list(temperature)[-10:],
    "Current":list(current)[-10:]

    })

    table=dbc.Table.from_dataframe(df,striped=True,bordered=True,hover=True)


    return(
    vib,
    temp,
    curr,
    healthg,
    trend,
    faultchart,
    f"Remaining Useful Life: {rul} hours",
    f"Maintenance Advice: {maintenance}",
    f"Detected Fault: {fault}",
    alarm,
    table
    )

# =========================================================
# RUN
# =========================================================

if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
