import asyncio
import traceback
from dataclasses import dataclass

import aiogram
from aiogram.types import Message


@dataclass
class Message:
    chat_id: int


@dataclass
class TextMessage(Message):
    chat_id: int
    text: str
    message_thread_id: int = None
    markup: aiogram.types.InlineKeyboardMarkup = None
    destroy_timeout: int = 0
    button_destroy: int = 0
    pin: bool = False


@dataclass
class EditMessage(Message):
    chat_id: int
    text: str
    message_id: int
    markup: aiogram.types.InlineKeyboardMarkup = None


# noinspection PyAsyncCall
class BotInter:
    disable_notifications: bool = False
    disable_web_page_preview: bool = True
    _parse_mode = 'html'

    def __init__(self):
        """
        Класс позволяющий взаимодействовать с ботом через aiogram
        """
        from main import bot
        self.bot = bot

    async def get_link(self, chat_id: int) -> str:
        try:
            res = await self.bot.create_chat_invite_link(
                chat_id=chat_id
            )
            return res.invite_link
        except Exception as err:
            traceback.print_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")

    async def send_text(self, message_obj: TextMessage) -> aiogram.types.Message:
            """
            Отправляет сообщение. Необходимо заполнить минимум text и chat_id
            :return: aiogram.types.Message
            """
            if TextMessage:
                try:
                    sent_message = await self.bot.send_message(
                        chat_id=message_obj.chat_id,
                        text=message_obj.text,
                        message_thread_id=message_obj.message_thread_id,
                        reply_markup=message_obj.markup,
                        parse_mode=self._parse_mode,
                        disable_notification=self.disable_notifications,
                        disable_web_page_preview=self.disable_web_page_preview
                    )

                    if message_obj.pin is True:
                        await self.bot.pin_chat_message(
                            chat_id=message_obj.chat_id,
                            message_id=sent_message.message_id,
                            disable_notification=True
                        )

                    if message_obj.destroy_timeout != 0:
                        asyncio.create_task(self._destroy_message(
                            message=sent_message,
                            destroy_timeout=message_obj.destroy_timeout
                        ))

                    if message_obj.button_destroy != 0:
                        asyncio.create_task(self._destroy_buttons(
                            message=sent_message,
                            destroy_timeout=message_obj.button_destroy
                        ))

                    return sent_message

                except Exception as err:
                    traceback.print_exc()
                    print(f"\033[1;31mERROR:\033[37m {err}\033[0m")

            else:
                raise Exception('При отправке сообщения необходимо передать TextMessage объект')

    async def edit_text(self, message_obj: EditMessage):
        await self.bot.edit_message_text(
            chat_id=message_obj.chat_id,
            text=message_obj.text,
            message_id=message_obj.message_id,
            reply_markup=message_obj.markup,
            parse_mode=self._parse_mode,
            disable_web_page_preview=self.disable_web_page_preview
        )

    async def delete_message(self, chat_id: int, message_id:int):
        try:
            await self.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
        except Exception as err:
            print(err)

    async def answer_query(self, callback_id, text: str):
        await self.bot.answer_callback_query(
            callback_query_id=callback_id,
            text=text
        )

    async def _destroy_message(self, message: aiogram.types.Message, destroy_timeout: int):
        await asyncio.sleep(destroy_timeout)
        try:
            chat_id = message.chat.id
            message_id = message.message_id
            await self.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
        except Exception as err:
            if err.__str__() not in [
                'Telegram server says - Bad Request: message to delete not found',
            ]:
                traceback.print_exc()
                print(f"\033[1;31mERROR:\033[37m {err}\033[0m")

    async def _destroy_buttons(self, message: aiogram.types.Message, destroy_timeout: int):
        await asyncio.sleep(destroy_timeout)
        try:
            chat_id = message.chat.id
            message_id = message.message_id
            text = message.text
            await self.bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode=self._parse_mode
            )
        except Exception as err:
            if err.__str__() not in [
                'Telegram server says - Bad Request: message to edit not found',
            ]:
                traceback.print_exc()
                print(f"\033[1;31mERROR:\033[37m {err}\033[0m")