import os
import json
from pathlib import Path
from typing import Dict


class Locale:
	_instance = None

	__base_path = Path(__file__).resolve().parent 
	_locales_path = __base_path.parent / 'locales'
	_locale_data: Dict[str, str] = {}

	def __new__(cls, locale_code: str):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self, locale_code: str):
		if hasattr(self, "_initialized") and self._initialized:
			return

		locale_file = locale_code + '.json'

		if locale_file not in os.listdir(self._locales_path):
			locale_file = "en_us.json"

		with open(self._locales_path / locale_file, 'r', encoding='utf-8') as file:
			Locale._locale_data = json.load(file)

		self._initialized = True

	@classmethod
	def translate(cls, key: str, *args) -> str:
		return cls._locale_data.get(key, key).format(*args)