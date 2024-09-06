import datetime
import re
from string import Template

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import BotInteraction
from BotInteraction import EditMessage, TextMessage
from command.command_interface import CallbackQueryCommand
from utils import float_to_str, markup_generate, story_generate, detail_generate, calculate



class Close(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'close', self.cdata)
            if rres:
                await self.process()
                return True


    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE user_pid = $1 AND 
            COALESCE(chat_pid, 1) = COALESCE($2, 1);
        """, self.db_user['id'], None if not self.db_chat else self.db_chat['id'])

        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.sent_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

# Команды админов в группе
class EditCurrencyEdit(CallbackQueryCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(r'curr/edit/edit/([0-9]+)/', self.cdata)
                if rres:
                    curr_pk = int(rres.group(1))
                    await self.process(curr_pk=curr_pk)
                    return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_pk'])

        title = res['title']

        text = Template(self.global_texts['message_command']['EditCurrencyCommand']).substitute(
            title=title.upper()
        )

        markup = markup_generate(
            buttons=self.buttons['EditCurrencyEdit'],
            curr_id=kwargs['curr_pk']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class CurrencyBalance(CallbackQueryCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(r'curr/balance/([0-9]+)/', self.cdata)
                if rres:
                    curr_pk = int(rres.group(1))
                    await self.process(curr_pk=curr_pk)
                    return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_pk'])

        text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
            title=res['title'].upper(),
            value=float_to_str(res['value'], res['rounding']),
            postfix=res['postfix'] if res['postfix'] else ''
        )

        markup = markup_generate(
            buttons=self.buttons['CurrencyBalanceCommand'],
            curr_id=res['id'],
            variable=['1']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class CurrChangeTitleCommand(CallbackQueryCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(r'curr/change_title/([0-9]+)/', self.cdata)
                if rres:
                    res = await self.db.fetchrow("""
                        SELECT * FROM pressure_button_table
                        WHERE chat_pid = $1 AND user_pid = $2;
                    """, None if not self.db_chat else self.db_chat['id'],
                                                 self.db_user['id'])
                    if not res:
                        curr_id = int(rres.group(1))
                        await self.process(curr_id=curr_id)
                        return True
                    else:
                        await self.bot.answer_clb_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, self.db_chat['id'], self.db_user['id'], self.sent_message_id, self.cdata)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        title = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, int(kwargs['curr_id']))
        text = Template(self.edit_texts['CurrChangeTitleCommand']).substitute(
            title=title['title'].upper()
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'curr/edit/edit/{kwargs["curr_id"]}/')]])
        )


class CurrChangeValueCommand(CallbackQueryCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(r'curr/change_value/([0-9]+)/', self.cdata)
                if rres:
                    res = await self.db.fetchrow("""
                        SELECT * FROM pressure_button_table
                        WHERE chat_pid = $1 AND user_pid = $2;
                    """, None if not self.db_chat else self.db_chat['id'],
                                                 self.db_user['id'])
                    if not res:
                        curr_id = int(rres.group(1))
                        await self.process(curr_id=curr_id)
                        return True
                    else:
                        await self.bot.answer_clb_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, self.db_chat['id'], self.db_user['id'], self.sent_message_id, self.cdata)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, int(kwargs['curr_id']))
        text = Template(self.edit_texts['CurrChangeValueCommand']).substitute(
            title=res['title'].upper(),
            value=float_to_str(res['value'], res['rounding'])
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'curr/edit/edit/{kwargs["curr_id"]}/')]])
        )


class CurrChangePostfixCommand(CallbackQueryCommand):
    async def define(self):
        if self.db_chat and self.db_chat['locked'] is False:
            if self.access_level == 'admin':
                rres = re.fullmatch(r'curr/change_postfix/([0-9]+)/', self.cdata)
                if rres:
                    res = await self.db.fetchrow("""
                        SELECT * FROM pressure_button_table
                        WHERE chat_pid = $1 AND user_pid = $2;
                    """, None if not self.db_chat else self.db_chat['id'],
                                                 self.db_user['id'])
                    if not res:
                        curr_id = int(rres.group(1))
                        await self.process(curr_id=curr_id)
                        return True
                    else:
                        await self.bot.answer_clb_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, self.db_chat['id'], self.db_user['id'], self.sent_message_id, self.cdata)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, int(kwargs['curr_id']))
        text = Template(self.edit_texts['CurrChangePostfixCommand']).substitute(
            title=res['title'].upper(),
            postfix=res['postfix']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'curr/edit/edit/{kwargs["curr_id"]}/')]])
        )


class CurrNullStoryCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'curr/null_story/([0-9]+)/', self.cdata)
            if rres:
                curr_id = rres.group(1)
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['CurrNullStoryCommand']).substitute()

        markup = markup_generate(
            self.buttons['CurrNullStoryCommand'],
            **kwargs
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class CurrNullStoryCommandSecond(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'curr/null_story/([0-9]+)/([^/]+)/', self.cdata)
            if rres:
                curr_id, answer = rres.groups()
                await self.process(curr_id=curr_id, answer=answer)
                return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['answer'] == 'no':
            await self.bot.delete_message(
                self.chat.id,
                self.sent_message_id
            )
        else:
            await self.db.execute("""
                UPDATE story_table
                SET status = FALSE
                WHERE currency_pid = $1;
            """, int(kwargs['curr_id']))

            message_obj = await self.generate_edit_message(**kwargs)
            await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table 
            WHERE id = $1;
        """, int(kwargs['curr_id']))
        text = Template(self.edit_texts['CurrNullStoryCommandSecond']).substitute(
            title=res['title'].upper()
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
        )


class CurrDropCurrCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'curr/drop_curr/([0-9]+)/', self.cdata)
            if rres:
                curr_id = rres.group(1)
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['CurrDropCurrCommand']).substitute()

        markup = markup_generate(
            self.buttons['CurrDropCurrCommand'],
            **kwargs
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class CurrDropCurrCommandSecond(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'curr/drop_curr/([0-9]+)/([^/]+)/', self.cdata)
            if rres:
                curr_id, answer = rres.groups()
                await self.process(curr_id=curr_id, answer=answer)
                return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['answer'] == 'no':
            await self.bot.delete_message(
                self.chat.id,
                self.sent_message_id
            )
        else:
            message_obj = await self.generate_edit_message(**kwargs)
            await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['CurrDropCurrCommandSecond']).substitute()

        markup = markup_generate(
            self.buttons['CurrDropCurrCommandSecond'],
            **kwargs
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class CurrDropCurrCommandThird(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'curr/drop_curr/([0-9]+)/[^/]+/([^/]+)/', self.cdata)
            if rres:
                curr_id, answer = rres.groups()
                await self.process(curr_id=curr_id, answer=answer)
                return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['answer'] == 'no':
            await self.bot.delete_message(
                self.chat.id,
                self.sent_message_id
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM currency_table
                WHERE id = $1;
            """, int(kwargs['curr_id']))

            await self.db.execute("""
                DELETE FROM story_table
                WHERE currency_pid = $1;
            """, int(kwargs['curr_id']))

            await self.db.execute("""
                DELETE FROM currency_table
                WHERE id = $1;
            """, int(kwargs['curr_id']))

            message_obj = await self.generate_edit_message(res=res, **kwargs)
            await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['CurrDropCurrCommandThird']).substitute(
            title=kwargs['res']['title'].upper()
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
        )


class EditChatTheme(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/edit_chat_theme/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['message_command']['EditChatThemeCommand']).substitute()

        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, self.db_chat['id'])

        variable = []
        if res['topic'] != res['main_topic']:
            variable.append('1')
        chat_id = res['id']

        if res['sign'] is False:
            variable.append('photo-')
        else:
            variable.append('photo+')

        if res['pin_balance'] is True:
            variable.append('pin_balance')
        else:
            variable.append('unpin_balance')

        rres = re.findall(r'([^|]+?)\|', res['answer_mode'])

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

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup,
        )


class EditCurrency(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/edit_currency/([0-9]+)/', self.cdata)
            if rres:
                curr_id = int(rres.group(1))
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        text = Template(self.global_texts['message_command']['EditCurrencyCommand']).substitute(
            title=res['title'].upper(),
            value=float_to_str(res['value'], res['rounding']),
            postfix=res['postfix'] if res['postfix'] else ''
        )

        markup = markup_generate(
            buttons=self.buttons['EditCurrencyCommand'],
            variable=['1'],
            curr_id=kwargs['curr_id'],
            chat_id=self.db_chat['id'],
            rounding=res['rounding']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class ChatBalancesCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/balances/[0-9]+/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM currency_table
            WHERE chat_pid = $1;
        """, self.db_chat['id'])
        cycle = [
            {'title': i['title'].upper(),
             'value': float_to_str(i['value'], i['rounding']),
             'postfix': i['postfix'] if i['postfix'] else '',
             'curr_id': i['id']}
            for i in res
        ]

        markup = markup_generate(
            self.buttons['ChatBalancesCommand'],
            cycle=cycle,
            chat_id=self.db_chat['id']
        )

        text = Template(self.edit_texts['ChatBalancesCommand']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class ChatTopicsCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/topics/([0-9]+)/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetch("""
            SELECT * FROM chat_table
            WHERE chat_id = $1;
        """, self.chat.id)
        message_obj = await self.generate_edit_message(res=res, **kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        theme_num = 1
        topic_list = []
        for i in kwargs['res']:
            if i['topic'] == i['main_topic']:
                topic_list.append(('Главная тема', f'https://t.me/c/{str(self.chat.id)[4:]}/{i["topic"]}', i['id']))
            else:
                topic_list.append((f'Тема {theme_num}', f'https://t.me/c/{str(self.chat.id)[4:]}/{i["topic"]}', i['id']))
                theme_num += 1

        str_topic_list = '\n'.join([f'<a href="{i[1]}">{i[0]}</a>' for i in topic_list]) if topic_list else ''

        text = Template(self.edit_texts['ChatTopicsCommand']).substitute(
            topic_list=str_topic_list
        )

        markup = markup_generate(
            self.buttons['ChatTopicsCommand'],
            cycle=[{'title': i[0], 'chat_id': i[2]} for i in topic_list]
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class ChatEditTopicCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/edit_topic/([0-9]+)/', self.cdata)
            if rres:
                chat_id = rres.group(1)
                chat_id = int(chat_id)
                await self.process(chat_id=chat_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_id'])
        text = Template(self.edit_texts['EditTopicCommand']).substitute()
        markup = markup_generate(
            buttons=self.buttons['ChatEditTopicCommand'],
            variable=[] if res['topic'] == res['main_topic'] else ['1'],
            **kwargs
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class ChatPhotoCalcCommand(EditChatTheme):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/photo_calc/([0-9]+)/([+-])/', self.cdata)
            if rres:
                chat_id = int(rres.group(1))
                sign = rres.group(2)
                await self.process(chat_id=chat_id, sign=sign)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            set sign = $1
            WHERE id = $2;
        """, True if kwargs['sign'] == '-' else False, kwargs['chat_id'])

        message_obj = await EditChatTheme.generate_edit_message(self)
        await self.bot.edit_text(message_obj)


class ChatLockCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/lock/([0-9]+)/', self.cdata)
            if rres:
                chat_id = int(rres.group(1))
                await self.process(chat_id=chat_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET locked = TRUE
            WHERE id = $1;
        """, kwargs['chat_id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_id'])
        text = Template(self.global_texts['message_command']['LockChatCommand']).substitute(
            title=res['title']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
        )


class ChatDropStory(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/drop_story/([0-9]+)/', self.cdata)
            if rres:
                chat_id = int(rres.group(1))
                await self.process(chat_id=chat_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['ChatDropStory']).substitute()
        markup = markup_generate(
            buttons=self.buttons['ChatDropStoryCommand'],
            chat_id=kwargs['chat_id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class ChatDropStorySecond(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/drop_story/([0-9]+)/([^/]+)/', self.cdata)
            if rres:
                chat_id, answer = rres.groups()
                chat_id = int(chat_id)
                await self.process(chat_id=chat_id, answer=answer)
                return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['answer'] == 'no':
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.sent_message_id
            )
        else:
            message_obj = await self.generate_edit_message(**kwargs)
            await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['ChatDropStorySecond']).substitute()
        markup = markup_generate(
            buttons=self.buttons['ChatDropStoryCommandSecond'],
            chat_id=kwargs['chat_id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class ChatDropStoryThird(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/drop_story/([0-9]+)/yes/([^/]+)/', self.cdata)
            if rres:
                chat_id, answer = rres.groups()
                chat_id = int(chat_id)
                await self.process(chat_id=chat_id, answer=answer)
                return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['answer'] == 'no':
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.sent_message_id
            )
        else:
            await self.db.execute("""
                DELETE FROM story_table 
                USING currency_table, chat_table
                WHERE story_table.currency_pid = currency_table.id
                  AND currency_table.chat_pid = chat_table.id;
            """)
            message_obj = await self.generate_edit_message(**kwargs)
            await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['ChatDropStoryThird']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
        )


class ChatGeneralTopicCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/general_topic/([0-9]+)/', self.cdata)
            if rres:
                chat_id = int(rres.group(1))
                await self.process(chat_id=chat_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET main_topic = (SELECT topic FROM chat_table WHERE id = $1)
            WHERE chat_id = $2;
        """, kwargs['chat_id'], self.chat.id)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['ChatGeneralTopicCommand']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
        )


class ChatMode(EditChatTheme):
    async def define(self):
        rres = re.fullmatch(r'chat/mode/([^/]+)/set/([^/]+)/', self.cdata)
        if rres:
            answer_type = rres.group(1)
            set_mode = rres.group(2)
            await self.process(answer_type=answer_type, set_mode=set_mode)
            return True

    async def process(self, *args, **kwargs) -> None:
        set_mode = kwargs['set_mode']

        new_mode = self.db_chat['answer_mode']

        x = re.search(r'forward|reply|quote', set_mode).group(0)

        if set_mode == f'non_{x}':
            new_mode = new_mode.replace(f'{x}', set_mode)
        elif set_mode == f'{x}|non_{x}':
            new_mode = new_mode.replace(f'non_{x}', set_mode)
        elif set_mode == f'{x}':
            new_mode = new_mode.replace(f'{x}|non_{x}', set_mode)

        await self.db.execute("""
            UPDATE chat_table
            SET answer_mode = $1
            WHERE chat_id = $2;
        """, new_mode, self.chat.id)

        message_obj = await EditChatTheme.generate_edit_message(self)
        await self.bot.edit_text(message_obj)


class ChatPinBalanceOption(EditChatTheme):
    async def define(self):
        rres = re.fullmatch(r'chat/(pin|unpin)_balances/', self.cdata)
        if rres:
            type_ = rres.group(1)
            await self.process(type_=type_)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET pin_balance = $1
            WHERE id = $2;
        """, True if kwargs['type_'] == 'pin' else False, self.db_chat['id'])

        message_obj = await EditChatTheme.generate_edit_message(self)
        await self.bot.edit_text(message_obj)


class CurrencyRounding(EditCurrency):
    async def define(self):
        rres = re.fullmatch(r'curr/rounding/([0-9]+)/([0-5])/', self.cdata)
        if rres:
            curr_pk = int(rres.group(1))
            rounding = int(rres.group(2))
            await self.process(curr_pk=curr_pk, rounding=rounding)
            return True

    async def process(self, *args, **kwargs) -> None:
        new_rounding = kwargs['rounding'] + 1
        
        if new_rounding == 6:
            new_rounding = 0
        
        await self.db.execute("""
            UPDATE currency_table 
            SET rounding = $1
            WHERE id = $2;
        """, new_rounding, kwargs['curr_pk'])
        
        message_obj = await EditCurrency.generate_edit_message(self, curr_id=kwargs['curr_pk'])
        await self.bot.edit_text(message_obj)

# Команды сотрудников в группе
class CurrCalculationCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'curr/calculation/([0-9]+)/', self.cdata)
            if rres:
                res = await self.db.fetchrow("""
                    SELECT * FROM pressure_button_table
                    WHERE chat_pid = $1 AND user_pid = $2;
                """, self.db_chat['id'], self.db_user['id'])
                if not res:
                    curr_id = int(rres.group(1))
                    await self.process(curr_id=curr_id)
                    return True
                else:
                    await self.bot.answer_clb_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, self.db_chat['id'], self.db_user['id'], self.sent_message_id, self.cdata)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])
        text = Template(self.edit_texts['CurrCalculationCommand']).substitute(
            title=res['title'].upper()
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'curr/balance/{kwargs["curr_id"]}/')]])
        )


class CurrSetNullCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'(?:curr|curr/ready)/set_null/([0-9]+)/', self.cdata)
            if rres:
                curr_id = int(rres.group(1))
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        await self.db.add_story(
            curr_id=kwargs['curr_id'],
            user_id=self.db_user['id'],
            expr_type='null',
            before_value=res['value'],
            after_value=0.0,
            message_id=self.got_message_id,
            expression='обнуление'
        )

        await self.db.execute("""
            UPDATE currency_table
            SET value = 0.0
            WHERE id = $1;
        """, kwargs['curr_id'])

        message_obj = await self.generate_send_message(res=res, **kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.sent_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.send_texts['CurrSetNullCommand']).substitute(
            title=kwargs['res']['title'].upper()
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

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


class CurrCancelCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'curr/cancel/([0-9]+)/', self.cdata)
            if rres:
                curr_id = int(rres.group(1))
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND status = TRUE
            ORDER BY id DESC
            LIMIT 1;
        """, kwargs['curr_id'])

        if not res:
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
        else:
            await self.db.execute("""
                UPDATE currency_table
                SET value = $1
                WHERE id = $2;
            """, res['before_value'], kwargs['curr_id'])

            await self.db.execute("""
                UPDATE story_table
                SET status = FALSE
                WHERE id = $1;
            """, res['id'])

            message_obj = await self.generate_send_message(res=res, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.sent_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])
        text = Template(self.global_texts['message_command']['CancelCommand']).substitute(
            expr_link=f'https://t.me/c/{str(self.chat.id)[4:]}/{kwargs["res"]["message_id"]}/',
            expression=kwargs['res']['expression'],
            title=res['title'].upper(),
            value=float_to_str(res['value'], res['rounding']),
            postfix=res['postfix'] if res['postfix'] else ''
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

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        text = Template(self.global_texts['error']['NoCurrencyStoryToday']).substitute(
            title=res['title'].upper()
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CurrStoryCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'(?:curr|curr/ready)/story/([0-9]+)/', self.cdata)
            if rres:
                curr_id = int(rres.group(1))
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.sent_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND status = TRUE;
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

        story = story_generate(story_items=today_story, chat_id=self.chat.id)

        text = Template(self.global_texts['message_command']['CurrencyStoryCommand']).substitute(
            title=res2['title'].upper(),
            story=story
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        text = Template(self.global_texts['error']['NoCurrencyStoryToday']).substitute(
            title=res['title'].upper()
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CurrDetailCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'(?:curr|curr/ready)/detailing/([0-9]+)/', self.cdata)
            if rres:
                curr_id = int(rres.group(1))
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.sent_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM story_table
            WHERE currency_pid = $1 AND status = TRUE;
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

        detail = detail_generate(today_story, chat_id=self.chat.id)

        text = Template(self.global_texts['message_command']['CurrencyDetailCommand']).substitute(
            title=res2['title'].upper(),
            detail=detail
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        text = Template(self.global_texts['error']['NoCurrencyDetailToday']).substitute(
            title=res['title'].upper()
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class CalculationCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'curr/ready/calculation/([0-9]+)/', self.cdata)
            if rres:
                curr_id = int(rres.group(1))
                await self.process(curr_id=curr_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
            SELECT * FROM callback_addition_table
            WHERE chat_pid = $1 AND got_message_id = $2;
        """, self.db_chat['id'], self.got_message_id)

        res2 = await self.db.fetchrow("""
            SELECT * FROM currency_table
            WHERE id = $1;
        """, kwargs['curr_id'])

        expression = self.addition['addition_info']
        expr_res = calculate(expression)
        before_value = res2['value']
        after_value = before_value + expr_res

        await self.db.add_story(
            curr_id=kwargs['curr_id'],
            user_id=self.db_user['id'],
            expr_type='add',
            before_value=before_value,
            after_value=after_value,
            message_id=self.got_message_id,
            expression=expression
        )

        await self.db.execute("""
            UPDATE currency_table
            SET value = $1
            WHERE id = $2;
        """, after_value, kwargs['curr_id'])

        message_obj = await self.generate_send_message(res=res2, after_value=after_value, **kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.sent_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
            title=kwargs['res']['title'].upper(),
            value=float_to_str(kwargs['after_value'], kwargs['res']['rounding']),
            postfix=kwargs['res']['postfix'] if kwargs['res']['postfix'] else ''
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


# Команды для сотрудников в лс
class AddressEditCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee', 'employee_parsing']:
            rres = re.fullmatch(r'address/([0-9]+)/', self.cdata)
            if rres:
                address_id = int(rres.group(1))
                await self.process(address_id=address_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['message_command']['AddAddressCommandEdit']).substitute()

        markup = markup_generate(
            self.buttons['AddAddressCommandEdit'],
            address_id=kwargs['address_id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AddressChangeMinValueCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee', 'employee_parsing']:
            rres = re.fullmatch(r'address/change_min_value/([0-9]+)/', self.cdata)
            if rres:
                address_id = int(rres.group(1))
                res = await self.db.fetchrow("""
                    SELECT * FROM pressure_button_table
                    WHERE user_pid = $1 AND chat_pid IS NULL;
                """, self.db_user['id'])

                if not res:
                    await self.process(address_id=address_id, res=res)
                    return True
                else:
                    await self.bot.answer_clb_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            INSERT INTO pressure_button_table
            (user_pid, message_id, callback_data)
            VALUES ($1, $2, $3);
        """, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM crypto_parsing_table
            WHERE id = $1;
        """, kwargs['address_id'])

        text = Template(self.edit_texts['AddressChangeMinValueCommand']).substitute(
            address=res['address']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'address/{res["id"]}/')]])
        )


class AddressDelete(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee', 'employee_parsing']:
            rres = re.fullmatch(r'address/delete/([0-9]+)/', self.cdata)
            if rres:
                address_id = int(rres.group(1))
                await self.process(address_id=address_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AddressDelete']).substitute()

        markup = markup_generate(
            buttons=self.buttons['AddressDeleteCommand'],
            address_id=kwargs['address_id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AddressDeleteSecond(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee', 'employee_parsing']:
            rres = re.fullmatch(r'address/delete/([0-9]+)/([^/]+)/', self.cdata)
            if rres:
                address_id, answer = rres.groups()
                address_id = int(address_id)
                await self.process(address_id=address_id, answer=answer)
                return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['answer'] == 'no':
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.sent_message_id
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM crypto_parsing_table
                WHERE id = $1
            """, kwargs['address_id'])

            await self.db.execute("""
                DELETE FROM crypto_parsing_table
                WHERE id = $1;
            """, kwargs['address_id'])

            message_obj = await self.generate_edit_message(res=res, **kwargs)
            await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AddressDeleteSecond']).substitute(
            address=kwargs['res']['address']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
        )


class EmployeeMenu(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee', 'employee_parsing']:
            rres = re.fullmatch(r'employee/menu/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['EmployeeMenuCommand']).substitute()

        variable = []

        if self.db_user['access_level'] == 'employee':
            variable.append('employee')
            variable.append('client')
            variable.append('employee_parsing')
        elif self.db_user['access_level'] == 'client':
            variable.append('client')
        elif self.db_user['access_level'] == 'employee_parsing':
            variable.append('employee_parsing')

        markup = markup_generate(
            self.buttons['EmployeeMenuCommand'],
            variable=variable
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class EmployeeMenuFolder(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee', 'employee_parsing']:
            rres = re.fullmatch(r'employee/menu/folder/([0-9]+)/', self.cdata)
            if rres:
                folder_id = int(rres.group(1))
                await self.process(folder_id=folder_id)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['folder_id'])

        res2 = await self.db.fetch("""
            SELECT * FROM note_table
            WHERE parent_id = $1;
        """, kwargs['folder_id'])

        notes = ''
        folder_cycle = []
        note_cycle = []

        for i in res2:
            if i['id'] == i['parent_id']:
                continue
            elif i['type'] == 'folder':
                folder_cycle.append({
                    'title': i['title'],
                    'folder_id': i['id']
                })
            elif i['type'] == 'note':
                note_cycle.append({
                    'title': i['title'],
                    'note_id': i['id']
                })

                title = i['title']
                text = i['text']
                if f'{text[:17]}...' == title:
                    notes += f'<blockquote expandable>{text}</blockquote>'
                else:
                    notes += f'<blockquote expandable><b>{title}:</b>\n{text}</blockquote>'
                notes += '\n'

        text = Template(self.edit_texts['AdminFolder']).substitute(
            folder_title=res['title'],
            notes=notes
        )

        variable = []

        kkw = {}

        if res['id'] == res['parent_id']:
            variable.append('back_to_menu')
        else:
            variable.append('back_to_parent_folder')
            kkw['parent_folder_id'] = res['parent_id']

        markup = markup_generate(
            self.buttons['EmployeeMenuFolder'],
            folder_cycle=folder_cycle,
            note_cycle=note_cycle,
            variable=variable,
            **kkw
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class EmployeeMenuNote(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'employee/menu/note/([0-9]+)/', self.cdata)
        if rres:
            note_id = int(rres.group(1))
            await self.process(note_id=note_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['note_id'])

        text = Template(self.edit_texts['AdminNote']).substitute(
            title=res['title'],
            text=res['text']
        )

        markup = markup_generate(
            buttons=self.buttons['EmployeeMenuNote'],
            parent_folder_id=res['parent_id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class EmployeeMenuInfo(EmployeeMenuFolder):
    async def define(self):
        rres = re.fullmatch(r'employee/menu/info/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = parent_id
                AND tag = $1;
        """, self.db_user['tag'])

        if res:
            return await EmployeeMenuFolder.generate_edit_message(self, folder_id=res['id'])
        else:

            text = Template(self.edit_texts['EmployeeMenuInfoNull']).substitute()

            markup = markup_generate(
                buttons=self.buttons['EmployeeMenuInfoNull']
            )

            return EditMessage(
                chat_id=self.chat.id,
                text=text,
                message_id=self.sent_message_id,
                markup=markup
            )


class EmployeeMenuCommands(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'employee/menu/commands/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        keywords = self.global_texts['keywords']

        text = Template(self.edit_texts['EmployeeMenuCommands']).substitute(
            **keywords
        )

        markup = markup_generate(
            buttons=self.buttons['EmployeeMenuCommands']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class EmployeeMenuParsing(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'employee/menu/parsing/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM crypto_parsing_table
            WHERE user_pid = $1;
        """, self.db_user['id'])

        address_list = []

        for i in res:
            address_list.append(Template(self.global_texts['addition']['address_list']).substitute(
                address=i['address'],
                min_value=float_to_str(i['min_value'])
            ))

        text = Template(self.global_texts['message_command']['AddressListCommand']).substitute(
            address_list=''.join(address_list)
        )

        res2 = await self.db.fetchrow("""
            SELECT * FROM user_table
            WHERE id = $1;
        """, self.db_user['id'])

        markup = markup_generate(
            buttons=self.buttons['EmployeeMenuParsing'],
            variable=['on'] if res2['tracking'] is True else ['off']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class EmployeeMenuParsingOnOff(EmployeeMenuParsing):
    async def define(self):
        rres = re.fullmatch(r'employee/menu/parsing/(on|off)/', self.cdata)
        if rres:
            status = rres.group(1)
            await self.process(status=status)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE user_table
            SET tracking = CASE
                WHEN tracking = FALSE THEN TRUE 
                ELSE FALSE
                END
            WHERE id = $1;
        """, self.db_user['id'])

        message_obj = await EmployeeMenuParsing.generate_edit_message(self, **kwargs)
        await self.bot.edit_text(message_obj)


# Команды админа в лс
class AdminMenu(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/menu/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['message_command']['AdminMenuCommand']).substitute()

        markup = markup_generate(
            buttons=self.buttons['AdminMenuCommand']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


# Балансы
class AdminBalances(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/balances/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM chat_table
            WHERE type = 'chat';
        """)

        chat_balance_list = ''

        for i in res:
            var_res2 = await self.db.fetch("""
                SELECT * FROM currency_table
                WHERE chat_pid = $1;
            """, i['id'])

            curr_info_list = ''

            for ii in var_res2:
                curr_info_list += '     ' + Template(self.global_texts['addition']['curr_info_list']).substitute(
                    title=ii['title'].upper(),
                    value=float_to_str(ii['value'], ii['rounding']),
                    postfix=ii['postfix'] if ii['postfix'] else ''
                )

            chat_balance_list += Template(self.global_texts['addition']['chat_balance']).substitute(
                title=i['title'],
                code_name=i['code_name'],
                link=i['link'],
                curr_info_list=curr_info_list
            )

        text = Template(self.edit_texts['AdminBalances']).substitute(
            chat_balance=chat_balance_list
        )

        markup = markup_generate(
            buttons=self.buttons['AdminBalances'],
            cycle=[{'title': i['title'],
                    'code_name': i['code_name'],
                    'chat_pk': i['id']
                    } for i in res]
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminBalance(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/balance/([0-9]+)/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        res2 = await self.db.fetch("""
            SELECT * FROM currency_table
            WHERE chat_pid = $1;
        """, kwargs['chat_pk'])

        curr_info_list = ''

        for item in res2:
            curr_info_list += '     ' + Template(self.global_texts['addition']['curr_info_list']).substitute(
                title=item['title'].upper(),
                value=float_to_str(item['value'], item['rounding']),
                postfix=item['postfix'] or ''
            )

        text = Template(self.global_texts['addition']['chat_balance']).substitute(
            title=res['title'],
            code_name=res['code_name'],
            link=res['link'],
            curr_info_list=''.join(curr_info_list)
        )

        markup = markup_generate(
            buttons=self.buttons['AdminBalance'],
            chat_pk=kwargs['chat_pk']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminBalanceStory(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/([^/]+)/([0-9]+)/story/', self.cdata)
            if rres:
                call_type = rres.group(1)
                chat_pk = int(rres.group(2))
                await self.process(chat_pk=chat_pk, call_type=call_type)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        res2 = await self.db.fetch("""
            SELECT * FROM currency_table
            WHERE chat_pid = $1;
        """, kwargs['chat_pk'])

        curr_story_list = ''

        for item in res2:
            res3 = await self.db.fetch("""
                SELECT * FROM story_table
                WHERE currency_pid = $1 AND status = TRUE;
            """, item['id'])

            curr_story_list += '<blockquote expandable>' + Template(self.global_texts['message_command']['CurrencyStoryCommand']).substitute(
                title=item['title'],
                story=story_generate(res3, self.chat.id) or ''
            ) + '</blockquote>' + '\n'

        text = Template(self.edit_texts[f'AdminBalanceStory']).substitute(
            title=res['title'],
            code_name=res['code_name'],
            curr_story_list=curr_story_list
        )

        markup = markup_generate(
            buttons=self.buttons[f'AdminBalanceStory'],
            chat_pk=kwargs['chat_pk'],
            call_type=kwargs['call_type']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminBalanceDetail(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/([^/]+)/([0-9]+)/detail/', self.cdata)
            if rres:
                call_type = rres.group(1)
                chat_pk = int(rres.group(2))
                await self.process(chat_pk=chat_pk, call_type=call_type)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        res2 = await self.db.fetch("""
            SELECT * FROM currency_table
            WHERE chat_pid = $1;
        """, kwargs['chat_pk'])

        curr_detail_list = ''

        for item in res2:
            res3 = await self.db.fetch("""
                SELECT * FROM story_table
                WHERE currency_pid = $1 AND status = TRUE;
            """, item['id'])

            curr_detail_list += '<blockquote expandable>' + Template(self.global_texts['message_command']['CurrencyDetailCommand']).substitute(
                title=item['title'],
                detail=detail_generate(res3, self.chat.id) or ''
            ) + '</blockquote>' + '\n'

        text = Template(self.edit_texts['AdminBalanceDetail']).substitute(
            title=res['title'],
            code_name=res['code_name'],
            curr_detail_list=curr_detail_list
        )

        markup = markup_generate(
            buttons=self.buttons['AdminBalanceDetail'],
            chat_pk=kwargs['chat_pk'],
            call_type=kwargs['call_type']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminBalanceTable(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/balance/([0-9]+)/tablexc/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        text = Template(self.global_texts['addition']['chat_balance']).substitute(
            title=res['title'],
            code_name=res['code_name']
        )

        markup = markup_generate(
            buttons=self.buttons['AdminBalance'],
            chat_pk=kwargs['chat_pk']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminBalanceVolume(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/balance/([0-9]+)/fdsstory/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        text = Template(self.global_texts['addition']['chat_balance']).substitute(
            title=res['title'],
            code_name=res['code_name']
        )

        markup = markup_generate(
            buttons=self.buttons['AdminBalance'],
            chat_pk=kwargs['chat_pk']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


# Чаты
class AdminChats(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chats/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM chat_table
            WHERE type = 'chat';
        """)

        chat_balance_list = ''

        for i in res:
            var_res2 = await self.db.fetch("""
                SELECT * FROM currency_table
                WHERE chat_pid = $1;
            """, i['id'])

            curr_info_list = ''

            for ii in var_res2:
                curr_info_list += '    ' + Template(self.global_texts['addition']['little_balance']).substitute(
                    title=ii['title'].upper(),
                    value=float_to_str(ii['value'], ii['rounding']),
                    postfix=ii['postfix'] if ii['postfix'] else ''
                )

            chat_balance_list += Template(self.global_texts['addition']['chat_balance']).substitute(
                title=i['title'],
                code_name=i['code_name'],
                link=i['link'],
                curr_info_list=curr_info_list
            )

        text = Template(self.edit_texts['AdminBalances']).substitute(
            chat_balance=chat_balance_list
        )

        markup = markup_generate(
            buttons=self.buttons['AdminChats'],
            cycle=[{'title': i['title'],
                    'code_name': i['code_name'],
                    'chat_pk': i['id']
                    } for i in res]
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )
        # res = await self.db.fetch("""
        #     SELECT * FROM chat_table
        #     WHERE type = 'chat';
        # """)
        #
        # chat_list = [f'<b><a href="{i["link"]}">{i["title"]}</a></b>: <code>{i["code_name"]}</code>'
        #              for i in res]
        #
        # chat_list_links = '\n'.join(chat_list)
        #
        # text = Template(self.edit_texts['AdminChats']).substitute(
        #     chat_list_links=chat_list_links
        # )
        #
        # markup = markup_generate(
        #     buttons=self.buttons['AdminChats'],
        #     cycle=[{'title': i['title'],
        #             'code_name': i['code_name'],
        #             'chat_pk': i['id']
        #             } for i in res]
        # )
        #
        # return EditMessage(
        #     chat_id=self.chat.id,
        #     text=text,
        #     message_id=self.sent_message_id,
        #     markup=markup
        # )


class AdminChat(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        text = Template(self.edit_texts['AdminChat']).substitute(
            title=res['title'],
            link=res['link'],
            code_name=res['code_name']
        )

        variable_list = []

        markup_kwargs = {
            'chat_pk': kwargs['chat_pk']
        }

        if res['locked'] is False:
            variable_list.append('lock')
        else:
            variable_list.append('unlock')

        if res['super'] is True:
            variable_list.append('unset_super')
        else:
            variable_list.append('set_super')

        markup_kwargs['tag'] = res['tag'] if res['tag'] else 'Пусто'

        markup = markup_generate(
            buttons=self.buttons['AdminChat'],
            variable=variable_list,
            **markup_kwargs
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminChatDelete(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/delete/', self.cdata)
            rres2 = re.fullmatch(r'admin/chat/([0-9]+)/delete/([^/]+)/', self.cdata)
            rres3 = re.fullmatch(r'admin/chat/([0-9]+)/delete/[^/]+/([^/]+)/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk, stage=1)
                return True
            elif rres2:
                chat_pk, answer = rres2.groups()
                chat_pk = int(chat_pk)
                await self.process(chat_pk=chat_pk, stage=2, answer=answer)
                return True
            elif rres3:
                chat_pk, answer = rres3.groups()
                chat_pk = int(chat_pk)
                await self.process(chat_pk=chat_pk, stage=3, answer=answer)
                return True

    async def process(self, *args, **kwargs) -> None:
        stage = kwargs['stage']
        answer = kwargs.get('answer')
        if answer and answer == 'no':
            await self.bot.delete_message(chat_id=self.chat.id, message_id=self.sent_message_id)
        elif stage == 1:
            message_obj = await self.generate_edit_message(**kwargs)
            await self.bot.edit_text(message_obj)
        elif stage == 2:
            message_obj = await self.generate_edit_message(**kwargs)
            await self.bot.edit_text(message_obj)
        elif stage == 3:
            res = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, kwargs['chat_pk'])

            await self.db.execute("""
                DELETE FROM story_table
                USING currency_table
                WHERE story_table.currency_pid = currency_table.id
                    AND currency_table.chat_pid = $1;                
            """, kwargs['chat_pk'])

            await self.db.execute("""
                DELETE FROM callback_addition_table
                WHERE chat_pid = $1;
            """, kwargs['chat_pk'])

            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE chat_pid = $1;
            """, kwargs['chat_pk'])

            await self.db.execute("""
                DELETE FROM currency_table
                WHERE chat_pid = $1;
            """, kwargs['chat_pk'])

            await self.db.execute("""
                DELETE FROM chat_table
                WHERE chat_id = (SELECT chat_id FROM chat_table WHERE id = $1 LIMIT 1);
            """, kwargs['chat_pk'])

            message_obj = await self.generate_edit_message(res=res, **kwargs)
            await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        stage = kwargs['stage']

        if stage in (1, 2):
            text = Template(self.edit_texts['AdminChatDelete' if stage == 1 else 'AdminChatDelete2']).substitute()

            markup = markup_generate(
                buttons=self.buttons['AdminChatDelete' if stage == 1 else 'AdminChatDelete2'],
                chat_pk=kwargs['chat_pk']
            )

            return EditMessage(
                chat_id=self.chat.id,
                text=text,
                message_id=self.sent_message_id,
                markup=markup
            )
        elif stage == 3:
            text = Template(self.edit_texts['AdminChatDelete3']).substitute(
                title=kwargs['res']['title'],
                code_name=kwargs['res']['code_name']
            )
            return EditMessage(
                chat_id=self.chat.id,
                text=text,
                message_id=self.sent_message_id
            )


class AdminChatLockUnlock(AdminChat):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/(lock|unlock)/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                type_ = rres.group(2)
                await self.process(chat_pk=chat_pk, type_=type_)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET locked = $1
            WHERE id = $2;
        """, True if kwargs['type_'] == 'lock' else False,kwargs['chat_pk'])

        message_obj = await AdminChat.generate_edit_message(self, **kwargs)
        await self.bot.edit_text(message_obj)


class AdminChatChangeCodeName(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/change_code_name/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminChatChangeCodeName']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/chat/{kwargs["chat_pk"]}/')]])
        )


class AdminChatSetSuper(AdminChat):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/set_super/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET super = TRUE
            WHERE id = $1;
        """, kwargs['chat_pk'])

        await self.bot.answer_clb_query(self.callback.id, 'Чат теперь супер')
        message_obj = await AdminChat.generate_edit_message(self, **kwargs)
        await self.bot.edit_text(message_obj)


class AdminChatUnsetSuper(AdminChat):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/unset_super/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET super = FALSE
            WHERE id = $1;
        """, kwargs['chat_pk'])

        await self.bot.answer_clb_query(self.callback.id, 'Чат теперь не супер')
        message_obj = await AdminChat.generate_edit_message(self, **kwargs)
        await self.bot.edit_text(message_obj)


class AdminChatSetTag(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/set_tag/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])
        text = Template(self.edit_texts['AdminChatSetTag']).substitute(
            title=res['title'],
            code_name=res['code_name']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/chat/{res["id"]}/')]])
        )


class AdminChatChangeTag(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/change_tag/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM note_table
            WHERE id = parent_id
                AND id <> 0;
        """)

        res2 = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        text = Template(self.edit_texts['AdminChatChangeTag']).substitute(
            title=res2['title'],
            code_name=res2['code_name']
        )

        cycle = []

        for i in res:
            status = '⏺'

            if i['tag'] == res2['tag']:
                status = '✅'

            cycle.append({
                'status': status,
                'tag': i['tag'],
                'chat_pk': kwargs['chat_pk']
            })

        markup = markup_generate(
            buttons=self.buttons['AdminChatChangeTag'],
            chat_pk=kwargs['chat_pk'],
            cycle=cycle,
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminChatChangeTagSet(AdminChatChangeTag):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/set_tag/([^/]+)/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                tag = rres.group(2)
                await self.process(chat_pk=chat_pk, tag=tag)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET tag = CASE
                    WHEN tag = $1 THEN NULL
                    ELSE $1
                END
            WHERE id = $2;
        """, kwargs['tag'] if kwargs['tag'] != 'null' else None, kwargs['chat_pk'])

        message_obj = await AdminChatChangeTag.generate_edit_message(self, **kwargs)
        await self.bot.edit_text(message_obj)


class AdminChatBalance(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/balance/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res1 = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        res2 = await self.db.fetch("""
            SELECT * FROM currency_table
            WHERE chat_pid = $1;
        """, kwargs['chat_pk'])

        curr_info_list = ''

        for i in res2:
            curr_info_list += Template(self.global_texts['addition']['little_balance']).substitute(
                title=i['title'].upper(),
                value=float_to_str(i['value'], i['rounding']),
                postfix=i['postfix'] if i['postfix'] else ''
            )

        text = Template(self.global_texts['message_command']['BalanceListCommand']).substitute(
            curr_info_list=curr_info_list
        )

        markup = markup_generate(
            buttons=self.buttons['AdminChatBalance'],
            chat_pk=kwargs['chat_pk']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


# Рассылки
class AdminDistribution(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/distribution/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT DISTINCT tag FROM chat_table;
        """)
        text = Template(self.edit_texts['AdminDistribution']).substitute()

        markup = markup_generate(
            buttons=self.buttons['AdminDistribution'],
            cycle=[{'tag': i['tag']} for i in res if i['tag']]
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminDistributionChoice(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/distribution/choice/([^/]+)/', self.cdata)
            if rres:
                tag = rres.group(1)
                await self.process(tag=tag)
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminDistributionChoice']).substitute()

        markup = markup_generate(
            buttons=self.buttons['AdminDistributionChoice'],
            tag=kwargs['tag']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminDistributionPin(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/distribution/pin/([^/]+)/', self.cdata)
            if rres:
                tag = rres.group(1)
                await self.process(tag=tag)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminDistributionPin']).substitute(
            tag=kwargs['tag'] if kwargs['tag'] != 'to_all' else 'всем'
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/distribution/choice/{kwargs["tag"]}/')]])
        )


class AdminDistributionUnpin(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/distribution/unpin/([^/]+)/', self.cdata)
            if rres:
                tag = rres.group(1)
                await self.process(tag=tag)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminDistributionUnpin']).substitute(
            tag=kwargs['tag'] if kwargs['tag'] != 'to_all' else 'всем'
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/distribution/choice/{kwargs["tag"]}/')]])
        )


# Заметки
class AdminFolder(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/folder/([0-9]+)/', self.cdata)
        if rres:
            folder_id = int(rres.group(1))
            await self.process(folder_id=folder_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res1 = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['folder_id'])

        res2 = await self.db.fetch("""
            SELECT * FROM note_table
            WHERE parent_id = $1;
        """, kwargs['folder_id'])

        notes = ''

        for i in res2:
            if i['type'] == 'note':
                title = i['title']
                text = i['text']
                if f'{text[:17]}...' == title:
                    notes += f'<blockquote expandable>{text}</blockquote>'
                else:
                    notes += f'<blockquote expandable><b>{title}:</b>\n{text}</blockquote>'
                notes += '\n'

        text = Template(self.edit_texts['AdminFolder']).substitute(
            folder_title=res1['title'],
            notes=notes[:3900]
        )

        cycle_folder = [{
                'child_folder_title': i['title'],
                'child_folder_id': i['id']
            } for i in res2 if i['type'] == 'folder' and i['id'] != i['parent_id']]

        cycle_note = [{
                'note_title': i['title'],
                'note_id': i['id']
            } for i in res2 if i['type'] == 'note']

        variable = []

        if res1['id'] == res1['parent_id']:
            if res1['tag'] == 'admin':
                variable.append('back_to_menu')
            elif res1['tag']:
                variable.append('back_to_tag')
        else:
            variable.append('back_to_parent_folder')

        if not cycle_folder and not cycle_note and res1['id'] != res1['parent_id']:
            variable.append('delete')

        markup = markup_generate(
            buttons=self.buttons['AdminFolder'],
            folder_id=kwargs['folder_id'],
            cycle_folder=cycle_folder,
            cycle_note=cycle_note,
            parent_folder_id=res1['parent_id'],
            variable=variable,
            tag=res1['tag']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminNote(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/note/([0-9]+)/', self.cdata)
        if rres:
            note_id = int(rres.group(1))
            await self.process(note_id=note_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['note_id'])

        text = Template(self.edit_texts['AdminNote']).substitute(
            title=res['title'],
            text=res['text']
        )

        markup = markup_generate(
            buttons=self.buttons['AdminNote'],
            note_id=res['id'],
            folder_id=res['parent_id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminFolderDelete(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/folder/([0-9]+)/delete/([12])/', self.cdata)
        if rres:
            folder_id = int(rres.group(1))
            stage = int(rres.group(2))
            await self.process(folder_id=folder_id, stage=stage)
            return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
                SELECT * FROM note_table
                WHERE id = $1;
            """, kwargs['folder_id'])

        if kwargs['stage'] == 2:

            await self.db.execute("""
                DELETE FROM note_table
                WHERE id = $1;
            """, kwargs['folder_id'])

        message_obj = await self.generate_edit_message(res=res, **kwargs)
        await self.bot.edit_text(message_obj)

        if kwargs['stage'] == 2:
            message_obj2 = await self.generate_send_message(res=res)
            await self.bot.send_text(message_obj2)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts[f'AdminFolderDelete{kwargs["stage"]}']).substitute(
            title=kwargs['res']['title']
        )

        markup = None

        if kwargs['stage'] == 1:
            markup = markup_generate(
                buttons=self.buttons['AdminFolderDelete2'],
                folder_id=kwargs['folder_id']
            )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        folder_id = kwargs['res']['parent_id']
        res1 = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, folder_id)

        res2 = await self.db.fetch("""
            SELECT * FROM note_table
            WHERE parent_id = $1;
        """, folder_id)

        notes = ''

        for i in res2:
            if i['type'] == 'note':
                title = i['title']
                text = i['text']
                if f'{text[:17]}...' == title:
                    notes += f'<blockquote expandable>{text}</blockquote>'
                else:
                    notes += f'<blockquote expandable><b>{title}:</b>\n{text}</blockquote>'
                notes += '\n'


        text = Template(self.edit_texts['AdminFolder']).substitute(
            folder_title=res1['title'],
            notes=notes[:3900]
        )

        cycle_folder = [{
            'child_folder_title': i['title'],
            'child_folder_id': i['id']
        } for i in res2 if i['type'] == 'folder' and i['id'] != 0]

        cycle_note = [{
            'note_title': i['title'],
            'note_id': i['id']
        } for i in res2 if i['type'] == 'note']

        variable = []

        if folder_id == 0:
            variable.append('back_to_menu')
        else:
            variable.append('back_to_parent_folder')

        if not cycle_folder and not cycle_note and folder_id != 0:
            variable.append('delete')

        markup = markup_generate(
            buttons=self.buttons['AdminFolder'],
            folder_id=folder_id,
            cycle_folder=cycle_folder,
            cycle_note=cycle_note,
            parent_folder_id=res1['parent_id'],
            variable=variable
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            markup=markup
        )


class AdminCreateFolder(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/folder/([0-9]+)/create_folder/', self.cdata)
        if rres:
            folder_id = int(rres.group(1))
            await self.process(folder_id=folder_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)


        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['folder_id'])

        text = Template(self.edit_texts['AdminCreateFolder']).substitute(
            title=res['title']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/folder/{kwargs["folder_id"]}/')]])
        )


class AdminCreateNote(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/folder/([0-9]+)/create_note/', self.cdata)
        if rres:
            folder_id = int(rres.group(1))
            await self.process(folder_id=folder_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['folder_id'])

        text = Template(self.edit_texts['AdminCreateNote']).substitute(
            title=res['title']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/folder/{kwargs["folder_id"]}/')]])
        )


class AdminNoteDelete(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/note/([0-9]+)/delete/([12])/', self.cdata)
        if rres:
            note_id = int(rres.group(1))
            stage = int(rres.group(2))
            await self.process(note_id=note_id, stage=stage)
            return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetchrow("""
                SELECT * FROM note_table
                WHERE id = $1;
            """, kwargs['note_id'])

        if kwargs['stage'] == 2:

            await self.db.execute("""
                DELETE FROM note_table
                WHERE id = $1;
            """, kwargs['note_id'])

        message_obj = await self.generate_edit_message(res=res, **kwargs)
        await self.bot.edit_text(message_obj)

        if kwargs['stage'] == 2:
            message_obj2 = await self.generate_send_message(res=res)
            await self.bot.send_text(message_obj2)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts[f'AdminNoteDelete{kwargs["stage"]}']).substitute(
            title=kwargs['res']['title']
        )

        markup = None

        if kwargs['stage'] == 1:
            markup = markup_generate(
                buttons=self.buttons['AdminNoteDelete2'],
                note_id=kwargs['note_id']
            )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        folder_id = kwargs['res']['parent_id']
        res1 = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, folder_id)

        res2 = await self.db.fetch("""
            SELECT * FROM note_table
            WHERE parent_id = $1;
        """, folder_id)

        notes = ''

        for i in res2:
            if i['type'] == 'note':
                title = i['title']
                text = i['text']
                if f'{text[:17]}...' == title:
                    notes += f'<blockquote expandable>{text}</blockquote>'
                else:
                    notes += f'<blockquote expandable><b>{title}:/b>\n{text}</blockquote>'
                notes += '\n'


        text = Template(self.edit_texts['AdminFolder']).substitute(
            folder_title=res1['title'],
            notes=notes[:3900]
        )

        cycle_folder = [{
            'child_folder_title': i['title'],
            'child_folder_id': i['id']
        } for i in res2 if i['type'] == 'folder' and i['id'] != 0]

        cycle_note = [{
            'note_title': i['title'],
            'note_id': i['id']
        } for i in res2 if i['type'] == 'note']

        variable = []

        if folder_id == 0:
            variable.append('back_to_menu')
        else:
            variable.append('back_to_parent_folder')

        if not cycle_folder and not cycle_note and folder_id != 0:
            variable.append('delete')

        markup = markup_generate(
            buttons=self.buttons['AdminFolder'],
            folder_id=folder_id,
            cycle_folder=cycle_folder,
            cycle_note=cycle_note,
            parent_folder_id=res1['parent_id'],
            variable=variable
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            markup=markup
        )


class AdminNoteChangeTitle(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/note/([0-9]+)/change_title/', self.cdata)
        if rres:
            note_id = int(rres.group(1))
            await self.process(note_id=note_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['note_id'])

        text = Template(self.edit_texts['AdminNoteChangeTitle']).substitute(
            title=res['title']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/note/{kwargs["note_id"]}/')]])
        )


class AdminNoteChangeText(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/note/([0-9]+)/change_text/', self.cdata)
        if rres:
            note_id = int(rres.group(1))
            await self.process(note_id=note_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['note_id'])

        text = Template(self.edit_texts['AdminNoteChangeText']).substitute(
            title=res['title']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/note/{kwargs["note_id"]}/')]])
        )


# Настройки
class AdminBotSettings(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/bot_settings/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminBotSettings']).substitute()

        markup = markup_generate(
            buttons=self.buttons['AdminBotSettings']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


# Теги
class AdminTags(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/tags/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminTags']).substitute()

        res = await self.db.fetch("""
            SELECT tag FROM note_table
            WHERE id = parent_id
                AND tag <> 'admin';
        """)

        cycle = [{
            'tag': i['tag']
        } for i in res if i['tag'] and i['tag'] != 'admin']

        markup = markup_generate(
            buttons=self.buttons['AdminTags'],
            cycle=cycle
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminTag(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+)/', self.cdata)
        if rres:
            tag = rres.group(1)
            if tag == 'create_tag':
                return
            await self.process(tag=tag)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        tag = kwargs['tag']
        text = Template(self.edit_texts['AdminTag']).substitute(
            tag=tag
        )

        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE tag = $1;
        """, tag)

        markup = markup_generate(
            buttons=self.buttons['AdminTag'],
            tag=tag,
            folder_id=res['id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminTagCreateTag(AdminTag):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/create_tag/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminTagCreateTag']).substitute()

        markup = markup_generate(
            buttons=self.global_texts['cancel'],
            callback='admin/tags/'
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminTagChangeTag(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+)/change_tag/', self.cdata)
        if rres:
            tag = rres.group(1)
            await self.process(tag=tag)
            return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        tag = kwargs['tag']
        text = Template(self.edit_texts['AdminTagChangeTag']).substitute(
            tag=tag
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data=f'admin/tag/{tag}/')]])
        )


class AdminTagChangeChats(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+)/change_chats/', self.cdata)
        if rres:
            tag = rres.group(1)
            await self.process(tag=tag)
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        tag = kwargs['tag']

        text = Template(self.edit_texts['AdminTagChangeChats']).substitute(
            tag=tag
        )

        res = await self.db.fetch("""
            SELECT * FROM chat_table
            WHERE type = 'chat'
            ORDER BY id ASC;
        """)

        cycle = []

        for i in res:
            status = '⏺'

            if i['tag'] == tag:
                status = '✅'

            cycle.append({
                'status': status,
                'code_name': i['code_name'],
                'title': i['title'],
                'tag': tag,
                'chat_pk': i['id']
            })

        markup = markup_generate(
            buttons=self.buttons['AdminTagChangeChats'],
            cycle=cycle,
            tag=tag
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminTagChangeUsers(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+)/change_users/', self.cdata)
        if rres:
            tag = rres.group(1)
            await self.process(tag=tag)
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        tag = kwargs['tag']

        text = Template(self.edit_texts['AdminTagChangeUsers']).substitute(
            tag=tag
        )

        res = await self.db.fetch("""
            SELECT * FROM user_table
            ORDER BY id ASC;
        """)

        cycle = []

        for i in res:
            if i['id'] == 0:
                continue
            access_level = ''

            if i['access_level'] == 'employee':
                access_level = 'сотрудник'
            elif i['access_level'] == 'client':
                access_level = 'контрагент'
            elif i['access_level'] in ['admin', 'zero', 'employee_parsing']:
                continue

            status = '⏺'

            if i['tag'] == tag:
                status = '✅'

            cycle.append({
                'status': status,
                'username': i['username'],
                'first_name': i['first_name'],
                'access_level': access_level,
                'user_pk': i['id'],
                'tag': tag
            })

        markup = markup_generate(
            buttons=self.buttons['AdminTagChangeUsers'],
            cycle=cycle,
            tag=tag
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminTagChangeChat(AdminTagChangeChats):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+)/change_chat/([0-9]+)/', self.cdata)
        if rres:
            tag = rres.group(1)
            chat_pk = int(rres.group(2))
            await self.process(tag=tag, chat_pk=chat_pk)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET tag = CASE
                WHEN tag = $1 THEN NULL 
                ELSE $1
                END
            WHERE id = $2;
        """, kwargs['tag'], kwargs['chat_pk'])

        message_obj = await AdminTagChangeChats.generate_edit_message(self, **kwargs)
        await self.bot.edit_text(message_obj)


class AdminTagChangeUser(AdminTagChangeUsers):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+)/change_user/([0-9]+)/', self.cdata)
        if rres:
            tag = rres.group(1)
            user_pk = int(rres.group(2))
            await self.process(tag=tag, user_pk=user_pk)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE user_table
            SET tag = CASE
                WHEN tag = $1 THEN NULL 
                ELSE $1
                END
            WHERE id = $2;
        """, kwargs['tag'], kwargs['user_pk'])

        message_obj = await AdminTagChangeUsers.generate_edit_message(self, **kwargs)
        await self.bot.edit_text(message_obj)


class AdminTagDeleteTag(AdminTagChangeChats):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+)/delete/([12])/', self.cdata)
        if rres:
            tag = rres.group(1)
            stage = rres.group(2)
            await self.process(tag=tag, stage=stage)
            return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['stage'] == '2':
            await self.db.execute("""
                UPDATE chat_table
                SET tag = NULL
                WHERE tag = $1;
            """, kwargs['tag'])

            await self.db.execute("""
                DELETE FROM note_table
                WHERE id <> parent_id
                    AND tag = $1;
            """, kwargs['tag'])

            await self.db.execute("""
                DELETE FROM note_table
                WHERE id = parent_id
                    AND tag = $1;
            """, kwargs['tag'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

        if kwargs['stage'] == '2':
            message_obj = await self.generate_send_message()
            await self.bot.send_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == '1':
            text = Template(self.edit_texts['AdminTagDeleteTag1']).substitute()
        else:
            text = Template(self.edit_texts['AdminTagDeleteTag2']).substitute(
                tag=kwargs['tag']
            )

        markup = None

        if kwargs['stage'] == '1':
            markup = markup_generate(
                buttons=self.buttons['AdminTagDeleteTag'],
                tag=kwargs['tag']
            )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminTags']).substitute()

        res = await self.db.fetch("""
            SELECT tag FROM note_table
            WHERE id = parent_id
                AND tag <> 'admin';
        """)

        cycle = [{
            'tag': i['tag']
        } for i in res if i['tag'] and i['tag'] != 'admin']

        markup = markup_generate(
            buttons=self.buttons['AdminTags'],
            cycle=cycle
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
            markup=markup
        )

# Cотрудники
class AdminEmployees(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/employees/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetch("""
            SELECT * FROM user_table;
        """)

        employees = ''

        employees_parsing = ''

        clients = ''

        for i in res:
            acs_lvl = i['access_level']
            first_name = i["first_name"] if i["first_name"] else "Без имени"
            username = ('@' + i["username"]) if i["username"] else i["user_id"]
            if acs_lvl == 'employee':
                employees += f'<b>{first_name}</b> ({username})\n'
            elif acs_lvl == 'employee_parsing':
                employees_parsing += f'<b>{first_name}</b> ({username})\n'
            elif acs_lvl == 'client':
                clients += f'<b>{first_name}</b> ({username})\n'

        text = Template(self.edit_texts['AdminEmployees']).substitute(
            employees=employees,
            employees_parsing=employees_parsing,
            clients=clients
        )

        markup = markup_generate(
            buttons=self.buttons['AdminEmployees']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminEmployeesAdd(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/employees/add/([^/]+)/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminEmployeesAdd']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='admin/employees/')]])
        )


class AdminEmployeesRemove(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/employees/remove/([^/]+)/', self.cdata)
            if rres:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        if self.pressure_info:
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminEmployeesAdd']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='admin/employees/')]])
        )


# Команды
class AdminCommands(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/commands/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminCommands']).substitute()
        markup = markup_generate(
            self.buttons['AdminCommands']
        )
        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminCommandsList(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/commands/([^/]+)/([^/]+)/', self.cdata)
        if rres:
            chat_type = rres.group(1)
            user_type = rres.group(2)
            await self.process(chat_type=chat_type, user_type=user_type)
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        chat_type = kwargs['chat_type']
        user_type = kwargs['user_type']

        command_list = []

        if chat_type == 'private':
            if user_type == 'admin':
                command_list = ['AdminMenuCommand']
            elif user_type == 'employee':
                command_list = [
                    'AddressListCommand',
                    'TrackingCommand',
                    'OffTrackingCommand'
                ]
        elif chat_type == 'group':
            if user_type == 'admin':
                command_list = [
                    'UnlockChatCommand',
                    'LockChatCommand',
                    'EditChatThemeCommand'
                ]
            elif user_type == 'employee':
                command_list = [
                    'BalanceListCommand',
                    'StoryCommand',
                    'DetailCommand',
                    'CancelCommand',
                    'NullCommand'
                ]

        text = Template(self.edit_texts['AdminCommandsList']).substitute()

        cycle = []

        for key, item in self.global_texts['keywords'].items():
            if key in command_list:
                cycle.append({'text': item.replace('\\', ''), "title": key})

        markup = markup_generate(
            self.buttons['AdminCommandsList'],
            cycle=cycle
        )
        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminChangeCommand(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/change_command/([^/]+)/', self.cdata)
        if rres:
            command = rres.group(1)
            await self.process(command=command)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminChangeCommand']).substitute(
            command=self.global_texts['keywords'][kwargs['command']].replace('\\', '')
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='admin/commands/')]])
        )


class AdminInstruction(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/instruction/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        keywords = self.global_texts['keywords']

        text = Template(self.edit_texts['AdminInstruction']).substitute(
            **keywords
        )

        markup = markup_generate(
            buttons=self.buttons['AdminInstruction']
        )
        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminRevise(CallbackQueryCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/revise/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            INSERT INTO pressure_button_table
            (chat_pid, user_pid, message_id, callback_data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_pid, message_id, callback_data) DO NOTHING;
        """, None, self.db_user['id'], self.sent_message_id, self.cdata)

        message_obj = await self.generate_edit_message()
        await self.bot.edit_text(message_obj)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminRevise']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
        )


class Null1(CallbackQueryCommand):
    async def define(self):
        pass

    async def process(self, *args, **kwargs) -> None:
        pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass
