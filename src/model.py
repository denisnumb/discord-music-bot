import discord
import asyncio
from threading import Thread
from discord.ext.commands import Converter
from copy import deepcopy
from typing import List
from config import Config
from locale_provider import LocaleKeys, translate


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
	VIDEO = translate(LocaleKeys.Label.track)
	PLAYLIST = translate(LocaleKeys.Label.playlist)
	PLAY_LIST = translate(LocaleKeys.Label.track_list)
	FILE = translate(LocaleKeys.Label.file)

class AddTrackTypes:
	ADD = 0
	INSERT = 1
	MIX_WITH_QUEUE = 2
	CANCEL = -1

class CustomBoolArgument(Converter):
    async def convert(cls, ctx, arg):
        return arg == cls.choices[0]

class PlayInsertArg(CustomBoolArgument):
    choices = (translate(LocaleKeys.Label.insert), translate(LocaleKeys.Label.not_insert))
class PlayMixArg(CustomBoolArgument):
    choices = (translate(LocaleKeys.Label.mix), )
class PlayMixWithQueueArg(CustomBoolArgument):
	choices = (translate(LocaleKeys.Label.mix_with_queue), )

class LoadingThread(Thread):
	def __init__(self, target, args=(), kwargs={}) -> None:
		super().__init__(target=target, args=args, kwargs=kwargs)
		self.result = None
		self.wait_time = 0

	def run(self) -> None:
		self.result = self._target(*self._args, **self._kwargs)

	async def join(self) -> None:
		while not self.result and self.wait_time < 180:
			await asyncio.sleep(.05)
			self.wait_time += .05
		return self.result

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