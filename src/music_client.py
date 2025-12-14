import discord
import asyncio
from yt_dlp import YoutubeDL
from urllib.request import urlopen
from urllib.error import HTTPError
from typing import List, Union
from discord.ui import View, Button
from locale_provider import LocaleKeys, translate
from model import (
	LightContext, 
	Track, 
	TrackFile, 
	YDL_OPTIONS, 
	FFMPEG_OPTIONS
)
from model import (
	Playlist, 
	Track, 
	TrackFile
)


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
		await self.channel.send(embed=discord.Embed(description=translate(LocaleKeys.Info.user_play_next, user.mention), colour=discord.Color.gold()), delete_after=60)

	async def previous(self, user: discord.Member) -> None:
		if not self.__voice_channels_are_equal(user):
			return
		self.track_index -= 2
		if self.track_index < -1:
			self.track_index = -1
		self.voice_client.stop()
		await self.channel.send(embed=discord.Embed(description=translate(LocaleKeys.Info.user_play_prev, user.mention), colour=discord.Color.gold()), delete_after=60)

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
		await self.channel.send(embed=discord.Embed(description=translate(LocaleKeys.Info.user_play_stop, user.mention), colour=discord.Color.red()))

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
				await self.channel.send(embed=discord.Embed(description=translate(LocaleKeys.Info.track_play_error), colour=discord.Color.red()), delete_after=10)
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
			if track_index+1 < len(queue) else translate(LocaleKeys.Label.end_of_queue)
		)
		
		self.__message = await self.music_client.channel.send(
			embed=discord.Embed(
				description=translate(LocaleKeys.Label.music_player_info, this_track_info, next_track_info),
				colour=discord.Color.from_rgb(0, 239, 255)
				), 
			view=MessagePlayerView(self.music_client)
		)

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