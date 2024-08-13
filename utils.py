import asyncio
import json
import os
import datetime
import time
from string import Template
from typing import List
import re

import aiogram
import asyncpg
import httpx
from asyncpg import Record
from dotenv import load_dotenv

import BotInteraction


class DotEnvData:
    BOT_TOKEN: str
    ADMIN_LIST: list
    HOST: str
    PORT: str
    USER: str
    PASSWORD: str
    DATABASE: str

    def __init__(self):
        environ = os.environ
        if environ.get('BOT_TOKEN') is None and environ.get('ADMIN_LIST') is None:
            load_dotenv('.env')
        self.BOT_TOKEN = environ.get('BOT_TOKEN')
        self.ADMIN_LIST = environ.get('ADMIN_LIST').split(' ')
        self.HOST = environ.get('HOST')
        self.PORT = environ.get('PORT')
        self.USER = environ.get('USER')
        self.PASSWORD = environ.get('PASSWORD')
        self.DATABASE = environ.get('DATABASE')


class GetLocales:
    global_texts: dict
    texts: dict
    buttons: dict
    lang: str
    category: str

    def __init__(self, category: str = None, lang: str = 'ru'):
        """
        Класс позволяет получать локали глобальные и более конкретные
        :param category: один из <error>, <message_command>, <callback_command>, <reaction_command>, <inline_command>
        :param lang: <ru> or <en>
        """
        with open('locales.json', 'r') as read:
            data = json.load(read)
            self.global_texts = data[lang]
            self.texts = data[lang][category] if category else None
            self.buttons = data[lang]['buttons']


class UserError:
    method_name: str
    message: str
    message_to_user: str
    texts: dict

    def __init__(self, method_name: str = 'unknown_error', message: str = None, message_to_user: str = None):
        """
        Класс описывающий ошибки, которые необходимо указать пльзователю
        :param method_name:
        :param message:
        :param message_to_user:
        """
        self.method_name = method_name
        self.message = message
        self.message_to_user = message_to_user
        self.texts = GetLocales('errors').texts

        check_attr = hasattr(self, method_name)

        if check_attr is True:
            method = getattr(self, method_name)()
            method()

        else:
            if message and message_to_user:
                pass

            else:
                self.unknown_error()

    def unknown_error(self):
        self.message = 'Unknown error'
        self.message_to_user = self.texts['errors'][self.message]

    def __repr__(self):
        return self.message_to_user

    def __str__(self):
        return self.message_to_user


# noinspection PyAsyncCall
class DataDB:
    conn: asyncpg.connection.Connection

    def __init__(self):
        """
        Класс описывающий взаимодействие с базой данный PostgreSQL
        """

    async def connect(self):
        data = DotEnvData()
        self.conn = await asyncpg.connect(
            host=data.HOST,
            port=data.PORT,
            user=data.USER,
            password=data.PASSWORD,
            database=data.DATABASE,
        )

    async def fetch(self, query, *args) -> List[Record]:
        if self.conn is None:
            raise Exception('Необходимо сначала подключиться к базе данных')
        async with self.conn.transaction():
            result = await self.conn.fetch(query, *args)

        return result

    async def fetchrow(self, query, *args, destroy_timeout: int = 0, table_name: str = None) -> Record:
        """
        :param query:
        :param args:
        :param destroy_timeout: Время удаления записи из бд
        :param table_name: Название таблицы для удаления записи
        :return:
        """
        if self.conn is None:
            raise Exception('Необходимо сначала подключиться к базе данных')
        async with self.conn.transaction():
            result = await self.conn.fetchrow(query, *args)
            if destroy_timeout != 0:
                asyncio.create_task(self._destroy(
                    table_name=table_name,
                    id_=result['id'],
                    destroy_timeout=destroy_timeout
                ))
        return result

    async def execute(self, query, *args) -> str:
        if self.conn is None:
            raise Exception('Необходимо сначала подключиться к базе данных')
        async with self.conn.transaction():
            result = await self.conn.execute(query, *args)
        return result

    async def reg_tables(self):
        async with self.conn.transaction():
            with open('schema.sql', 'r') as read_file:
                schema = read_file.read()
            await self.execute(schema)

    async def _async_del(self):
        await self.conn.close()

    async def add_story(self,
                        curr_id: int, user_id: int,
                        expr_type: str,
                        before_value: float, after_value: float,
                        message_id: int, expression: str):
        await self.execute("""
            INSERT INTO story_table 
            (currency_pid, user_pid, expr_type, before_value, after_value, message_id, expression)
            VALUES
            ($1, $2, $3, $4, $5, $6, $7)
        """, curr_id, user_id, expr_type, before_value, after_value, message_id, expression)

    async def _destroy(self, table_name: str, id_: int, destroy_timeout: int):
        await asyncio.sleep(destroy_timeout)

        ex = f'DELETE FROM {table_name} WHERE id = {id_};'
        await self.execute(ex)

    def __del__(self):
        asyncio.create_task(self._async_del())


db = DataDB()


def str_to_float(value: str):
    try:
        value = value.replace(',', '.')
        return float(value)
    except:
        return None


def float_to_str(value: float) -> str:
    if int == type(value):
        value = float(value)
    value = str(value)
    split_value = value.split('.')
    before_dot = split_value[0][::-1]

    update_before_dot = []
    while before_dot:
        update_before_dot.append(before_dot[:3])
        before_dot = before_dot[3:]

    update_before_dot = [i[::-1] for i in update_before_dot[::-1]]
    final_before_dot_str = ' '.join(update_before_dot)

    after_dot = split_value[1]

    if after_dot[:2] in ['0', '00']:
        final_after_dot_str = None
    else:
        final_after_dot_str = after_dot[:2]

    if final_after_dot_str:
        return final_before_dot_str + ',' + final_after_dot_str
    else:
        return final_before_dot_str


def markup_generate(buttons: list, variable: list = None, *args, **kwargs) -> aiogram.types.InlineKeyboardMarkup:
    """
    :param buttons: list[list[{button_info}]]
    :param variable: list[int] указывает нужно ли применять вариабельную кнопку под номером int
    :param args: no usage
    :param kwargs: аргументы для вставки в шаблоны |
     cycle=[{}] список словарей с аргументами для кнопки с множественным вызовом
    :return:
    """
    if variable is None:
        variable = []
    button_list_list = []

    for i in buttons:
        button_list_list.append([])

        if i[0].get('cycle') is True:
            var1 = 0
            for ii in kwargs['cycle']:
                for iii in range(len(i)):

                    if var1 == i[0]['row_width']:
                        var1 = 0
                        button_list_list.append([])
                    var1 += 1

                    text = Template(i[iii]['text']).substitute(ii)
                    callback_data = None
                    url = None

                    if i[iii].get('callback_data') is not None:
                        callback_data = Template(i[iii]['callback_data']).substitute(ii)
                    elif i[iii].get('url') is not None:
                        url = Template(i[iii]['url']).substitute(ii)
                    else:
                        raise Exception('Ошибка, нельзя в InlineButton передавать url и callback_data одновременно')

                    button_list_list[-1].append(
                        aiogram.types.InlineKeyboardButton(
                            text=text,
                            url=url,
                            callback_data=callback_data
                        )
                    )

            continue

        for ii in i:

            if ii.get('variable') is not None:
                if ii['variable'] not in variable:
                    continue

            text = Template(ii['text']).substitute(**kwargs)
            callback_data = None
            url = None

            if ii.get('callback_data') is not None:
                callback_data = Template(ii['callback_data']).substitute(**kwargs)
            elif ii.get('get') is not None:
                url = Template(ii['url']).substitute(**kwargs)
            else:
                print(ii)
                raise Exception('Ошибка, нельзя в InlineButton передавать url и callback_data одновременно')

            button_list_list[-1].append(
                aiogram.types.InlineKeyboardButton(
                    text=text,
                    url=url,
                    callback_data=callback_data
                )
            )

    return aiogram.types.InlineKeyboardMarkup(inline_keyboard=button_list_list)


def calculate(expression: str):
    expression = expression.replace(' ', '').replace(',', '.')

    def ccc(expr):
        return f'(({expression[:expr.start() - 1]})*0.01*{expr.group().replace("%", "")})'

    find = re.findall(r'[+*%/^0-9.()-]', expression)
    if not find:
        return False

    try:
        res = float(eval(expression))
        return res
    except SyntaxError:
        pass

    if expression.count('(') != expression.count(')'):
        return False

    for _ in range(expression.count('%')):
        expression = re.sub(r'([0-9.]+%)', ccc, expression, 1)

    try:
        res = float(eval(expression))
        return res
    except:
        return False


def story_generate(story_items: List[Record], days: int = 1) -> str:
    today = datetime.datetime.today().strftime('%Y.%m.%d')

    expr_type_first = story_items[0]['expr_type']

    if expr_type_first == 'create':
        string = f'0 --> {story_items[0]["after_value"]}'
    elif expr_type_first in ['add', 'update']:
        string = f'{story_items[0]["before_value"]} --> {story_items[0]["after_value"]} '
    else:
        string = 'Ошибка'

    for i in story_items[:-1]:
        operation_td = (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y.%m.%d')

        if operation_td != today:
            continue

        expr_type = i['expr_type']
        expr = i['expression'].replace(' ', '').replace(',', '.')

        if expr[0] == '(' and expr[-1]:
            expr = expr[1:-1]

        if expr[0] == '+':
            expr = expr[1:]

        if expr_type == 'add':
            if expr[0] == '-':
                string += f' - {expr[1:]}'
            else:
                string += f' + {expr}'

        elif expr_type == 'update':
            expr += f' = {expr}'

        elif expr_type == 'null':
            expr += f' = 0'

    string += f' = {story_items[-1]["after_value"]}'

    string = re.sub(r'[0-9.]+', lambda x: float_to_str(float(x.group())), string)

    return string


def detail_generate(story_items: List[Record], days: int = 1) -> str:
    today = datetime.datetime.today().strftime('%Y.%m.%d')

    expr_type_first = story_items[0]['expr_type']

    string = ''

    var1 = 0

    for i in story_items:
        operation_td = (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y.%m.%d')

        if operation_td != today:
            continue

        var1 += 1

        expr_type = i['expr_type']
        expr = i['expression'].replace(' ', '').replace(',', '.')

        if expr[0] == '(' and expr[-1]:
            expr = expr[1:-1]

        if expr[0] == '+':
            expr = expr[1:]

        if expr_type == 'add':
            var2 = ''
            if var1 == 1:
                var2 = f'{i["before_value"]} '
            if expr[0] == '-':
                string += f'\n{var2}- {expr[1:]} = {i["after_value"]}'
            else:
                string += f'\n{var2}+ {expr} = {i["after_value"]}'

        elif expr_type == 'update':
            string += f'\n= {i["after_value"]}'

        elif expr_type_first == 'create':
            string += f'0 -> {i["after_value"]}'

    string = re.sub(r'[0-9.]+', lambda x: float_to_str(float(x.group())), string)

    return string


class Tracking:
    address_list = [str]
    user_list: [Record] = None
    last_parse_time: float = time.time()

    def __init__(self):
        self.bot = BotInteraction.BotInter()
        self.text_pattern = GetLocales().global_texts['addition']['new_transaction']

    async def async_init(self):
        self.user_list = await db.fetch("""
            SELECT * FROM user_table
            WHERE tracking = TRUE;
        """)

        count = 0

        while True:
            count += 1
            await asyncio.sleep(1)
            if count == 20:
                self.user_list = await db.fetch("""
                    SELECT * FROM user_table
                    WHERE tracking = TRUE;
                """)
            for user in self.user_list:
                await self._user_addresses_parsing(user)

    async def _user_addresses_parsing(self, user: Record):
        res = await db.fetch("""
            SELECT * FROM crypto_parsing_table
            WHERE status = TRUE and user_pid = $1
        """, user['id'])

        if not res:
            return

        for i in res:
            timedelta = time.time() - self.last_parse_time
            if timedelta < 0.35:
                await asyncio.sleep(0.35 - timedelta)

            status_code, token_transfer = await self._address_parsing(i)

            if status_code == 403:
                await asyncio.sleep(121)

            if token_transfer['from_address'] == i['address']:
                return

            transaction_id = token_transfer['transaction_id']
            if transaction_id == i['last_transaction_id']:
                return
            else:
                await db.execute("""
                    UPDATE crypto_parsing_table
                    SET last_transaction_id = $1
                    WHERE address = $2 and user_pid = $3;
                """, transaction_id, i['address'], i['user_pid'])

            transfer_value = float(token_transfer['quant']) / 1000000

            if transfer_value < i['min_value']:
                return

            timestamp = token_transfer['block_ts'] / 1000
            transfer_datetime = str(datetime.datetime.utcfromtimestamp(timestamp) + datetime.timedelta(hours=3))

            text = Template(self.text_pattern).substitute(
                address=i['address'],
                transaction_link=f'https://tronscan.org/#/transaction/{transaction_id}',
                value=transfer_value,
                datetime=transfer_datetime
            )

            message_obj = BotInteraction.TextMessage(
                chat_id=user['user_id'],
                text=text
            )
            await self.bot.send_text(message_obj)

    @staticmethod
    async def _address_parsing(address_row: Record) -> (int, dict):
        async with httpx.AsyncClient() as client:
            response = await client.get('https://apilist.tronscanapi.com/api/filter/trc20/transfers', params={
                'limit': '1',
                'sort': '-timestamp',
                'count': 'true',
                'filterTokenValue': '0',
                'relatedAddress': address_row['address']
            })

        return response.status_code, response.json()['token_transfers'][0]

    @staticmethod
    async def check_address(address):
        async with httpx.AsyncClient() as client:
            response = await client.get('https://apilist.tronscanapi.com/api/filter/trc20/transfers', params={
                'limit': '1',
                'sort': '-timestamp',
                'count': 'true',
                'filterTokenValue': '0',
                'relatedAddress': address
            })

            if response.json().get('message') == 'some parameters are invalid or out of range':
                return False
            else:
                return True

