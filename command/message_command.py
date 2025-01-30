import datetime
import inspect
import os
import re
import sys
from string import Template
from typing import List

from aiogram.types import InlineKeyboardMarkup as IMarkup, InlineKeyboardButton as IButton, FSInputFile

import BotInteraction
from command.command_interface import MessageCommand

from BotInteraction import TextMessage, EditMessage
from utils import str_to_float, float_to_str, markup_generate, calculate, detail_generate, detail_generate, Tracking, \
    story_generate, entities_to_html, volume_generate, calendar


class StartCommand(MessageCommand):
    async def define(self):
        rres = re.fullmatch(rf'{self.keywords["StartCommand"]}', self.text)
        if rres:
            await self.process()
            return True
        return None

    async def process(self, **kwargs):
        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs):
        text = Template(self.texts['StartCommand']).substitute(
            first_name=self.message.from_user.first_name
        )
        return TextMessage(chat_id=self.chat.id,
                           text=text,
                           message_thread_id=self.topic)

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


# Команды для админов в группе
class UnlockChatCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'supergroup':
            if self.access_level == 'admin':
                rres = re.fullmatch(rf'{self.keywords["UnlockChatCommand"]}', self.text_low)
                if rres:
                    res = await self.db.fetchrow("""
                        SELECT * FROM chat_table
                        WHERE chat_id = $1 AND type = 'chat';
                    """, self.chat.id)

                    if res:
                        if not self.db_chat or (self.db_chat and self.db_chat['locked'] is True):
                            await self.process()
                            return True
                    else:
                        if self.topic == 0:
                            await self.process()
                            return True

    async def process(self, **kwargs) -> None:
        link = await self.bot.get_link(self.chat.id)

        chat_type = 'chat'
        if self.topic != 0:
            chat_type = 'topic'

        res = await self.db.fetchrow("""
            SELECT COUNT(*)
            FROM chat_table
            WHERE chat_id = $1;
        """, self.chat.id)

        if res['count'] != 0 and self.db_chat:
            if self.db_chat['topic'] == self.db_chat['main_topic']:
                link = await self.bot.get_link(self.chat.id)
                print(link)
                await self.db.execute("""
                    UPDATE chat_table
                    SET locked = FALSE, link = $1
                    WHERE chat_id = $2;
                """, link, self.chat.id)
            else:
                await self.db.execute("""
                    UPDATE chat_table
                    SET locked = FALSE
                    WHERE chat_id = $1 AND topic = $2; 
                """, self.chat.id, self.topic)

        else:
            await self.db.execute("""
                INSERT INTO chat_table
                (chat_id, type, topic, code_name, title, link, locked, super, pin_balance)
                VALUES ($1, $2, $3, $4, $5, $6, FALSE, FALSE, $7);
            """, self.chat.id, chat_type, self.topic, str(self.chat.id), self.chat.title, link, False if self.topic == 0 else True)

        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['UnlockChatCommand']).substitute(
            title=self.chat.title
        )
        return TextMessage(self.chat.id, text, self.topic)

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class LockChatCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(rf'{self.keywords["LockChatCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, **kwargs) -> None:

        if self.db_chat['topic'] == self.db_chat['main_topic']:
            await self.db.execute("""            
                UPDATE chat_table
                SET locked = TRUE
                WHERE chat_id = $1;
            """, self.chat.id)

        else:
            await self.db.execute("""
                UPDATE chat_table
                SET locked = TRUE
                WHERE chat_id = $1 and topic = $2;
            """, self.chat.id, self.topic)

        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['LockChatCommand']).substitute(
            title=self.chat.title
        )
        return TextMessage(self.chat.id, text, self.topic)

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class CreateCurrencyCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                if not self.text.count('\n'):
                    rres = re.fullmatch(r'([^ ]+) = ([0-9.,-]+) ?([^ ]*)', self.text)
                    if rres:
                        title, value, postfix = rres.groups()
                        rres2 = re.search(r'[а-яА-Яa-zA-Z]', title)
                        if rres2:
                            await self.process(title=title, value=value, postfix=postfix)
                            return True

    async def process(self, **kwargs) -> None:
        split_text = self.text_low.split(' ')
        title = kwargs['title'].lower()
        value = str_to_float(kwargs['value'])
        postfix = kwargs['postfix'] if kwargs['postfix'] else None

        before_res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE chat_pid = (SELECT id FROM chat_table WHERE type = 'chat' AND chat_id = $1 LIMIT 1)
            AND title = $2
        """, self.chat.id, title)

        after_res = await self.db.fetchrow("""
            INSERT INTO currency_table
            (chat_pid, title, value, postfix) VALUES
            ((SELECT id FROM chat_table WHERE type = 'chat' AND chat_id = $1 LIMIT 1), $2, $3, $4)
            ON CONFLICT (chat_pid, title) DO
            UPDATE SET value = $3, postfix = $4
            RETURNING *;
        """, self.chat.id, title, value, postfix)

        message_obj = await self.generate_send_message(**{
            'title': title,
            'value': value,
            'postfix': postfix
        })
        sent_message = await self.bot.send_text(message_obj)

        await self.db.add_story(
            curr_id=after_res['id'],
            user_id=self.db_user['id'],
            expr_type='create' if not before_res else 'update',
            before_value=None if not before_res else before_res['value'],
            after_value=after_res['value'],
            message_id=self.message.message_id,
            expression=split_text[2],
            sent_message_id=sent_message.message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['CreateCurrencyCommand']).substitute(
            title=kwargs['title'].upper(),
            value=float_to_str(kwargs['value']),
            postfix=kwargs['postfix'] if kwargs['postfix'] else ''
        )
        return TextMessage(chat_id=self.chat.id, text=text, message_thread_id=self.topic)

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class EditCurrencyCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(r'\*(.+)', self.text_low)
                if rres:
                    r_curr = rres.group(1)

                    res = await self.db.fetch("""
                        SELECT currency_table.title 
                        FROM currency_table
                        JOIN chat_table ON chat_table.id = currency_table.chat_pid
                        WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                        ORDER BY currency_table.title ASC; 
                    """, self.chat.id)

                    curr_list = [i['title'] for i in res]

                    for i in curr_list:
                        if i == r_curr:
                            await self.process(**{'title': i})
                            return True

    async def process(self, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        sent_message = await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['EditCurrencyCommand']).substitute(
            title=kwargs['title'].upper()
        )

        res = await self.db.fetchrow("""
            SELECT currency_table.* FROM currency_table
            JOIN chat_table ON currency_table.chat_pid = chat_table.id
            WHERE currency_table.title = $1
            AND chat_table.chat_id = $2
            AND chat_table.type = 'chat';
        """, kwargs['title'], self.chat.id)

        markup = markup_generate(
            buttons=self.buttons['EditCurrencyCommand'],
            curr_id=res['id'],
            rounding=res['rounding'],
            chat_id=res['chat_pid']
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
            markup=markup,
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class EditChatThemeCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(rf'{self.keywords["EditChatThemeCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['EditChatThemeCommand']).substitute()

        res = await self.db.fetchrow("""
            SELECT id, topic, main_topic FROM chat_table
            WHERE id = $1;
        """, self.db_chat['id'])

        variable = []
        if res['topic'] != res['main_topic']:
            variable.append('1')
        chat_id = res['id']

        if self.db_chat['sign'] is False:
            variable.append('photo-')
        else:
            variable.append('photo+')

        if self.db_chat['pin_balance'] is True:
            variable.append('pin_balance')
        else:
            variable.append('unpin_balance')

        rres = re.findall(r'([^|]+?)\|', self.db_chat['answer_mode'])

        if 'forward' in rres:
            if 'non_forward' in rres:
                variable.append('forward|non_forward')
            else:
                variable.append('forward')
        else:
            if 'non_forward' in rres:
                variable.append('non_forward')

        if 'reply' in rres:
            if 'non_reply' in rres:
                variable.append('reply|non_reply')
            else:
                variable.append('reply')
        else:
            if 'non_reply' in rres:
                variable.append('non_reply')

        if 'quote' in rres:
            if 'non_quote' in rres:
                variable.append('quote|non_quote')
            else:
                variable.append('quote')
        else:
            if 'non_quote' in rres:
                variable.append('non_quote')


        markup = markup_generate(
            self.buttons['EditChatThemeCommand'],
            chat_id=chat_id,
            topic=self.topic,
            variable=variable
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
            markup=markup,
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


# Команды для сотрудников в группе
class BalanceListCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'{self.keywords["BalanceListCommand"]}|{self.keywords["BalanceListCommand"]}ы', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, **kwargs) -> None:
        res = await self.db.fetch("""
            SELECT currency_table.* 
            FROM currency_table
            JOIN chat_table ON chat_table.id = currency_table.chat_pid
            WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
            ORDER BY currency_table.title ASC;
        """, self.chat.id)
        if res:
            message_obj = await self.generate_send_message(res)
        else:
            message_obj = await self.generate_error_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        curr_info_list = ''

        for i in args[0]:
            var = Template(self.global_texts['addition']['little_balance']).substitute(
                title=i['title'].upper(),
                value=float_to_str(i['value'], i['rounding']),
                postfix=i['postfix'] if i['postfix'] else ''
            )
            curr_info_list += var

        text = Template(self.texts['BalanceListCommand']).substitute(
            curr_info_list=curr_info_list
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )

    async def generate_error_message(self, *args, **kwargs):
        text = '<b>В данном чате нет валют</b>'
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CurrencyCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                res = await self.db.fetch("""
                    SELECT currency_table.*
                    FROM currency_table
                    JOIN chat_table ON chat_table.id = currency_table.chat_pid
                    WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                    ORDER BY currency_table.title ASC; 
                """, self.chat.id)
                for i in res:
                    if self.text_low == i['title']:
                        await self.process(curr=i)
                        return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['CurrencyBalance']).substitute(
            title=kwargs['curr']['title'].upper(),
            value=float_to_str(kwargs['curr']['value'], kwargs['curr']['rounding']),
            postfix=kwargs['curr']['postfix'] if kwargs['curr']['postfix'] else ''
        )

        markup = markup_generate(
            buttons=self.global_texts['buttons']['CurrencyBalanceCommand'],
            curr_id=kwargs['curr']['id']
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
            markup=markup,
            button_destroy=20
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class CurrencyCalculationCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(r'(.+) +([*+%/0-9., ()-]+)', self.text_low)
                if rres:
                    curr, expr = rres.groups()
                    if self.photo is True and self.db_chat['sign'] is False:
                        expr = f'-({expr})'

                    calc_res = calculate(expr)
                    if calc_res is not False:

                        res = await self.db.fetch("""
                            SELECT currency_table.*
                            FROM currency_table
                            JOIN chat_table ON chat_table.id = currency_table.chat_pid
                            WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                            ORDER BY currency_table.title ASC; 
                        """, self.chat.id)

                        for i in res:
                            if curr == i['title']:
                                await self.process(
                                    curr=i,
                                    calc_res=calc_res,
                                    expr=expr
                                )
                                return True

    async def process(self, *args, **kwargs) -> None:
        new_value = kwargs['curr']['value'] + kwargs['calc_res']

        res = await self.db.fetchrow("""
            UPDATE currency_table
            SET value = $1
            WHERE id = $2
            RETURNING *;
        """, new_value, kwargs['curr']['id'])

        message_obj = await self.generate_send_message(new_value=new_value, **kwargs)
        sent_message = await self.bot.send_text(message_obj)

        await self.db.add_story(
            curr_id=res['id'],
            user_id=self.db_user['id'],
            expr_type='add',
            before_value=kwargs['curr']['value'],
            after_value=new_value,
            message_id=self.message.message_id,
            expression=kwargs['expr'],
            sent_message_id=sent_message.message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['CurrencyBalance']).substitute(
            title=kwargs['curr']['title'].upper(),
            value=float_to_str(kwargs['new_value'], kwargs['curr']['rounding']),
            postfix=kwargs['curr']['postfix'] if kwargs['curr']['postfix'] else ''
        )

        pin, thread = False, self.topic

        if self.db_chat['pin_balance'] is True:
            pin, thread = True, self.db_chat['main_topic']


        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=thread,
            pin=pin
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class CalculationCommand(CurrencyCalculationCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(r'[*+%/0-9., ()=\n-]+', self.text_low)
                if rres:
                    expr = rres.group()
                    if self.text.count('\n'):
                        expr = expr.split('\n')[-1]
                    else:
                        expr = expr.split('=')[-1]
                    if self.photo is True and self.db_chat['sign'] is False:
                        expr = f'-({expr})'
                    calc_res = calculate(expr)
                    if calc_res is not False:
                        res = await self.db.fetch("""
                                SELECT currency_table.*
                                FROM currency_table
                                JOIN chat_table ON chat_table.id = currency_table.chat_pid
                                WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                                ORDER BY currency_table.title ASC; 
                            """, self.chat.id)
                        if res:
                            answer_mode_list = re.findall(r'([^/]+?)\|', self.db_chat['answer_mode'])
                            if self.message.forward_origin:
                                if 'forward' not in answer_mode_list:
                                    return
                            else:
                                if 'non_forward' not in answer_mode_list:
                                    return

                            if self.message.quote:
                                if 'quote' not in answer_mode_list:
                                    return
                            else:
                                if 'non_quote' not in answer_mode_list:
                                    return

                            if not self.message.quote:
                                if self.message.reply_to_message:
                                    if 'reply' not in answer_mode_list:
                                        return
                                else:
                                    if 'non_reply' not in answer_mode_list:
                                        return

                            await self.process(res=res, calc_res=calc_res, expr=expr)
                            return True

    async def process(self, *args, **kwargs) -> None:
        if len(kwargs['res']) == 1:
            await super().process(
                curr=kwargs['res'][0],
                **kwargs
            )
        else:
            destroy_timeout = 10
            message_obj = await self.generate_send_message(**kwargs, destroy_timeout=destroy_timeout)
            sent_message = await self.bot.send_text(message_obj)
            await self.db.fetchrow("""
                INSERT INTO callback_addition_table
                (chat_pid, user_pid, got_message_id, sent_message_id, type, addition_info)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *;
            """, self.db_chat['id'], self.db_user['id'], self.message.message_id, sent_message.message_id, 'add', kwargs['expr'],
                                  destroy_timeout=destroy_timeout,
                                  table_name='callback_addition_table')

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs.get('res') and len(kwargs['res']) == 1:
            return await super().generate_send_message(**kwargs)
        else:
            text = Template(self.texts['CalculationCommand']).substitute(
                expression=kwargs['expr']
            )

            currencies = [{'title': i['title'], 'curr_id': i['id']} for i in kwargs['res']]

            markup = markup_generate(
                buttons=self.global_texts['buttons']['CalculationCommand'],
                cycle=currencies,
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup,
                destroy_timeout=kwargs['destroy_timeout']
            )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error'][kwargs['error']]).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CurrencyStoryCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'(.+) +{self.keywords["StoryCommand"]}', self.text_low)
                if rres:
                    curr = rres.group(1)
                    res = await self.db.fetch("""
                        SELECT currency_table.*
                        FROM currency_table
                        JOIN chat_table ON chat_table.id = currency_table.chat_pid
                        WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                        ORDER BY currency_table.title ASC; 
                    """, self.chat.id)

                    for i in res:
                        if curr == i['title']:
                            await self.process(curr_id=i['id'], title=i['title'], postfix=i['postfix'])
                            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        sent = await self.bot.send_text(message_obj)
        await self.db.execute("""
            INSERT INTO message_table
            (user_pid, chat_pid, message_id, type, addition)
            VALUES ($1, $2, $3, 'story', $4);
        """, self.db_user['id'], self.db_chat['id'], sent.message_id, str(kwargs['curr_id']))

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND status = TRUE;
        """, kwargs['curr_id'])

        today_story = []

        today = datetime.datetime.today().strftime('%Y.%m.%d')

        for i in res:
            story_dt = (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y.%m.%d')
            if story_dt == today:
                today_story.append(i)

        if not today_story:
            return await self.generate_error_message(**kwargs)

        sel = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        before_first_story = await self.db.fetchrow("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND id < $2
            ORDER BY id DESC
            LIMIT 1;
        """, today_story[0]["currency_pid"], today_story[0]["id"])

        story = story_generate(story_list=today_story, chat_id=self.chat.id, rounding=sel['rounding'])

        text = Template(self.texts['CurrencyStoryCommand']).substitute(
            title=kwargs['title'].upper(),
            story=story,
            postfix=kwargs['postfix'] if kwargs.get('postfix') else ''
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
            reply_to_message_id=before_first_story["sent_message_id"] if before_first_story else None
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['NoCurrencyStoryToday']).substitute(
            title=kwargs['title'].upper()
        )
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class StoryCommand(CurrencyStoryCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'{self.keywords["StoryCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:
        chat_id = kwargs.get('chat_id')

        if not chat_id:
            chat_id = self.chat.id

        res = await self.db.fetch("""
            SELECT currency_table.*
            FROM currency_table
            JOIN chat_table ON chat_table.id = currency_table.chat_pid
            WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
            ORDER BY currency_table.title ASC; 
        """, chat_id)

        if len(res) == 1:
            await super().process(
                title=res[0]['title'],
                curr_id=res[0]['id'],
                postfix=res[0]['postfix'],
                res=res,
                **kwargs
            )
        elif len(res) == 0:
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
        else:
            destroy_timeout = 10
            message_obj = await self.generate_send_message(res=res, destroy_timeout=destroy_timeout, **kwargs)
            await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs.get('res') and len(kwargs['res']) == 1:
            return await super().generate_send_message(**kwargs)
        else:
            story_list = [{'title': i['title'], 'curr_id': i['id']} for i in kwargs['res']]

            markup = markup_generate(
                buttons=self.global_texts['buttons']['StoryCommand'],
                cycle=story_list
            )

            text = Template(self.global_texts['message_command']['StoryCommand']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup,
                destroy_timeout=kwargs['destroy_timeout']
            )

    async def generate_error_message(self, *args, **kwargs):
        text = Template(self.global_texts['error']['ZeroCurrencies']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CurrencyVolumeCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'(.+) +{self.keywords["VolumeCommand"]}', self.text_low.replace('е', 'ё'))
                if rres:
                    curr = rres.group(1)
                    res = await self.db.fetch("""
                        SELECT currency_table.*
                        FROM currency_table
                        JOIN chat_table ON chat_table.id = currency_table.chat_pid
                        WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                        ORDER BY currency_table.title ASC; 
                    """, self.chat.id)

                    for i in res:
                        if curr == i['title']:
                            await self.process(curr_id=i['id'], title=i['title'])
                            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj1 = await CurrencyStoryCommand.generate_send_message(self, **kwargs)
        await self.bot.send_text(message_obj1)

        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND status = TRUE;
        """, kwargs['curr_id'])

        res2 = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        story = story_generate(res, chat_id=self.chat.id, rounding=res2['rounding'])

        volume = volume_generate(story, rounding=res2['rounding'])

        text = Template(self.global_texts['message_command']['CurrencyVolumeCommand']).substitute(
            title=res2['title'].upper(),
            volume=volume
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['NoCurrencyVolumeToday']).substitute(
            title=kwargs['title'].upper()
        )
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class VolumeCommand(CurrencyVolumeCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'{self.keywords["VolumeCommand"]}', self.text_low.replace('е', 'ё'))
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:
        chat_id = kwargs.get('chat_id')

        if not chat_id:
            chat_id = self.chat.id

        res = await self.db.fetch("""
            SELECT currency_table.*
            FROM currency_table
            JOIN chat_table ON chat_table.id = currency_table.chat_pid
            WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
            ORDER BY currency_table.title ASC; 
        """, chat_id)

        if len(res) == 1:
            await super().process(
                title=res[0]['title'],
                curr_id=res[0]['id'],
                res=res,
                **kwargs
            )
        elif len(res) == 0:
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
        else:
            destroy_timeout = 10
            message_obj = await self.generate_send_message(res=res, destroy_timeout=destroy_timeout, **kwargs)
            await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs.get('res') and len(kwargs['res']) == 1:
            return await super().generate_send_message(**kwargs)
        else:
            story_list = [{'title': i['title'], 'curr_id': i['id']} for i in kwargs['res']]

            markup = markup_generate(
                buttons=self.global_texts['buttons']['VolumeCommand'],
                cycle=story_list
            )

            text = Template(self.global_texts['message_command']['VolumeCommand']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup,
                destroy_timeout=kwargs['destroy_timeout']
            )

    async def generate_error_message(self, *args, **kwargs):
        text = Template(self.global_texts['error']['ZeroCurrencies']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CurrencyDetailCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'(.+) +{self.keywords["DetailCommand"]}', self.text_low)
                if rres:
                    curr = rres.group(1)
                    res = await self.db.fetch("""
                        SELECT currency_table.*
                        FROM currency_table
                        JOIN chat_table ON chat_table.id = currency_table.chat_pid
                        WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                        ORDER BY currency_table.title ASC; 
                    """, self.chat.id)

                    for i in res:
                        if curr == i['title']:
                            await self.process(curr_id=i['id'], title=i['title'])
                            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        sent = await self.bot.send_text(message_obj)

        await self.db.execute("""
            INSERT INTO message_table
            (user_pid, chat_pid, message_id, type, addition)
            VALUES ($1, $2, $3, 'detail', $4);
        """, self.db_user['id'], self.db_chat['id'], sent.message_id, str(kwargs['curr_id']))

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND status = TRUE
            ORDER BY id ASC;
        """, kwargs['curr_id'])

        res2 = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        today_story = []

        today = datetime.datetime.today().strftime('%Y.%m.%d')

        for i in res:
            story_dt = (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y.%m.%d')
            if story_dt == today:
                today_story.append(i)

        if not today_story:
            return await self.generate_error_message(**kwargs)

        detail = detail_generate(today_story, chat_id=self.chat.id, rounding=res2["rounding"])

        before_first_story = await self.db.fetchrow("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND id < $2
            ORDER BY id DESC
            LIMIT 1;
        """, today_story[0]["currency_pid"], today_story[0]["id"])

        text = Template(self.texts['CurrencyDetailCommand']).substitute(
            title=kwargs['title'].upper(),
            detail=detail
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
            reply_to_message_id=before_first_story["sent_message_id"] if before_first_story else None
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['NoCurrencyDetailToday']).substitute(
            title=kwargs['title'].upper()
        )
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class DetailCommand(CurrencyDetailCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'{self.keywords["DetailCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:

        res = await self.db.fetch("""
            SELECT currency_table.*
            FROM currency_table
            JOIN chat_table ON chat_table.id = currency_table.chat_pid
            WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
            ORDER BY currency_table.title ASC; 
        """, self.chat.id)

        if len(res) == 1:
            await super().process(
                title=res[0]['title'],
                curr_id=res[0]['id'],
                res=res,
                **kwargs
            )
        elif len(res) == 0:
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
        else:
            destroy_timeout = 10
            message_obj = await self.generate_send_message(res=res, destroy_timeout=destroy_timeout, **kwargs)
            sent_message = await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs.get('res') and len(kwargs['res']) == 1:
            return await super().generate_send_message(**kwargs)
        else:
            story_list = [{'title': i['title'], 'curr_id': i['id']} for i in kwargs['res']]

            markup = markup_generate(
                buttons=self.global_texts['buttons']['DetailCommand'],
                cycle=story_list
            )

            text = Template(self.texts['DetailCommand']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup,
                destroy_timeout=kwargs['destroy_timeout']
            )

    async def generate_error_message(self, *args, **kwargs):
        text = Template(self.global_texts['error']['ZeroCurrencies']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CancelCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'{self.keywords["CancelCommand"]}', self.text_low)
                if rres:
                    if not self.message.reply_to_message:
                        await self.process()
                        return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetch("""
            SELECT 
                story_table.expr_type AS story__expr_type,
                story_table.before_value AS story__before_value,
                story_table.expression AS story__expression,
                story_table.message_id AS story__message_id,
                story_table.id AS story__id,
                currency_table.title AS currency__title,
                currency_table.postfix AS currency__postfix,
                currency_table.rounding AS currency__rounding
                
            FROM story_table
            JOIN currency_table ON story_table.currency_pid = currency_table.id
            JOIN chat_table ON currency_table.chat_pid = chat_table.id 
            WHERE chat_table.chat_id = $1 AND story_table.status = TRUE;
        """, self.chat.id)

        if len(res) == 0:
            message_obj = await self.generate_error_message(pattern='ZeroStory')
            await self.bot.send_text(message_obj)
        else:
            last_res = res[-1]
            if last_res['story__expr_type'] == 'create':
                message_obj = await self.generate_error_message(pattern='ErrorDeleteStoryCurrencyCreating')
                await self.bot.send_text(message_obj)
            else:
                await self.db.execute("""
                    UPDATE currency_table
                    SET value = $1
                    WHERE title = $2
                    AND chat_pid = (SELECT id FROM chat_table WHERE type = 'chat' AND chat_id = $3);
                """, last_res['story__before_value'], last_res['currency__title'], self.chat.id)

                await self.db.execute("""
                    UPDATE story_table
                    SET status = FALSE
                    WHERE id = $1 AND status = TRUE;
                """, last_res['story__id'])

                message_obj = await self.generate_send_message(last_res=res[-1])
                await self.bot.send_text(message_obj)
                pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        expr_link = 'https://t.me/c/{chat_id}/{msg_id}'.format(
            chat_id=str(self.chat.id)[4:],
            msg_id=str(kwargs['last_res']['story__message_id'])
        )

        expression = kwargs['last_res']['story__expression'] \
            if kwargs['last_res']['story__expr_type'] != 'null' else 'обнуление'

        text = Template(self.texts['CancelCommand']).substitute(
            expr_link=expr_link,
            expression=expression,
            title=kwargs['last_res']['currency__title'].upper(),
            value=float_to_str(kwargs['last_res']['story__before_value'], kwargs['last_res']['currency__rounding']),
            postfix=kwargs['last_res']['currency__postfix'] if kwargs['last_res']['currency__postfix'] else ''
        )

        pin, thread = False, self.topic

        if self.db_chat['pin_balance'] is True:
            pin, thread = True, self.db_chat['main_topic']


        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=thread,
            pin=pin
        )

    async def generate_error_message(self, *args, **kwargs):
        text = Template(self.global_texts['error'][kwargs['pattern']]).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CurrencyNullCommand(MessageCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(r'0 +(.+)', self.text_low)
                if rres:
                    curr = rres.group(1)

                    res = await self.db.fetch("""
                        SELECT currency_table.*
                        FROM currency_table
                        JOIN chat_table ON chat_table.id = currency_table.chat_pid
                        WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
                        ORDER BY currency_table.title ASC; 
                    """, self.chat.id)

                    for i in res:
                        if i['title'] == curr:
                            await self.process(
                                title=i['title'],
                                value=i['value'],
                                postfix=i['postfix'],
                                curr_id=i['id']
                            )
                            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE currency_table
            SET value = 0.0
            WHERE id = $1;
        """, kwargs['curr_id'])

        message_obj = await self.generate_send_message(**kwargs)
        sent_message = await self.bot.send_text(message_obj)

        await self.db.add_story(
            curr_id=kwargs['curr_id'],
            user_id=self.db_user['id'],
            expr_type='null',
            before_value=kwargs['value'],
            after_value=0.0,
            message_id=self.message.message_id,
            expression=None,
            sent_message_id=sent_message.message_id
        )


    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['CurrencyBalance']).substitute(
            title=kwargs['title'].upper(),
            value='0',
            postfix=kwargs['postfix'] if kwargs['postfix'] else ''
        )

        pin, thread = False, self.topic

        if self.db_chat['pin_balance'] is True:
            pin, thread = True, self.db_chat['main_topic']

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=thread,
            pin=pin
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class NullCommand(CurrencyNullCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level in ('admin', 'employee'):
                rres = re.fullmatch(rf'{self.keywords["NullCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:

        res = await self.db.fetch("""
            SELECT currency_table.*
            FROM currency_table
            JOIN chat_table ON chat_table.id = currency_table.chat_pid
            WHERE chat_table.type = 'chat' AND chat_table.chat_id = $1
            ORDER BY currency_table.title ASC; 
        """, self.chat.id)

        if len(res) == 1:
            await super().process(
                title=res[0]['title'],
                value=res[0]['value'],
                postfix=res[0]['postfix'],
                curr_id=res[0]['id'],
                res=res,
                **kwargs
            )
        elif len(res) == 0:
            message_obj = await self.generate_error_message()
            self.bot.send_text(message_obj)
        else:
            destroy_timeout = 10
            message_obj = await self.generate_send_message(res=res, destroy_timeout=destroy_timeout, **kwargs)
            sent_message = await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs.get('res') and len(kwargs['res']) == 1:
            return await super().generate_send_message(**kwargs)
        else:
            story_list = [{'title': i['title'], 'curr_id': i['id']} for i in kwargs['res']]

            markup = markup_generate(
                buttons=self.global_texts['buttons']['NullCommand'],
                cycle=story_list
            )

            text = Template(self.texts['NullCommand']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup,
                destroy_timeout=kwargs['destroy_timeout']
            )

    async def generate_error_message(self, *args, **kwargs):
        text = Template(self.global_texts['error']['ZeroCurrencies']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


# Команды для админов в приватном чате
class MenuCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] != 'zero':
                rres = re.fullmatch(rf'{self.keywords["MenuCommand"]}', self.text_low)
                if not rres:
                    rres = re.fullmatch(r'/menu|/menu +@.+', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if self.access_level == 'admin':
            text = Template(self.texts['MenuCommand']).substitute()

            markup = markup_generate(
                buttons=self.buttons['MenuCommand']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )
        else:
            text = Template(self.global_texts['callback_command']['edit']['EmployeeMenuCommand']).substitute()

            variable = []

            folder_id = '_'

            info_id = None
            if self.db_user['tag']:
                info_res = await self.db.fetchrow("""
                    SELECT * FROM note_table
                    WHERE id = parent_id
                        AND tag = $1;
                """, self.db_user['tag'])
                info_id = info_res['id']
                variable.append('info')

            if self.access_level == 'employee':
                variable.append('parsing')
                variable.append('commands')
                variable.append('notes')
                folder_id = 1
            elif self.access_level == 'employee_parsing':
                variable.append('parsing')
                variable.append('notes')
                folder_id = 2

            markup = markup_generate(
                self.buttons['EmployeeMenuCommand'],
                variable=variable,
                folder_id=folder_id,
                info_id=info_id
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class AdminChangeNote(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] == 'admin':
                if self.message.quote:
                    res = await self.db.fetchrow("""
                        SELECT * FROM message_table
                        WHERE type in ('note', 'hidden_note')
                            AND is_bot_message = TRUE
                            AND message_id = $1;
                    """, self.message.reply_to_message.message_id)
                    if res:
                        hidden = False
                        if res['type'] == 'hidden_note':
                            hidden = True
                        await self.process(res=res, hidden=hidden)
                        return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, int(kwargs['res']['addition']))

        new_text = res['add_info' if kwargs['hidden'] else 'text'].replace(self.message.quote.text, self.text)

        if kwargs['hidden']:
            await self.db.execute("""
                UPDATE note_table
                SET add_info = $1
                WHERE id = $2;
            """, new_text, res['id'])
        else:
            await self.db.execute("""
                UPDATE note_table
                SET text = $1
                WHERE id = $2;
            """, new_text, res['id'])

        await self.bot.delete_message(self.chat.id, self.message.message_id)
        message_obj = await self.generate_edit_message(res=res, hidden=kwargs['hidden'])
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> EditMessage:
        new_res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['res']['id'])

        text = new_res['add_info' if kwargs['hidden'] else 'text']

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.message.reply_to_message.message_id
        )


class AdminAddInfoNote(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] == 'admin':
                if not self.message.quote and self.message.reply_to_message:
                    res = await self.db.fetchrow("""
                        SELECT * FROM message_table
                        WHERE type = 'note'
                            AND is_bot_message = TRUE
                            AND message_id = $1;
                    """, self.message.reply_to_message.message_id)
                    if res:
                        await self.process(res=res)
                        return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, int(kwargs['res']['addition']))

        text = self.text or self.message.caption
        if not text:
            text = "..."

        hidden_text = entities_to_html(text, self.message.entities)

        if self.message.photo:
            hidden_text = "photo=" + self.message.photo[-1].file_id + "&" + "text=" + hidden_text

        await self.db.execute("""
            UPDATE note_table
            SET add_info = $1
            WHERE id = $2;
        """, hidden_text, res['id'])

        await self.bot.set_emoji(
            chat_id=self.chat.id,
            message_id=self.message.message_id if res['add_info'] else self.message.reply_to_message.message_id,
            emoji=self.global_texts['reactions']['HiddenInfo']
        )

        await self.bot.delete_message(self.chat.id, self.message.message_id)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> EditMessage:
        pass


class FindCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.access_level == 'admin':
                if not self.message.reply_to_message:
                    from main import check_define
                    cls_list = []
                    self_module = sys.modules[__name__]
                    for name, obj in inspect.getmembers(self_module, inspect.isclass):
                        if obj.__dict__['__module__'] == self_module.__dict__['__name__']:
                            if obj != FindCommand:
                                cls_list.append(obj)

                    if await check_define(cls_list, MessageCommand, self.message) is None:
                        await self.process()
                        return True

    async def process(self, *args, **kwargs) -> None:
        res1 = await self.db.fetch("""
            SELECT * FROM note_table
            WHERE id <> parent_id
            ORDER BY title ASC;
        """)

        markup = []
        notes = []

        word = self.text_low
        len_word = len(word)
        if len_word >= 3:
            patterns_list = [word[:i] + '.' + word[i+1:] for i in range(len_word)]
        else:
            patterns_list = [word]

        for i in res1:
            string = i['title'].lower().strip()
            if i['text']:
                string = i['text'].lower().strip()
                if i['add_info']:
                    string += i['add_info'].lower().strip()
            string.replace('\\', '/')
            find = False
            for patt in patterns_list:
                if re.search(patt, string):
                    find = True
                    break
            if find is True:
                note_type = i['type']
                type_text = 'Заметка' if note_type == 'note' else 'Категория'
                note_title = i['title']
                note_id = i['id']
                if i['type'] == 'folder':
                    markup.append([IButton(text=f'{type_text} {note_title}', callback_data=f'{note_type}/{note_id}/')])
                elif i['type'] == 'note':
                    notes.append(i)

        if len(markup) == 0 and len(notes) == 0:
            message_obj = await self.generate_error_message()
        else:
            markup.append([IButton(text='Закрыть', callback_data='close')])
            message_obj = await self.generate_send_message(markup=markup)
            for i in notes:
                text = i['text']
                if i['add_info']:
                    text += '\n\n' + f'<blockquote expandable>{i["add_info"]}</blockquote>'
                sent_message = await self.bot.send_text(TextMessage(
                    chat_id=self.chat.id,
                    text=text,
                    destroy_timeout=120
                ))
                await self.db.execute("""
                    INSERT INTO message_table
                    (user_pid, message_id, text, type, is_bot_message)
                    VALUES ($1, $2, $3, $4, TRUE);
                """,
                                      self.db_user['id'],
                                      sent_message.message_id,
                                      sent_message.text,
                                      'note'
                                      )

        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['FindCommand']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            markup=IMarkup(inline_keyboard=kwargs['markup']),
            destroy_timeout=120
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['NotFound']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            destroy_timeout=30
        )


class DistributionCommand(MessageCommand):
    async def define(self):
        if self.access_level == 'admin':
            if self.chat.type == 'private':
                rres = re.fullmatch(rf'{self.keywords["DistributionCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT DISTINCT tag FROM 
                (
                SELECT * FROM chat_table
                ORDER BY title ASC
                )
            AS subquery;
        """)
        text = Template(self.global_texts['callback_command']['edit']['AdminDistribution']).substitute()

        markup = markup_generate(
            buttons=self.buttons['AdminDistribution'],
            cycle=[{'tag': i['tag']} for i in res if i['tag']],
            variable=['back']
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            markup=markup
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class InlineTable(MessageCommand):
    async def define(self):
        if self.access_level == 'admin':
            if self.text:
                rres = re.fullmatch(r'/inline_table', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:
        import csv
        filename = datetime.datetime.now().strftime('%Y.%m.%d') + ' inline_table.csv'

        res = await self.db.fetch("""
            SELECT * FROM inline_query;
        """)
        with open(filename, 'w') as w_csv:
            writer = csv.writer(w_csv)
            writer.writerow(['ID', 'ID пользователя', 'Username', 'Время'])
            for i in res:
                writer.writerow([
                    i['id'],
                    i['user_id'],
                    i['username'] or 'пусто',
                    (i['datetime'] + datetime.timedelta(hours=3)).strftime('%Y.%m.%d %H:%M:%S')
                ])
        csv_file = FSInputFile(filename)
        await self.bot.bot.send_document(
            chat_id=self.chat.id,
            document=csv_file
        )
        os.remove(filename)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

# Команды для сотрудников в приватном чате
class AddressListCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing', 'client'):
                rres = re.fullmatch(rf'{self.keywords["AddressListCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetch("""
            SELECT * FROM crypto_parsing_table
            WHERE user_pid = $1;
        """, self.db_user['id'])

        if len(res) == 0:
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
        else:
            message_obj = await self.generate_send_message(res=res)
            await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        address_list = []

        for i in kwargs['res']:
            address_list.append(Template(self.global_texts['addition']['address_list']).substitute(
                address=i['address'],
                min_value=float_to_str(i['min_value'])
            ))

        text = Template(self.texts['AddressListCommand']).substitute(
            address_list=''.join(address_list)
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )

    async def generate_error_message(self, *args, **kwargs):
        text = Template(self.global_texts['error']['ZeroAddresses']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AddAddressCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing', 'client'):
                rres = re.fullmatch(r'[аА][дД][рР][еЕ][сС] +([^ ]+)(| +[0-9.,]+)', self.text.strip())
                if rres:
                    address, min_value = rres.groups()
                    min_value = 0 if min_value == '' else str_to_float(min_value)

                    res = await self.db.fetch("""
                        SELECT * FROM crypto_parsing_table
                        WHERE user_pid = $1;
                    """, self.db_user['id'])

                    for i in res:
                        if i['address'] == address:
                            await self.process(address=address, min_value=min_value, type='edit', record=i)
                            return True

                    valid = await Tracking.check_address(address)
                    if valid is True:
                        await self.process(address=address, min_value=min_value, type='create')
                        return True
                    elif valid is False:
                        await self.process(type='error')
                        return True

    async def process(self, *args, **kwargs) -> None:
        type_ = kwargs['type']

        if type_ == 'create':
            await self.db.execute("""
                INSERT INTO crypto_parsing_table
                (user_pid, address, min_value)
                VALUES ($1, $2, $3);
            """, self.db_user['id'], kwargs['address'], kwargs['min_value'])

            message_obj = await self.generate_send_message(**kwargs)
            await self.bot.send_text(message_obj)

        elif type_ == 'edit':
            message_obj = await self.generate_send_message(**kwargs)
            sent_message = await self.bot.send_text(message_obj)


        elif type_ == 'error':
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        type_ = kwargs['type']
        if type_ == 'create':
            text = Template(self.texts['AddAddressCommandCreate']).substitute()
            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        elif type_ == 'edit':
            text = Template(self.texts['AddAddressCommandEdit']).substitute()

            markup = markup_generate(
                self.buttons['AddAddressCommandEdit'],
                address_id=kwargs['record']['id']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup,
            )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['IncorrectAddress']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class TrackingCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing', 'client'):
                rres = re.fullmatch(rf'{self.keywords["TrackingCommand"]}', self.text_low)
                if rres:
                    res = await self.db.fetchrow("""
                        SELECT tracking FROM user_table
                        WHERE id = $1;
                    """, self.db_user['id'])

                    if res['tracking'] is False:
                        await self.process()
                        return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE user_table
            SET tracking = TRUE
            WHERE id = $1;
        """, self.db_user['id'])

        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['TrackingCommand']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class OffTrackingCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing', 'client'):
                rres = re.fullmatch(rf'{self.keywords["OffTrackingCommand"]}', self.text_low)
                if rres:
                    res = await self.db.fetchrow("""
                        SELECT tracking FROM user_table
                        WHERE id = $1;
                    """, self.db_user['id'])

                    if res['tracking'] is True:
                        await self.process()
                        return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE user_table
            SET tracking = FALSE
            WHERE id = $1;
        """, self.db_user['id'])

        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['OffTrackingCommand']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class QuoteReplied(MessageCommand):
    async def define(self):
        if self.message.quote or self.message.reply_to_message:
            res = await self.db.fetchrow("""
                SELECT * FROM message_table
                WHERE message_id = $1
                    AND type = 'reply1';
            """, self.message.reply_to_message.message_id)
            if res:
                await QuoteReplied.process(self)

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
            SELECT * FROM message_table
            WHERE message_id = $1;
        """, self.message.reply_to_message.message_id)

        await self.db.execute("""
            INSERT INTO message_table
            (user_pid, chat_pid, message_id, type, addition)
            VALUES ($1, $2, $3, 'reply2', $4);
        """, self.db_user['id'], self.db_chat['id'], self.message.message_id, str(res['id']))

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class ClientStory(MessageCommand):
    async def define(self):
        if self.access_level == 'client':
            rres = re.fullmatch(rf'{self.keywords["StoryCommand"]}', self.text_low)
            if rres:
                if self.db_user['bind_chat']:
                    await self.process(chat_id=self.db_user['bind_chat'])
                    return True

    async def process(self, *args, **kwargs) -> None:
        res1 = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_id'])

        res2 = await self.db.fetch("""
            SELECT * FROM currency_table
            WHERE chat_pid = $1;
        """, res1['id'])

        message_obj = await self.generate_send_message(res1=res1, res2=res2)
        await self.bot.send_text(message_obj)

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        curr_story_list = ''

        for item in kwargs['res2']:
            res3 = await self.db.fetch("""
                SELECT * FROM story_table
                WHERE currency_pid = $1 AND status = TRUE;
            """, item['id'])

            story = story_generate(res3, kwargs['res1']['chat_id'], rounding=item['rounding']) or ''

            curr_story_list += '<blockquote expandable>' + Template(self.texts['CurrencyStoryCommand']).substitute(
                title=item['title'].upper(),
                postfix=((item['postfix'] or '') if story else ''),
                story=story
            ) + '</blockquote>' + '\n'

        text = Template(self.texts['ClientStory']).substitute(
            title=kwargs['res1']['title'].upper(),
            curr_story_list=curr_story_list
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
        )


class ClientStoryMenu(MessageCommand):
    async def define(self):
        if self.access_level in ["client"]:
            rres = re.fullmatch(rf'(.+) +{self.keywords["StoryCommand"]}', self.text_low)
            if rres:
                chat_id = self.db_user['bind_chat']
                if chat_id:
                    curr = rres.group(1)
                    res = await self.db.fetch("""
                        SELECT * FROM currency_table
                        WHERE chat_pid = $1
                        ORDER BY title ASC; 
                    """, chat_id)
                    for i in res:
                        if curr == i['title']:
                            await self.process(curr=i, chat_id=chat_id)
                            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        curr = kwargs["curr"]

        text = Template(self.global_texts["callback_command"]["edit"]['CurrStoryMenu']).substitute(
            title=curr['title'].upper()
        )

        buttons: List[List[IButton]] = []

        start_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime("%Y-%m-%d")
        end_date = start_date

        buttons.append([])
        for i in ("ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"):
            buttons[-1].append(IButton(text=i, callback_data="None"))
        buttons.append([])
        row_count = 0
        underlining = False
        for i in calendar():
            if i["date"] == start_date:
                underlining = True

            if row_count == 7:
                buttons.append([])
                row_count = 0
            row_count += 1
            callback_data = f'client_story_menu?curr={kwargs["curr"]["id"]}&start={i["date"]}' if i["use"] is True else 'None'

            button_text = i["text"]
            if underlining:
                button_text = "".join([i + "\u0331" for i in button_text])

            buttons[-1].append(IButton(text=button_text, callback_data=callback_data))

            if i["date"] == start_date:
                underlining = False

        buttons.append([IButton(text="Получить историю", callback_data=f"get_story_menu?curr={kwargs['curr']['id']}&start={start_date}&end={end_date}")])

        markup = IMarkup(inline_keyboard=buttons)

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            markup=markup
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass