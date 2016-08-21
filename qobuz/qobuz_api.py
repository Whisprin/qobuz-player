import hashlib
import time
import requests
import json
import os
import urllib.request
import shutil

class QobuzApi:
    def __init__(self, app_id, app_secret, user_auth_token, format_id=6, base_path='.'):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_auth_token = user_auth_token
        self.format_id = format_id
        os.chdir(base_path)

    def set_track_id(self, track_id):
        self.track_id = track_id

    def format_id(self, format_id):
        self.format_id = format_id

    def get_request_sig(self):
        params = {
            'format_id': self.format_id,
            'track_id': self.track_id,
            'request_ts': self.request_ts,
            'app_secret': self.app_secret,
        }
        request_hash = hashlib.md5()
        string_to_hash = "trackgetFileUrlformat_id{format_id}intentstreamtrack_id{track_id}{request_ts}{app_secret}".format_map(params)
        request_hash.update(string_to_hash.encode('utf-8'))
        request_sig = request_hash.hexdigest()
        return request_sig

    def get_file_url(self):
        self.track_id = self.track_id
        self.request_ts = int(time.time())
        params = {
            'track_id': self.track_id,
            'format_id': self.format_id,
            'app_id': self.app_id,
            'request_ts': self.request_ts,
            'request_sig': self.get_request_sig(),
            'user_auth_token': self.user_auth_token
        }

        get_file_url = "http://www.qobuz.com/api.json/0.2/track/getFileUrl?track_id={track_id}&format_id={format_id}&app_id={app_id}&intent=stream&request_ts={request_ts}&request_sig={request_sig}&user_auth_token={user_auth_token}".format_map(params)

        response = requests.get(get_file_url)
        json_response = json.loads(response.text)

        file_url = json_response['url']
        return file_url

    def get_json_from_url(self, url):
        response = requests.get(url)
        json_response = json.loads(response.text)
        return json_response

    def get_meta_data(self):
        params = {
            'track_id': self.track_id,
            'app_id': self.app_id
        }
        meta_data_url = "http://www.qobuz.com/api.json/0.2/track/get?track_id={track_id}&app_id={app_id}".format_map(params)
        json_response = self.get_json_from_url(meta_data_url)

        meta_data = {
            'album_artist': json_response['album']['artist']['name'],
            'album' :json_response['album']['title'],
            'genre': json_response['album']['genre']['name'],
            'title': json_response['title'],
            'cover_url': json_response['album']['image']['large'],
            'track_number': json_response['track_number'],
            'duration': json_response['duration']
        }
        return meta_data

    def download_file(self, file_url, file_path):
        with urllib.request.urlopen(file_url) as response, open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

    def download_track(self, track_id, with_cover=True, wait=True):
        self.set_track_id(track_id)
        file_url = self.get_file_url()
        track_meta_data = self.get_meta_data()
        album_path = os.path.join(track_meta_data['album_artist'], track_meta_data['album'])
        os.makedirs(album_path, exist_ok=True)

        params = {
            'track_number': int(track_meta_data['track_number']),
            'title': track_meta_data['title'],
            'ext': 'flac' if self.format_id > 5 else 'mp3',
            'duration': track_meta_data['duration']
        }

        file_name = "{track_number:02d} {title}.{ext}".format_map(params)
        file_path = os.path.join(album_path, file_name)

        if os.path.isfile(file_path):
            print("{title} already exists".format_map(params))
            wait = False
        else:
            print("Downloading {title}...".format_map(params))
            self.download_file(file_url, file_path)

        if with_cover:
            cover_url = track_meta_data['cover_url']
            cover_path = os.path.join(album_path, 'cover.jpg')

            if not os.path.isfile(cover_path):
                self.download_file(cover_url, cover_path)

        if wait:
            print("Waiting for \"{title}\" ({duration}s)".format_map(params))
            time.sleep(int(track_meta_data['duration']))

    def get_meta_data_for_album_id(self, album_id):
        params = {
            'app_id': self.app_id,
            'album_id': album_id
        }

        album_url = "http://www.qobuz.com/api.json/0.2/album/get?app_id={app_id}&album_id={album_id}".format_map(params)
        json_response = self.get_json_from_url(album_url)
        return json_response

    def download_album(self, album_id):
        album_meta_data = self.get_meta_data_for_album_id(album_id)
        params = {
            'artist': album_meta_data['artist']['name'],
            'album': album_meta_data['title']
        }
        print("Getting tracks for \"{artist} - {album}\"".format_map(params))
        for track in album_meta_data['tracks']['items']:
            self.download_track(track['id'])
