import _thread
import base64
import json
import os
import sched
import time
import urllib.parse

import requests
from flask import Flask, request, redirect, render_template


class Connect:
    app = Flask(__name__)
    schedule = sched.scheduler(time.time, time.sleep)

    #  Client Keys
    CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
    CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']

    # Spotify URLS
    SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
    SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
    SPOTIFY_API_BASE_URL = "https://api.spotify.com"
    API_VERSION = "v1"
    SPOTIFY_API_URL = "{}/{}".format(SPOTIFY_API_BASE_URL, API_VERSION)

    # Server-side Parameters
    CLIENT_SIDE_URL = os.environ['CLIENT_SIDE_URL']
    PORT = os.environ['PORT']
    REDIRECT_URI = "{}:{}/callback/q".format(CLIENT_SIDE_URL, PORT)
    SCOPE = "user-read-private user-modify-playback-state user-read-playback-state"
    STATE = ""
    SHOW_DIALOG_bool = True
    SHOW_DIALOG_str = str(SHOW_DIALOG_bool).lower()

    auth_query_parameters = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        # "state": STATE,
        # "show_dialog": SHOW_DIALOG_str,
        "client_id": CLIENT_ID
    }

    access_token = None
    refresh_token = None
    token_type = None
    expires_in = None

    @staticmethod
    @app.route("/")
    def index():
        # Auth Step 1: Authorization
        url_args = "&".join(
            ["{}={}".format(key, urllib.parse.quote_plus(val)) for key, val in Connect.auth_query_parameters.items()])
        auth_url = "{}/?{}".format(Connect.SPOTIFY_AUTH_URL, url_args)
        return redirect(auth_url)

    @staticmethod
    @app.route("/callback/q")
    def callback():
        # Auth Step 4: Requests refresh and access tokens
        auth_token = request.args['code']
        code_payload = {
            "grant_type": "authorization_code",
            "code": str(auth_token),
            "redirect_uri": Connect.REDIRECT_URI
        }
        base64encoded = base64.b64encode(
            bytes("{}:{}".format(Connect.CLIENT_ID, Connect.CLIENT_SECRET), 'utf-8')).decode('utf-8')
        headers = {"Authorization": "Basic {}".format(base64encoded)}
        post_request = requests.post(Connect.SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

        # Auth Step 5: Tokens are Returned to Application
        response_data = json.loads(post_request.text)
        Connect.access_token = response_data["access_token"]
        Connect.refresh_token = response_data["refresh_token"]
        Connect.token_type = response_data["token_type"]
        Connect.expires_in = response_data["expires_in"]

        Connect.schedule.enter(int(Connect.expires_in) - 60, 30, Connect.refresh_api_token,
                               (Connect, Connect.schedule,))

        # Auth Step 6: Use the access token to access Spotify API
        authorization_header = {"Authorization": "Bearer {}".format(Connect.access_token)}

        # Get User Active Devices
        devices_api_endpoint = "{}/me/player/devices".format(Connect.SPOTIFY_API_URL)
        devices_response = requests.get(devices_api_endpoint, headers=authorization_header)
        devices_data = json.loads(devices_response.text)

        # Get profile data
        user_profile_api_endpoint = "{}/me".format(Connect.SPOTIFY_API_URL)
        profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
        profile_data = json.loads(profile_response.text)

        return render_template("index.html", profile=profile_data, devices=devices_data['devices'])

    @staticmethod
    @app.route('/play', methods=['POST'])
    def play():
        content: dict = request.get_json(silent=True)
        authorization_header = {"Authorization": "Bearer {}".format(Connect.access_token)}
        player_play_api_endpoint = "{}/me/player/play".format(Connect.SPOTIFY_API_URL)

        if content is not None and 'device_id' in content.keys():
            player_play_api_endpoint += "?device_id={}".format(content['device_id'])
        player_play_response = requests.put(player_play_api_endpoint, headers=authorization_header)

        print(player_play_response.text)

        return 'Playback Started!'

    @staticmethod
    @app.route('/pause', methods=['POST'])
    def pause():
        content: dict = request.get_json(silent=True)
        authorization_header = {"Authorization": "Bearer {}".format(Connect.access_token)}
        player_play_api_endpoint = "{}/me/player/pause".format(Connect.SPOTIFY_API_URL)
        if content is not None and 'device_id' in content.keys():
            player_play_api_endpoint += "?device_id={}".format(content['device_id'])
        player_play_response = requests.put(player_play_api_endpoint, headers=authorization_header)

        print(player_play_response.text)

        return 'Playback Paused!'

    @classmethod
    def refresh_api_token(cls, sc):
        code_payload = {
            "grant_type": "authorization_code",
            "code": str(Connect.refresh_token),
            "redirect_uri": Connect.REDIRECT_URI
        }
        base64encoded = base64.b64encode(
            bytes("{}:{}".format(Connect.CLIENT_ID, Connect.CLIENT_SECRET), 'utf-8')).decode('utf-8')
        headers = {"Authorization": "Basic {}".format(base64encoded)}
        post_request = requests.post(Connect.SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

        # Auth Step 5: Tokens are Returned to Application
        response_data = json.loads(post_request.text)
        Connect.access_token = response_data["access_token"]
        Connect.refresh_token = response_data["refresh_token"]
        Connect.token_type = response_data["token_type"]
        Connect.expires_in = response_data["expires_in"]

        cls.schedule.enter(int(Connect.expires_in) - 60, 30, cls.refresh_api_token, (cls, sc,))


if __name__ == '__main__':
    _thread.start_new_thread(Connect.schedule.run, ())
    Connect.app.run(host='0.0.0.0')
