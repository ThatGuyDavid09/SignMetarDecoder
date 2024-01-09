import requests
import json

with open("passwords.txt", "r", encoding="utf-8") as f:
    password = f.readline().strip().split("=")[-1]

s = requests.Session()
base_headers = {"Content-Type":"application/json", "Accept":"application/json"}
s.headers.update(base_headers)
base_url = "https://flightclub502.pisignage.com/api"
data = {
    "email":"karen.harrell@flightclub502.org",
    "password": password,
    "getToken": True
}
login_r = s.post(base_url + "/session", json=data)
login_json = json.loads(login_r.text)
token = login_json["token"]
s.headers.update({"X-Access-Token": token})
# print(json.loads(s.get(base_url + "/playlists/Main Slideshow").text))
headers = {
    'accept': 'application/json',
    "X-Access-Token": token,
    # requests won't add a boundary if this header is set when you pass files=
    # 'Content-Type': 'multipart/form-data',
}

files = {
    # 'Upload file': ('latest_metar.png', open('img_out/latest_metar.png', 'rb'), 'image/png')
    'Upload file': ("latest_metar.png", open('img_out/latest_metar.png', 'rb'), "image/png")
}

response = requests.post(base_url + "/files", headers=headers, files=files)
# print(response.text)
# print(response.status_code)
json_file = json.loads(response.text)
# json_file = 
postupload_data = {
    "files": json_file["data"],
    "categories": [
        "string"
    ]
}

playlist_data = {"filename":"latest_metar.png","duration":15,"selected":True,"option":{"main":False},"dragSelected":False,"fullscreen":True,"expired":False,"deleted":False}

main_playlist_res = requests.get("https://flightclub502.pisignage.com/api/playlists/Main%20Slideshow", headers=headers)
main_playlist_json = json.loads(main_playlist_res.text)
amended_assets = list(main_playlist_json["data"]["assets"])
amended_assets.append(playlist_data)
print(amended_assets)

change_playlist = requests.post("https://flightclub502.pisignage.com/api/playlists/Main%20Slideshow", headers=headers, json=amended_assets)

print(change_playlist.text)
