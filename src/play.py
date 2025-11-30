import discord
import random
from typing import Union, List
from yt_dlp import YoutubeDL
from storage import Storage
from music_client import MusicClient
from views import ChoicePlayOptionView
from model import (
	Track,
	TrackFile,
	Playlist,
	LightContext,
	AddTrackTypes,
	PlayEmbedTypes,
	YDL_OPTIONS,
	LoadingThread
)
from functions import (
	get_data_type,
	get_embed_data,
	get_music_client,
	is_playlist_url,
	parse_video_url,
	delete_message,
	ask_yes_no,
	send_load_video_error,
	prepare_request
)


async def try_connect(ctx: Union[discord.ApplicationContext, LightContext]) -> bool:
	try:
		get_music_client(ctx.guild).voice_client = await ctx.author.voice.channel.connect()
		return True
	except Exception as e:
		mc = get_music_client(ctx.guild)
		await mc.reset(force=True)
		await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention}, не удалось подключиться к голосовому каналу! {e}', colour=discord.Color.red()), delete_after=60)
		return False

async def add_tracks_to_queue(
	music_client: MusicClient, 
	tracks: Union[List[Union[Track, TrackFile]], Union[Track, TrackFile]], 
	insert: bool, 
	mix_with_queue: bool
	) -> None:
	queue = music_client.queue
	track_index = music_client.track_index
	
	if not isinstance(tracks, list):
		tracks = [tracks]
	
	if mix_with_queue:
		updated_queue = queue[track_index+2:] + tracks
		random.shuffle(updated_queue)
		music_client.queue = queue[:track_index+2] + updated_queue
	elif insert:
		music_client.queue = queue[:track_index+1] + tracks + queue[track_index+1:]
	else:
		music_client.queue += tracks

def create_play_object(yt_dlp_data: dict) -> Union[Track, Playlist]:
	if not yt_dlp_data:
		return
	
	is_playlist = yt_dlp_data.get('_type') == 'playlist'

	if not is_playlist:
		return Track(
			url=yt_dlp_data.get('original_url'),
			title=yt_dlp_data.get('title'),
			source=yt_dlp_data.get('url')
		)

	entries = yt_dlp_data.get('entries')
	while entries[0] and 'entries' in entries[0].keys():
		entries = entries[0].get('entries')

	if len(entries) == 0:
		raise ValueError(f'По данной ссылке нечего проигрывать')

	playlist_entries = [
		Track(
			url=video.get('original_url'), 
			title=video.get('title'),
			source=video.get('url')
		) 
		for video in entries if video
	]

	return Playlist(
		url=yt_dlp_data.get('original_url'),
		title=yt_dlp_data.get('title'),
		entries=playlist_entries
	)

def create_play_object_wrapper(url: str) -> Union[Track, Playlist] | None:
	with YoutubeDL(YDL_OPTIONS) as ydl:
		try:
			return create_play_object(ydl.extract_info(url, download=False))
		except Exception as e:
			print(f'Не удалось получить данные для ссылки [{url}]: {e}')

async def get_play_object_by_url(url: str) -> Union[Track, Playlist] | None:
	if url not in Storage.audio_cache:
		t = LoadingThread(target=create_play_object_wrapper, args=(url,))
		t.start()
		play_object = await t.join()

		if not play_object:
			return

		Storage.audio_cache[url] = play_object
		await Storage.save_audio_cache()
	
	return Storage.audio_cache[url]

async def choice_play_option(message: discord.Message, request: str) -> int:
	view = ChoicePlayOptionView()
	await message.channel.send(
		f'{message.author.mention}, как добавить запрос `{request}` в очередь?', 
		view=view
	)
	return await view.wait_result()

async def ask_to_mix_request(message: discord.Message):
	return await ask_yes_no(
		message.channel, 
		f'{message.author.mention}, перемешать треки в плейлисте?',
		7
	)

async def ask_to_find_video(message: discord.Message):
	return await ask_yes_no(
		message.channel,
		f'{message.author.mention}, выполнить поиск трека по запросу `{message.content}`?',
		10
	)

async def play_from_message(message: discord.Message):
	insert, mix, mix_with_queue = False, False, False

	args = [x for x in message.content.split(',') if x]
	audio_files = []
	if message.attachments:
		audio_files = [
			TrackFile(file.url, file.filename) 
			for file in message.attachments 
			if any(map(lambda x: x in file.content_type, ('audio', 'video')))
		]

	if not audio_files and not args:
		return

	call_play_list = len(args) + len(audio_files) > 1
	
	ctx = LightContext(message.author, message.channel, message.guild)
	mc = get_music_client(ctx.guild)

	if audio_files or message.content.startswith('http') or message.content in Storage.get_guild_saved_urls(ctx) or call_play_list:
		if call_play_list or is_playlist_url(parse_video_url(ctx, message.content)):
			mix = await ask_to_mix_request(message)
	elif not await ask_to_find_video(message):
		return

	if mc.is_playing_or_paused and mc.track_index < len(mc.queue)-1:
		request = await prepare_request(ctx, message.content, audio_files)
		play_option = await choice_play_option(message, request)
		if play_option == AddTrackTypes.CANCEL:
			return
		insert = play_option == AddTrackTypes.INSERT
		mix_with_queue = play_option == AddTrackTypes.MIX_WITH_QUEUE

	if call_play_list:
		return await play_list(ctx, message.content, audio_files, insert, mix, mix_with_queue)
	if not args and len(audio_files) == 1:
		return await play_from_file(ctx, audio_files[0], insert, mix_with_queue)
	await play(ctx, message.content, insert, mix, mix_with_queue)

async def play_from_file(
	ctx: Union[discord.ApplicationContext, LightContext],
	file: TrackFile,
	insert: bool,
	mix_with_queue: bool
) -> None:
	await delete_message(ctx)
	mc = get_music_client(ctx.guild)
	dj_channel = Storage.dj_channels[ctx.guild.id]

	await add_tracks_to_queue(mc, file, insert, mix_with_queue)

	message_text, embed_color = await get_embed_data(mc, insert, mix_with_queue, PlayEmbedTypes.FILE)
	play_message = await dj_channel.send(embed=discord.Embed(description=f'{ctx.author.mention} {message_text}\n\n**{file.title}**', colour=embed_color))

	if not mc.voice_client and not await try_connect(ctx):
		return await delete_message(play_message)

	await mc.play_music(ctx)

async def play_list(
	ctx: Union[discord.ApplicationContext, LightContext], 
	urls_or_names: str, 
	files: List[TrackFile],
	insert: bool, 
	mix: bool, 
	mix_with_queue: bool
	) -> None:
	args = [parse_video_url(ctx, x.strip()) for x in urls_or_names.split(',') if x]
	args_without_empty = [arg for arg in args if arg]
	
	if len(args_without_empty) == 1 and not files:
		return await play(ctx, args_without_empty[0], insert, mix, mix_with_queue)
	if len(files) == 1 and not args_without_empty:
		return await play_from_file(ctx, files[0], insert, mix_with_queue)

	mc = get_music_client(ctx.guild)
	dj_channel = Storage.dj_channels[ctx.guild.id]

	quick_start = f'\n\nБыстрый запуск: {urls_or_names}' if urls_or_names else ''
	message_text, _ = await get_embed_data(mc, insert, mix_with_queue, PlayEmbedTypes.PLAY_LIST)
	play_list_message = await dj_channel.send(embed=discord.Embed(description=f'{ctx.author.mention} {message_text}\n\n*(Названия и треки загружаются)*{quick_start}', colour=discord.Color.default()))

	entries_count = len(args) + len(files)
	track_titles = []
	temp_queue: List[Union[Track, TrackFile]] = []
	error_args = []
	nl = '\n'
	
	for i, url in enumerate(args, 1):
		play_object = await get_play_object_by_url(url)
		if not play_object:
			error_args.append(url)
			continue

		playlist_mark = '' if not isinstance(play_object, Playlist) else ' *(Плейлист)*'
		track_titles.append(f'[{play_object.title}]({play_object.url}){playlist_mark}')
		if isinstance(play_object, Playlist):
			temp_queue += play_object.entries
		else:
			temp_queue.append(play_object)

		await play_list_message.edit(embed=discord.Embed(description=f'{ctx.author.mention} {message_text}\n\n*(Названия и треки загружаются)* **[{i}/{entries_count}]**{quick_start}', colour=discord.Color.default()))
	
	for i, file in enumerate(files, 1):
		track_titles.append(f'{file.title} *(Файл)*')
		temp_queue.append(file)
		await play_list_message.edit(embed=discord.Embed(description=f'{ctx.author.mention} {message_text}\n\n*(Названия и треки загружаются)* **[{i+len(args)}/{entries_count}]**{quick_start}', colour=discord.Color.default()))

	if len(error_args) > 0:
		await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention}, возникла ошибка при получении данных для:\n\n**{nl.join(error_args)}**', colour=discord.Color.red()), delete_after=60)
	if len(track_titles) == 0:
		await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention}, не удалось получить трек ни из одного из указанных значений', colour=discord.Color.red()), delete_after=10)
		return await play_list_message.delete()

	if mix:
		random.shuffle(temp_queue)
	await add_tracks_to_queue(mc, temp_queue, insert, mix_with_queue)

	lendth = len(''.join(track_titles))
	if lendth > 1700:
		track_titles = track_titles[:10]
		track_titles.append('...')

	if not mc.voice_client and not await try_connect(ctx):
		return await delete_message(play_list_message)

	message_text, embed_color = await get_embed_data(mc, insert, mix_with_queue, PlayEmbedTypes.PLAY_LIST)
	await play_list_message.edit(embed=discord.Embed(description=f'{ctx.author.mention} {message_text}\n\n**{nl.join(track_titles)}**{quick_start}', colour=embed_color))
	
	await mc.play_music(ctx)

async def play(
	ctx: Union[discord.ApplicationContext, LightContext], 
	url_or_name: str, 
	insert: bool, 
	mix: bool, 
	mix_with_queue: bool
	) -> None:
	mc = get_music_client(ctx.guild)
	dj_channel = Storage.dj_channels[ctx.guild.id]

	if len([x for x in url_or_name.split(',') if x]) > 1:
		return await play_list(ctx, url_or_name, insert, mix, mix_with_queue)

	track_url = parse_video_url(ctx, url_or_name)
	if not track_url:
		return await send_load_video_error(ctx, url_or_name)

	is_playlist = is_playlist_url(track_url)
	message_text, _ = await get_embed_data(mc, insert, mix_with_queue, get_data_type(is_playlist))
	play_message = await dj_channel.send(embed=discord.Embed(description=f'{ctx.author.mention} {message_text}\n\n*(Загрузка займет некоторое время)*', colour=discord.Color.default()))
	
	play_object = await get_play_object_by_url(track_url)
	if not play_object:
		return await send_load_video_error(ctx, track_url, loading_message=play_message)

	if isinstance(play_object, Playlist):
		playlist_videos = list(play_object.entries)
		if mix:
			random.shuffle(playlist_videos)
		await add_tracks_to_queue(mc, playlist_videos, insert, mix_with_queue)
	else:
		await add_tracks_to_queue(mc, play_object, insert, mix_with_queue)

	message_text, embed_color = await get_embed_data(mc, insert, mix_with_queue, get_data_type(isinstance(play_object, Playlist)))
	saved_urls = Storage.get_guild_saved_urls(ctx)
	quick_start_names = [name for name in saved_urls if saved_urls[name] == play_object.url]
	quick_start = '' if not quick_start_names else f'\n\nБыстрый запуск: {" / ".join(quick_start_names)}'
	data_title = f'[{play_object.title}]({play_object.url})'
	await play_message.edit(embed=discord.Embed(description=f'{ctx.author.mention} {message_text}\n\n**{data_title}**{quick_start}', colour=embed_color))

	if not mc.voice_client and not await try_connect(ctx):
		return await delete_message(play_message)

	await mc.play_music(ctx)