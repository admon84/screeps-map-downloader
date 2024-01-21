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
            host=self.config["api_host"],
            prefix=self.config["api_prefix"],
            token=self.config["api_token"] if self.config["api_token"] else None,
            u=self.config["api_username"] if self.config["api_username"] else None,
            p=self.config["api_password"] if self.config["api_password"] else None,
            secure=self.config["api_secure"] if self.config["api_secure"] else None,
        )

    def log(self, *args, **kwargs):
        time = datetime.now().strftime("[%H:%M:%S]")
        print(time, *args, **kwargs)

    def get_room_data(
        self, shard, room, deposit_type, room_status, room_index, rooms_count
    ):
        room_terrain_res = self.api.room_terrain(room=room, shard=shard, encoded=True)
        time.sleep(0.3)
        room_objects_res = self.api.room_objects(room=room, shard=shard)
        time.sleep(0.3)
        room_status_res = self.api.room_status(room=room, shard=shard)

        if self.config["verbose_logging"]:
            percent_complete = room_index / rooms_count * 100
            est_time = self.estimate_time_remaining(percent_complete)

            bar_length = 20
            completed_length = int(bar_length * percent_complete // 100)
            bar = "\u25A0" * completed_length + "-" * (bar_length - completed_length)

            self.log(
                f"\[{bar}] \[{round(percent_complete, 1)}%] \[{room_index}/{rooms_count}] \[{shard}/{room}] \[{est_time}]"
            )
        if room_status_res["ok"] == 1:
            return {
                "room": room,
                "terrain": room_terrain_res["terrain"][0]["terrain"],
                "objects": room_objects_res["objects"],
                "status": room_status,
                "bus": True,
                "depositType": deposit_type,
            }
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

        queue = Queue()
        threads_list = list()
        data = {
            "description": self.config["map_description"],
            "rooms": [],
        }

        room_index = 0
        room_directions = [("W", "N"), ("W", "S"), ("E", "N"), ("E", "S")]

        shard = self.config["map_shard"]
        worldsize_res = self.api.worldsize(shard=shard)
        world_width = worldsize_res["width"] // 2
        world_height = worldsize_res["height"] // 2
        rooms_count = world_width * world_height * len(room_directions)
        formatted_rooms_count = "{:,}".format(rooms_count)
        self.start_time = time.time()

        self.log(f"Fetching {formatted_rooms_count} rooms...")
        for dx, dy in room_directions:
            deposit_type = self.get_deposit_type(dx, dy)
            room_status = self.get_room_status(dx, dy)
            for y in range(world_width):
                for x in range(world_height):
                    room_index += 1
                    room = f"{dx}{x}{dy}{y}"
                    t = Thread(
                        target=lambda q, arg1, arg2, arg3, arg4, arg5, arg6: q.put(
                            self.get_room_data(arg1, arg2, arg3, arg4, arg5, arg6)
                        ),
                        args=(
                            queue,
                            shard,
                            room,
                            deposit_type,
                            room_status,
                            room_index,
                            rooms_count,
                        ),
                    )
                    t.start()
                    threads_list.append(t)
                    time.sleep(1)

        for t in threads_list:
            t.join()

        while not queue.empty():
            room_data = queue.get()
            data["rooms"].append(room_data)

        if self.config["results_save_file"]:
            with open(self.config["results_filename"], "w") as file:
                json.dump(data, file, separators=(",", ":"))
            self.log(f"Results saved to {self.config['results_filename']}")

        self.log(f"Complete")


if __name__ == "__main__":
    downloader = ScreepsMapDownloader()
    downloader.run()
