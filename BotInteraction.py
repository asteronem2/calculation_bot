import asyncio
import re
import time
import traceback
from dataclasses import dataclass
from typing import Union, List

import aiogram
from aiogram.exceptions import AiogramError
from aiogram.types import InputMediaPhoto
from aiogram.types.reaction_type_emoji import ReactionTypeEmoji

from utils import log


@dataclass
class Message:
    chat_id: int
    text: str


@dataclass
class TextMessage(Message):
    chat_id: int
    text: str
    message_thread_id: int = None
    markup: aiogram.types.InlineKeyboardMarkup = None
    destroy_timeout: int = 0
    button_destroy: int = 0
    pin: bool = False
    photo: Union[str, List[str]] = None
    reply_to_message_id: int = None
    disable_web_page_preview: bool = True


@dataclass
class EditMessage(Message):
    chat_id: int
    text: str
    message_id: int
    markup: aiogram.types.InlineKeyboardMarkup = None,
    button_destroy: int = 0
    disable_web_page_preview: bool = True


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
            err_str = traceback.format_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            print(err_str)
            await log(err_str)

    async def send_text(self, message_obj: TextMessage) -> aiogram.types.Message:
            """
            Отправляет сообщение. Необходимо заполнить минимум text и chat_id
            :return: aiogram.types.Message
            """
            if TextMessage:
                try:
                    if message_obj.photo:
                        if type(message_obj.photo) == str:
                            sent_message = await self.bot.send_photo(
                                chat_id=message_obj.chat_id,
                                photo=message_obj.photo,
                                caption=message_obj.text[:2000],
                                message_thread_id=message_obj.message_thread_id,
                                reply_markup=message_obj.markup,
                                parse_mode=self._parse_mode,
                                disable_notification=self.disable_notifications,
                                reply_to_message_id=message_obj.reply_to_message_id
                            )
                        elif type(message_obj.photo) == list:
                            sent_messages = await self.bot.send_media_group(
                                chat_id=message_obj.chat_id,
                                media=[InputMediaPhoto(
                                    media=i,
                                    caption=message_obj.text[:2000],
                                    parse_mode=self._parse_mode,
                                ) for i in message_obj.photo],
                                message_thread_id=message_obj.message_thread_id,
                                disable_notification=self.disable_notifications,
                                reply_to_message_id=message_obj.reply_to_message_id
                            )
                            await log('SEND BOT: MEDIA GROUP PHOTO', 'info')
                            print(f'\033[1;36mSEND BOT: \033[1;32mMEDIA GROUP PHOTO\033[0;0m')
                            return sent_messages

                    else:
                        sent_message = await self.bot.send_message(
                            chat_id=message_obj.chat_id,
                            text=message_obj.text[:4000],
                            message_thread_id=message_obj.message_thread_id,
                            reply_markup=message_obj.markup,
                            parse_mode=self._parse_mode,
                            disable_notification=self.disable_notifications,
                            disable_web_page_preview=message_obj.disable_web_page_preview,
                            reply_to_message_id=message_obj.reply_to_message_id
                        )
                    rres = re.sub(r'<.+?>|/n', '', sent_message.text or sent_message.caption or 'Without caption')
                    await log(f'SEND BOT: {rres}', 'info')
                    print(f'\033[1;36mSEND BOT: \033[1;32m{rres}\033[0;0m')

                    if message_obj.pin is True:
                        await self.bot.pin_chat_message(
                            chat_id=message_obj.chat_id,
                            message_id=sent_message.message_id,
                            disable_notification=True
                        )

                        try:
                            await self.bot.delete_message(
                                chat_id=message_obj.chat_id,
                                message_id=sent_message.message_id + 1,
                            )
                        except:
                            pass

                    if message_obj.destroy_timeout != 0:
                        asyncio.create_task(self._destroy_message(
                            message=sent_message,
                            destroy_timeout=message_obj.destroy_timeout
                        ))

                    if message_obj.button_destroy != 0:
                        asyncio.create_task(self._destroy_buttons(
                            chat_id=sent_message.chat.id,
                            message_id=sent_message.message_id,
                            destroy_timeout=message_obj.button_destroy,
                            message_obj=message_obj
                        ))

                    return sent_message
                except aiogram.exceptions.TelegramNetworkError:
                    asyncio.sleep(3)
                    return await self.send_text(message_obj)
                except aiogram.exceptions.TelegramRetryAfter:
                    await asyncio.sleep(3)
                except Exception as err:
                    err_str = traceback.format_exc()
                    print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
                    print(err_str)
                    await log(err_str)

            else:
                raise Exception('При отправке сообщения необходимо передать TextMessage объект')

    async def edit_text(self, message_obj: EditMessage):
        rres = re.sub(r'<.+?>|/n', '', message_obj.text)
        await log(f'EDIT BOT: {rres}', 'info')
        print(f'\033[1;36mEDIT BOT: \033[1;32m{rres}\033[0;0m')
        if message_obj.markup == (None,):
            message_obj.markup = None
        try:
            try:
                await self.bot.edit_message_text(
                    chat_id=message_obj.chat_id,
                    text=message_obj.text[:4000],
                    message_id=message_obj.message_id,
                    reply_markup=message_obj.markup,
                    parse_mode=self._parse_mode,
                    disable_web_page_preview=message_obj.disable_web_page_preview
                )
            except:
                await self.bot.edit_message_caption(
                    chat_id=message_obj.chat_id,
                    caption=message_obj.text[:4000],
                    message_id=message_obj.message_id,
                    reply_markup=message_obj.markup,
                    parse_mode=self._parse_mode
                )
        except aiogram.exceptions.TelegramNetworkError as err:
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            asyncio.sleep(2)
            await self.edit_text(message_obj)
            return
        except aiogram.exceptions.TelegramBadRequest as err:
            err_str = traceback.format_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            print(err_str)
            await log(err_str)
            return
        except Exception as err:
            err_str = traceback.format_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            print(err_str)
            await log(err_str)
            return

        if message_obj.button_destroy != 0:
            asyncio.create_task(self._destroy_buttons(
                chat_id=message_obj.chat_id,
                message_id=message_obj.message_id,
                destroy_timeout=message_obj.button_destroy,
                message_obj=message_obj
            ))

    async def delete_message(self, chat_id: int, message_id:int):
        try:
            await self.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
        except aiogram.exceptions.TelegramBadRequest:
            pass
        except Exception as err:
            err_str = traceback.format_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            print(err_str)
            await log(err_str)

    async def answer_clb_query(self, callback_id, text: str):
        await self.bot.answer_callback_query(
            callback_query_id=callback_id,
            text=text
        )

    async def answer_inline_query(self, results: [aiogram.types.InlineQueryResult], query_id):
        await self.bot.answer_inline_query(
            inline_query_id=query_id,
            results=results,
            cache_time=1
        )

    async def set_emoji(self, chat_id: int, message_id: int, emoji: str):
        try:
            await self.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[ReactionTypeEmoji(emoji=emoji)]
            )
        except Exception as err:
            err_str = traceback.format_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            print(err_str)
            await log(err_str)

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
                err_str = traceback.format_exc()
                print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
                print(err_str)
                await log(err_str)

    async def _destroy_buttons(self, chat_id: int, message_id: int, destroy_timeout: int, message_obj: TextMessage):
        await asyncio.sleep(destroy_timeout)
        try:
            if not message_obj.photo:
                await self.bot.edit_message_text(
                    text=message_obj.text[:4000],
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode=self._parse_mode
                )
        except Exception as err:
            if err.__str__() not in [
                'Telegram server says - Bad Request: message to edit not found',
            ]:
                err_str = traceback.format_exc()
                print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
                print(err_str)
                await log(err_str)
