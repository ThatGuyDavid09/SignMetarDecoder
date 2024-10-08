from datetime import datetime
import math
import os
import textwrap
from io import BytesIO
import traceback

from metar.Metar import Metar
import requests
import sys
from PIL import Image, ImageDraw, ImageFont

from dateutil import tz

from PiSignageDeployer import PiSignageDeployer


def is_out_of_date(metar: Metar):
    """
    Given METAR, returns whether the metar is more than two hours old.
    """
    metar_date = metar.time
    now = datetime.now()
    hours_diff = (now - metar_date).total_seconds() // 3600
    return hours_diff > 2


def get_ceiling(metar):
    """
    Given METAR, calculates highest ceiling. A ceiling is a cloud layer of Broken or Overcast.  
    """
    ceil = 99999999
    ceil_layers = ["BKN", "OVC"]
    
    for layer in metar.sky:
        if layer[0] in ceil_layers:
            ceil = min(ceil, layer[1].value())
    return ceil


def get_flight_condition(metar):
    """
    Given METAR, calculates whether flight is VFR, MVFR, IFR, or LIFR
    """
    if metar.vis is None:
        return "unknown"
    
    visibility = metar.vis.value() # In miles
    ceiling = get_ceiling(metar) # In feet

    if visibility >= 5 and ceiling >= 3000:
        return "VFR"
    elif visibility >= 3 and ceiling >= 1000:
        return "MVFR"
    elif visibility >= 1 and ceiling >= 500:
        return "IFR"
    else:
        return "LIFR"



def get_most_cloud(metar):
    """
    Finds the densest cloud level type, from Clear to Overcast.
    """
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
    """
    Given METAR, decodes it and converts it into a string.
    Time:
    Flight condition:
    Wind:
    Visibility:
    Sky:
    Temp/dew point:
    Altimiter:
    Weather
    """
    conditions = get_flight_condition(metar)
    if conditions == "LIFR":
        conditions = "Low IFR"
    
    metar_txt = ""

    if is_out_of_date(metar):
        print(f"[WARNING {str(datetime.now())}] METAR date recieved more than 2 hours old. Weather station \
              may be unresponsive.")
        metar_txt += "METAR out of date! Weather station likely unresponsive.\n\n"

    # Adds direction of wind in degrees in parentheses after compass direction if needed
    # From "ESE" to "ESE (105)"
    wind_dir = int(metar.wind_dir.value()) if metar.wind_dir else None
    wind_spd = metar.wind_speed.value() if metar.wind_speed else None
    wind_str = metar.wind()
    if wind_dir is not None and wind_spd is not None and wind_spd > 0:
        wind_str_lst = wind_str.split()
        wind_str_lst[0] += f" ({wind_dir:03d})"
        wind_str = " ".join(wind_str_lst)

    # Convert UTC time (from metar) to local time
    utc_zone = tz.tzutc()
    local_zone = tz.tzlocal()
    utc_time = metar.time.replace(tzinfo=utc_zone)
    local_time = utc_time.astimezone(local_zone)

    metar_txt += f"Time: {local_time.strftime(r'%H:%M')} ({utc_time.strftime(r'%H:%M')} Z) on {utc_time.strftime(r'%m/%d')}\n"
    metar_txt += f"Flight condition: {conditions}\n" 
    metar_txt += f"Wind: {wind_str}\n"
    metar_txt += f"Visibility: {metar.visibility()}\n"

    sky_mapping = {
        "CLR": "clear",
        "SKC": "clear",
        "FEW": "few",
        "SCT": "scattered",
        "BKN": "broken",
        "OVC": "overcast"
    }

    # Maps return value of cloud levels (CLR, BKN, etc) to actual words
    if metar.sky_conditions():
        for i, cond in enumerate(metar.sky):
            if cond[0] == "CLR" or cond[0] == "SKC":
                metar_txt += "Sky: clear\n"
                break

            if i == 0:
                metar_txt += f"Sky: {sky_mapping[cond[0]]} at {format(int(cond[1].value()), ',')} ft\n"
            else:
                # Spaces account for font differences
                metar_txt += f"        {sky_mapping[cond[0]]} at {format(int(cond[1].value()), ',')} ft\n"

    if metar.temp is not None:
        metar_txt += f"Temp: {round(metar.temp.value())} °C, Dew point: {round(metar.dewpt.value())} °C\n"
    else:
        metar_txt += "Temp: missing"

    if metar.press is not None:
        metar_txt += f"Altimeter: {metar.press.value():.2f} inHg\n"
    else:
        metar_txt += "Altimeter: missing"

    if metar.present_weather():
        for i, weather in enumerate(metar.present_weather().split("; ")):
            if i == 0:
                metar_txt += f"Weather: {weather}\n"
            else:
                # Spaces account for font differences
                metar_txt += f"                 {weather}\n"

    return metar_txt


def get_metar():
    """
    Gets METAR from internet
    """
    metar_url = "http://tgftp.nws.noaa.gov/data/observations/metar/stations/KLOU.TXT"
    metar_req = requests.get(metar_url)
    if metar_req.ok:
        print(f"[INFO {str(datetime.now())}] METAR fetched")
    else:
        print(f"[ERROR {str(datetime.now())}] METAR fetch fail, status {metar_req.status_code}")
        print(metar_req.text)
        sys.exit(-1)
    metar_req_text = metar_req.text
    # Website returns metar date and actual metar on different lines, so this extracts metar only
    metar_date, metar_text = [i.strip() for i in metar_req_text.strip().split("\n")]
    metar = Metar(metar_text)

    # Commented out, this is for testing
    # metar = Metar(
    #    "METAR KLOU 021753Z 06008G22KT 10SM +RA -TSRA FZFG FZHZ FZBR FEW123 OVC456 02/M03 A3029 RMK AO2 SLP261 T00221028 10028 20011 58016")
    # metar = Metar(
    #    "METAR KLOU 021753Z 09008G22KT 10SM  FEW123 OVC456 02/M03 A3029 RMK AO2 SLP261 T00221028 10028 20011 58016")
    # metar = Metar("KLOU 311453Z VRB05KT 10SM FEW013 BKN044 04/02 A3019 RMK AO2 SLP227 T00440017 51011")

    # metar_decoded = metar.string()
    return metar


def create_image(metar, is_error=False):
    """
    Generates the actual metar image

    metar: the METAR object to use as a base
    is_error: whether the image should be an error message
    """
    template = f"image_bases/metar_base.png"
    img = Image.open(template, 'r').convert('RGBA')
    imgdraw = ImageDraw.Draw(img)

    font_size = 50
    font = ImageFont.truetype(r"C:/Windows/Fonts/Timesbd.ttf", font_size)

    margin = offset = 100

    if is_error:
        print(f"[ERROR {str(datetime.now())}] Error detected, generating error image")

        large_font_size = 70
        large_font = ImageFont.truetype(r"C:/Windows/Fonts/Timesbd.ttf", large_font_size)

        metar_error = "Error detected when generating METAR image!\n"
        metar_error += f"Generated time {str(datetime.now())}\n"
        metar_error += "Please contact software maintainer. More info in logs."

        for line in metar_error.split("\n"):
            imgdraw.text((margin, offset), line, font=large_font, fill="#FFFFFF")
            offset += large_font_size + 7
        offset += font_size + 7

        for line in traceback.format_exc().split("\n"):
            imgdraw.text((margin, offset), line, font=font, fill="#FFFFFF")
            offset += font_size + 7
        return img

    else:
        metar_decoded = compose_metar_string(metar)
        print(f"[INFO {str(datetime.now())}] METAR decoded")

        # template = f"image_bases/{flight_condition}.png"
        
        # icon = icon.resize((500, 500))
        # img.alpha_composite(icon, (700, 100))

        # cloud = get_most_cloud(metar)

        # cloud_img = Image.open(f"image_bases/{cloud}.png")

        # # Cloud image is same size as base image, so just draw corrent cloud layer on top
        # img.alpha_composite(cloud_img, (0, 0))

        runways = Image.open("image_bases/KLOU_runways.png")
        rwy_size_base = 400
        rwy_pos_base = (1200, 450)
        runways = runways.resize((rwy_size_base, int(runways.size[1] * (rwy_size_base / runways.size[0]))))
        img.alpha_composite(runways, rwy_pos_base)

        if metar.wind_dir is not None and metar.wind_speed is not None and metar.wind_speed.value() > 0:

            # This doesn't work because the text is on the arrow image itself. Too lazy to fix.
            # Flips arrow if wind is between 0 and 180 to maintain readability
            if 0 < metar.wind_dir.value() < 180:
                arrow = Image.open("image_bases/arrow_reverse.png")
            else:
                arrow = Image.open("image_bases/arrow_normal.png")

            arrow = arrow.resize((150, int(arrow.size[1] * (150 / arrow.size[0]))))
            # Rotates arrow in wind direction, taking into account the way the arrow is already facing
            arrow = arrow.rotate(-(90 + metar.wind_dir.value()), expand=True)

            rwy_width, rwy_height = runways.size
            rwy_pos_x = rwy_pos_base[0] + rwy_width // 2
            rwy_pos_y = rwy_pos_base[1] + rwy_height // 2

            arrow_width, arrow_height = arrow.size

            # Calculate the center coordinates of the image to paste
            arrow_center_x = arrow_width // 2
            arrow_center_y = arrow_height // 2

            # Offsets arrow from center of runway image based on wind direction
            base_center = [rwy_pos_x - arrow_center_x, rwy_pos_y - arrow_center_y]
            offset_amt = 330
            wind_radians = math.radians(metar.wind_dir.value())
            base_center[0] += round(offset_amt * math.sin(wind_radians))
            base_center[1] -= round(offset_amt * math.cos(wind_radians))
            base_center = tuple(base_center)

            img.alpha_composite(arrow, base_center)

    
        # Wraps text of METAR to ensure it fits on image
        for line in textwrap.wrap(metar.code, width=60):
            imgdraw.text((margin, offset), line, font=font, fill="#FFFFFF")
            offset += font_size

        offset += font_size
        # Writes each line of font
        split_decoded = metar_decoded.split("\n")
        if len(split_decoded) > 12:
            split_decoded = split_decoded[:12]
            split_decoded[-1] = "..."
        for line in split_decoded:
            imgdraw.text((margin, offset), line, font=font, fill="#FFFFFF")
            offset += font_size + 7
        # imgdraw.text((100,100), metar.code, (0,0,0), font=font)
        # imgdraw.text((654,231), "KLOU", (0,0,0), font=font)

        return img


# def get_current_weather_icon(weather_fetcher):
#     icon_url = f"https:{weather_fetcher.get_weather_icon_url()}"
#     icon_r = requests.get(icon_url)
#     icon = Image.open(BytesIO(icon_r.content))
#     return icon


def deploy_pisignage(image_path):
    """
    Deploys the image to PiSignage
    """
    deployer = PiSignageDeployer()
    return deployer.deploy_image(image_path)


def check_log_file_size():
    """
    Erases logs when log file > 50mb in size
    """
    path = r"logs/sign_metar_run_log.txt"
    file_size_mb = os.stat(path).st_size  / (1024 * 1024)
    if file_size_mb > 50:
        with open(path, "r") as f:
            f.truncate()


def main():
    check_log_file_size()
    print(f"[INFO {str(datetime.now())}] Started")
    # with open("keys.txt", "r", encoding="utf-8") as f:
    #     weather_api_key = f.readline().split("=")[-1]

    # weather_fetcher = WeatherFetcher(weather_api_key)
    # icon = get_current_weather_icon(weather_fetcher)

    metar = get_metar()

    # metar_decoded = "\n".join([i for i in metar_decoded.split("\n")])
    # print(metar_date)
    # print(metar_text)
    # print(metar_decoded)
    # print(most_cloud)
    # print(template)
    try:
        img = create_image(metar)
    except Exception as e:
        # Some error has prevented the METAR image from being properly generated,
        # so we will deploy another error message for extra info

        # Print exception for logging reasons
        print(traceback.format_exc())
        img = create_image(metar, True)
    img.save(f'img_out/latest_metar.png')
    print(f"[INFO {str(datetime.now())}] METAR image saved")

    deploy_ok = deploy_pisignage("img_out/latest_metar.png")

    if not deploy_ok:
        print(f"[ERROR {str(datetime.now())}] Pisignage METAR failed to deploy")
    else:
        print(f"[INFO {str(datetime.now())}] METAR image deployed to PiSignage")
    print(f"[INFO {str(datetime.now())}] Exiting")
    print("---------------------------------------------")


if __name__ == "__main__":
    main()
