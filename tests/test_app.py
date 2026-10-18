import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app import _nominatim_cache, _nominatim_lock, app


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


def forecast_response():
    return FakeResponse(200, {
        "city": {"timezone": 19800},
        "list": [
            forecast_entry(2026, 10, 18, 13, 18, 60, 0.1),
            forecast_entry(2026, 10, 18, 16, 21, 65, 0.2),
            forecast_entry(2026, 10, 18, 19, 23, 70, 0.3),
            forecast_entry(2026, 10, 18, 22, 26, 75, 0.8),
            forecast_entry(2026, 10, 19, 1, 24, 80, 0.5),
            forecast_entry(2026, 10, 19, 4, 18, 70, 0.4),
        ],
    })


def forecast_entry(year, month, day, hour, temp, humidity, pop):
    timestamp = int(datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp())
    return {
        "dt": timestamp,
        "main": {"temp": temp, "humidity": humidity},
        "weather": [{"description": "clear sky", "icon": "01d"}],
        "pop": pop,
    }


def current_response():
    timestamp = int(datetime(2026, 10, 18, 12, tzinfo=timezone.utc).timestamp())
    return FakeResponse(200, {
        "dt": timestamp,
        "main": {
            "temp": 23,
            "feels_like": 22,
            "humidity": 55,
        },
        "wind": {"speed": 5},
        "weather": [{"description": "clear sky", "icon": "01d"}],
    })


class CitySearchTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with _nominatim_lock:
            _nominatim_cache.clear()

    @patch("app.requests.get")
    def test_searches_world_city_by_geocoded_coordinates(self, get):
        get.side_effect = [
            FakeResponse(200, [{
                "name": "Paris",
                "state": "",
                "country": "FR",
                "lat": 48.8566,
                "lon": 2.3522,
            }]),
            current_response(),
            forecast_response(),
        ]

        response = self.client.post("/", data={"city": "Paris, France"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Paris, FR", response.data)
        self.assertIn(b"48.8566", response.data)
        self.assertIn(b"23\xc2\xb0C", response.data)
        self.assertIn(b"updated Oct 18, 2026 at 05:30 PM", response.data)
        self.assertIn(b"Wind: 18.0 km/h", response.data)
        self.assertIn(b"Upcoming Forecast (3-hour intervals)", response.data)
        self.assertIn(b"Monday", response.data)
        self.assertIn(b"26\xc2\xb0 / 18\xc2\xb0", response.data)
        self.assertIn(b"Avg. humidity: 74%", response.data)
        self.assertIn(b"Peak 3-hour rain chance: 80%", response.data)
        current_params = get.call_args_list[1].kwargs["params"]
        forecast_params = get.call_args_list[2].kwargs["params"]
        self.assertEqual(current_params["lat"], 48.8566)
        self.assertEqual(forecast_params["lat"], 48.8566)
        self.assertEqual(forecast_params["lon"], 2.3522)

    @patch("app.requests.get")
    def test_falls_back_to_global_search_for_region(self, get):
        get.side_effect = [
            FakeResponse(200, []),
            FakeResponse(200, [{
                "lat": "15.5",
                "lon": "78.0",
                "display_name": "Rayalaseema, Andhra Pradesh, India",
            }]),
            current_response(),
            forecast_response(),
        ]

        response = self.client.post("/", data={"city": "Rayalaseema"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rayalaseema, Andhra Pradesh, India", response.data)
        self.assertIn(b"15.5", response.data)
        self.assertEqual(get.call_args_list[3].kwargs["params"]["lat"], 15.5)

    @patch("app.requests.get")
    def test_reports_unmatched_global_location(self, get):
        get.side_effect = [FakeResponse(200, []), FakeResponse(200, [])]

        response = self.client.post("/", data={"city": "not a real place"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Location not found", response.data)
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
