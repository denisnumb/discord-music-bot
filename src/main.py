import os
import discord
from discord import Option
from config import Config
from business import Storage
from model import (
	TrackFile,
	Playlist, 
	PlayInsertArg, 
	PlayMixArg, 
	PlayMixWithQueueArg
)
from functions import (
	delete_message, 
	get_music_client, 
	get_video_title,
	get_tracknames,
	is_playlist_url,
	prepare_url
)
from play import (
	play_from_message, 
	play, 
	play_list,
	play_from_file,
	get_play_object_by_url
)


Config.load_config()

bot = discord.Bot(intents=discord.Intents.all())
guild_ids = Config.guild_ids

is_bot_started = False

@bot.event
async def on_ready() -> None:
	global is_bot_started

	if is_bot_started:
		return
	is_bot_started = True

	await Storage.load_urls()
	await Storage.load_audio_cache()
	await Storage.load_dj_channels(bot)

	print('Bot started')


@bot.event
async def on_message(message: discord.Message) -> None:
	if message.author == bot.user:
		return
	if message.channel in Storage.dj_channels.values():
		await delete_message(message)
		if message.author.voice:
			await play_from_message(message)


@bot.event
async def on_voice_state_update(
	member: discord.Member, 
	before: discord.VoiceState, 
	after: discord.VoiceState
	) -> None:
	# отключить бота от голосового канала, если никого нет
	bot_member = discord.utils.get(member.guild.members, id=bot.user.id)
	if bot_member.voice and len(bot_member.voice.channel.members) == 1:
		music_client = get_music_client(bot_member.guild)
		await music_client.leave_the_channel_with_timeout(bot_member)


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error) -> None:
	print(f'Ошибка при выполнении команды {ctx.command.qualified_name}: {error}')
	await ctx.send(
		embed=discord.Embed(
			description=f'{ctx.author.mention}, при выполнении команды `{ctx.command.qualified_name}` произошла ошибка!', 
			colour=discord.Color.red()
			), 
		delete_after=10
	)

@bot.slash_command(
	name='set_dj_channel', 
	description='Устанавливает на сервере канал для включения музыки', 
	guild_ids=guild_ids
)
async def set_dj_channel(
	ctx: discord.ApplicationContext,
	channel: discord.Option(discord.TextChannel, 'Канал для включения музыки', required=True, default=None)
	) -> None:
	if not channel:
		channel = ctx.channel

	Storage.dj_channels[ctx.guild.id] = channel

	await ctx.respond(
		f'{ctx.author.mention}, канал {channel.mention} установлен как канал для включения музыки.',
		ephemeral=True,
		delete_after=30
	)
	await Storage.save_dj_channels()

@bot.slash_command(
	name='remove_dj_channel', 
	description='Отключает канал для проигрывания музыки', 
	guild_ids=guild_ids
)
async def remove_dj_channel(
	ctx: discord.ApplicationContext
	) -> None:
	if ctx.guild.id in Storage.dj_channels:
		channel = Storage.dj_channels.pop(ctx.guild.id)
		await Storage.save_dj_channels()
		return await ctx.respond(f'{ctx.author.mention}, канал {channel.mention} больше не является каналом для проигрывания музыки.', ephemeral=True, delete_after=15)

@bot.slash_command(name='play', description='Воспроизводит видео или плейлист(ы) по названию быстрого запуска или названию/ссылке', guild_ids=guild_ids)
async def _play(
	ctx: discord.ApplicationContext, 
	url_or_name: Option(str, "Ссылка или название (можно указать несколько через запятую)", required=False, defailt=None, autocomplete=get_tracknames), 
	file: Option(discord.Attachment, 'Аудио файл', required=False, default=None),
	insert: Option(PlayInsertArg, "Добавить трек вне очереди", choices=PlayInsertArg.choices, required=False, default=False),
	mix: Option(PlayMixArg, "Перемешать треки в списке", choices=PlayMixArg.choices, required=False, default=False),
	mix_with_queue: Option(PlayMixWithQueueArg, "Перемешать треки с очередью", choices=PlayMixWithQueueArg.choices, required=False, default=False)
	):
	if not await check_dj_channel(ctx):
		return
	if not ctx.author.voice:
		return await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, войдите в голосовой канал, нужно поговорить!', colour=discord.Color.red()), ephemeral=True, delete_after=15)
	
	if file:
		file = (None if not any(map(lambda x: x in file.content_type, ('audio', 'video')))
			else TrackFile(file.url, file.filename))

	if not any((url_or_name, file)):
		return await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, укажите ссылку, введите название или прикрепите файл!', colour=discord.Color.red()), ephemeral=True, delete_after=15)

	await delete_message(ctx)

	if url_or_name and file:
		return await play_list(ctx, url_or_name, [file], insert, mix, mix_with_queue)
	if not url_or_name and file:
		return await play_from_file(ctx, file, insert, mix_with_queue)
	await play(ctx, url_or_name, insert, mix, mix_with_queue)

@bot.slash_command(name='clear_music_cache', description='Удаляет конкретный или все треки, сохраненные в кэше', guild_ids=guild_ids)
async def _clear_music_cache(ctx: discord.ApplicationContext, url_or_name: Option(str, 'Ссылка или название (не указывать, если нужно очистить все)', required=False, default=None)):
	if url_or_name:
		if not url_or_name.startswith('http'):
			saved_urls = Storage.get_guild_saved_urls(ctx)

			if url_or_name not in saved_urls:
				return await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, трека с указанным названием нет в списке `/tracklist`. Укажите прямую ссылку', colour=discord.Color.red()), delete_after=15)
			url_or_name = saved_urls[url_or_name]
		
		if url_or_name not in Storage.audio_cache:
			return await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, ссылка не содержится в кэше ({url_or_name})', colour=discord.Color.red()), delete_after=15)
		
		Storage.audio_cache.pop(url_or_name)
		await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, ссылка удалена из кэша ({url_or_name})', colour=discord.Color.from_rgb(255, 255, 255)), delete_after=15)
	
	else:
		Storage.audio_cache = {}
		await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, кэш очищен', colour=discord.Color.from_rgb(255, 255, 255)), delete_after=15)
	os.system('yt-dlp --rm-cache-dir')
	await Storage.save_audio_cache()

@bot.slash_command(name='play_save', description='Добавляет название быстрого запуска для указанной ссылки', guild_ids=guild_ids)
async def _add_track(ctx: discord.ApplicationContext, url: Option(str, "Ссылка для сохранения", required=True), name: Option(str, "Название для быстрого запуска", required=True)):
	if not await check_dj_channel(ctx):
		return
	await ctx.delete()
	dj_channel = Storage.dj_channels[ctx.guild.id]
	message: discord.Message = None

	saved_urls = Storage.get_guild_saved_urls(ctx)

	if name in saved_urls:
		return await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention}, название `{name}` уже используется для трека или плейлиста: {saved_urls[name]}', colour=discord.Color.red()), delete_after=15)
		
	if not url.startswith('http'):
		return await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention}, укажите ссылку', colour=discord.Color.red()), delete_after=15)

	url = prepare_url(url)

	if is_playlist_url(url):
		message = await dj_channel.send(embed=discord.Embed(description=f'{ctx.author.mention} добавляет название "**{name}**" для плейлиста\n\n*(Загрузка займет некоторое время)*\n\n{url} ', colour=discord.Color.orange()))

	play_object = await get_play_object_by_url(url)
	if not play_object:
		await ctx.send(embed=discord.Embed(description = f'{ctx.author.mention}, не удалось получить данные. Укажите ссылку на видео или плейлист с **YouTube**!', colour=discord.Color.red()), delete_after=15)
		return await delete_message(message)

	url = play_object.url
	if isinstance(play_object, Playlist):
		await message.edit(embed=discord.Embed(description=f'{ctx.author.mention} добавляет название "**{name}**" для плейлиста\n\n**{play_object.title}**\n\n{url} ', colour=discord.Color.orange()))
	else:
		await dj_channel.send(embed=discord.Embed(description=f'{ctx.author.mention} добавляет название "**{name}**" для трека\n\n**{play_object.title}**\n\n{url} ', colour=discord.Color.orange()))
		
	saved_urls[name] = url
	await Storage.save_urls()

@bot.slash_command(name='next', description='Переход на следующий трек', guild_ids=guild_ids)
async def _next(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).next(ctx.author)

@bot.slash_command(name='previous', description='Переход на предыдущий трек', guild_ids=guild_ids)
async def _prev(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).previous(ctx.author)
	
@bot.slash_command(name='pause', description='Приостановить/продолжить воспроизведение трека', guild_ids=guild_ids)
async def _pause(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).pause(ctx.author)

@bot.slash_command(name='stop', description='Отключает бота от голосового канала и очищает список треков', guild_ids=guild_ids)
async def _stop(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).stop(ctx.author)
	
@bot.slash_command(name='remove_track', description='Удаляет из списка сохраненных названий указанный трек', guild_ids=guild_ids)
async def _remove_track(ctx: discord.ApplicationContext, name: Option(str, "Название быстрого запуска", required=True, autocomplete=get_tracknames)):
	await ctx.delete()
	
	saved_urls = Storage.get_guild_saved_urls(ctx)

	if name not in saved_urls:
		return await ctx.send(embed=discord.Embed(description=f'{ctx.author.mention}, указанный трек не найден', colour=discord.Color.red()), delete_after=5)

	saved_urls.pop(name)
	await Storage.save_urls()
	await ctx.send(embed = discord.Embed(description=f'{ctx.author.mention}, сохраненная ссылка "*{name}*" удалена', colour=discord.Color.green()))
	

@bot.slash_command(name='get_track_names', description='Возвращает все названия для указанного трека', guild_ids=guild_ids)
async def _get_names(ctx: discord.ApplicationContext, url_or_name: Option(str, "Ссылка или название сохраненного трека", required=True, autocomplete=get_tracknames)):
	saved_urls = Storage.get_guild_saved_urls(ctx)
	
	if url_or_name in saved_urls:
		url_or_name = saved_urls[url_or_name]
	
	names = [name for name in saved_urls if saved_urls[name] == url_or_name]
	
	if not names:
		return await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, для указанной ссылки нет названий для быстрого запуска', colour=discord.Color.red()), delete_after=5)
	await ctx.respond(embed=discord.Embed(description=f'{ctx.author.mention}, названия для быстрого запуска: {", ".join(names)}\nСсылка: {url_or_name}', colour=discord.Color.from_rgb(153, 0, 255)))

@bot.slash_command(name='tracklist', description='Возвращает таблицу сохраненных треков для dj-bot', guild_ids=guild_ids)
async def _tracklist(ctx: discord.ApplicationContext):
	saved_urls = Storage.get_guild_saved_urls(ctx)
	links = {link for link in saved_urls.values()}

	if not links:
		return await ctx.respond(f'{ctx.author.mention}, сохраненные треки не найдены. Используйте команду `/play_save` для сохранения', ephemeral=True, delete_after=15)

	msg_text = f'{ctx.author.mention}, пожалуйста подождите, выполняется запрос данных...'
	await ctx.respond(msg_text, delete_after=5)

	maxlen = 100
	msg = '```\n'

	s = 'Видео/Ссылка'
	while len(s) < (maxlen / 2):
		s = ' ' + s
	while len(s) < maxlen:
		s += ' '
	msg += f'{s}  Название\n\n'

	for url in links:
		names = [key for key in saved_urls if saved_urls[key] == url]
		title = get_video_title(url)
		while len(title) < maxlen:
			title += ' '
		msg += f'{title}| {", ".join(names)}\n'

		if len(msg) > 1800:
			msg += '```'
			await ctx.send(msg, delete_after=120)
			msg = '```\n'
	
	msg += '```'

	await ctx.send(msg, delete_after=120)

async def check_dj_channel(ctx: discord.ApplicationContext) -> bool:
	if ctx.guild.id not in Storage.dj_channels:
		await ctx.respond(f'Используйте команду `/set_dj_channel`, чтобы установить канал для проигрывания музыки', ephemeral=True, delete_after=15)
		return False
	return True


bot.run(Config.token)