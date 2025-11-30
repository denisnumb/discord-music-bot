import json
from pathlib import Path
from typing import List

class Config:
    __base_path = Path(__file__).resolve().parent 
    _config_path = __base_path.parent / 'config.json'

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