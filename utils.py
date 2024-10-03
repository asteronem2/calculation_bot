import asyncio
import json
import os
import datetime
import time
import traceback
from string import Template
from typing import List, Any, Union
import re
import logging

import aiogram
import asyncpg
import httpx
from aiogram.types import FSInputFile
from asyncpg import Record, Pool
from dotenv import load_dotenv

import BotInteraction

class DotEnvData:
    BOT_TOKEN: str
    ADMIN_LIST: list
    DEBUG_CHAT_ID: int
    HOST: str
    PORT: str
    USER: str
    PASSWORD: str
    DATABASE: str
    TRONSCAN_API_KEY: str
    def __init__(self):
        environ = os.environ
        if environ.get('BOT_TOKEN') is None and environ.get('ADMIN_LIST') is None:
            load_dotenv('.env')
        self.BOT_TOKEN = environ.get('BOT_TOKEN')
        self.ADMIN_LIST = environ.get('ADMIN_LIST').split(' ')
        self.DEBUG_CHAT_ID = int(environ.get('DEBUG_CHAT_ID'))
        self.HOST = environ.get('HOST')
        self.PORT = environ.get('PORT')
        self.USER = environ.get('USER')
        self.PASSWORD = environ.get('PASSWORD')
        self.DATABASE = environ.get('DATABASE')
        self.TRONSCAN_API_KEY = environ.get('TRONSCAN_API_KEY')


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
    pool: Pool

    def __init__(self):
        """
        Класс описывающий взаимодействие с базой данный PostgreSQL
        """

    async def connect(self):
        data = DotEnvData()

        self.pool = await asyncpg.create_pool(
            dsn=f'postgres://{data.USER}:{data.PASSWORD}@{data.HOST}:{data.PORT}/{data.DATABASE}?',
            min_size=1,
            max_size=200
        )

    async def fetch(self, query, *args) -> List[Record]:
        if self.pool is None:
            raise Exception('Необходимо сначала подключиться к базе данных')
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch(query, *args)

            return result

    async def fetchrow(self, query, *args, destroy_timeout: int = 0, table_name: str = None) -> Record:
        """
        :param query:
        :param args:
        :param destroy_timeout: Время удаления записи из бд
        :param table_name: Название таблицы для удаления записи
        :return:
        """
        try:
            if self.pool is None:
                raise Exception('Необходимо сначала подключиться к базе данных')
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.fetchrow(query, *args)
                    if destroy_timeout != 0:
                        asyncio.create_task(self._destroy(
                            table_name=table_name,
                            id_=result['id'],
                            destroy_timeout=destroy_timeout
                        ))
                return result
        except Exception as err:
            if err.__str__() == 'cannot perform operation: another operation is in progress':
                pass
            else:
                err_str = traceback.format_exc()
                print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
                print(err_str)
                await log(err_str)

    async def execute(self, query, *args) -> str:
        if self.pool is None:
            raise Exception('Необходимо сначала подключиться к базе данных')
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(query, *args)
            return result

    async def reg_tables(self):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                with open('schema.sql', 'r') as read_file:
                    schema = read_file.read()
                await self.execute(schema)

            from main import bot
            me = await bot.get_me()
            await self.execute("""
                INSERT INTO user_table
                (user_id, access_level, first_name, username)
                VALUES ($1, 'admin', $2, $3)
                ON CONFLICT (user_id) 
                DO UPDATE
                SET access_level = 'admin';
            """, me.id, me.first_name, me.username)

    async def _async_del(self):
        await self.pool.close()

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
DED = DotEnvData()

async def log(message: str, level: str = 'error'):
    if level == 'error':
        logging.error(message)
        try:
            import main
            await main.bot.send_document(DED.DEBUG_CHAT_ID, FSInputFile('logs.log'), disable_notification=True)
            await main.bot.send_message(DED.DEBUG_CHAT_ID, message, disable_notification=True)
        except Exception as err:
            err_str = traceback.format_exc()
            print(f"\033[1;31mERROR:\033[37m {err}\033[0m")
            print(err_str)
        return True
    elif level == 'info':
        logging.info(message)
        return True
    else:
        return False


def str_to_float(value: str):
    try:
        value = value.replace(',', '.')
        return float(value)
    except:
        return None


def float_to_str(value: float, rounding: int = 2) -> str:
    if int == type(value):
        value = float(value)
    value = f'{value:.{rounding}f}'
    split_value = value.split('.')
    before_dot = split_value[0][::-1]



    update_before_dot = []
    while before_dot:
        update_before_dot.append(before_dot[:3])
        before_dot = before_dot[3:]

    update_before_dot = [i[::-1] for i in update_before_dot[::-1]]
    final_before_dot_str = ' '.join(update_before_dot)

    after_dot = split_value[1] if len(split_value) == 2 else '0'

    # for i in range(len(after_dot) - rounding, 1):
    #     if after_dot[-i] in '01234':
    #         after_dot = after_dot[:-(i+1)]
    #     elif after_dot[-i] == '9':
    #         cond = True
    #         num = 0
    #         while cond is True:
    #             if after_dot[-(i+num)] == '9':
    #                 after_dot = after_dot[:-(i+num-1)]
    #             else:
    #                 cond = False
    #     else:
    #         after_dot = after_dot[:-(i + 1)] + str(int(after_dot[-(i + 1)]) + 1)
    zero_max = '0'*(rounding+1)
    zero_list = []
    for i in range(len(zero_max)):
        zero_list.append(zero_max[:i])

    if after_dot[:rounding] in zero_list:
        final_after_dot_str = None
    else:
        final_after_dot_str = after_dot[:rounding]

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

        if i[0].get('cycle'):
            var1 = 0
            for ii in kwargs[i[0].get('cycle')]:
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


def story_generate(story_items: List[Record], chat_id: int, start_date: str= None, end_date: str=None) -> str:
    if not start_date or not end_date:
        start_date = datetime.datetime.today().strftime('%Y-%m-%d')
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')
    print(chat_id)
    link_pattern = Template(f'$sign<a href="https://t.me/c/{str(chat_id)[4:]}/$message_id/">$expression</a>')

    current_story_items = []

    for i in story_items:
        story_datetime = (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
        if start_date <= story_datetime <= end_date:
            if i['status'] is True:
                expr = re.sub(r'(--|\+\+| )|(,)', lambda x: '' if x.group(1) else '.', i['expression']) if i['expression'] else None
                current_story_items.append({
                    'type': i['expr_type'],
                    'expr': expr,
                    'after_value': i['after_value'],
                    'before_value': i['before_value'],
                    'message_id': i['message_id']
                })

    if not current_story_items:
        return False

    string: str = ''

    temp_expr_list = []

    for story_item in current_story_items:
        si_type = story_item['type']

        if si_type == 'add':

            expr = story_item['expr']

            rres1 = re.search(r'^\(*([+-])', expr)
            sign = '+' if not rres1 else (rres1.group(1))

            expr = re.sub(r'^[+-]', '', expr)

            temp_expr_list.append([
                expr,
                story_item['message_id'],
                sign
            ])

        elif si_type == 'update':
            temp_expr_list.append([
                story_item['after_value'],
                story_item['message_id'],
                '-->'
            ])

        elif si_type == 'null':
            temp_expr_list.insert(0, '(')
            temp_expr_list.append(')')
            temp_expr_list.append([
                '*0',
                story_item['message_id'],
                ''
            ])

    for it in temp_expr_list:
        if str == type(it):
            string += it
        elif list == type(it):
            string += link_pattern.substitute(
                expression=it[0],
                message_id=it[1],
                sign=it[2]
            )

    string = '<b>' + str(current_story_items[0]['before_value'] if current_story_items[0]['before_value'] else '0') + '</b>-->' + string

    string += '=<b>' + str(current_story_items[-1]['after_value'] if current_story_items[0]['after_value'] else '0') + '</b>'
    print(string)
    string = re.sub(r'(<a href=.+?>)|( +)', lambda x: x.group(1) or '', string)
    string = re.sub(r'\(([+-]?[0-9.,]+)\)', lambda x: x.group(1), string)
    string = re.sub(r'([+-])[+-]+[^>]', lambda x: x.group(1), string)
    string = re.sub(r'(<a href=.+?>|https://t.me/c/[0-9]+?/[0-9]+?/)|([0-9>])([*+/%-])([0-9<])', lambda x: x.group(1) or f'{x.group(2)} {x.group(3)} {x.group(4)}', string)
    string = re.sub(r"(<a href=.+?>)|([0-9.]{2,})",
                    lambda x: x.group(1) if x.group(1) else float_to_str(float(x.group(2))), string)
    string = re.sub(r'(href=)|(=|-->)', lambda x: x.group(1) or f' {x.group(2)} ', string)
    string = re.sub(r' +', ' ', string)

    print(string)

    return string


def detail_generate(story_items: List[Record], chat_id: int, start_date: str = None, end_date: str = None) -> str:
    if not start_date or not end_date:
        start_date = datetime.datetime.today().strftime('%Y-%m-%d')
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')

    link_pattern = Template(f'\n$sign<a href="https://t.me/c/{str(chat_id)[4:]}/$message_id/">$expression</a> = $value')

    current_story_items = []

    for i in story_items:
        story_datetime = (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
        if start_date <= story_datetime <= end_date:
            if i['status'] is True:
                expr = re.sub(r'(--|\+\+| )|(,)', lambda x: '' if x.group(1) else '.', i['expression']) if i['expression'] else None
                current_story_items.append({
                    'type': i['expr_type'],
                    'expr': expr,
                    'after_value': i['after_value'],
                    'before_value': i['before_value'],
                    'message_id': i['message_id']
                })

    if not current_story_items:
        return False

    string: str = '\n' + '<b>' +str(current_story_items[0]['before_value'] or 'Создание -->') + '</b>'

    for story_item in current_story_items:
        if current_story_items.index(story_item) == len(current_story_items)-1:
            last = True
        else:
            last = False

        si_type = story_item['type']

        if si_type == 'add':
            expr = story_item['expr']

            rres1 = re.search(r'^\(*([+-])', expr)
            sign = '+ ' if not rres1 else (rres1.group(1) + ' ')

            expr = re.sub(r'^[+-]', '', expr)

            string += link_pattern.substitute(
                sign=sign,
                message_id=story_item['message_id'],
                expression=expr,
                value=story_item['after_value'] if not last else f'<b>{story_item["after_value"]}</b>'
            )
        elif si_type == 'update':
            string += link_pattern.substitute(
                sign='--> ',
                message_id=story_item['message_id'],
                expression=story_item['after_value'] if not last else f'<b>{story_item["after_value"]}</b>',
                value=''
            )
        elif si_type == 'null':
            string += link_pattern.substitute(
                sign='',
                message_id=story_item['message_id'],
                expression='0 ' if not last else f'<b>0</b>',
                value=''
            )

    string = re.sub(r'(<a href=.+?>)|( +)', lambda x: x.group(1) or '', string)
    string = re.sub(r'\(([+-]?[0-9.,]+)\)', lambda x: x.group(1), string)
    string = re.sub(r'([+-])[+-]+[^>]', lambda x: x.group(1), string)
    string = re.sub(r'(<a href=.+?>)|([0-9>])([*+/%-])([0-9<])', lambda x: x.group(1) or f'{x.group(2)} {x.group(3)} {x.group(4)}', string)
    string = re.sub(r"(<a href=.+?>)|([0-9.]{2,})",
                    lambda x: x.group(1) if x.group(1) else float_to_str(float(x.group(2))), string)
    string = re.sub(r'(href=)|(=|-->)', lambda x: x.group(1) or f' {x.group(2)} ', string)
    string = re.sub(r' +', ' ', string)

    return string


def volume_generate(story_items: List[Record], chat_id: int, start_date: str = None, end_date: str = None):
    if not start_date or not end_date:
        start_date = datetime.datetime.today().strftime('%Y-%m-%d')
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')

    current_story_items = []

    for i in story_items:
        story_datetime = (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y-%m-%d')
        if start_date <= story_datetime <= end_date:
            if i['status'] is True:
                expr = re.sub(r'(--|\+\+| )|(,)', lambda x: '' if x.group(1) else '.', i['expression']) if i['expression'] else None
                current_story_items.append({
                    'type': i['expr_type'],
                    'expr': expr,
                    'after_value': i['after_value'],
                    'before_value': i['before_value'],
                    'message_id': i['message_id']
                })

    if not current_story_items:
        return False

    string: str = '\n' + str(current_story_items[0]['before_value'] or 'Создание -->')

    for story_item in current_story_items:
        si_type = story_item['type']

        # if si_type == 'add':
        #     expr = story_item['expr']
        #
        #     rres1 = re.search(r'^\(*([+-])', expr)
        #     sign = '+ ' if not rres1 else (rres1.group(1) + ' ')
        #
        #     expr = re.sub(r'^[+-]', '', expr)
        #
        #     string += link_pattern.substitute(
        #         sign=sign,
        #         message_id=story_item['message_id'],
        #         expression=expr,
        #         value=story_item['after_value']
        #     )
        # elif si_type == 'update':
        #     string += link_pattern.substitute(
        #         sign='--> ',
        #         message_id=story_item['message_id'],
        #         expression=story_item['after_value'],
        #         value=''
        #     )
        # elif si_type == 'null':
        #     string += link_pattern.substitute(
        #         sign='',
        #         message_id=story_item['message_id'],
        #         expression='0 ',
        #         value=''
        #     )

    return string


def entities_to_html(text: str, entities: List[aiogram.types.MessageEntity]) -> str:
    plus_len = 0
    if not entities:
        return text
    for ent in entities:
        if ent.type == 'bold':
            tag = 'b'
            pll1 = 1
            pll2 = 1
        elif ent.type == 'italic':
            tag = 'i'
            pll1 = 1
            pll2 = 1
        elif ent.type == 'underline':
            tag = 'u'
            pll1 = 1
            pll2 = 1
        elif ent.type == 'strikethrough':
            tag = 's'
            pll1 = 1
            pll2 = 1
        elif ent.type == 'code':
            tag = 'code'
            pll1 = 4
            pll2 = 4
        elif ent.type == 'blockquote':
            tag = 'blockquote'
            pll1 = 10
            pll2 = 10
        elif ent.type == 'pre':
            tag = 'pre'
            pll1 = 3
            pll2 = 3
        elif ent.type == 'spoiler':
            tag = 'tg_spoiler'
            pll1 = 10
            pll2 = 10
        else:
            continue

        text = text[:ent.offset+plus_len] + f'<{tag}>' + text[ent.offset+plus_len:]
        text = text[:ent.offset+ent.length+plus_len+pll1+2] + f'</{tag}>' + text[ent.offset+ent.length+plus_len+pll1+2:]

        plus_len += 5 + pll1 + pll2

    return text


def calendar(weeks: int = 4):
    today = datetime.datetime.today()
    today_weekday = today.weekday()

    def day_delta(delta: int, date: datetime.datetime = today):
        return date + datetime.timedelta(days=delta)

    dates_list = []

    start_week_date = day_delta(-today_weekday)
    end_date = day_delta(6-today_weekday)
    start_date = day_delta(-7*(weeks-1), start_week_date)


    cycle_date = start_date
    while True:
        text = str(cycle_date.day)
        use = True
        if cycle_date > today:
            use = False
            text = ''.join([i + '\u0336' for i in text]) + '\u0336'

        dates_list.append({
            'date': str(cycle_date.strftime('%Y-%m-%d')),
            'use': use,
            'text': text
        })

        if cycle_date == end_date:
            break

        cycle_date = day_delta(1, cycle_date)

    return dates_list


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
            try:
                count += 1
                await asyncio.sleep(2)
                if count == 20:
                    self.user_list = await db.fetch("""
                        SELECT * FROM user_table
                        WHERE tracking = TRUE;
                    """)
                for user in self.user_list:
                    await self._user_addresses_parsing(user)
            except Exception as err:
                count += 1
                await asyncio.sleep(5)

    async def _user_addresses_parsing(self, user: Record):
        self.res = await db.fetch("""
            SELECT * FROM crypto_parsing_table
            WHERE status = TRUE and user_pid = $1
        """, user['id'])


        if not self.res:
            return

        for i in self.res:
            timedelta = time.time() - self.last_parse_time
            if timedelta < 1:
                await asyncio.sleep(1 - timedelta)

            status_code, token_transfer, response = await self._address_parsing(i)

            if status_code == 403:
                await log(str(response.json()))
                await asyncio.sleep(121)

            if token_transfer['from_address'] == i['address']:
                continue

            transaction_id = token_transfer['transaction_id']
            if transaction_id == i['last_transaction_id']:
                continue
            else:
                await db.execute("""
                    UPDATE crypto_parsing_table
                    SET last_transaction_id = $1
                    WHERE address = $2 and user_pid = $3;
                """, transaction_id, i['address'], i['user_pid'])

            transfer_value = float(token_transfer['quant']) / 1000000

            if transfer_value < i['min_value']:
                continue

            timestamp = token_transfer['block_ts'] / 1000
            transfer_datetime = str(datetime.datetime.utcfromtimestamp(timestamp) + datetime.timedelta(hours=3))

            text = Template(self.text_pattern).substitute(
                address=i['address'],
                transaction_link=f'https://tronscan.org/#/transaction/{transaction_id}',
                value=float_to_str(float(transfer_value)),
                datetime=transfer_datetime
            )

            message_obj = BotInteraction.TextMessage(
                chat_id=user['user_id'],
                text=text
            )

            await self.bot.send_text(message_obj)
            await asyncio.sleep(1)
            return

    @staticmethod
    async def _address_parsing(address_row: Record) -> (int, dict):
        async with httpx.AsyncClient() as client:
            response = await client.get('https://apilist.tronscanapi.com/api/filter/trc20/transfers',
                                        params={
                'limit': '1',
                'sort': '-timestamp',
                'count': 'true',
                'filterTokenValue': '0',
                'relatedAddress': address_row['address']
            },
                                        headers={'TRON-PRO-API-KEY': DED.TRONSCAN_API_KEY} if DED.TRONSCAN_API_KEY else None)

        return response.status_code, response.json()['token_transfers'][0], response

    @staticmethod
    async def check_address(address):
        async with httpx.AsyncClient() as client:
            print('sadasdasdsadasdasd')
            response = await client.get('https://apilist.tronscanapi.com/api/filter/trc20/transfers',
                                        params={
                                            'limit': '1',
                                            'sort': '-timestamp',
                                            'count': 'true',
                                            'filterTokenValue': '0',
                                            'relatedAddress': address
                                        },
                                        headers={'TRON-PRO-API-KEY': DED.TRONSCAN_API_KEY} if DED.TRONSCAN_API_KEY else None)
            print(response)
            print(response.json())
            print(DED.TRONSCAN_API_KEY)
            if response.json().get('message') == 'some parameters are invalid or out of range':
                return False
            else:
                return True
