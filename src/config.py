import os
import json
from typing import List

class Config:
    __base_path = os.path.dirname(os.path.realpath(__file__))
    _config_path = f'{__base_path}/config.json'

    token: str = ''
    guild_ids: List[int] = []
    playlistend: int = 100

    @classmethod
    def load_config(cls):
        with open(cls._config_path, 'r', encoding='utf-8') as config_file:
            data = json.load(config_file)
            cls.token = data['token']
            cls.guild_ids = data['guild_ids']
            cls.playlistend = data['playlistend']