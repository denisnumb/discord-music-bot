from config import Config
from locale_provider import *

Config.load_config()
Locale.init(Config.locale)

import os
import discord
from discord import Option
from storage import Storage
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
	# disconnect the bot from the voice channel if no one is present
	bot_member = discord.utils.get(member.guild.members, id=bot.user.id)
	if bot_member.voice and len(bot_member.voice.channel.members) == 1:
		music_client = get_music_client(bot_member.guild)
		await music_client.leave_the_channel_with_timeout(bot_member)


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error) -> None:
	print(f'Error executing command {ctx.command.qualified_name}: {error}')
	await ctx.send(
		embed=discord.Embed(
			description=translate(LocaleKeys.Info.appliaction_command_error, ctx.author.mention, ctx.command.qualified_name), 
			colour=discord.Color.red()
			), 
		delete_after=10
	)

@bot.slash_command(
	name='set_dj_channel', 
	description=translate(LocaleKeys.Cmd.SetDjChannel.desc), 
	guild_ids=guild_ids
)
async def set_dj_channel(
	ctx: discord.ApplicationContext,
	channel: discord.Option(discord.TextChannel, translate(LocaleKeys.Cmd.SetDjChannel.channel), required=True, default=None)
	) -> None:
	if not channel:
		channel = ctx.channel

	Storage.dj_channels[ctx.guild.id] = channel

	await ctx.respond(
		translate(LocaleKeys.Info.dj_channel_installed, ctx.author.mention, channel.mention),
		ephemeral=True,
		delete_after=30
	)
	await Storage.save_dj_channels()

@bot.slash_command(
	name='remove_dj_channel', 
	description=translate(LocaleKeys.Cmd.RemoveDjChannel.desc), 
	guild_ids=guild_ids
)
async def remove_dj_channel(
	ctx: discord.ApplicationContext
	) -> None:
	if ctx.guild.id in Storage.dj_channels:
		channel = Storage.dj_channels.pop(ctx.guild.id)
		await Storage.save_dj_channels()
		return await ctx.respond(translate(LocaleKeys.Info.dj_channel_uninstalled, ctx.author.mention, channel.mention), ephemeral=True, delete_after=15)

@bot.slash_command(name='play', description=translate(LocaleKeys.Cmd.Play.desc), guild_ids=guild_ids)
async def _play(
	ctx: discord.ApplicationContext, 
	url_or_name: Option(str, translate(LocaleKeys.Cmd.Play.url_or_name), required=False, defailt=None, autocomplete=get_tracknames), 
	file: Option(discord.Attachment, translate(LocaleKeys.Cmd.Play.file), required=False, default=None),
	insert: Option(PlayInsertArg, translate(LocaleKeys.Cmd.Play.insert), choices=PlayInsertArg.choices, required=False, default=False),
	mix: Option(PlayMixArg, translate(LocaleKeys.Cmd.Play.mix), choices=PlayMixArg.choices, required=False, default=False),
	mix_with_queue: Option(PlayMixWithQueueArg, translate(LocaleKeys.Cmd.Play.mix_with_queue), choices=PlayMixWithQueueArg.choices, required=False, default=False)
	):
	if not await check_dj_channel(ctx):
		return
	if not ctx.author.voice:
		return await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.join_voice_channel, ctx.author.mention), colour=discord.Color.red()), ephemeral=True, delete_after=15)
	
	if file:
		file = (None if not any(map(lambda x: x in file.content_type, ('audio', 'video')))
			else TrackFile(file.url, file.filename))

	if not any((url_or_name, file)):
		return await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.enter_url_name_or_file, ctx.author.mention), colour=discord.Color.red()), ephemeral=True, delete_after=15)

	await delete_message(ctx)

	if url_or_name and file:
		return await play_list(ctx, url_or_name, [file], insert, mix, mix_with_queue)
	if not url_or_name and file:
		return await play_from_file(ctx, file, insert, mix_with_queue)
	await play(ctx, url_or_name, insert, mix, mix_with_queue)

@bot.slash_command(name='clear_music_cache', description=translate(LocaleKeys.Cmd.ClearMusicCache.desc), guild_ids=guild_ids)
async def _clear_music_cache(
	ctx: discord.ApplicationContext, 
	url_or_name: Option(str, translate(LocaleKeys.Cmd.ClearMusicCache.url_or_name), required=False, default=None)
	):
	if url_or_name:
		if not url_or_name.startswith('http'):
			saved_urls = Storage.get_guild_saved_urls(ctx)

			if url_or_name not in saved_urls:
				return await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.track_with_name_not_found, ctx.author.mention), colour=discord.Color.red()), delete_after=15)
			url_or_name = saved_urls[url_or_name]
		
		if url_or_name not in Storage.audio_cache:
			return await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.url_not_in_cache, ctx.author.mention, url_or_name), colour=discord.Color.red()), delete_after=15)
		
		Storage.audio_cache.pop(url_or_name)
		await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.url_removed_from_cache, ctx.author.mention, url_or_name), colour=discord.Color.from_rgb(255, 255, 255)), delete_after=15)
	
	else:
		Storage.audio_cache = {}
		await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.cache_cleared, ctx.author.mention), colour=discord.Color.from_rgb(255, 255, 255)), delete_after=15)
	os.system('yt-dlp --rm-cache-dir')
	await Storage.save_audio_cache()

@bot.slash_command(name='play_save', description=translate(LocaleKeys.Cmd.PlaySave.desc), guild_ids=guild_ids)
async def _add_track(
	ctx: discord.ApplicationContext, 
	url: Option(str, translate(LocaleKeys.Cmd.PlaySave.url), required=True), 
	name: Option(str, translate(LocaleKeys.Cmd.PlaySave.name), required=True)
	):
	if not await check_dj_channel(ctx):
		return
	await ctx.delete()
	dj_channel = Storage.dj_channels[ctx.guild.id]
	message: discord.Message = None

	saved_urls = Storage.get_guild_saved_urls(ctx)

	if name in saved_urls:
		return await ctx.send(embed=discord.Embed(description=translate(LocaleKeys.Info.name_already_in_use, ctx.author.mention, name, saved_urls[name]), colour=discord.Color.red()), delete_after=15)
		
	if not url.startswith('http'):
		return await ctx.send(embed=discord.Embed(description=translate(LocaleKeys.Info.enter_url, ctx.author.mention), colour=discord.Color.red()), delete_after=15)

	url = prepare_url(url)

	if is_playlist_url(url):
		message = await dj_channel.send(embed=discord.Embed(description=translate(LocaleKeys.Info.user_adds_name_loading, ctx.author.mention, name, url), colour=discord.Color.orange()))

	play_object = await get_play_object_by_url(url)
	if not play_object:
		await ctx.send(embed=discord.Embed(description=translate(LocaleKeys.Info.cant_get_data, ctx.author.mention), colour=discord.Color.red()), delete_after=15)
		return await delete_message(message)

	url = play_object.url
	if isinstance(play_object, Playlist):
		await message.edit(embed=discord.Embed(description=translate(LocaleKeys.Info.user_adds_playlist_name, ctx.author.mention, name, play_object.title, url), colour=discord.Color.orange()))
	else:
		await dj_channel.send(embed=discord.Embed(description=translate(LocaleKeys.Info.user_adds_track_name, ctx.author.mention, name, play_object.title, url), colour=discord.Color.orange()))
		
	saved_urls[name] = url
	await Storage.save_urls()

@bot.slash_command(name='next', description=translate(LocaleKeys.Cmd.Next.desc), guild_ids=guild_ids)
async def _next(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).next(ctx.author)

@bot.slash_command(name='previous', description=translate(LocaleKeys.Cmd.Previous.desc), guild_ids=guild_ids)
async def _prev(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).previous(ctx.author)
	
@bot.slash_command(name='pause', description=translate(LocaleKeys.Cmd.Pause.desc), guild_ids=guild_ids)
async def _pause(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).pause(ctx.author)

@bot.slash_command(name='stop', description=translate(LocaleKeys.Cmd.Stop.desc), guild_ids=guild_ids)
async def _stop(ctx: discord.ApplicationContext):
	await ctx.delete()
	await (get_music_client(ctx.guild)).stop(ctx.author)
	
@bot.slash_command(name='remove_track', description=translate(LocaleKeys.Cmd.RemoveTrack.desc), guild_ids=guild_ids)
async def _remove_track(ctx: discord.ApplicationContext, name: Option(str, translate(LocaleKeys.Cmd.RemoveTrack.name), required=True, autocomplete=get_tracknames)):
	await ctx.delete()
	
	saved_urls = Storage.get_guild_saved_urls(ctx)

	if name not in saved_urls:
		return await ctx.send(embed=discord.Embed(description=translate(LocaleKeys.Info.track_with_name_not_found, ctx.author.mention), colour=discord.Color.red()), delete_after=5)

	saved_urls.pop(name)
	await Storage.save_urls()
	await ctx.send(embed=discord.Embed(description=translate(LocaleKeys.Info.saved_url_removed, ctx.author.name, name), colour=discord.Color.green()))
	

@bot.slash_command(name='get_track_names', description=translate(LocaleKeys.Cmd.GetTrackNames.desc), guild_ids=guild_ids)
async def _get_names(ctx: discord.ApplicationContext, url_or_name: Option(str, translate(LocaleKeys.Cmd.GetTrackNames.url_or_name), required=True, autocomplete=get_tracknames)):
	saved_urls = Storage.get_guild_saved_urls(ctx)
	
	if url_or_name in saved_urls:
		url_or_name = saved_urls[url_or_name]
	
	names = [name for name in saved_urls if saved_urls[name] == url_or_name]
	
	if not names:
		return await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.no_names_for_url, ctx.author.mention), colour=discord.Color.red()), delete_after=5)
	await ctx.respond(embed=discord.Embed(description=translate(LocaleKeys.Info.names_for_url, ctx.author.mention, ', '.join(names), url_or_name), colour=discord.Color.from_rgb(153, 0, 255)))

@bot.slash_command(name='tracklist', description=translate(LocaleKeys.Cmd.Tracklist.desc), guild_ids=guild_ids)
async def _tracklist(ctx: discord.ApplicationContext):
	saved_urls = Storage.get_guild_saved_urls(ctx)
	links = {link for link in saved_urls.values()}

	if not links:
		return await ctx.respond(translate(LocaleKeys.Info.saved_tracks_not_found, ctx.author.mention), ephemeral=True, delete_after=15)

	await ctx.respond(translate(LocaleKeys.Info.data_request, ctx.author.mention), delete_after=5)

	maxlen = 100
	msg = '```\n'

	s = translate(LocaleKeys.Label.tracklist_video_and_url_column)
	while len(s) < (maxlen / 2):
		s = ' ' + s
	while len(s) < maxlen:
		s += ' '
	msg += translate(LocaleKeys.Label.tracklist_name_column, s)

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
		await ctx.respond(translate(LocaleKeys.Info.use_dj_channel_command), ephemeral=True, delete_after=15)
		return False
	return True


bot.run(Config.token)