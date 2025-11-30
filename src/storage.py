import json
import os
import discord
from pathlib import Path
from typing import Union, Dict
from music_client import MusicClient
from model import (
	LightContext, 
	Playlist, 
	Track
)


class Storage:
	__base_path = Path(__file__).resolve().parent 
	_saved_urls_path = __base_path.parent / 'data/saved_urls.json'
	_audio_cache_path = __base_path.parent / 'data/audio_cache.json'
	_dj_channels_path = __base_path.parent / 'data/dj_channels.json'
	_cookies_file_path = __base_path.parent / 'data/cookies.txt'

	music_clients: Dict[int, MusicClient] = {}
	saved_urls: Dict[int, Dict[str, str]] = {}
	audio_cache: Dict[str, Union[Track, Playlist]] = {}
	dj_channels: Dict[int, discord.TextChannel] = {}

	@classmethod
	def get_guild_saved_urls(cls, ctx: Union[discord.ApplicationContext, LightContext, discord.AutocompleteContext]) -> Dict[str, str]:
		guild_id = ctx.interaction.guild.id if isinstance(ctx, discord.AutocompleteContext) else ctx.guild.id

		if guild_id not in cls.saved_urls:
			cls.saved_urls[guild_id] = {}

		return cls.saved_urls[guild_id]

	@classmethod
	def prepare_path(cls) -> None:
		if not os.path.exists(directory := os.path.split(cls._saved_urls_path)[0]):
			os.mkdir(directory)

		for path in cls._saved_urls_path, cls._audio_cache_path, cls._dj_channels_path:
			if not os.path.exists(path):
				with open(path, 'w', encoding='utf-8') as file:
					json.dump({}, file)

	@classmethod
	async def save_urls(cls) -> None:
		cls.prepare_path()
		saved_urls = {str(guild_id): urls_data for guild_id, urls_data in cls.saved_urls.items()}
		with open(cls._saved_urls_path, 'w', encoding='utf-8') as file:
			file.write(json.dumps(saved_urls, indent=4, ensure_ascii=False))

	@classmethod
	async def save_audio_cache(cls) -> None:
		cls.prepare_path()
		cache_dict = {url: cache_item.get_dict() for url, cache_item in cls.audio_cache.items()}
		with open(cls._audio_cache_path, 'w', encoding='utf-8') as file:
			file.write(json.dumps(cache_dict, indent=4, ensure_ascii=False))

	@classmethod
	async def save_dj_channels(cls) -> None:
		cls.prepare_path()
		channels = {str(guild_id): channel.id for guild_id, channel in cls.dj_channels.items()}
		with open(cls._dj_channels_path, 'w', encoding='utf-8') as file:
			file.write(json.dumps(channels, indent=4, ensure_ascii=False))

	@classmethod
	async def load_urls(cls) -> None:
		cls.prepare_path()

		try:
			with open(cls._saved_urls_path, 'r', encoding='utf-8') as file:
				raw_saved_urls = json.load(file)
				cls.saved_urls = {
					int(guild_id): urls_data
					for guild_id, urls_data in raw_saved_urls.items()
				}
		except Exception as e:
			print(f'Ошибка при загрузке сохраненных ссылок из файла {cls._saved_urls_path}: {e}')

	@classmethod
	async def load_audio_cache(cls) -> None:
		cls.prepare_path()

		try:
			with open(cls._audio_cache_path, 'r', encoding='utf-8') as file:
				raw_audio_cache = json.load(file)

			for url, data in raw_audio_cache.items():
				if not data.get('entries'):
					cls.audio_cache[url] = Track(**data)
					continue
				
				cls.audio_cache[url] = Playlist(
					url=data.get('url'),
					title=data.get('title'),
					entries=[Track(**track_data) for track_data in data.get('entries')]
				)
		except Exception as e:
			print(f'Ошибка при загрузке кэша из файла {cls._audio_cache_path}: {e}')

	@classmethod
	async def load_dj_channels(cls, bot: discord.Bot) -> None:
		cls.prepare_path()

		try:
			with open(cls._dj_channels_path, 'r', encoding='utf-8') as file:
				raw_dj_channels = json.load(file)
			cls.dj_channels = {
				int(guild_id): bot.get_channel(channel_id)
				for guild_id, channel_id in raw_dj_channels.items()
			}	
		except Exception as e:
			print(f'Ошибка при загрузке кэша из файла {cls._audio_cache_path}: {e}')