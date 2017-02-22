import hashlib
import time
import requests
import json
import os
import urllib.request
import shutil
import subprocess
import taglib
from unidecode import unidecode

class QobuzFileError(Exception):
    def __init__(self,*args,**kwargs):
        Exception.__init__(self,*args,**kwargs)

class QobuzApi:
    def __init__(self, app_id, app_secret, user_auth_token, format_id=6, cache_dir='.', log_dir='.'):
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_auth_token = user_auth_token
        self.format_id = format_id
        self.cache_dir = cache_dir
        self.log_dir = log_dir

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
            'request_ts': self.request_ts,
            'request_sig': self.get_request_sig()
        }

        get_file_url = "http://www.qobuz.com/api.json/0.2/track/getFileUrl?track_id={track_id}&format_id={format_id}&intent=stream&request_ts={request_ts}&request_sig={request_sig}".format_map(params)

        json_response = self.get_json_from_url(get_file_url)

        if 'url' in json_response:
            file_url = json_response['url']
        else:
            raise QobuzFileError("Track {} doesn't provide an url.".format(self.track_id))
        if 'sample' in json_response:
            raise QobuzFileError("Track {} is a sample.".format(self.track_id))
        return file_url

    def print_as_json(self, data):
        print(json.dumps(data, indent=4, sort_keys=True))

    def get_save_file_name(self, file_name):
        if file_name.startswith('.'):
            file_name = '_{}'.format(file_name)
        return file_name.replace('/', '-')

    def get_json_from_url(self, url):
        headers = {
            'X-User-Auth-Token': self.user_auth_token,
            'X-App-Id': self.app_id
        }
        response = requests.get(url, headers=headers)
        json_response = json.loads(response.text)
        return json_response

    def get_meta_data(self):
        meta_data_url = "http://www.qobuz.com/api.json/0.2/track/get?track_id={}".format(self.track_id)
        json_response = self.get_json_from_url(meta_data_url)

        meta_data = {
            'album_artist': json_response['album']['artist']['name'],
            'artist': json_response['performer']['name'],
            'album' :json_response['album']['title'],
            'genre': json_response['album']['genre']['name'],
            'title': json_response['title'],
            'cover_url': json_response['album']['image']['large'],
            'track_number': json_response['track_number'],
            'cd_count': json_response['album']['media_count'],
            'cd_number': json_response['media_number'],
            'duration': json_response['duration'],
            'released_at': time.gmtime(json_response['album']['released_at'])
        }
        return meta_data

    def absolute_opener(self, path, flags, base_path):
        dir_fd = os.open(base_path, os.O_RDONLY, 0o600)
        return os.open(path, flags, dir_fd=dir_fd)

    def cache_opener(self, path, flags):
        return self.absolute_opener(path, flags, self.cache_dir)

    def log_opener(self, path, flags):
        return self.absolute_opener(path, flags, self.log_dir)

    def cache_file(self, file_url, file_path):
        temp_file_path = "{}.qtmp".format(file_path)
        with urllib.request.urlopen(file_url) as response, open(temp_file_path, 'wb', opener=self.cache_opener) as out_file:
            shutil.copyfileobj(response, out_file)
        shutil.move(self.get_cache_file_path(temp_file_path), self.get_cache_file_path(file_path))

    def play_track(self, track_id, with_cover=True, cache_only=False, skip_existing=False):
        self.set_track_id(track_id)

        track_meta_data = self.get_meta_data()
        artist = self.get_save_file_name(track_meta_data['album_artist'])
        album = self.get_save_file_name(track_meta_data['album'])
        album_path = os.path.join(artist, album)
        if track_meta_data['cd_count'] > 1:
            album_path = os.path.join(album_path, 'CD{}'.format(track_meta_data['cd_number']))
        os.makedirs(self.get_cache_file_path(album_path), exist_ok=True)

        params = {
            'track_number': int(track_meta_data['track_number']),
            'title': track_meta_data['title'],
            'ext': 'flac' if self.format_id > 5 else 'mp3',
            'duration': track_meta_data['duration']
        }

        file_name = "{track_number:02d} {title}.{ext}".format_map(params)
        save_file_name = self.get_save_file_name(file_name)
        file_path = os.path.join(album_path, save_file_name)

        track_exists = False
        if os.path.isfile(self.get_cache_file_path(file_path)):
            track_exists = True
            print("{title} already exists".format_map(params))
        else:
            try:
                file_url = self.get_file_url()
            except QobuzFileError as e:
                print(e)
                missing_file_path = '{}.missing'.format(file_path)
                with open(missing_file_path, 'w', opener=cache_opener):
                    pass
                return False
            print("Caching {title}...".format_map(params))
            self.cache_file(file_url, file_path)
            self.tag_file(file_path, track_meta_data)

        if with_cover:
            cover_url = track_meta_data['cover_url']
            cover_path = os.path.join(album_path, 'folder.jpg')

            if not os.path.isfile(cover_path):
                self.cache_file(cover_url, cover_path)

        if not cache_only and not (skip_existing and track_exists):
            print("Playing \"{title}\" for {duration}s".format_map(params))
            #time.sleep(int(track_meta_data['duration']))
            absolute_file_path = self.get_cache_file_path(file_path)
            subprocess.call(["mplayer", "-msgcolor", "-nolirc", "-msglevel", "cplayer=-1:codeccfg=-1:decaudio=-1:decvideo=-1:demux=-1:demuxer=-1:subreader=-1", absolute_file_path])
        return True

    def get_cache_file_path(self, file_path):
        return os.path.join(self.cache_dir, file_path)

    def tag_file(self, file_path, meta_data):
        song = taglib.File(self.get_cache_file_path(file_path))
        song.tags['TITLE'] = meta_data['title']
        song.tags["ALBUM"] = meta_data['album']
        song.tags['ALBUMARTIST'] = meta_data['album_artist']
        song.tags["ARTIST"] = meta_data['artist']
        song.tags["GENRE"] = meta_data['genre']
        song.tags["DATE"] = str(meta_data['released_at'].tm_year)
        song.tags['DISCNUMBER'] = str(meta_data['cd_number'])
        song.tags['TOTALDISCS'] = str(meta_data['cd_count'])
        song.tags['TRACKNUMBER'] = str(meta_data['track_number'])
        song.save()

    def get_meta_data_for_album_id(self, album_id):
        album_url = "http://www.qobuz.com/api.json/0.2/album/get?album_id={}".format(album_id)
        json_response = self.get_json_from_url(album_url)
        return json_response

    def get_meta_data_for_artist_id(self, artist_id, extra=''):
        params = {
            'artist_id': artist_id,
            'extra': extra
        }

        artist_url = "http://www.qobuz.com/api.json/0.2/artist/get?artist_id={artist_id}&limit=50&extra={extra}".format_map(params)
        json_response = self.get_json_from_url(artist_url)
        return json_response

    def play_album(self, album_id, cache_only=False, skip_existing=False):
        album_meta_data = self.get_meta_data_for_album_id(album_id)
        params = {
            'artist': album_meta_data['artist']['name'],
            'album': album_meta_data['title']
        }
        print("Getting tracks for \"{artist} - {album}\"".format_map(params))
        for track in album_meta_data['tracks']['items']:
            self.play_track(track['id'], cache_only=cache_only, skip_existing=skip_existing)

    def play_artist(self, artist_id, cache_only=False, track_limit=None):
        artist_meta_data = self.get_meta_data_for_artist_id(artist_id, extra='tracks')
        params = {
            'artist': artist_meta_data['name']
        }
        print("Getting tracks for \"{artist}\"".format_map(params))
        played_track_count = 0
        for track in artist_meta_data['tracks']['items']:
            if self.play_track(track['id'], cache_only=cache_only):
                played_track_count += 1
            if track_limit and played_track_count >= track_limit:
                return

    def play_artist_albums(self, artist_id, confirm_album=False, cache_only=False, skip_existing=False):
        artist_meta_data = self.get_meta_data_for_artist_id(artist_id, extra='albums')
        artist_name = artist_meta_data['name']
        print("Getting tracks for \"{}\"".format(artist_name))

        for album in artist_meta_data['albums']['items']:
            skip_album = False
            album_log_file_name = 'artist-albums-{}.log'.format(artist_id)
            with open(album_log_file_name, 'a+', opener=self.log_opener) as album_log:
                album_log.seek(0)
                for album_id in album_log.readlines():
                    if album_id.rstrip() == album['id']:
                        skip_album = True
            if not skip_album and (not confirm_album or input('Play album: {}? '.format(album['title'])) == 'y'):
                self.play_album(album['id'], cache_only=cache_only, skip_existing=skip_existing)
                with open(album_log_file_name, 'a', opener=self.log_opener) as album_log:
                    album_log.write('{}\n'.format(album['id']))

        with open('artists.log', 'a', opener=self.log_opener) as artist_log:
            artist_log.write('{},{},{}\n'.format(artist_id, artist_name, time.time()))

    def play_similar_artists(self, artist_id, artist_limit=3, track_limit=1, cache_only=False):
        params = {
            'artist_id': artist_id,
            'limit': artist_limit
        }
        similar_artist_url = 'http://www.qobuz.com/api.json/0.2/artist/getSimilarArtists?artist_id={artist_id}&limit={limit}'.format_map(params)
        similar_artists = self.get_json_from_url(similar_artist_url)
        for artist in similar_artists['artists']['items']:
            self.play_artist(artist['id'], track_limit=track_limit, cache_only=cache_only)

    def search_catalog(self, query, item_type=None, limit=2):
        if item_type:
            params_type = "&type={}".format(item_type)
        else:
            params_type = ""
        if limit:
            params_limit = "&limit={}".format(limit)
        else:
            params_type = ""

        params = {
            'query': query,
            'type': params_type,
            'limit': params_limit
        }

        search_url = "http://www.qobuz.com/api.json/0.2/catalog/search?query={query}{type}{limit}".format_map(params)
        json_response = self.get_json_from_url(search_url)
        return json_response

    def search_catalog_for_artists(self, artist, limit=5):
        response = self.search_catalog(artist, 'artists', limit=limit)
        return response['artists']['items']

    def get_artist_from_catalog(self, artist):
        artists = self.search_catalog_for_artists(artist, limit=5)
        # sometimes another but the first result is a perfect match
        for artist_item in artists:
            #if unidecode(artist.lower()) == artist_item['name'].lower():
            if artist == artist_item['name']:
                return artist_item

    def search_catalog_for_albums(self, album, limit=2):
        response = self.search_catalog(album, 'albums')
        return response['albums']['items']
