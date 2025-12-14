import os
import json
from pathlib import Path
from typing import Dict


def translate(key: str, *args) -> str:
	return Locale.translate(key, * args)

class Locale:
	__base_path = Path(__file__).resolve().parent 
	_locales_path = __base_path.parent / 'locales'
	_locale_data: Dict[str, str] = {}

	@classmethod
	def init(cls, locale_code: str):
		locale_file = locale_code + '.json'

		if locale_file not in os.listdir(cls._locales_path):
			locale_file = "en_us.json"

		with open(cls._locales_path / locale_file, 'r', encoding='utf-8') as file:
			Locale._locale_data = json.load(file)

	@classmethod
	def translate(cls, key: str, *args) -> str:
		return cls._locale_data.get(key, key).format(*args)

class LocaleKeys:
	class Info:
		dj_channel_installed = 'info.dj_channel_installed'
		dj_channel_uninstalled = 'info.dj_channel_uninstalled'
		join_voice_channel = 'info.join_voice_channel'
		enter_url_name_or_file = 'info.enter_url_name_or_file'
		track_with_name_not_found = 'info.track_with_name_not_found'
		url_not_in_cache = 'info.url_not_in_cache'
		url_removed_from_cache = 'info.url_removed_from_cache'
		cache_cleared = 'info.cache_cleared'
		name_already_in_use = 'info.name_already_in_use'
		enter_url = 'info.enter_url'
		user_adds_name_loading = 'info.user_adds_name_loading'
		cant_get_data = 'info.cant_get_data'
		user_adds_playlist_name = 'info.user_adds_playlist_name'
		user_adds_track_name = 'info.user_adds_track_name'
		saved_url_removed = 'info.saved_url_removed'
		no_names_for_url = 'info.no_names_for_url'
		names_for_url = 'info.names_for_url'
		saved_tracks_not_found = 'info.saved_tracks_not_found'
		data_request = 'info.data_request'
		use_dj_channel_command = 'info.use_dj_channel_command'
		user_insert = 'info.user_insert'
		user_mix_with_queue = 'info.user_mix_with_queue'
		user_adds = 'info.user_adds'
		user_play = 'info.user_play'
		cant_get_data_for = 'info.cant_get_data_for'
		cant_get_title = 'info.cant_get_title'
		appliaction_command_error = 'info.appliaction_command_error'
		user_play_next = 'info.user_play_next'
		user_play_prev = 'info.user_play_prev'
		user_play_stop = 'info.user_play_stop'
		track_play_error = 'info.track_play_error'
		join_channel_error = 'info.join_channel_error'
		cant_get_data_for_list = 'info.cant_get_data_for_list'
		cant_get_data_for_everyone = 'info.cant_get_data_for_everyone'

	class Label:
		tracklist_video_and_url_column = 'label.tracklist_video_and_url_column'
		tracklist_name_column = 'label.tracklist_name_column'
		for_track = 'label.for_track'
		and_ = 'label.and_'
		playlist = 'label.playlist'
		track = 'label.track'
		track_list = 'label.track_list'
		file = 'label.file'
		insert = 'label.insert'
		not_insert = 'label.not_insert'
		mix = 'label.mix'
		mix_with_queue = 'label.mix_with_queue'
		end_of_queue = 'label.end_of_queue'
		music_player_info = 'label.music_player_info'
		ask_how_add_query_to_queue = 'label.ask_how_add_query_to_queue'
		ask_mix_playlist = 'label.ask_mix_playlist'
		ask_find_track_by_query = 'label.ask_find_track_by_query'
		quick_play = 'label.quick_play'
		names_and_tracks_loading = 'label.names_and_tracks_loading'
		loading_take_some_time = 'label.loading_take_some_time'
		add_query_to_queue = 'label.add_query_to_queue'
		insert_query = 'label.insert_query'
		mix_query_with_queue = 'label.mix_query_with_queue'
		cancel = 'label.cancel'
		yes = 'label.yes'
		no = 'label.no'

	class Cmd:
		class SetDjChannel:
			desc = 'cmd.set_dj_channel.desc'
			channel = 'cmd.set_dj_channel.channel'

		class RemoveDjChannel:
			desc = 'cmd.remove_dj_channel.desc'

		class Play:
			desc = 'cmd.play.desc'
			url_or_name = 'cmd.play.url_or_name'
			file = 'cmd.play.file'
			insert = 'cmd.play.insert'
			mix = 'cmd.play.mix'
			mix_with_queue = 'cmd.play.mix_with_queue'

		class ClearMusicCache:
			desc = 'cmd.clear_music_cache.desc'
			url_or_name = 'cmd.clear_music_cache.url_or_name'

		class PlaySave:
			desc = 'cmd.play_save.desc'
			url = 'cmd.play_save.url'
			name = 'cmd.play_save.name'

		class Next:
			desc = 'cmd.next.desc'

		class Previous:
			desc = 'cmd.previous.desc'

		class Pause:
			desc = 'cmd.pause.desc'

		class Stop:
			desc = 'cmd.stop.desc'

		class RemoveTrack:
			desc = 'cmd.remove_track.desc'
			name = 'cmd.remove_track.name'

		class GetTrackNames:
			desc = 'cmd.get_track_names.desc'
			url_or_name = 'cmd.get_track_names.url_or_name'

		class Tracklist:
			desc = 'cmd.tracklist.desc'