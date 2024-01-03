import json
import requests

import geocoder
from requests import HTTPError


class WeatherFetcher:
    def __init__(self, api_key):
        self.base_url = f"http://api.weatherapi.com/v1/current.json?key={api_key}"
        self.location = geocoder.ip('me')

    def get_local_weather(self):
        req_url = self.base_url + f"&q={self.location.lat},{self.location.lng}"
        r = requests.get(req_url)
        if r.status_code != 200:
            raise HTTPError(f"Weather fetch fail, {r.status_code}")
        weather_json = json.loads(r.text)
        return weather_json

    def get_weather_icon_url(self):
        weather = self.get_local_weather()
        icon_url = weather["current"]["condition"]["icon"].replace("64", "128")
        # print(icon_url)
        return icon_url
