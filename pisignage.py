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
    # requests won't add a boundary if this header is set when you pass files=
    'Content-Type': 'multipart/form-data',
    "X-Access-Token": token
}

files = {
    'Upload file': ('latest_metar.png', open('img_out/latest_metar.png', 'rb'), 'image/png'),
}

response = s.post('https://flightclub502.pisignage.com/api/files', headers=headers, files=files)
print(response.text)
print(response.status_code)
