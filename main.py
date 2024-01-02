from metar import Metar
import requests
import sys
import re

# TODO make this actually compose the metar instead of modifying the string
def modify_metar_list(metar_lst):
    # station: KLOU -> Station: KLOU
    metar_0 = metar_lst[0].split(":")
    metar_0[0] = metar_0[0].capitalize()
    metar_lst[0] = ":".join(metar_0)
    
    # type
    # metar_lst[1]
    # time
    # metar_lst[2]
    
    # temp
    metar_lst[3] = metar_lst[3].title()
    # dew point
    metar_lst[4] = metar_lst[4].title()
    
    # wind
    # wind: WSW at 8 knots -> Wind: WSW at 8 knots
    metar_5 = metar_lst[5].split(":")
    metar_5[0] = metar_5[0].capitalize()
    metar_lst[5] = ":".join(metar_5)

    # visibility
    # visibility: 10 miles -> Visibility: 10 miles
    metar_lst[6] = metar_lst[6].capitalize()

    # pressure
    # pressure: 1028.1 mb -> Altimeter: 30.21 inHg
    altimeter_regex = r"A\d{4}"
    metar_press = re.findall(altimeter_regex, metar_lst[-1])[0][1:]
    metar_lst[7] = f"Altimeter: {metar_press[:2]}.{metar_press[2:]} inHg"
    metar_lst[0]
    metar_lst[0]
    metar_lst[0]

    return metar_lst

metar_url = "http://tgftp.nws.noaa.gov/data/observations/metar/stations/KLOU.TXT"
metar_req = requests.get(metar_url)
if metar_req.status_code != 200:
    sys.exit(-1)
metar_req_text = metar_req.text
metar_date, metar_text = [i.strip() for i in metar_req_text.strip().split("\n")]
metar = Metar.Metar(metar_text)

metar_decoded = metar.string()
metar_decoded = modify_metar_list(metar_decoded.split("\n"))

# metar_decoded = "\n".join([i for i in metar_decoded.split("\n")])
print(metar_date)
print(metar_text)
print("\n".join(metar_decoded))
