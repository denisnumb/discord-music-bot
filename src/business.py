import json
import os
import discord
import asyncio
from threading import Thread
from discord.ui import View, Button
from yt_dlp import YoutubeDL
from urllib.request import urlopen
from urllib.error import HTTPError
from typing import List, Union, Dict
from model import (
	LightContext, 
	Playlist, 
	Track, 
	TrackFile, 
	AddTrackTypes,
	YDL_OPTIONS, 
	FFMPEG_OPTIONS
)


class LoadingThread(Thread):
	def __init__(self, target, args=(), kwargs={}) -> None:
		super().__init__(target=target, args=args, kwargs=kwargs)
		self.result = None
		self.wait_time = 0

	def run(self) -> None:
		self.result = self._target(*self._args, **self._kwargs)

	async def join(self) -> None:
		while not self.result and self.wait_time < 30:
			await asyncio.sleep(.05)
			self.wait_time += .05
		return self.result

class MusicClient:
	def __init__(self, channel: discord.TextChannel=None) -> None:
		self.lock: asyncio.Lock = asyncio.Lock()
		self.channel: discord.TextChannel = channel
		self.voice_client: discord.VoiceClient = None
		self.queue: List[Union[Track, TrackFile]] = []
		self.track_index: int = 0
		self.message_player: MessagePlayer = MessagePlayer(self)
		self.__started: bool = False
		self.__intends_to_leave: bool = False

	@property
	def is_playing_or_paused(self) -> bool:
		return self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused())

	@property
	def is_paused(self) -> bool:
		return self.voice_client and self.voice_client.is_paused()
	
	@property
	def is_started(self) -> bool:
		return self.__started
	
	def start(self) -> None:
		self.__started = True

	def __voice_channels_are_equal(self, user: discord.Member) -> bool:
		return user.voice and user.voice.channel == self.voice_client.channel

	async def next(self, user: discord.Member) -> None:
		if not self.__voice_channels_are_equal(user):
			return
		if self.track_index + 1 >= len(self.queue):
			self.track_index = -1
		self.voice_client.stop()
		await self.channel.send(embed=discord.Embed(description=f'{user.mention} переключает трек ⏩', colour=discord.Color.gold()), delete_after=60)

	async def previous(self, user: discord.Member) -> None:
		if not self.__voice_channels_are_equal(user):
			return
		self.track_index -= 2
		if self.track_index < -1:
			self.track_index = -1
		self.voice_client.stop()
		await self.channel.send(embed=discord.Embed(description=f'{user.mention} переключает трек ⏪', colour=discord.Color.gold()), delete_after=60)

	async def pause(self, user: discord.Member) -> bool:
		if not self.__voice_channels_are_equal(user):
			return False
		self.voice_client.resume() if self.is_paused else self.voice_client.pause()
		await discord.utils.get(user.guild.members, id=self.voice_client.client.user.id).edit(mute=self.is_paused)
		return True

	async def stop(self, user: discord.Member) -> None:
		if not self.__voice_channels_are_equal(user):
			return False
		await self.reset()
		await self.channel.send(embed=discord.Embed(description=f'{user.mention} отключил бота от голосового канала ❌', colour=discord.Color.red()))

	async def _prepare_sound_source(self) -> str:
		current_track = self.queue[self.track_index]
		sound_source = None

		try:
			sound_source = current_track.source
			urlopen(sound_source)
		except (HTTPError, AttributeError):
			if not isinstance(current_track, TrackFile):
				with YoutubeDL(YDL_OPTIONS) as ydl:
					sound_source = ydl.extract_info(current_track.url, download=False)['url']
					current_track.source = sound_source

		return sound_source

	async def play_music(self, ctx: Union[discord.ApplicationContext, LightContext]):
		if self.is_started:
			return await self.message_player.update()

		self.start()
		excepted = 0

		while len(self.queue) > self.track_index and excepted < 3:
			await self.message_player.update()
			await discord.utils.get(ctx.guild.members, id=self.voice_client.client.user.id).edit(mute=False)

			try:
				sound_source = await self._prepare_sound_source()
				self.voice_client.play(discord.FFmpegPCMAudio(source=sound_source, **FFMPEG_OPTIONS))
			except Exception:
				await self.channel.send(embed=discord.Embed(description=f'При попытке воспроизведения трека возникла ошибка!', colour=discord.Color.red()), delete_after=10)
				excepted += 1
				self.voice_client.stop()

			while self.is_playing_or_paused:
				await asyncio.sleep(1)
			self.track_index += 1
		
		await self.reset()

	async def leave_the_channel_with_timeout(self, bot_member: discord.Member):
		if self.__intends_to_leave:
			return
		self.__intends_to_leave = True

		for _ in range(30):
			await asyncio.sleep(10)
			if not bot_member.voice or bot_member.voice and len(bot_member.voice.channel.members) > 1:
				break
		else:
			await self.reset()

		self.__intends_to_leave = False

	async def reset(self, *, force: bool=False) -> None:
		if self.voice_client:
			self.voice_client.stop()
			await self.voice_client.disconnect(force=force)
			
		self.voice_client = None
		self.queue = []
		self.track_index = 0
		self.__started = False
		await self.message_player.delete()

class MessagePlayerButton(Button):
	def __init__(self, emoji: str) -> None:
		super().__init__(emoji=emoji, custom_id=emoji, style=discord.ButtonStyle.blurple)

class MessagePlayerView(View):
	def __init__(self, music_client: MusicClient) -> None:
		self.music_client = music_client
		self.pause_button = MessagePlayerButton('▶️' if music_client.is_paused else '⏸')
		prev_button = MessagePlayerButton('⏪')
		stop_button = MessagePlayerButton(emoji='⏹')
		next_button = MessagePlayerButton(emoji='⏩')

		buttons = (prev_button, self.pause_button, stop_button, next_button)
		for button in buttons:
			button.callback = self.callback

		super().__init__(*buttons, timeout=None)

	async def callback(self, interaction: discord.Interaction) -> None:
		match interaction.custom_id:
			case '▶️' | '⏸':
				if await self.music_client.pause(interaction.user):
					self.pause_button.emoji = '▶️' if self.music_client.is_paused else '⏸'
					return await interaction.response.edit_message(view=self)
			case '⏪':
				await self.music_client.previous(interaction.user)
			case '⏹':
				await self.music_client.stop(interaction.user)
			case '⏩':
				await self.music_client.next(interaction.user)
		try:
			await interaction.response.defer()
		except:
			pass

class MessagePlayer:
	def __init__(self, music_client: MusicClient):
		self.music_client = music_client
		self.__message: discord.Message = None

	@staticmethod
	def get_track_link_title(track: Union[Track, Playlist, TrackFile]) -> str:
		if isinstance(track, TrackFile):
			return track.title
		return f'[{track.title}]({track.url})'

	async def update(self) -> None:
		async with self.music_client.lock:
			await self._update()

	async def delete(self) -> None:
		try:
			await self.__message.delete()
		except:
			pass

	async def _update(self):
		if not any((self.music_client.voice_client, self.music_client.queue)):
			return

		queue = self.music_client.queue
		track_index = self.music_client.track_index

		await self.delete()
		this_track_info = self.get_track_link_title(queue[track_index])
		next_track_info = (
			self.get_track_link_title(queue[track_index+1]) 
			if track_index+1 < len(queue) else '*Конец очереди*'
		)
		
		self.__message = await self.music_client.channel.send(
			embed=discord.Embed(
				description=f'**Сейчас играет: {this_track_info}**\nСледующий трек: {next_track_info}',
				colour=discord.Color.from_rgb(0, 239, 255)
				), 
			view=MessagePlayerView(self.music_client)
		)

class ChoicePlayOptionView(View):
	def __init__(self, timeout: int=15):
		add_button = Button(
			custom_id=str(AddTrackTypes.ADD),
			label='Добавить в очередь', 
			style=discord.ButtonStyle.green
		)
		insert_button = Button(
			custom_id=str(AddTrackTypes.INSERT),
			label='Добавить вне очереди', 
			style=discord.ButtonStyle.green
		)
		mix_with_queue_button = Button(
			custom_id=str(AddTrackTypes.MIX_WITH_QUEUE),
			label='Перемешать с другими треками в очереди', 
			style=discord.ButtonStyle.green
		)
		cancel_button = Button(
			custom_id=str(AddTrackTypes.CANCEL),
			label='Отмена', 
			style=discord.ButtonStyle.red
		)
		self.result = None

		buttons = (add_button, insert_button, mix_with_queue_button, cancel_button)
		for button in buttons:
			button.callback = self.callback
		super().__init__(*buttons, timeout=timeout)

	async def on_timeout(self) -> None:
		self.result = AddTrackTypes.ADD

	async def callback(self, interaction: discord.Interaction) -> None:
		self.result = int(interaction.custom_id)

	async def wait_result(self) -> int:
		while self.result == None:
			await asyncio.sleep(.05)
		await self.message.delete()
		return self.result

class AskYesNoView(View):
	def __init__(self, timeout: int=60) -> None:
		self.yes_button = Button(label='Да', style=discord.ButtonStyle.green)
		self.no_button = Button(label='Нет', style=discord.ButtonStyle.red)
		self.yes_button.callback = lambda _: self.set_result(True)
		self.no_button.callback = lambda _: self.set_result(False)
		self.result = None
		super().__init__(self.yes_button, self.no_button, timeout=timeout)

	async def on_timeout(self) -> None:
		self.result = False

	async def set_result(self, value: bool) -> None:
		self.result = value

	async def wait_result(self) -> bool:
		while self.result == None:
			await asyncio.sleep(.05)
		await self.message.delete()
		return self.result

class Storage:
	__base_path = os.path.dirname(os.path.realpath(__file__))
	_saved_urls_path = f'{__base_path}/data/saved_urls.json'
	_audio_cache_path = f'{__base_path}/data/audio_cache.json'
	_dj_channels_path = f'{__base_path}/data/dj_channels.json'
	_cookies_file_path = f'{__base_path}/data/cookies.txt'

	music_clients: Dict[int, MusicClient] = {}
	saved_urls: Dict[str, str] = {}
	audio_cache: Dict[str, Union[Track, Playlist]] = {}
	dj_channels: Dict[int, discord.TextChannel] = {}

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
		with open(cls._saved_urls_path, 'w', encoding='utf-8') as file:
			file.write(json.dumps(cls.saved_urls, indent=4, ensure_ascii=False))

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
				cls.saved_urls = json.load(file)
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