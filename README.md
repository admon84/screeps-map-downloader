# screeps-map-downloader

A script that compiles a Screeps World map into a json file by fetching the map data for each room using the unofficial Screeps API

### Requirements

Python 3

### Install

Download or clone this repo and then install python packages in a virtual env:

```sh
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install pyyaml jsonschema rich envyaml
pip install git+https://github.com/admon84/python-screeps.git@v0.5.2#egg=screepsapi
deactivate
```

### Running the script

Configure `config.yaml` with the correct host, auth token, and other settings.

After configuration, run the script:

```sh
source env/bin/activate
python3 map_downloader.py
deactivate
```

### Importing a map to a private server

To import a map with screepsmod-map-tool, drag and drop a map json file into the map tool window, save, done!

For other contenient options, see [screepsmod-admin-utils](https://github.com/ScreepsMods/screepsmod-admin-utils#readme)
