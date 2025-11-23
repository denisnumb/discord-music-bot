import discord
from discord.ext.commands import Converter
from copy import deepcopy
from typing import List
from config import Config

YDL_OPTIONS = {
	'format': 'bestaudio/best', 
	'forcetitle': True, 
	'quiet': True, 
	'playlistend': Config.playlistend, 
	'cookiefile': 'data/cookies.txt', 
	'ignoreerrors': True
}

FFMPEG_OPTIONS = {
	'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
	'options': '-vn'
}

class PlayEmbedTypes:
	VIDEO = 'трек'
	PLAYLIST = 'плейлист'
	PLAY_LIST = 'список треков'
	FILE = 'файл'

class AddTrackTypes:
	ADD = 0
	INSERT = 1
	MIX_WITH_QUEUE = 2
	CANCEL = -1

class CustomBoolArgument(Converter):
    async def convert(cls, ctx, arg):
        return arg == cls.choices[0]

class PlayInsertArg(CustomBoolArgument):
    choices = ('Воспроизвести трек/плейлист следующим (вне очереди)', 'Добавить трек/плейлист в очередь')
class PlayMixArg(CustomBoolArgument):
    choices = ('Перемешать треки между собой', )
class PlayMixWithQueueArg(CustomBoolArgument):
	choices = ('Перемешать треки с другими треками в очереди', )

class LightContext:
	def __init__(
        self, 
        author: discord.Member, 
        channel: discord.TextChannel, 
        guild: discord.Guild
        ) -> None:
		self.author = author
		self.channel = channel
		self.guild = guild

	async def delete(self, delay: int=0) -> None:
		pass

	async def send(self, content=None, **kwargs):
		return await self.channel.send(content, **kwargs)

	async def respond(self, content=None, **kwargs):
		return await self.channel.send(content, **kwargs)


class ErrorPlayArgument(str):
	def __bool__(self):
		return False

class PlayObject:
	def __init__(self, url: str, title: str):
		self.url = url
		self.title = title

class TrackFile(PlayObject):
	def __init__(self, url: str, title: str):
		super().__init__(url, title)
		self.source = url

class Track(PlayObject):
	def __init__(self, url: str, title: str, source: str=None):
		super().__init__(url, title)
		self.source = source

	def get_dict(self) -> dict:
		dict_to_save = self.__dict__.copy()
		dict_to_save.pop('source')
		return dict_to_save

class Playlist(PlayObject):
	def __init__(self, url: str, title: str, entries: List[Track]=None):
		super().__init__(url, title)
		self.entries: List[Track] = entries or []

	def get_dict(self) -> dict:
		cache_item_dict = deepcopy(self.__dict__)
		cache_item_dict['entries'] = [track.get_dict() for track in self.entries]
		return cache_item_dict