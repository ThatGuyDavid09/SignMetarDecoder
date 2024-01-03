import datetime
import math
import textwrap
from io import BytesIO

from metar.Metar import Metar
import requests
import sys
from PIL import Image, ImageDraw, ImageFont
from dateutil import tz
import geocoder
from requests import HTTPError

from WeatherFetcher import WeatherFetcher


def get_most_cloud(metar):
    if not metar.sky:
        return "CLR"

    sky_mapping = {
        "CLR": 0,
        "SKC": 0,
        "FEW": 1,
        "SCT": 2,
        "BKN": 3,
        "OVC": 4
    }

    most_cloud = "CLR"
    for layer in metar.sky:
        if sky_mapping[layer[0]] > sky_mapping[most_cloud]:
            most_cloud = layer[0]

    if most_cloud == "SKC":
        most_cloud = "CLR"
    return most_cloud


def compose_metar_string(metar: Metar):
    metar_txt = ""
    metar_txt += f"Time: {metar.time.strftime(r'%H:%M')} Z\n"
    metar_txt += f"Temp: {round(metar.temp.value())} °C, Dew point: {round(metar.dewpt.value())} °C\n"
    metar_txt += f"Wind: {metar.wind()}\n"
    metar_txt += f"Visibility: {metar.visibility()}\n"
    metar_txt += f"Altimeter: {metar.press.value()} inHg\n"

    sky_mapping = {
        "CLR": "clear",
        "SKC": "clear",
        "FEW": "few",
        "SCT": "scattered",
        "BKN": "broken",
        "OVC": "overcast"
    }

    if metar.sky_conditions():
        for i, cond in enumerate(metar.sky):
            if cond[0] == "CLR" or cond[0] == "SKC":
                metar_txt += "Sky: clear\n"
                break

            if i == 0:
                metar_txt += f"Sky: {sky_mapping[cond[0]]} at {format(int(cond[1].value()), ',')} ft\n"
            else:
                metar_txt += f"        {sky_mapping[cond[0]]} at {format(int(cond[1].value()), ',')} ft\n"

    if metar.present_weather():
        for i, weather in enumerate(metar.present_weather().split("; ")):
            if i == 0:
                metar_txt += f"Weather: {weather}\n"
            else:
                metar_txt += f"                  {weather}\n"

    return metar_txt


def get_metar():
    metar_url = "http://tgftp.nws.noaa.gov/data/observations/metar/stations/KLOU.TXT"
    metar_req = requests.get(metar_url)
    if metar_req.status_code != 200:
        raise HTTPError(f"Metar fetch fail, {metar_req.status_code}")
    metar_req_text = metar_req.text
    metar_date, metar_text = [i.strip() for i in metar_req_text.strip().split("\n")]
    metar = Metar(metar_text)

    #metar = Metar(
    #    "METAR KLOU 021753Z 06008G22KT 10SM +RA -TSRA FZFG FZHZ FZBR FEW123 OVC456 02/M03 A3029 RMK AO2 SLP261 T00221028 10028 20011 58016")

    # metar_decoded = metar.string()
    return metar


def create_image(metar, metar_decoded, template, icon):
    img = Image.open(template, 'r').convert('RGBA')
    imgdraw = ImageDraw.Draw(img)

    # icon = icon.resize((500, 500))
    # img.alpha_composite(icon, (700, 100))

    runways = Image.open("image_bases/KLOU_runways.png")
    rwy_size_base = 400
    rwy_pos_base = (1100, 450)
    runways = runways.resize((rwy_size_base, int(runways.size[1] * (rwy_size_base / runways.size[0]))))
    img.alpha_composite(runways, rwy_pos_base)

    arrow = Image.open("image_bases/black_arrow.png")
    arrow = arrow.resize((150, int(arrow.size[1] * (150 / arrow.size[0]))))
    arrow = arrow.rotate(-(90 + metar.wind_dir.value()), expand=True)

    rwy_width, rwy_height = runways.size
    rwy_pos_x = rwy_pos_base[0] + rwy_width // 2
    rwy_pos_y = rwy_pos_base[1] + rwy_height // 2

    arrow_width, arrow_height = arrow.size

    # Calculate the center coordinates of the image to paste
    arrow_center_x = arrow_width // 2
    arrow_center_y = arrow_height // 2

    base_center = [rwy_pos_x - arrow_center_x, rwy_pos_y - arrow_center_y]
    offset_amt = 330
    wind_radians = math.radians(metar.wind_dir.value())
    base_center[0] += round(offset_amt * math.sin(wind_radians))
    base_center[1] -= round(offset_amt * math.cos(wind_radians))
    base_center = tuple(base_center)

    img.alpha_composite(arrow, base_center)

    font = ImageFont.truetype("C:/Windows/Fonts/Calibril.ttf", 48)

    margin = offset = 100
    for line in textwrap.wrap(metar.code, width=72):
        imgdraw.text((margin, offset), line, font=font, fill="#000000")
        offset += 48

    offset += 48
    for line in metar_decoded.split("\n"):
        imgdraw.text((margin, offset), line, font=font, fill="#000000")
        offset += 55
    # imgdraw.text((100,100), metar.code, (0,0,0), font=font)
    # imgdraw.text((654,231), "KLOU", (0,0,0), font=font)
    return img


def get_current_weather_icon(weather_fetcher):
    icon_url = f"https:{weather_fetcher.get_weather_icon_url()}"
    icon_r = requests.get(icon_url)
    icon = Image.open(BytesIO(icon_r.content))
    return icon

def main():
    with open("keys.txt", "r", encoding="utf-8") as f:
        weather_api_key = f.readline().split("=")[-1]

    weather_fetcher = WeatherFetcher(weather_api_key)
    icon = get_current_weather_icon(weather_fetcher)

    metar = get_metar()
    most_cloud = get_most_cloud(metar)
    metar_decoded = compose_metar_string(metar)

    template = f"image_bases/{most_cloud}.png"

    # metar_decoded = "\n".join([i for i in metar_decoded.split("\n")])
    # print(metar_date)
    # print(metar_text)
    # print(metar_decoded)
    # print(most_cloud)
    # print(template)
    img = create_image(metar, metar_decoded, template, icon)
    img.save(f'img_out/latest_metar.png')


if __name__ == "__main__":
    main()
