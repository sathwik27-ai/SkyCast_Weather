from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta, timezone
import plotly.graph_objs as go
import plotly.io as pio
import time
from threading import Lock
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()

_nominatim_lock = Lock()
_last_nominatim_request = 0.0
_nominatim_cache = {}


def _service_error(response, service):
    if response.status_code == 401:
        return "The OpenWeather API key is invalid or has not been activated."
    if response.status_code == 429:
        return "The weather service rate limit was reached. Please try again shortly."
    return f"The {service} service returned an error (HTTP {response.status_code})."


def _search_nominatim(query):
    global _last_nominatim_request

    cache_key = " ".join(query.casefold().split())
    with _nominatim_lock:
        if cache_key in _nominatim_cache:
            return 200, _nominatim_cache[cache_key]

        wait = 1 - (time.monotonic() - _last_nominatim_request)
        if wait > 0:
            time.sleep(wait)

        _last_nominatim_request = time.monotonic()
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": "PythonCBPWeather/1.0"},
            timeout=10,
        )

        if response.status_code != 200:
            return response.status_code, None

        results = response.json()
        _nominatim_cache[cache_key] = results
        if len(_nominatim_cache) > 256:
            _nominatim_cache.pop(next(iter(_nominatim_cache)))

    return 200, results


def _resolve_location(query):
    if not API_KEY:
        return None, "OpenWeather API key is not configured. Set OPENWEATHER_API_KEY in your .env file."

    response = requests.get(
        "https://api.openweathermap.org/geo/1.0/direct",
        params={"q": query, "limit": 1, "appid": API_KEY},
        timeout=10,
    )
    if response.status_code != 200:
        return None, _service_error(response, "OpenWeather location search")

    results = response.json()
    if results:
        result = results[0]
        label = ", ".join(
            part for part in (result.get("name"), result.get("state"), result.get("country"))
            if part
        )
        return {
            "lat": float(result["lat"]),
            "lon": float(result["lon"]),
            "label": label,
        }, None

    status_code, results = _search_nominatim(query)
    if status_code != 200:
        return None, f"The global place search service returned an error (HTTP {status_code})."

    if not results:
        return None, "Location not found. Try a city, region, or country name."

    result = results[0]
    return {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "label": result["display_name"],
    }, None


def _build_forecast(data, location, current_data):
    hourly = []
    daily = []
    message = ""
    temp_chart = ""
    forecast_chart = ""

    city_timezone = timezone(timedelta(seconds=data["city"]["timezone"]))
    current_time = datetime.fromtimestamp(
        current_data["dt"], tz=timezone.utc
    ).astimezone(city_timezone)
    current = current_data
    next_period = data["list"][0]
    weather = {
        "city": location["label"],
        "temperature": current["main"]["temp"],
        "feels_like": current["main"]["feels_like"],
        "humidity": current["main"]["humidity"],
        "wind": round(current["wind"]["speed"] * 3.6, 1),
        "description": current["weather"][0]["description"].title(),
        "icon": current["weather"][0]["icon"],
        "precip": round(next_period.get("pop", 0) * 100),
        "updated_at": current_time.strftime("%b %d, %Y at %I:%M %p"),
    }

    times = []
    temps = []

    for entry in data["list"][:5]:
        local_time = datetime.fromtimestamp(
            entry["dt"], tz=timezone.utc
        ).astimezone(city_timezone)
        time = local_time.strftime("%a %I %p")
        temp = entry["main"]["temp"]
        icon = entry["weather"][0]["icon"]

        hourly.append({"time": time, "temp": temp, "icon": icon})
        times.append(time)
        temps.append(temp)

    days = {}
    for entry in data["list"]:
        local_time = datetime.fromtimestamp(
            entry["dt"], tz=timezone.utc
        ).astimezone(city_timezone)
        date = local_time.date()
        if date <= current_time.date():
            continue
        temp = entry["main"]["temp"]
        humidity = entry["main"]["humidity"]
        pop = entry.get("pop", 0) * 100
        icon = entry["weather"][0]["icon"]
        if date not in days:
            days[date] = {
                "min": temp,
                "max": temp,
                "humidity_total": humidity,
                "samples": 1,
                "precip": pop,
                "icons": {icon: 1},
            }
        else:
            days[date]["min"] = min(days[date]["min"], temp)
            days[date]["max"] = max(days[date]["max"], temp)
            days[date]["humidity_total"] += humidity
            days[date]["samples"] += 1
            days[date]["precip"] = max(days[date]["precip"], pop)
            days[date]["icons"][icon] = days[date]["icons"].get(icon, 0) + 1

    day_labels = []
    day_temps = []
    day_humidity = []
    day_precip = []

    for date, info in days.items():
        day = date.strftime("%A")
        icon = max(info["icons"], key=info["icons"].get)
        daily.append({
            "day": day,
            "max": round(info["max"]),
            "min": round(info["min"]),
            "humidity": round(info["humidity_total"] / info["samples"]),
            "precip": round(info["precip"]),
            "icon": icon
        })
        day_labels.append(day)
        day_temps.append(round(info["max"]))
        day_humidity.append(daily[-1]["humidity"])
        day_precip.append(info["precip"])

    if daily:
        message = (
            f"Tomorrow's estimated high is {daily[0]['max']}°C "
            f"and low is {daily[0]['min']}°C."
        )

    temp_fig = go.Figure(go.Scatter(x=times, y=temps, mode='lines+markers', name='Temperature', line=dict(color='orange')))
    temp_fig.update_layout(title="Hourly Temperature", xaxis_title="Time", yaxis_title="°C", template="plotly_white", hovermode="x unified")
    temp_chart = pio.to_html(temp_fig, full_html=False)

    forecast_fig = go.Figure()
    forecast_fig.add_trace(go.Scatter(x=day_labels, y=day_temps, mode='lines+markers', name='Temperature (°C)', line=dict(color='orange')))
    forecast_fig.add_trace(go.Scatter(x=day_labels, y=day_humidity, mode='lines+markers', name='Humidity (%)', line=dict(color='blue')))
    forecast_fig.add_trace(go.Scatter(x=day_labels, y=day_precip, mode='lines+markers', name='Precipitation (%)', line=dict(color='green')))
    forecast_fig.update_layout(title="5-Day Forecast Overview", xaxis_title="Day", yaxis_title="Value", template="plotly_white", hovermode="x unified")
    forecast_chart = pio.to_html(forecast_fig, full_html=False)

    return weather, hourly, daily, message, temp_chart, forecast_chart


@app.route("/", methods=["GET", "POST"])
def index():
    weather = None
    hourly = []
    daily = []
    message = ""
    temp_chart = ""
    forecast_chart = ""
    error = None
    city_query = ""
    map_location = None

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        city_query = city
        if city:
            try:
                location, error = _resolve_location(city)
                if location:
                    current_response = requests.get(
                        "https://api.openweathermap.org/data/2.5/weather",
                        params={
                            "lat": location["lat"],
                            "lon": location["lon"],
                            "appid": API_KEY,
                            "units": "metric",
                        },
                        timeout=10,
                    )
                    if current_response.status_code != 200:
                        error = _service_error(current_response, "OpenWeather current weather")
                    else:
                        response = requests.get(
                            "https://api.openweathermap.org/data/2.5/forecast",
                            params={
                                "lat": location["lat"],
                                "lon": location["lon"],
                                "appid": API_KEY,
                                "units": "metric",
                            },
                            timeout=10,
                        )
                        if response.status_code == 200:
                            map_location = location
                            (
                                weather, hourly, daily, message, temp_chart, forecast_chart
                            ) = _build_forecast(response.json(), location, current_response.json())
                        else:
                            error = _service_error(response, "OpenWeather forecast")
            except requests.RequestException:
                app.logger.exception("A location or weather API request failed")
                error = "Could not connect to a location or weather service. Please try again."
        else:
            error = "Enter a city, region, or country to search."

    return render_template("index.html", weather=weather, hourly=hourly, daily=daily, message=message,
                           temp_chart=temp_chart, forecast_chart=forecast_chart, error=error,
                           city_query=city_query, map_location=map_location)

if __name__ == "__main__":
    app.run(debug=True)
