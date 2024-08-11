# Screeps Map Downloader

Python script for downloading a Screeps World map into a JSON file, utilizing the unofficial Screeps API.

### Requirements

* Python 3

### Install

Download or clone this repo and then install Python dependencies from the project root:

```sh
make setup
```

### Running the Script

1. Configure `config.yaml` with the server host and map settings.
2. Run the script:

```sh
make run
```

![screeps-map-downloader](https://github.com/admon84/screeps-map-downloader/assets/10291543/8f6163c3-2498-4cff-a8de-240a4a53fb29)

### Importing a Map to a Private Server

Importing maps to your private Screeps server can be done using Screeps mods.

- Using **screepsmod-map-tool** &mdash; Drag and drop a map file into the map tool window and then save.
- Using **screepsmod-admin-utils** &mdash; Copy a map file to the screeps server/launcher directory and run `utils.importMapFile('map_file.json')` command in the server CLI.

For more details, see [screepsmod-admin-utils](https://github.com/ScreepsMods/screepsmod-admin-utils#readme).
