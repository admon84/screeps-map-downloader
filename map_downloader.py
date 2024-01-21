import re
import sys
import time
import yaml
import json
import jsonschema
import screepsapi
from datetime import datetime
from rich import print
from envyaml import EnvYAML
from queue import Queue
from threading import Thread


class ScreepsMapDownloader(object):
    def __init__(self):
        self.get_config()
        self.connect_api()

    def get_config(self):
        self.config_file = "config.yaml"
        with open(self.config_file) as config_file:
            config = yaml.safe_load(config_file)
        with open("config.schema.yaml") as schema_file:
            schema = yaml.safe_load(schema_file)
        try:
            jsonschema.validate(instance=config, schema=schema)
        except (jsonschema.ValidationError, jsonschema.SchemaError) as error:
            print("Config fatal error:", error.args[0])
            sys.exit(0)
        self.config = EnvYAML(self.config_file)

    def connect_api(self):
        self.api = screepsapi.API(
            host=self.config.get("api_host"),
            prefix=self.config.get("api_prefix"),
            token=self.config.get("api_token"),
            u=self.config.get("api_username"),
            p=self.config.get("api_password"),
            secure=self.config.get("api_secure"),
        )

    def log(self, *args, **kwargs):
        time = datetime.now().strftime("[%H:%M:%S]")
        print(time, *args, **kwargs)

    def get_room_data(
        self, shard, room, deposit_type, room_status, room_index, total_rooms
    ):
        # Fetch room data from API
        room_terrain_res = self.api.room_terrain(room=room, shard=shard, encoded=True)
        time.sleep(0.3)
        room_objects_res = self.api.room_objects(room=room, shard=shard)
        time.sleep(0.3)
        room_status_res = self.api.room_status(room=room, shard=shard)

        if self.config["progress_bar"]:
            # Estimate time remaining
            percent_complete = room_index / total_rooms * 100
            percent_complete = round(percent_complete, 1)
            percent_complete = (
                int(percent_complete)
                if percent_complete.is_integer()
                else percent_complete
            )
            est_time = self.estimate_time_remaining(percent_complete)

            # Progress bar
            bar_length = 20
            block_char = "\u25A0"
            line_char = "\u2500"
            completed_length = int(bar_length * percent_complete // 100)
            bar = block_char * completed_length + line_char * (
                bar_length - completed_length
            )

            # Format output
            fmt_percent = f"{percent_complete}%".ljust(5)
            fmt_room_count = f"#{room_index}/{total_rooms}".rjust(
                2 * len(str(total_rooms)) + 2
            )

            # Print progress bar output
            self.log(
                f"\[{bar}] {fmt_percent} | {fmt_room_count} | {shard}/{room} | {est_time}"
            )

        if room_status_res["ok"] == 1:
            # Remove ruins, spawns and construction sites
            room_objects = [
                o
                for o in room_objects_res["objects"]
                if o["type"] not in ["ruin", "spawn", "constructionSite"]
            ]

            # Reset controller data
            for objects_data in room_objects:
                if objects_data["type"] == "controller":
                    objects_data["level"] = 0
                    for key in [
                        "safeMode",
                        "safeModeAvailable",
                        "safeModeCooldown",
                        "user",
                        "isPowerEnabled",
                        "downgradeTime",
                        "progress",
                        "progressTotal",
                        "hits",
                        "hitsMax",
                    ]:
                        objects_data.pop(key, None)

            # Room data including terrain and objects
            data = {
                "room": room,
                "terrain": room_terrain_res["terrain"][0]["terrain"],
                "objects": room_objects,
                "status": room_status,
            }

            # Add deposits to highway rooms
            if self.is_highway(room):
                data.update(
                    {
                        "bus": True,
                        "depositType": deposit_type,
                    }
                )
            return data

        return None

    def estimate_time_remaining(self, percent_complete):
        time_elapsed = time.time() - self.start_time
        time_per_unit = time_elapsed / percent_complete
        est_time_remaining = time_per_unit * (100 - percent_complete)
        hours, remainder = divmod(est_time_remaining, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if hours > 0:
            parts.append(f"{int(hours)}h")
        if minutes > 0:
            parts.append(f"{int(minutes)}m")
        if seconds > 0 or (hours == 0 and minutes == 0):
            parts.append(f"{int(seconds)}s")
        return " ".join(parts)

    def is_highway(self, room_name):
        regex_room = re.compile("^([WE])(\d+)([NS])(\d+)$")
        parsed = regex_room.match(room_name)
        return parsed and (
            int(parsed.group(2)) % 10 == 0 or int(parsed.group(4)) % 10 == 0
        )

    def get_deposit_type(self, dx, dy):
        deposit_types = {
            ("W", "N"): "silicon",
            ("W", "S"): "biomass",
            ("E", "N"): "metal",
            ("E", "S"): "mist",
        }
        return deposit_types.get((dx, dy))

    def get_room_status(self, dx, dy):
        room_status = {
            ("W", "N"): "normal",
            ("W", "S"): "normal",
            ("E", "N"): "not available",
            ("E", "S"): "not available",
        }
        return room_status.get((dx, dy))

    def run(self):
        self.log(f"Downloading: {self.config['map_description']}")

        # Create queue and thread list
        queue = Queue()
        threads_list = list()

        # Create data object
        data = {
            "description": self.config["map_description"],
            "rooms": [],
        }

        # Fetch world size from API
        shard = self.config["map_shard"]
        worldsize_res = self.api.worldsize(shard=shard)
        world_max_dy = worldsize_res["width"] // 2
        world_max_dx = worldsize_res["height"] // 2

        # Calculate total rooms
        room_directions = [("W", "N"), ("W", "S"), ("E", "N"), ("E", "S")]
        total_rooms = world_max_dy * world_max_dx * len(room_directions)
        fmt_total_rooms = "{:,}".format(total_rooms)

        # Start fetching rooms
        self.log(f"Fetching {fmt_total_rooms} rooms...")
        self.start_time = time.time()

        # Iterate over all rooms
        room_index = 0
        for dx, dy in room_directions:
            deposit_type = self.get_deposit_type(dx, dy)
            room_status = self.get_room_status(dx, dy)
            for y in range(world_max_dy):
                for x in range(world_max_dx):
                    room_index += 1
                    room = f"{dx}{x}{dy}{y}"
                    t = Thread(
                        target=lambda q, args: q.put(self.get_room_data(*args)),
                        args=(
                            queue,
                            (
                                shard,
                                room,
                                deposit_type,
                                room_status,
                                room_index,
                                total_rooms,
                            ),
                        ),
                    )
                    t.start()
                    threads_list.append(t)
                    time.sleep(1)

        # Wait for all threads to finish
        for t in threads_list:
            t.join()

        # Get results from queue
        while not queue.empty():
            room_data = queue.get()
            data["rooms"].append(room_data)

        # Save results to file
        if self.config["save_results_filename"] is not None:
            with open(self.config["save_results_filename"], "w") as file:
                json.dump(data, file, separators=(",", ":"))
            self.log(f"Results saved to {self.config['save_results_filename']}")
        self.log("Complete")


if __name__ == "__main__":
    downloader = ScreepsMapDownloader()
    downloader.run()
