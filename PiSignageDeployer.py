import sys
from datetime import datetime
import time

import requests
import json


class PiSignageDeployer:
    def __init__(self):
        # Loads PiSignage password from file
        with open("passwords.txt", "r", encoding="utf-8") as f:
            password = f.readline().strip().split("=")[-1]
            if password:
                print(f"[INFO {str(datetime.now())}] Read password")
            else:
                print(f"[INFO {str(datetime.now())}] No password")
                sys.exit(-1)

            # s = requests.Session()
            # base_headers = {"Content-Type": "application/json", "Accept": "application/json"}
            # s.headers.update(base_headers)
            
            # Makes request to get auth token 
            self.base_url = "https://flightclub502.pisignage.com/api"
            login_data = {
                "email": "info@flightclub502.org",
                "password": password,
                "getToken": True
            }
            login_r = requests.post(self.base_url + "/session", json=login_data)
            if login_r.ok:
                print(f"[INFO {str(datetime.now())}] Fetched token")
            else:
                print(f"[ERROR {str(datetime.now())}] Token fetch failed, check auth, status {login_r.status_code}")
                print(login_r.text)
                sys.exit(-1)

            # Saves token
            login_json = json.loads(login_r.text)
            self.token = login_json["token"]
            # s.headers.update({"X-Access-Token": token})
            # print(json.loads(s.get(base_url + "/playlists/Main Slideshow").text))

            # Creates base headers for all requests
            self.headers = {
                'accept': 'application/json',
                "X-Access-Token": self.token,
                # requests won't add a boundary if this header is set when you pass files=
                # 'Content-Type': 'multipart/form-data',
            }

    def deploy_image(self, image_path):
        # Deletes old latest_metar image
        response_del = requests.delete(self.base_url + "/files/latest_metar.png", headers=self.headers)
        if response_del.ok:
            print(f"[INFO {str(datetime.now())}] Deleted old METAR image")
        else:
            print(f"[WARNING {str(datetime.now())}] Old METAR image delete fail, status {response_del.status_code}")
            print(response_del.text)

        # Uploads latest metar image
        files = {
            # 'Upload file': ('latest_metar.png', open('img_out/latest_metar.png', 'rb'), 'image/png')
            'Upload file': ("latest_metar.png", open(image_path, 'rb'), "image/png")
        }

        response_img = requests.post(self.base_url + "/files", headers=self.headers, files=files)
        if response_img.ok:
            print(f"[INFO {str(datetime.now())}] Uploaded new METAR image")
        else:
            print(f"[ERROR {str(datetime.now())}] New METAR image upload fail, status {response_img.status_code}")
            print(response_img.text)
            sys.exit(-1)

        # print(response.text)
        # print(response.status_code)
        json_file = json.loads(response_img.text)
        # json_file =

        # API says we have to call this "postupload" thing based on some info from file response, so we do that
        postupload_data = {
            "files": json_file["data"],
            "categories": [
                "string"
            ]
        }
        post_r = requests.post(self.base_url + "/postupload", headers=self.headers, json=postupload_data)
        if post_r.ok:
            print(f"[INFO {str(datetime.now())}] New METAR image queued for processing")
        else:
            print(f"[WARNING {str(datetime.now())}] New METAR image processing queue fail, status {post_r.status_code}")
            print(post_r.text)
        # print(post_r.text)

        # Data for the latest_metar as an asset on the playlist
        playlist_data = {
            "filename": "latest_metar.png",
            "duration": 30,
            "selected": True,
            "option": {"main": False},
            "dragSelected": False,
            "fullscreen": True,
            "expired": False,
            "deleted": False
        }

        # Get the old playlist info
        main_playlist_res = requests.get(self.base_url + "/playlists/Main%20Slideshow", headers=self.headers)
        if main_playlist_res.ok:
            print(f"[INFO {str(datetime.now())}] Old playlist fetched")
        else:
            print(f"[ERROR {str(datetime.now())}] Old playlist fetch fail, status {main_playlist_res.status_code}")
            print(main_playlist_res.text)
            sys.exit(-1)
        main_playlist_json = json.loads(main_playlist_res.text)
        # Extract old assets
        amended_assets = list(main_playlist_json["data"]["assets"])

        # Remove any asset called "latest_metar"
        index = 0
        while index < len(amended_assets):
            if amended_assets[index]["filename"].lower() == "latest_metar.png":
                amended_assets.pop(index)
                index -= 1
            index += 1
        # for index, item in enumerate(amended_assets):
            # if item["filename"].lower() == "latest_metar.png":
            #     amended_assets.pop(index)
                
        # Add our latest_metar asset data
        amended_assets.append(playlist_data)
        # print(amended_assets)

        # Upload the change back to the API
        change_json = {
            "assets": amended_assets
        }
        change_playlist = requests.post(self.base_url + "/playlists/Main%20Slideshow", headers=self.headers,
                                        json=change_json)
        if change_playlist.ok:
            print(f"[INFO {str(datetime.now())}] Playlist updated")
        else:
            print(f"[ERROR {str(datetime.now())}] Playlist update fail, status {change_playlist.status_code}")
            print(change_playlist.text)
            sys.exit(-1)
        # cng_json = json.loads(change_playlist.text)
        # print(change_playlist.text)
        # print(cng_json["data"]["assets"])
        
        # Create deploy request data. Most of this is probably unnecesary, but I do not know which parts
        assets_names_only = [asset["filename"] for asset in amended_assets]
        assets_names_only.append("__Main Slideshow.json")
        assets_names_only.append("custom_layout.html")
        deploy_data = {
            "sleep": {
                "enable": False,
                "ontime": "07:00",
                "offtime": "21:00"
            },
            "reboot": {
                "enable": False
            },
            "kioskUi": {
                "enable": False
            },
            "showClock": {
                "enable": False,
                "format": "12",
                "position": "bottom"
            },
            "monitorArrangement": {
                "mode": "mirror",
                "reverse": False
            },
            "emergencyMessage": {
                "msg": "",
                "hPos": "middle",
                "vPos": "middle"
            },
            "createdBy": {
                "_id": "6329aec82e6eea773f23739a",
                "name": "flightclub502"
            },
            "_id": "6329aec82e6eea773f2373a6",
            "playlists": [
                {
                "name": "Main Slideshow",
                "settings": {
                    "ads": {
                    "adPlaylist": False,
                    "adCount": 1,
                    "adInterval": 60
                    },
                    "audio": {
                    "enable": False,
                    "random": False,
                    "volume": 50
                    }
                },
                "skipForSchedule": False,
                "plType": "regular"
                }
            ],
            "combineDefaultPlaylist": False,
            "playAllEligiblePlaylists": False,
            "shuffleContent": False,
            "alternateContent": False,
            "timeToStopVideo": 0,
            "assetsValidity": [],
            "assets": assets_names_only,
            "deployedPlaylists": [
                {
                "name": "Main Slideshow",
                "settings": {
                    "ads": {
                    "adPlaylist": False,
                    "adCount": 1,
                    "adInterval": 60
                    },
                    "audio": {
                    "enable": False,
                    "random": False,
                    "volume": 50
                    }
                },
                "skipForSchedule": False,
                "plType": "regular"
                }
            ],
            "labels": [],
            "deployEveryday": False,
            "enableMpv": False,
            "mpvAudioDelay": "0",
            "selectedVideoPlayer": "default",
            "disableWebUi": False,
            "disableWarnings": False,
            "enablePio": False,
            "disableAp": False,
            "installation": "flightclub502",
            "orientation": "landscape",
            "animationEnable": False,
            "animationType": None,
            "resizeAssets": True,
            "videoKeepAspect": False,
            "videoShowSubtitles": False,
            "imageLetterboxed": True,
            "signageBackgroundColor": "#000",
            "urlReloadDisable": True,
            "keepWeblinksInMemory": False,
            # This part is important. It makes sure the playlist deploys after the latest one completes
            "loadPlaylistOnCompletion": True,
            "resolution": "auto",
            "omxVolume": 100,
            "logo": None,
            "logox": 10,
            "logoy": 10,
            "name": "default",
            # This is also important.
            "createdAt": datetime.now().strftime(r"%Y-%m-%dT%H:%M:%S.%fZ"),
            "__v": 133,
            "playlistToSchedule": "Flight Club 502 Logo",
            "deployedTicker": {
                "enable": False,
                "behavior": "scroll",
                "textSpeed": 3,
                "rss": {
                "enable": False,
                "link": None,
                "feedDelay": 10
                }
            },
            # This is also important.
            "lastDeployed": str(time.time() * 1000),
            "deployTime": None,
            "ticker": {
                "enable": False,
                "behavior": "scroll",
                "textSpeed": 3,
                "rss": {
                "enable": False,
                "link": None,
                "feedDelay": 10
                }
            },
            "disableHwWidgets": False,
            "deploy": True,
            "exportAssets": False
        }
        
        # Make the actual deploy request
        deploy_r = requests.post(
            # This group ID is for the defailt group
            self.base_url + '/groups/6329aec82e6eea773f2373a6',
            headers=self.headers,
            json=deploy_data,
        )
        if deploy_r.ok:
            print(f"[INFO {str(datetime.now())}] Playlist deployed")
        else:
            print(f"[ERROR {str(datetime.now())}] Playlist deploy fail, status {deploy_r.status_code}")
            print(deploy_r.text)
            sys.exit(-1)
        # deploy_json = json.loads(deploy_r.text)
        # print(deploy_r.text)

if __name__ == "__main__":
    psd = PiSignageDeployer()
    psd.deploy_image("img_out/latest_metar.png")
