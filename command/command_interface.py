import re
from abc import abstractmethod

import asyncpg
from aiogram.types.message import Message
from aiogram.types.callback_query import CallbackQuery
from aiogram.types.message_reaction_updated import MessageReactionUpdated
from aiogram.types.inline_query import InlineQuery

import BotInteraction
import utils
from BotInteraction import EditMessage, TextMessage


class MessageCommand:
    db_user: asyncpg.Record
    db_chat: asyncpg.Record
    access_level: str = None

    def __init__(self, message: Message):
        self.message = message
        self.chat = message.chat
        self.user = message.from_user
        self.text = message.text if message.text else (message.caption if message.caption else '')
        self.text_low = self.text.lower().strip()
        self.topic = 0 if message.is_topic_message is None else message.message_thread_id
        self.photo = True if message.content_type == 'photo' else False

        self.db = utils.db

        self.data_locales = utils.GetLocales('message_command')
        self.global_texts = self.data_locales.global_texts
        self.texts = self.data_locales.texts
        self.buttons = self.data_locales.buttons
        self.keywords = self.global_texts['keywords']
        self.bot = BotInteraction.BotInter()

    async def async_init(self):
        await self._get_addition_from_db()

    @abstractmethod
    async def define(self):
        """
        :return: True if this command define and None if not define
        """
        pass

    @abstractmethod
    async def process(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    @abstractmethod
    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> EditMessage:
        pass

    async def _get_addition_from_db(self):
        self.db_user = await self.db.fetchrow("""
            SELECT * FROM user_table
            WHERE user_id = $1;
        """, self.user.id)

        if self.db_user is None:

            from main import EnvData
            access_level = 'zero'
            if self.user.username in EnvData.ADMIN_LIST:
                access_level = 'admin'

            await self.db.execute("""
                INSERT INTO user_table
                (user_id, access_level, first_name, username)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING;
            """, self.user.id, access_level, self.user.first_name, self.user.username)

            self.db_user = await self.db.fetchrow("""
                        SELECT * FROM user_table
                        WHERE user_id = $1;
                    """, self.user.id)

        self.db_chat = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE chat_id = $1 AND topic = $2;
        """, self.chat.id, self.topic)

        self.access_level = self.db_user['access_level']
         

class CallbackQueryCommand:
    db_user: asyncpg.Record
    db_chat: asyncpg.Record
    addition: asyncpg.Record = None
    access_level: str = None
    got_message_id: int = None

    def __init__(self, callback: CallbackQuery):
        self.callback = callback
        self.chat = callback.message.chat
        self.user = callback.from_user
        self.message = callback.message
        self.sent_message_id = callback.message.message_id
        self.topic = 0 if callback.message.message_thread_id is None else callback.message.message_thread_id
        self.cdata = callback.data

        self.db = utils.db

        self.data_locales = utils.GetLocales('callback_command')
        self.global_texts = self.data_locales.global_texts
        self.texts = self.data_locales.texts
        self.edit_texts = self.texts['edit']
        self.send_texts = self.texts['send']
        self.buttons = self.data_locales.buttons
        self.bot = BotInteraction.BotInter()

    async def async_init(self):
        await self._get_addition_from_db()

        rres = re.fullmatch(r'(folder|info)/[0-9]+/(settings|(show|hide)_hidden|top_message)/|None|admin/tag(s|)/([^/]+/|)', self.cdata)
        if not rres:
            rres1 = re.fullmatch(r'(folder/[0-9]+/|menu/)', self.cdata)
            rres2 = re.fullmatch(r'folder/[0-9]+/((change_title|change_parent|delete)/(1/|)|)', self.cdata)
            rres3 = re.fullmatch(r'(menu/|folder/[0-9]+/(create_folder|create_note)/)', self.cdata)

            res = []

            if rres3 or rres1:
                res = await self.db.fetch("""
                    SELECT * FROM message_table
                    WHERE user_pid = $1
                        AND type in ('note', 'settings_folder', 'hidden_note');
                """, self.db_user['id'])
            elif rres2:
                res = await self.db.fetch("""
                    SELECT * FROM message_table
                    WHERE user_pid = $1
                        AND type in ('note', 'hidden_note', 'menu_folder');
                """, self.db_user['id'])
            else:
                res = await self.db.fetch("""
                    SELECT * FROM message_table
                    WHERE user_pid = $1
                        AND type in ('note', 'settings_folder', 'hidden_note', 'menu_folder', 'distribution_last');
                """, self.db_user['id'])

            for i in res:
                await self.db.execute("""
                    DELETE FROM message_table
                    WHERE id = $1;
                """, i['id'])

            if res:
                msg_ids = [i['message_id'] for i in res]
                try:
                    await self.bot.bot.delete_messages(self.chat.id, msg_ids)
                except:
                    pass


    @abstractmethod
    async def define(self):
        """
        :return: True if this command define and None if not define
        """
        pass

    @abstractmethod
    async def process(self, *args, **kwargs) -> None:
        pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    @abstractmethod
    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def _get_addition_from_db(self):
        self.db_user = await self.db.fetchrow("""
            SELECT * FROM user_table
            WHERE user_id = $1;
        """, self.user.id)

        if self.db_user is None:

            from main import EnvData
            access_level = 'zero'
            if self.user.username in EnvData.ADMIN_LIST:
                access_level = 'admin'

            await self.db.execute("""
                INSERT INTO user_table
                (user_id, access_level, first_name, username)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING;
            """, self.user.id, access_level, self.user.first_name, self.user.username)

            self.db_user = await self.db.fetchrow("""
                        SELECT * FROM user_table
                        WHERE user_id = $1;
                    """, self.user.id)

        self.db_chat = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE chat_id = $1 AND topic = $2;
        """, self.chat.id, self.topic)

        self.access_level = self.db_user['access_level']

        self.addition = await self.db.fetchrow("""
            SELECT * FROM callback_addition_table
            WHERE sent_message_id = $1;
        """, self.sent_message_id)

        self.pressure_info: asyncpg.Record = await self.db.fetchrow("""
            SELECT * FROM pressure_button_table
            WHERE user_pid = $1 AND 
            COALESCE(chat_pid, 1) = COALESCE($2, 1);
        """, self.db_user['id'], None if not self.db_chat else self.db_chat['id'])

        self.got_message_id = self.sent_message_id - 1


class NextCallbackMessageCommand:
    cdata: str
    press_message_id: int

    def __init__(self, message: Message):
        self.message = message
        self.chat = message.chat
        self.user = message.from_user
        self.text = message.text or message.caption or ''
        self.text_low = self.text.lower().strip()
        self.topic = 0 if message.message_thread_id is None else message.message_thread_id

        self.db = utils.db

        self.data_locales = utils.GetLocales('next_callback_message_command')
        self.global_texts = self.data_locales.global_texts
        self.texts = self.data_locales.texts
        self.send_texts = self.texts['send']
        self.call_edit_texts = self.global_texts['callback_command']['edit']
        self.call_send_texts = self.global_texts['callback_command']['send']
        self.buttons = self.data_locales.buttons
        self.bot = BotInteraction.BotInter()

        self.last_message_id = self.message.message_id - 1

    async def async_init(self):
        await self._get_addition_from_db()

    @abstractmethod
    async def define(self):
        pass

    @abstractmethod
    async def process(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def _get_addition_from_db(self):
        self.db_user = await self.db.fetchrow("""
            SELECT * FROM user_table
            WHERE user_id = $1;
        """, self.user.id)

        if self.db_user is None:

            from main import EnvData
            access_level = 'zero'
            if self.user.username in EnvData.ADMIN_LIST:
                access_level = 'admin'

            await self.db.execute("""
                INSERT INTO user_table
                (user_id, access_level, first_name, username)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING;
            """, self.user.id, access_level, self.user.first_name, self.user.username)

            self.db_user = await self.db.fetchrow("""
                        SELECT * FROM user_table
                        WHERE user_id = $1;
                    """, self.user.id)

        self.db_chat = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE chat_id = $1 AND topic = $2;
        """, self.chat.id, self.topic)

        self.pressure_info: asyncpg.Record = await self.db.fetchrow("""
            SELECT * FROM pressure_button_table
            WHERE user_pid = $1 AND 
            COALESCE(chat_pid, 1) = COALESCE($2, 1);
        """, self.db_user['id'], None if not self.db_chat else self.db_chat['id'])

        self.cdata = self.pressure_info['callback_data']
        self.press_message_id = self.pressure_info['message_id']


class MessageReactionCommand:
    def __init__(self, reaction: MessageReactionUpdated):
        self.reaction = reaction
        self.chat = reaction.chat
        self.user = reaction.user
        self.new = False
        self.old = False

        if reaction.new_reaction:
            self.new = True
        else:
            self.old = True

        self.emoji = reaction.new_reaction[-1].emoji if self.new else reaction.old_reaction[-1].emoji

        self.db = utils.db

        self.data_locales = utils.GetLocales('reaction_command')
        self.global_texts = self.data_locales.global_texts
        self.texts = self.data_locales.texts
        self.reactions_text = self.global_texts['reactions']
        self.buttons = self.data_locales.buttons
        self.bot = BotInteraction.BotInter()

        self.message_id = reaction.message_id

    async def async_init(self):
        await self._get_addition_from_db()

    @abstractmethod
    async def define(self):
        pass

    @abstractmethod
    async def process(self, *args, **kwargs) -> None:
        pass

    async def generate_send_message(self, *args, **kwargs) -> TextMessage:
        pass

    async def _get_addition_from_db(self):
        self.db_user = await self.db.fetchrow("""
            SELECT * FROM user_table
            WHERE user_id = $1;
        """, self.user.id)

        if self.db_user is None:

            from main import EnvData
            access_level = 'zero'
            if self.user.username in EnvData.ADMIN_LIST:
                access_level = 'admin'

            await self.db.execute("""
                INSERT INTO user_table
                (user_id, access_level, first_name, username)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO NOTHING;
            """, self.user.id, access_level, self.user.first_name, self.user.username)

            self.db_user = await self.db.fetchrow("""
                        SELECT * FROM user_table
                        WHERE user_id = $1;
                    """, self.user.id)

        self.db_chat = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE chat_id = $1 AND type = 'chat';
        """, self.chat.id)


class InlineQueryCommand:
    def __init__(self, inline: InlineQuery):
        self.inline = inline
        self.query = inline.query
        self.bot = BotInteraction.BotInter()
        self.db = utils.db

    async def async_init(self):
        pass

    @abstractmethod
    async def define(self):
        pass

    @abstractmethod
    async def process(self, *args, **kwargs):
        pass

    @abstractmethod
    async def generate_results(self, *args, **kwargs):
        pass
