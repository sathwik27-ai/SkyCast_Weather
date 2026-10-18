import unittest
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
        "list": [{
            "dt_txt": "2026-10-18 12:00:00",
            "main": {
                "temp": 18,
                "feels_like": 17,
                "humidity": 60,
            },
            "wind": {"speed": 3},
            "weather": [{"description": "clear sky", "icon": "01d"}],
        }]
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
            forecast_response(),
        ]

        response = self.client.post("/", data={"city": "Paris, France"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Paris, FR", response.data)
        self.assertIn(b"48.8566", response.data)
        forecast_params = get.call_args_list[1].kwargs["params"]
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
            forecast_response(),
        ]

        response = self.client.post("/", data={"city": "Rayalaseema"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rayalaseema, Andhra Pradesh, India", response.data)
        self.assertIn(b"15.5", response.data)
        self.assertEqual(get.call_args_list[2].kwargs["params"]["lat"], 15.5)

    @patch("app.requests.get")
    def test_reports_unmatched_global_location(self, get):
        get.side_effect = [FakeResponse(200, []), FakeResponse(200, [])]

        response = self.client.post("/", data={"city": "not a real place"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Location not found", response.data)
        self.assertEqual(get.call_count, 2)


if __name__ == "__main__":
    unittest.main()
