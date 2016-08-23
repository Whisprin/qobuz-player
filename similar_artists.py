#!/usr/bin/env python3
import os
import shutil
import sys
import configparser
from qobuz import qobuz_api as qobuz
import pylast

CONFIG_PATH = os.path.expanduser('~/.qdl/qdl_config.ini')

config_folder = os.path.dirname(CONFIG_PATH)
if not os.path.exists(config_folder):
    os.makedirs(config_folder)

if not os.path.isfile(CONFIG_PATH):
    config_skel_path = os.path.join(os.path.dirname(__file__), 'config.ini.skel')
    shutil.copyfile(config_skel_path, CONFIG_PATH)
    print("A new config file in {} has been created.".format(CONFIG_PATH))
    print("Please add your app and user info")
    sys.exit(-1)

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

app_secret = config['QOBUZ']['app_secret']
app_id = config['QOBUZ']['app_id']
user_auth_token = config['QOBUZ']['user_auth_token']
download_dir = config['DOWNLOAD']['directory']
format_id = int(config['DOWNLOAD']['format_id'])
lastfm_api_key = config['LASTFM']['api_key']
lastfm_api_secret = config['LASTFM']['api_secret']

search_artist = 'Ólafur Arnalds'

lastfm = pylast.LastFMNetwork(api_key=lastfm_api_key, api_secret=lastfm_api_secret)

lastfm_artist = lastfm.get_artist(search_artist)

lastfm_similar_artists = lastfm_artist.get_similar(limit=8)

qobuz_client = qobuz.QobuzApi(app_id, app_secret, user_auth_token, format_id, download_dir)

for similar_artist in lastfm_similar_artists:
    lastfm_artist_name = similar_artist.item.name
    artist = qobuz_client.get_artist_from_catalog(lastfm_artist_name)
    if artist:
        print('Found {}: {}'.format(artist['name'], artist['id']))
        qobuz_client.play_artist(artist['id'], track_limit=1)
    else:
        print("Not found {}".format(lastfm_artist_name))
