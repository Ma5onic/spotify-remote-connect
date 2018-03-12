Spotify Playback Controller
==========================

Control Playback of Spotify via a Simple API to allow for external services, like IFTTT to start and stop Spotify
Playback. Controling Spotify in this manner requires a Spotify Premium Subscription.

# Docker
For simplicity, this project has been packaged into a Docker Container that builds off of the default `python:3` image.
Creating a container is simple, provided you have created your application in the Spotify Developer Console.

```sh
docker create --name SpotifyConnect \
    -p 5000:5000 \
    -e SPOTIFY_CLIENT_ID='your-spotify-client-id' \
    -e SPOTIFY_CLIENT_SECRET='your-spotify-client-secret' \
    -e CLIENT_SIDE_URL='http://127.0.0.1' \
    -e PORT='5000' \
    --restart=always \
    tpaulus/spotify-remote-connect
```

# Endpoints
### **GET** `/`
Initiate the OAuth2 sequence. This is required on first launch to grant the necessary permissions to the web app.
Once the necessary permissions have been obtained, the list of active devices associated with the user are listed.

### **POST** `/play`
Resume Playback. A device ID can be supplied in the request body with the following format:
```json
{"deviceId" : "your-device-id"}
```

If a device ID is supplied, playback will resume on the specified device, else playback will resume on the active
device, as determined by Spotify.

### **POST** `/pause`
Pause Playback. A device ID can be supplied in the request body with the following format:
```json
{"deviceId" : "your-device-id"}
```

If a device ID is supplied, playback will pause only if the device specified is the active device. If a different device
is the active device and does not match the specified ID, playback will continue.

## ENV Configuration
Be sure to set the following env vars with the correct values from the Spotify Developers Console:

```sh
export SPOTIFY_CLIENT_ID='your-spotify-client-id'
export SPOTIFY_CLIENT_SECRET='your-spotify-client-secret'
export CLIENT_SIDE_URL='http://127.0.0.1'
export PORT='5000'
```


## Projects Used
- [drshrey/spotify-flask-auth-example](https://github.com/drshrey/spotify-flask-auth-example)
- [plamere/spotipy](https://github.com/plamere/spotipy)