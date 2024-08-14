from abc import abstractmethod

import asyncpg
from aiogram.types.message import Message
from aiogram.types.callback_query import CallbackQuery
from aiogram.types.message_reaction_updated import MessageReactionUpdated
from aiogram.types.inline_query import InlineQuery

import BotInteraction
import utils


class MessageCommand:
    db_user: asyncpg.Record
    db_chat: asyncpg.Record
    access_level: str = None

    def __init__(self, message: Message):
        self.message = message
        self.chat = message.chat
        self.user = message.from_user
        self.text = message.text
        self.text_low = message.text.lower().strip()
        self.topic = 0 if message.message_thread_id is None else message.message_thread_id

        self.db = utils.db

        self.data_locales = utils.GetLocales('message_command')
        self.global_texts = self.data_locales.global_texts
        self.texts = self.data_locales.texts
        self.buttons = self.data_locales.buttons
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

        self.got_message_id = self.sent_message_id - 1


class NextCallbackMessageCommand:
    cdata: str
    press_message_id: int

    def __init__(self, message: Message):
        self.message = message
        self.chat = message.chat
        self.user = message.from_user
        self.text = message.text
        self.text_low = message.text.lower().strip()
        self.topic = 0 if message.message_thread_id is None else message.message_thread_id

        self.db = utils.db

        self.data_locales = utils.GetLocales('next_callback_message_command')
        self.global_texts = self.data_locales.global_texts
        self.texts = self.data_locales.texts
        self.send_texts = self.texts['send']
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

    @abstractmethod
    async def define(self):
        pass

    @abstractmethod
    async def send_error(self):
        pass


class InlineQueryCommand:
    def __init__(self, inline: InlineQuery):
        self.inline = inline
        self.query = inline.query
        self.bot = BotInteraction.BotInter()

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
