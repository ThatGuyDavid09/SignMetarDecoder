import textwrap

from metar.Metar import Metar
import requests
import sys
from PIL import Image, ImageDraw, ImageFont
from dateutil import tz


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


metar_url = "http://tgftp.nws.noaa.gov/data/observations/metar/stations/KLOU.TXT"
metar_req = requests.get(metar_url)
if metar_req.status_code != 200:
    sys.exit(-1)
metar_req_text = metar_req.text
metar_date, metar_text = [i.strip() for i in metar_req_text.strip().split("\n")]
metar = Metar(metar_text)

metar = Metar(
    "METAR KLOU 021753Z 24008G22KT 10SM +RA -TSRA FZFG FZHZ FZBR FEW123 OVC456 02/M03 A3029 RMK AO2 SLP261 T00221028 10028 20011 58016")

# metar_decoded = metar.string()

most_cloud = get_most_cloud(metar)
if most_cloud == "SKC":
    most_cloud = "CLR"
metar_decoded = compose_metar_string(metar)

template = f"image_bases/{most_cloud}.png"

# metar_decoded = "\n".join([i for i in metar_decoded.split("\n")])
# print(metar_date)
# print(metar_text)
# print(metar_decoded)
# print(most_cloud)
# print(template)
img = Image.open(template, 'r').convert('RGB')
imgdraw = ImageDraw.Draw(img)
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
img.save(r'out.png')
