import discord
import asyncio
from discord.ui import View, Button
from model import AddTrackTypes


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