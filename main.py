import asyncio
import inspect
import time
import traceback
from typing import Type

import aiogram
from aiogram.types.message import Message
from aiogram.types.callback_query import CallbackQuery
from aiogram.types.message_reaction_updated import MessageReactionUpdated
from aiogram.types.inline_query import InlineQuery

from command.command_interface import MessageCommand, CallbackQueryCommand, NextCallbackMessageCommand, InlineQueryCommand, MessageReactionCommand
from utils import DotEnvData, db, Tracking, GetLocales

EnvData = DotEnvData()

bot = aiogram.Bot(token=EnvData.BOT_TOKEN)
dispatcher = aiogram.Dispatcher()

message_command_cls = []
callback_command_cls = []
next_callback_message_cls = []
reaction_command_cls = []
inline_command_cls = []


async def add_all_cls():
    from command import (message_command, callback_query_command, message_reaction_command, inline_query_command,
                         next_callback_message)
    x_x = (
        (message_command_cls, message_command),
        (callback_command_cls, callback_query_command),
        (reaction_command_cls, message_reaction_command),
        (inline_command_cls, inline_query_command),
        (next_callback_message_cls, next_callback_message)
    )
    for x in x_x:
        for i in inspect.getmembers(x[1], inspect.isclass):
            if i[1].__dict__['__module__'] == x[1].__dict__['__name__']:
                x[0].append(i[1])


async def check_define(cls_list: list, interface_class, obj):
    interface = interface_class(obj)
    await interface.async_init()
    for cls in cls_list:
        define = await cls.define(interface)
        if define is True:
            return cls
        elif define:
            return cls, define
    return None


@dispatcher.message()
async def telegram_message_update(message: Message):
    try:
        if message.content_type in ['text', 'photo']:
            t1 = time.time()
            print(f'\n\n\033[1;36mMESSAGE {message.from_user.username}: \033[1;32m{message.text}\033[0;0m')

            if message.text == '/fix':
                await db.execute("""
                    DELETE FROM pressure_button_table
                """)
                return

            res = await db.fetchrow("""
                SELECT * FROM pressure_button_table
                WHERE
                COALESCE(chat_pid, 1) = COALESCE((SELECT id FROM chat_table WHERE chat_id = $1 LIMIT 1), 1)
                AND
                user_pid = (SELECT id FROM user_table WHERE user_id = $2 LIMIT 1);
            """, None if message.chat.type == 'private' else message.chat.id,
                                    message.from_user.id)

            if res:
                result: Type[MessageCommand] = await check_define(next_callback_message_cls, NextCallbackMessageCommand, message)
                if result is None:
                    return None

                command_obj = result(message)
                await command_obj.async_init()
                define = await command_obj.define()

                if define is None:
                    return None
            else:
                result: Type[MessageCommand] = await check_define(message_command_cls, MessageCommand, message)
                if result is None:
                    return None

                command_obj = result(message)
                await command_obj.async_init()
                define = await command_obj.define()

                if define is None:
                    return None
            t2 = time.time()
            print(f'\033[1;34m{round(t2 - t1, 3)}\033[0;0m')
    except Exception as err:
        traceback.print_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")


@dispatcher.callback_query()
async def telegram_callback_query_update(callback: CallbackQuery):
    try:
        t1 = time.time()
        print(f'\n\n\033[1;36mCALLBACK {callback.from_user.username}: \033[1;32m{callback.data}\033[0;0m')
        result: Type[CallbackQueryCommand] = await check_define(callback_command_cls, CallbackQueryCommand, callback)
        if result is None:
            return None

        command_obj = result(callback)
        await command_obj.async_init()
        define = await command_obj.define()

        if define is None:
            return None

        t2 = time.time()
        print(f'\033[1;34m{round(t2 - t1, 3)}\033[0;0m')
    except Exception as err:
        traceback.print_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")

@dispatcher.message_reaction()
async def telegram_message_reaction_update(reaction: MessageReactionUpdated):
    try:
        if reaction.new_reaction:
            t1 = time.time()
            print(f'\n\n\033[1;36mREACTION {reaction.user.username}: \033[1;32m{reaction.new_reaction[-1].emoji}\033[0;0m')
            result: Type[MessageReactionCommand] = await check_define(reaction_command_cls, MessageReactionCommand, reaction)
            if result is None:
                return None

            command_obj = result(reaction)
            await command_obj.async_init()
            define = await command_obj.define()

            if define is None:
                return None

            t2 = time.time()
            print(f'\033[1;34m{round(t2 - t1, 3)}\033[0;0m')
    except Exception as err:
        traceback.print_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")


@dispatcher.inline_query()
async def telegram_inline_query_update(inline: InlineQuery):
    try:
        result: Type[InlineQueryCommand] = await check_define(inline_command_cls, InlineQueryCommand, inline)
        if result is None:
            return None

        command_obj = result(inline)
        await command_obj.async_init()
        define = await command_obj.define()
    except Exception as err:
        traceback.print_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")


allowed_updates = ['message', 'message_reaction', 'inline_query', 'callback_query']


# noinspection PyAsyncCall
async def main():
    while True:
        try:
            await add_all_cls()

            global db
            await db.connect()
            await db.reg_tables()

            t = Tracking()
            asyncio.create_task(t.async_init())

            print("\033[1;32mSUCCESS:\033[37m bot started\033[0m")

            await dispatcher.start_polling(bot, polling_timeout=300, allowed_updates=allowed_updates)

        except Exception as err:
            traceback.print_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            time.sleep(1)


if __name__ == '__main__':
    asyncio.run(main())
