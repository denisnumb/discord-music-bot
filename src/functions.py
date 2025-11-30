import re
import json
import discord
from urllib.request import urlopen
from urllib.parse import urlencode
from yt_dlp import YoutubeDL
from typing import Union, Set, List
from music_client import MusicClient
from storage import Storage
from views import AskYesNoView
from model import (
    PlayEmbedTypes,
	TrackFile, 
    Playlist, 
    ErrorPlayArgument,
    YDL_OPTIONS,
	LightContext
)


def get_music_client(guild: discord.Guild) -> MusicClient:
	if guild.id not in Storage.music_clients.keys():
		Storage.music_clients[guild.id] = MusicClient(Storage.dj_channels.get(guild.id))
	return Storage.music_clients[guild.id]

async def get_tracknames(ctx) -> Set[str]:
	key = ctx.options.get('name') or ctx.options.get('url_or_name')
	return {name for name in list(Storage.get_guild_saved_urls(ctx)) if name.startswith(key)}

def get_data_type(is_playlist: bool) -> str:
	return PlayEmbedTypes.PLAYLIST if is_playlist else PlayEmbedTypes.VIDEO

async def get_embed_data(music_client: MusicClient, insert: bool, mix_with_queue: bool, data_type: str) -> str:
	if music_client.is_playing_or_paused:
		if insert and not mix_with_queue:
			return f'добавляет вне очереди {data_type}', discord.Color.purple()
		elif mix_with_queue:
			return f'перемешивает с очередью {data_type}', discord.Color.gold()
		else:
			return f'добавляет в очередь {data_type}', discord.Color.gold()
	return f'включает {data_type}', discord.Color.green()

async def send_load_video_error(ctx, video_url: str, loading_message=None) -> None:
	if loading_message:
		await delete_message(loading_message)
	arg_data = f'[**трека**]({video_url})' if video_url.startswith('http') else f'`{video_url}`'
	await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention}, не удалось получить данные для {arg_data}!', colour=discord.Color.red()), delete_after=60)


async def prepare_request(ctx: Union[discord.ApplicationContext, LightContext], message_content: str, audio_files: List[TrackFile]) -> str:
	request = message_content
	filenames = ', '.join(file.title for file in audio_files)

	if not request or request.isspace():
		return filenames
	if (play_object := Storage.audio_cache.get(Storage.get_guild_saved_urls(ctx).get(request) or request)):
		request = play_object.title
	if audio_files:
		request += f' и {filenames}'
	
	return request

def is_playlist_url(url: str) -> bool:
	if url in Storage.audio_cache:
		return isinstance(Storage.audio_cache[url], Playlist)
	if 'yandex' in url:
		return not 'track' in url
	return any(map(lambda x: x in url, ('/playlist', '/channel', '@', '/videos'))) or any(map(lambda x: url.endswith(x), ('/videos', '/shorts')))

def parse_video_url(ctx: Union[discord.ApplicationContext, LightContext], url_or_name: str) -> str:
	saved_urls = Storage.get_guild_saved_urls(ctx)
	
	if url_or_name in saved_urls:
		return saved_urls[url_or_name]
	elif not url_or_name.startswith('http') and url_or_name and not url_or_name.isspace():
		with YoutubeDL(YDL_OPTIONS) as ydl:
			info = ydl.extract_info(f'ytsearch:{url_or_name}', download=False)
		return 'https://youtu.be/' + info['entries'][0]['id'] if (info and info['entries']) else ErrorPlayArgument(url_or_name)
	return prepare_url(url_or_name)

def get_youtube_video_id(url: str) -> str:
	pattern = r'(?:https?:\/\/)?(?:[0-9A-Z-]+\.)?(?:youtube|youtu|youtube-nocookie)\.(?:com|be)\/(?:watch\?v=|watch\?.+&v=|embed\/|v\/|.+\?v=)?([^&=\n%\?]{11})'
	return re.findall(pattern, url, re.MULTILINE | re.IGNORECASE)[0]

def get_youtube_playlist_id(url: str) -> str:
	return re.findall('[&?]list=([^&]+)', url)[0]

def prepare_url(url: str) -> str:
	if not re.search('youtu|youtube', url):
		return url
	if is_playlist_url(url):
		if not '/playlist' in url:
			return url
		return 'https://www.youtube.com/playlist?list='+get_youtube_playlist_id(url)

	result = 'https://youtu.be/' + get_youtube_video_id(url)
	if len(timecode := re.findall('[?|&]t=\d{1,}', url)):
		result += timecode[0]
	return result

def get_video_title(url: str) -> str:
	if is_playlist_url(url):
		if url in Storage.audio_cache:
			return f'{Storage.audio_cache[url].title} (Плейлист)'
		return url
	try:
		pattern = r'(?:https?:\/\/)?(?:[0-9A-Z-]+\.)?(?:youtube|youtu|youtube-nocookie)\.(?:com|be)\/(?:watch\?v=|watch\?.+&v=|embed\/|v\/|.+\?v=)?([^&=\n%\?]{11})'
		video_id = re.findall(pattern, url, re.MULTILINE | re.IGNORECASE)
		params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % video_id[0]}
		url = "https://www.youtube.com/oembed"
		query_string = urlencode(params)
		url = url + "?" + query_string

		with urlopen(url) as response:
			response_text = response.read()
			data = json.loads(response_text.decode())

		return data['title']
	except:
		return 'Не удалось получить название :('

async def ask_yes_no(channel: discord.TextChannel, question: str, timeout: int=60):
	view = AskYesNoView(timeout)
	await channel.send(question, view=view)
	return await view.wait_result()

async def delete_message(message: Union[discord.Message, discord.Interaction], timeout: int=0) -> None:
	if timeout == None:
		return
	try:
		if isinstance(message, discord.Interaction):
			return await message.delete_original_response(delay=timeout)
		await message.delete(delay=timeout)
	except Exception as e:
		print(f'Ошибка при удалении сообщения: {e}')