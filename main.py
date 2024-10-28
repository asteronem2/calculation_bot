import asyncio
import inspect
import logging
import os.path
import time
import traceback
from datetime import datetime
from typing import Type

import aiogram
from aiogram.enums import ReactionTypeType
from aiogram.types import ReactionTypeEmoji, InputFile, FSInputFile
from aiogram.types.message import Message
from aiogram.types.callback_query import CallbackQuery
from aiogram.types.message_reaction_updated import MessageReactionUpdated
from aiogram.types.inline_query import InlineQuery

import command.message_command
from command.command_interface import MessageCommand, CallbackQueryCommand, NextCallbackMessageCommand, InlineQueryCommand, MessageReactionCommand
from utils import DotEnvData, db, Tracking, GetLocales, log, entities_to_html, DED

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
        if message.via_bot:
            return
        if message.content_type in ['text', 'photo']:
            t1 = time.time()
            print(f'\n\n\033[1;36mMESSAGE {message.from_user.username}: \033[1;32m{message.text}\033[0;0m')
            await log(f'MESSAGE: {message.from_user.username or message.from_user.id}: {message.text or message.caption}', 'info')

            if message.text == '/fix':
                await db.execute("""
                    DELETE FROM pressure_button_table
                """)
                return

            res = await db.fetchrow("""
                SELECT * FROM pressure_button_table
                WHERE
                COALESCE(chat_pid, 1) = COALESCE((SELECT id FROM chat_table WHERE chat_id = $1 AND type = 'chat' LIMIT 1), 1)
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
        err_str = traceback.format_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
        print(err_str)
        await log(err_str)


@dispatcher.callback_query()
async def telegram_callback_query_update(callback: CallbackQuery):
    try:
        t1 = time.time()
        print(f'\n\n\033[1;36mCALLBACK {callback.from_user.username}: \033[1;32m{callback.data}\033[0;0m')
        await log(f'CALLBACK: {callback.from_user.username or callback.from_user.id}: {callback.data}',
                  'info')
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
        err_str = traceback.format_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
        print(err_str)
        await log(err_str)


@dispatcher.message_reaction()
async def telegram_message_reaction_update(reaction: MessageReactionUpdated):
    try:
        new = reaction.new_reaction
        old = reaction.old_reaction
        if new:
            react = new[-1]
        else:
            react = old[-1]
        if react.type == ReactionTypeType.CUSTOM_EMOJI:
            return
        t1 = time.time()
        print(f'\n\n\033[1;36mREACTION {reaction.user.username}: \033[1;32m{react.emoji}\033[0;0m')
        await log(f'REACTION: {reaction.user.username or reaction.user.id}: {react}', 'info')
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
        err_str = traceback.format_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
        print(err_str)
        await log(err_str)


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
        err_str = traceback.format_exc()
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
        print(err_str)
        await log(err_str)


allowed_updates = ['message', 'message_reaction', 'inline_query', 'callback_query']

async def check_logs():
    while True:
        try:
            await asyncio.sleep(1*60*60)
            if os.path.exists('logs.log'):
                file_size = os.path.getsize('logs.log')
                file_size_mb = file_size / 1024 / 1024
                if file_size_mb > 20:
                    print("SEND LOGS")
                    await bot.send_document(
                        chat_id=DED.DEBUG_CHAT_ID,
                        document=FSInputFile('logs.log'),
                        caption=datetime.today().strftime('%Y.%m.%d %H:%M:%S'),
                        disable_notification=True
                    )
                    with open('logs.log', 'w') as w:
                        w.write('')
            else:
                with open('logs.log', 'w') as w:
                    w.write('')
        except:
            await asyncio.sleep(1*60*60)

# noinspection PyAsyncCall
async def main():
    asyncio.create_task(check_logs())
    try:
        await bot.send_document(EnvData.DEBUG_CHAT_ID, FSInputFile('logs.log'), disable_notification=True)
    except Exception as err:
        print(f"\033[1;31mERROR:\033[37m {err}\033[0m")

    logging.basicConfig(level=logging.INFO, filename='logs.log', filemode='w', format='%(asctime)s - [%(levelname)s] - %(message)s')

    while True:
        try:
            await add_all_cls()
            message_command_cls.remove(command.message_command.QuoteReplied)
            message_command_cls.insert(0, command.message_command.QuoteReplied)

            global db
            await db.connect()
            await db.reg_tables()

            # with open('test.py', 'w') as tpy:
            #     rrr = await db.fetch("""
            #         SELECT story_table.* FROM story_table
            #         JOIN currency_table ON currency_table.id = story_table.currency_pid
            #         WHERE currency_table.title = 'гг';
            #     """)
            #
            #     list_ = [dict(i) for i in rrr]
            #
            #     tpy.write('CONST = {list_}')
            #
            t = Tracking()
            asyncio.create_task(t.async_init())

            print("\033[1;32mSUCCESS:\033[37m bot started\033[0m")

            await log('SUCCESS: bot started', 'info')

            await dispatcher.start_polling(bot, polling_timeout=300, allowed_updates=allowed_updates, handle_signals=False)
        except Exception as err:
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            error = traceback.format_exc()
            print(error)
            await log(error)
            time.sleep(3)

if __name__ == '__main__':
    asyncio.run(main())
