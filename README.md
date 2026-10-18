# 🌍 World Weather Explorer

Search for a city, region, or country and explore its weather forecast on an
interactive world map. This lightweight Flask web app combines global place
search with weather details and forecast charts in one simple interface.

## Live demo

Try the deployed app: [World Weather Explorer](https://sky-cast-weather-nine.vercel.app/)

## ✨ What it does

- **Search worldwide:** Look up locations by name, not just within India.
- **Find places on the map:** Pan and zoom around the OpenStreetMap world map;
  a successful search centers the map and marks the matched location.
- **See current conditions:** Get OpenWeather's current conditions separately
  from the forecast, including temperature, humidity, and wind speed.
- **Explore the forecast:** Browse 3-hour forecast intervals and estimated
  daily summaries with interactive charts.
- **Handle regional names:** If OpenWeather does not find a place, the app
  tries OpenStreetMap's global place search.

> Weather and location results require an internet connection and depend on the
> coverage and availability of the configured services.

## 🧰 Built with

| Part | Technology |
| --- | --- |
| Web application | Python, Flask |
| Weather and geocoding | OpenWeather API |
| Place-search fallback and map tiles | OpenStreetMap / Nominatim |
| Interactive map | Leaflet |
| Forecast charts | Plotly |

## 🚀 Run locally on Windows

### 1. Requirements

- Python 3.10 or newer
- An internet connection
- An OpenWeather API key with access to its Geocoding and 5-day Forecast APIs

### 2. Get the project

Open PowerShell in the project folder. If you have not cloned the project yet:

```powershell
git clone https://github.com/sathwik27-ai/Python-CBP.git
cd Python-CBP
```

If the project is already on your computer, just open PowerShell in its folder.

### 3. Create and activate a virtual environment

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, you can run the environment's Python
directly instead: `.\venv\Scripts\python.exe`.

### 4. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Configure your OpenWeather API key

Create a local `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Then open `.env` and replace `your_api_key` with your OpenWeather API key:

```env
OPENWEATHER_API_KEY=your_api_key
```

The `.env` file is ignored by Git so your key stays local. Never commit or share
it. New API keys may take a little while to become active.

### 6. Start the app

```powershell
python app.py
```

Open **http://127.0.0.1:5000** in your browser, enter a location, and select
**Get Weather**. Stop the local server with **Ctrl+C** in PowerShell.

## 🧪 Run the tests

The location-search route tests use mocked API responses, so they do not need
live API access:

```powershell
python -m unittest discover -s tests -v
```

## 🗺️ How a search works

1. The app searches OpenWeather's geocoding service for the submitted location.
2. If there is no match, it tries OpenStreetMap's Nominatim place search.
3. The matched coordinates are used to retrieve the OpenWeather forecast.
4. The page shows the forecast and moves the map to the matching location.

For more specific matches, include a region or country—for example, `Paris,
France` or `Springfield, Illinois, USA`. Some regions and informal place names
may not have weather forecasts available even if they appear in the map search.
For a region, weather is for the resolved map coordinate, not a guarantee that
conditions represent every part of that region. Current conditions come from
the current-weather endpoint; upcoming and daily values are forecasts, with
daily highs and lows estimated from 3-hour samples. Weather forecasts are
inherently uncertain, especially further into the future, so no result can be
guaranteed exact.

## 📁 Project layout

```text
Python-CBP/
├── app.py              # Flask routes, place search, weather data, and charts
├── templates/
│   └── index.html      # Search form, results, charts, and interactive map
├── tests/
│   └── test_app.py     # Location search route tests
├── requirements.txt    # Python package dependencies
└── README.md           # Project overview and setup guide
```

## ⚠️ Troubleshooting

- **Invalid or inactive API key:** Check `OPENWEATHER_API_KEY` in your local
  `.env` file and verify that your OpenWeather key is active and has the
  required API access.
- **Location not found:** Try a more specific spelling, or include the
  country/region. Search coverage for informal regional names can vary.
- **Could not connect / service error:** Check your internet connection and try
  again later; the app relies on external weather, place-search, and map-tile
  services.
- **Map or charts do not load:** Allow access to the external CDN and map
  services used by the page.

## 📜 Attributions

- Weather data and weather icons: [OpenWeather](https://openweathermap.org/)
- Map tiles and place search: [OpenStreetMap](https://www.openstreetmap.org/)
  and [Nominatim](https://nominatim.org/)
- Interactive map library: [Leaflet](https://leafletjs.com/)
- Charts: [Plotly](https://plotly.com/python/)
