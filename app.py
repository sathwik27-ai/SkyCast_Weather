from flask import Flask, render_template, request
import requests
from datetime import datetime
import plotly.graph_objs as go
import plotly.io as pio

app = Flask(__name__)
API_KEY = "9861c5018b0abf48d7396eea2b0cb26e"

@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    hourly = []
    daily = []
    message = ""
    temp_chart = ""
    forecast_chart = ""
    error = None

    if request.method == "POST":
        city = request.form.get("city")
        if city:
            url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                current = data["list"][0]

                weather = {
                    "city": data["city"]["name"],
                    "temperature": current["main"]["temp"],
                    "feels_like": current["main"]["feels_like"],
                    "humidity": current["main"]["humidity"],
                    "wind": current["wind"]["speed"],
                    "description": current["weather"][0]["description"].title(),
                    "icon": current["weather"][0]["icon"],
                    "precip": current.get("pop", 0) * 100
                }

                times = []
                temps = []

                for entry in data["list"][1:6]:
                    time = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S").strftime("%I %p")
                    temp = entry["main"]["temp"]
                    icon = entry["weather"][0]["icon"]

                    hourly.append({"time": time, "temp": temp, "icon": icon})
                    times.append(time)
                    temps.append(temp)

                # Daily forecast
                days = {}
                for entry in data["list"]:
                    date = entry["dt_txt"].split(" ")[0]
                    temp = entry["main"]["temp"]
                    humidity = entry["main"]["humidity"]
                    pop = entry.get("pop", 0) * 100
                    icon = entry["weather"][0]["icon"]
                    if date not in days:
                        days[date] = {"min": temp, "max": temp, "humidity": humidity, "precip": pop, "icon": icon}
                    else:
                        days[date]["min"] = min(days[date]["min"], temp)
                        days[date]["max"] = max(days[date]["max"], temp)
                        days[date]["humidity"] = humidity
                        days[date]["precip"] = pop

                day_labels = []
                day_temps = []
                day_humidity = []
                day_precip = []

                for i, (date, info) in enumerate(days.items()):
                    if i == 0: continue
                    day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
                    daily.append({
                        "day": day,
                        "max": round(info["max"]),
                        "min": round(info["min"]),
                        "humidity": info["humidity"],
                        "precip": info["precip"],
                        "icon": info["icon"]
                    })
                    day_labels.append(day)
                    day_temps.append(round(info["max"]))
                    day_humidity.append(info["humidity"])
                    day_precip.append(info["precip"])

                # Forecast message
                if daily:
                    diff = round(daily[0]["max"] - weather["temperature"])
                    if diff < 0:
                        message = f"Tomorrow's temperature will be {abs(diff)}° lower."
                    elif diff > 0:
                        message = f"Tomorrow's temperature will be {diff}° higher."
                    else:
                        message = "Tomorrow's temperature will be the same as today."

                # Plotly charts
                temp_fig = go.Figure(go.Scatter(x=times, y=temps, mode='lines+markers', name='Temperature', line=dict(color='orange')))
                temp_fig.update_layout(title="Hourly Temperature", xaxis_title="Time", yaxis_title="°C", template="plotly_white", hovermode="x unified")
                temp_chart = pio.to_html(temp_fig, full_html=False)

                forecast_fig = go.Figure()
                forecast_fig.add_trace(go.Scatter(x=day_labels, y=day_temps, mode='lines+markers', name='Temperature (°C)', line=dict(color='orange')))
                forecast_fig.add_trace(go.Scatter(x=day_labels, y=day_humidity, mode='lines+markers', name='Humidity (%)', line=dict(color='blue')))
                forecast_fig.add_trace(go.Scatter(x=day_labels, y=day_precip, mode='lines+markers', name='Precipitation (%)', line=dict(color='green')))
                forecast_fig.update_layout(title="5-Day Forecast Overview", xaxis_title="Day", yaxis_title="Value", template="plotly_white", hovermode="x unified")
                forecast_chart = pio.to_html(forecast_fig, full_html=False)

            else:
                error = "City not found or API error."

    return render_template("index.html", weather=weather, hourly=hourly, daily=daily, message=message,
                           temp_chart=temp_chart, forecast_chart=forecast_chart, error=error)

if __name__ == "__main__":
    app.run(debug=True)
