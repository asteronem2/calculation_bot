import datetime
import re
from string import Template

import aiogram

import BotInteraction
from command.command_interface import MessageCommand

from BotInteraction import TextMessage
from utils import str_to_float, float_to_str, markup_generate, calculate, detail_generate, detail_generate, Tracking, \
    story_generate


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
                await self.db.execute("""
                    UPDATE chat_table
                    SET locked = FALSE
                    WHERE chat_id = $1;
                """, self.chat.id)
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
                rres = re.fullmatch(r'([^ ]+) *= *([0-9.,-]+) *([^ ]*)', self.text)
                if rres:
                    title, value, postfix = rres.groups()
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

        await self.db.add_story(
            curr_id=after_res['id'],
            user_id=self.db_user['id'],
            expr_type='create' if not before_res else 'update',
            before_value=None if not before_res else before_res['value'],
            after_value=after_res['value'],
            message_id=self.message.message_id,
            expression=split_text[2]
        )

        message_obj = await self.generate_send_message(**{
            'title': title,
            'value': value,
            'postfix': postfix
        })
        await self.bot.send_text(message_obj)

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
                        WHERE type = 'chat' AND chat_table.chat_id = $1; 
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
            SELECT * FROM currency_table
            WHERE title = $1;
        """, kwargs['title'])

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
                rres = re.fullmatch(rf'{self.keywords["BalanceListCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, **kwargs) -> None:
        res = await self.db.fetch("""
            SELECT currency_table.* 
            FROM currency_table
            JOIN chat_table ON chat_table.id = currency_table.chat_pid
            WHERE type = 'chat' AND chat_table.chat_id = $1;
        """, self.chat.id)
        if res:
            message_obj = await self.generate_send_message(res)
        else:
            message_obj = await self.generate_error_message()
        await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        curr_info_list = ''

        for i in args[0]:
            var = Template(self.global_texts['addition']['curr_info_list']).substitute(
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
                    WHERE type = 'chat' AND chat_table.chat_id = $1; 
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
                rres = re.fullmatch(r'(.+) +([*+%/0-9., -]+)', self.text_low)
                if rres:
                    curr, expr = rres.groups()
                    calc_res = calculate(expr)
                    if calc_res is not False:

                        res = await self.db.fetch("""
                            SELECT currency_table.*
                            FROM currency_table
                            JOIN chat_table ON chat_table.id = currency_table.chat_pid
                            WHERE type = 'chat' AND chat_table.chat_id = $1; 
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

        await self.db.add_story(
            curr_id=res['id'],
            user_id=self.db_user['id'],
            expr_type='add',
            before_value=kwargs['curr']['value'],
            after_value=new_value,
            message_id=self.message.message_id,
            expression=kwargs['expr']
        )

        message_obj = await self.generate_send_message(new_value=new_value, **kwargs)
        await self.bot.send_text(message_obj)

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
                rres = re.fullmatch(r'[*+%/0-9., -]+', self.text_low)
                if rres:
                    expr = rres.group()
                    calc_res = calculate(expr)
                    if calc_res is not False:
                        res = await self.db.fetch("""
                                SELECT currency_table.*
                                FROM currency_table
                                JOIN chat_table ON chat_table.id = currency_table.chat_pid
                                WHERE type = 'chat' AND chat_table.chat_id = $1; 
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
                expression=self.text_low
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
        pass


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
                        WHERE type = 'chat' AND chat_table.chat_id = $1; 
                    """, self.chat.id)

                    for i in res:
                        if curr == i['title']:
                            await self.process(curr_id=i['id'], title=i['title'])
                            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)

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

        story = story_generate(story_items=today_story, chat_id=self.chat.id)

        text = Template(self.texts['CurrencyStoryCommand']).substitute(
            title=kwargs['title'].upper(),
            story=story
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
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

        res = await self.db.fetch("""
            SELECT currency_table.*
            FROM currency_table
            JOIN chat_table ON chat_table.id = currency_table.chat_pid
            WHERE type = 'chat' AND chat_table.chat_id = $1; 
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
                buttons=self.global_texts['buttons']['StoryCommand'],
                cycle=story_list
            )

            text = Template(self.texts['StoryCommand']).substitute()

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
                        WHERE type = 'chat' AND chat_table.chat_id = $1; 
                    """, self.chat.id)

                    for i in res:
                        if curr == i['title']:
                            await self.process(curr_id=i['id'], title=i['title'])
                            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)

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

        detail = detail_generate(today_story, chat_id=self.chat.id)

        text = Template(self.texts['CurrencyDetailCommand']).substitute(
            title=kwargs['title'].upper(),
            detail=detail
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
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
            WHERE type = 'chat' AND chat_table.chat_id = $1; 
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
                currency_table.postfix AS currency__postfix
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
            value=float_to_str(kwargs['last_res']['story__before_value'], kwargs['last_res']['currency_rounding']),
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
                        WHERE type = 'chat' AND chat_table.chat_id = $1; 
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

        await self.db.add_story(
            curr_id=kwargs['curr_id'],
            user_id=self.db_user['id'],
            expr_type='null',
            before_value=kwargs['value'],
            after_value=0.0,
            message_id=self.message.message_id,
            expression=None
        )

        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)

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
            WHERE type = 'chat' AND chat_table.chat_id = $1; 
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
class AdminMenuCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] == 'admin':
                rres = re.fullmatch(rf'{self.keywords["AdminMenuCommand"]}', self.text_low)
                if rres:
                    await self.process()
                    return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message()
        sent_message = await self.bot.send_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['AdminMenuCommand']).substitute()

        markup = markup_generate(
            self.global_texts['buttons']['AdminMenuCommand']
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            markup=markup
        )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


# Команды для сотрудников в приватном чате
class AddressListCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing'):
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
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing'):
                rres = re.fullmatch(r'адрес +([^ ]+)(| +[0-9.,]+)', self.text.strip())
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
                address=kwargs['record']['id']
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


# class ChangeAddressCommand(MessageCommand):
#     async def define(self):
#         pass
#
#     async def process(self, *args, **kwargs) -> None:
#         pass
#
#     async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
#         pass


class TrackingCommand(MessageCommand):
    async def define(self):
        if self.chat.type == 'private':
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing'):
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
            if self.db_user['access_level'] in ('admin', 'employee', 'employee_parsing'):
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


class Pass(MessageCommand):
    async def define(self):
        pass

    async def process(self, *args, **kwargs) -> None:
        pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass
