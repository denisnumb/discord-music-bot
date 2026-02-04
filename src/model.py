import discord
import asyncio
from threading import Thread, Event
from discord.ext.commands import Converter
from copy import deepcopy
from typing import List
from pathlib import Path
from locale_provider import LocaleKeys, translate


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
	def __init__(self, target, *, response_timeout: int, args=None, kwargs=None) -> None:
		super().__init__(target=target, args=args or (), kwargs=kwargs or {})
		self.__error_message = None
		self.__result = None
		self._done = Event()
		self.response_timeout = response_timeout

	def run(self) -> None:
		try:
			self.__result = self._target(*self._args, **self._kwargs)
		except Exception as e:
			self.__error_message = str(e)
		finally:
			self._done.set()

	def get_error_message(self) -> str | None:
		return self.__error_message

	async def wait_result_async(self):
		waited = 0
		while not self._done.is_set() and waited < self.response_timeout:
			await asyncio.sleep(0.05)
			waited += 0.05

		return self.__result

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


class InvalidPlayArgument(str):
	def __bool__(self):
		return False

class PlayObject:
	def __init__(self, url: str, title: str):
		self.url = url
		self.title = title

class TrackFile(PlayObject):
	def __init__(self, file_object: discord.Attachment):
		super().__init__(file_object.proxy_url, file_object.filename)
		self.source = None
		self.file_object = file_object

	async def save_temp(self, directory: Path) -> None:
		temp_file_path = directory / f'{self.file_object.id}.{self.title.split(".")[-1]}'
		await self.file_object.save(temp_file_path, use_cached=True)
		self.source = temp_file_path


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