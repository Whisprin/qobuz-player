#!/usr/bin/env python3

import configparser
import os
import shutil
import sys

from IPython import embed
from qobuz import qobuz_api as qobuz

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
log_dir = config['LOG']['directory']

os.makedirs(download_dir, exist_ok=True)

qobuz_client = qobuz.QobuzApi(app_id, app_secret, user_auth_token, format_id, download_dir, log_dir)

embed()
