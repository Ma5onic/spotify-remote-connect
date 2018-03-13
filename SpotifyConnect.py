import base64
import json
import os
import urllib.parse

import requests
from flask import Flask, request, redirect, render_template


class Connect:
    app = Flask(__name__)

    @staticmethod
    @app.route("/")
    def index():
        # Auth Step 1: Authorization
        url_args = "&".join(
            ["{}={}".format(key, urllib.parse.quote_plus(val)) for key, val in
             SpotifyAPI.auth_query_parameters.items()])
        auth_url = "{}/?{}".format(SpotifyAPI.SPOTIFY_AUTH_URL, url_args)
        return redirect(auth_url)

    @staticmethod
    @app.route("/callback/q")
    def callback():
        SpotifyAPI.process_callback(request.args['code'])

        # Get User Active Devices
        devices_data = SpotifyAPI.get_user_devices()

        # Get profile data
        profile_data = SpotifyAPI.get_user_profile()

        return render_template("index.html", profile=profile_data, devices=devices_data['devices'])

    @staticmethod
    @app.route('/play', methods=['POST'])
    def play():
        content: dict = request.get_json(silent=True)
        device_id = content['device_id'] if 'device_id' in content.keys() else None
        context_id = content['context_uri'] if 'context_uri' in content.keys() else None

        # Resume Playback, or play the specified content
        player_play_response = SpotifyAPI.play(context_uri=context_id, device_id=device_id)
        if player_play_response.status_code == 401:
            # Unauthorized - Token is expired
            SpotifyAPI.refresh_api_token()
            player_play_response = SpotifyAPI.play(context_uri=context_id, device_id=device_id)

        if int(player_play_response.status_code / 100) != 2:
            return "Something went wrong", 400
        print(player_play_response.text)

        # Turn on shuffle mode if requested
        if content is not None and 'shuffle' in content.keys():
            player_shuffle_response = SpotifyAPI.shuffle(bool(content['shuffle']), device_id=device_id)
            if player_shuffle_response.status_code == 401:
                # Unauthorized - Token is expired
                SpotifyAPI.refresh_api_token()
                player_shuffle_response = SpotifyAPI.shuffle(bool(content['shuffle']), device_id=device_id)

            if int(player_shuffle_response.status_code / 100) != 2:
                return "Something went wrong", 400
            print(player_shuffle_response.text)

        # Set the correct Volume if requested
        if content is not None and 'volume' in content.keys():
            player_volume_response = SpotifyAPI.set_volume(content['volume'], device_id=device_id)
            if player_volume_response.status_code == 401:
                # Unauthorized - Token is expired
                SpotifyAPI.refresh_api_token()
                player_volume_response = SpotifyAPI.set_volume(content['volume'], device_id=device_id)

            print(player_volume_response.text)
            if int(player_volume_response.status_code / 100) != 2:
                return "Something went wrong", 400

        return 'Playback Started!'

    @staticmethod
    @app.route('/pause', methods=['POST'])
    def pause():
        content: dict = request.get_json(silent=True)
        device_id = content['device_id'] if 'device_id' in content.keys() else None

        player_pause_response = SpotifyAPI.pause(device_id=device_id)
        print(player_pause_response.text)
        if int(player_pause_response.status_code / 100) != 2:
            return "Something went wrong", 400

        return 'Playback Paused!'


class SpotifyAPI:
    #  Client Keys
    __CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
    __CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']

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
        "client_id": __CLIENT_ID
    }

    __access_token = None
    __refresh_token = None
    __token_type = None
    __expires_in = None

    @classmethod
    def process_callback(cls, auth_token):
        # Auth Step 4: Requests refresh and access tokens
        code_payload = {
            "grant_type": "authorization_code",
            "code": str(auth_token),
            "redirect_uri": SpotifyAPI.REDIRECT_URI
        }
        base64encoded = base64.b64encode(
            bytes("{}:{}".format(SpotifyAPI.__CLIENT_ID, SpotifyAPI.__CLIENT_SECRET), 'utf-8')).decode('utf-8')
        headers = {"Authorization": "Basic {}".format(base64encoded)}
        post_request = requests.post(SpotifyAPI.SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

        # Auth Step 5: Tokens are Returned to Application
        response_data = json.loads(post_request.text)
        SpotifyAPI.__access_token = response_data["access_token"]
        SpotifyAPI.__refresh_token = response_data["refresh_token"]
        SpotifyAPI.__token_type = response_data["token_type"]
        SpotifyAPI.__expires_in = response_data["expires_in"]

    @classmethod
    def refresh_api_token(cls):
        code_payload = {
            "grant_type": "refresh_token",
            "refresh_token": str(SpotifyAPI.__refresh_token),
        }
        base64encoded = base64.b64encode(
            bytes("{}:{}".format(SpotifyAPI.__CLIENT_ID, SpotifyAPI.__CLIENT_SECRET), 'utf-8')).decode('utf-8')
        headers = {"Authorization": "Basic {}".format(base64encoded)}
        post_request = requests.post(SpotifyAPI.SPOTIFY_TOKEN_URL, data=code_payload, headers=headers)

        # Auth Step 5: Tokens are Returned to Application
        response_data: dict = json.loads(post_request.text)
        SpotifyAPI.__access_token = response_data["access_token"]
        SpotifyAPI.__refresh_token = response_data["refresh_token"] if "refresh_token" in response_data.keys() \
            else SpotifyAPI.__refresh_token
        SpotifyAPI.__token_type = response_data["token_type"]
        SpotifyAPI.__expires_in = response_data["expires_in"]

    @staticmethod
    def set_volume(volume_percent: int, device_id: str = None) -> requests.Response:
        authorization_header = {"Authorization": "Bearer {}".format(SpotifyAPI.__access_token)}

        player_volume_api_endpoint = "{}/me/player/volume".format(SpotifyAPI.SPOTIFY_API_URL)
        player_volume_api_endpoint += "?volume_percent=" + str(volume_percent)
        if device_id is not None:
            player_volume_api_endpoint += "&device_id={}".format(device_id)
        player_volume_response = requests.put(player_volume_api_endpoint, headers=authorization_header)
        return player_volume_response

    @staticmethod
    def play(device_id: str = None, context_uri: str = None) -> requests.Response:
        authorization_header = {"Authorization": "Bearer {}".format(SpotifyAPI.__access_token)}

        player_play_request_body: dict = dict()
        player_play_api_endpoint = "{}/me/player/play".format(SpotifyAPI.SPOTIFY_API_URL)

        if device_id is not None:
            player_play_api_endpoint += "?device_id={}".format(device_id)

        if context_uri is not None:
            player_play_request_body["context_uri"] = context_uri

        player_play_response = requests.put(player_play_api_endpoint, headers=authorization_header,
                                            data=json.dumps(player_play_request_body))
        return player_play_response

    @staticmethod
    def pause(device_id: str = None) -> requests.Response:
        authorization_header = {"Authorization": "Bearer {}".format(SpotifyAPI.__access_token)}
        player_pause_api_endpoint = "{}/me/player/pause".format(SpotifyAPI.SPOTIFY_API_URL)
        if device_id is not None:
            player_pause_api_endpoint += "?device_id={}".format(device_id)
        player_pause_response = requests.put(player_pause_api_endpoint, headers=authorization_header)
        return player_pause_response

    @staticmethod
    def shuffle(state: bool, device_id: str = None) -> requests.Response:
        authorization_header = {"Authorization": "Bearer {}".format(SpotifyAPI.__access_token)}

        player_shuffle_api_endpoint = "{}/me/player/shuffle".format(SpotifyAPI.SPOTIFY_API_URL)
        player_shuffle_api_endpoint += "?state=" + str(state).lower()

        if device_id is not None:
            player_shuffle_api_endpoint += "&device_id={}".format(device_id)

        player_shuffle_response = requests.put(player_shuffle_api_endpoint, headers=authorization_header)
        return player_shuffle_response

    @staticmethod
    def get_user_profile() -> dict:
        authorization_header = {"Authorization": "Bearer {}".format(SpotifyAPI.__access_token)}

        user_profile_api_endpoint = "{}/me".format(SpotifyAPI.SPOTIFY_API_URL)
        profile_response = requests.get(user_profile_api_endpoint, headers=authorization_header)
        profile_data = json.loads(profile_response.text)
        return profile_data

    @staticmethod
    def get_user_devices() -> dict:
        authorization_header = {"Authorization": "Bearer {}".format(SpotifyAPI.__access_token)}

        devices_api_endpoint = "{}/me/player/devices".format(SpotifyAPI.SPOTIFY_API_URL)
        devices_response = requests.get(devices_api_endpoint, headers=authorization_header)
        devices_data = json.loads(devices_response.text)
        return devices_data


if __name__ == '__main__':
    Connect.app.run(host='0.0.0.0')
