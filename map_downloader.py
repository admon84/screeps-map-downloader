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
        self.config_file = 'config.yaml'
        with open(self.config_file) as config_file:
            config = yaml.safe_load(config_file)
        with open('config.schema.yaml') as schema_file:
            schema = yaml.safe_load(schema_file)
        try:
            jsonschema.validate(instance=config, schema=schema)
        except (jsonschema.ValidationError, jsonschema.SchemaError) as error:
            print('Config fatal error:', error.args[0])
            sys.exit(0)
        self.config = EnvYAML(self.config_file)

    def connect_api(self):
        self.api = screepsapi.API(
            host=self.config['api_host'],
            prefix=self.config['api_prefix'],
            token=self.config['api_token'] if self.config['api_token'] else None,
            u=self.config['api_username'] if self.config['api_username'] else None,
            p=self.config['api_password'] if self.config['api_password'] else None,
            secure=self.config['api_secure'] if self.config['api_secure'] else None
        )

    def log(self, *args, **kwargs):
        use_sep = ('sep' in kwargs and kwargs['sep'] == '')
        spacer = ' ' if use_sep else ''
        time = datetime.now().strftime('[%H:%M:%S]' + spacer)
        print(time, *args, **kwargs)

    def get_room_data(self, shard, room, depositType):
        room_terrain_res = self.api.room_terrain(room=room, shard=shard, encoded=True)
        time.sleep(0.3)
        room_objects_res = self.api.room_objects(room=room, shard=shard)
        time.sleep(0.3)
        room_status_res = self.api.room_status(room=room, shard=shard)

        if self.config['verbose_logging']:
            self.log(f"Processing room {room} with status {room_status_res['room']['status']}...")
        return {
            'room': room,
            'terrain': room_terrain_res['terrain'][0]['terrain'],
            'objects': room_objects_res['objects'],
            'status': room_status_res['room']['status'],
            'bus': True,
            'depositType': depositType,
        }

    def run(self):
        shard = self.config['map_shard']
        data = {
            'description': self.config['map_description'],
            'rooms': [],
        }

        que = Queue()
        threads_list = list()

        worldsize_res = self.api.worldsize(shard=shard)
        world_width = worldsize_res['width']
        world_height = worldsize_res['height']

        for dy in range(world_height // 2):
            for dx in range(world_width // 2):
                rooms = [
                    (f"W{dx}N{dy}", "silicon"),
                    (f"E{dx}N{dy}", "metal"),
                    (f"W{dx}S{dy}", "biomass"),
                    (f"E{dx}S{dy}", "mist")
                ]
                for (room, depositType) in rooms:
                    t = Thread(target=lambda q, arg1, arg2, arg3: q.put(self.get_room_data(arg1, arg2, arg3)), args=(que, shard, room, depositType))
                    t.start()
                    threads_list.append(t)
                    time.sleep(1)

        for t in threads_list:
            t.join()

        while not que.empty():
            room_data = que.get()
            data['rooms'].append(room_data)
            
        if self.config['results_save_file']:
            with open(self.config['results_filename'], 'w') as file:
                json.dump(data, file, separators=(',', ':'))
            self.log(f"Results saved to {self.config['results_filename']}")

        self.log(f"Finished")

if __name__ == "__main__":
    downloader = ScreepsMapDownloader()
    downloader.run()