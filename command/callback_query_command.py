import datetime
import re
from string import Template

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
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.sent_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass


# Команды админов в группе
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
                        await self.bot.answer_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

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
            message_id=self.sent_message_id
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
                        await self.bot.answer_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

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
            value=float_to_str(res['value'])
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
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
                        await self.bot.answer_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

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
            message_id=self.sent_message_id
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
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, self.db_chat['id'])

        markup = markup_generate(
            self.buttons['EditChatThemeCommand'],
            chat_id=self.db_chat['id'],
            variable=[] if res['topic'] == res['main_topic'] else ['1']
        )
        text = Template(self.global_texts['message_command']['EditChatThemeCommand']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
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
            title=res['title'],
            value=float_to_str(res['value']),
            postfix=res['postfix'] if res['postfix'] else ''
        )

        markup = markup_generate(
            buttons=self.buttons['EditCurrencyCommand'],
            variable=['2'],
            curr_id=kwargs['curr_id'],
            chat_id=self.db_chat['id']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


# class CurrencyBalance(CallbackQueryCommand):
#     async def define(self):
#         if self.access_level == 'admin':
#             rres = re.fullmatch(r'chat/curr_balance/([0-9]+)/', self.cdata)
#             if rres:
#                 curr_id = int(rres.group(1))
#                 await self.process(curr_id=curr_id)
#                 return True
#
#     async def process(self, *args, **kwargs) -> None:
#         message_obj = await self.generate_edit_message(**kwargs)
#         await self.bot.edit_text(message_obj)
#
#     async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
#         pass
#
#     async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
#         res = await self.db.fetchrow("""
#             SELECT * FROM currency_table
#             WHERE id = $1;
#         """, kwargs['curr_id'])
#
#         text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
#             title=res['title'],
#             value=float_to_str(res['value']),
#             postfix=res['postfix'] if res['postfix'] else ''
#         )
#
#         markup = markup_generate(
#             buttons=self.buttons['CurrencyBalanceCommand'],
#             variable=['1'],
#             curr_id=kwargs['curr_id'],
#             chat_id=self.db_chat['id']
#         )
#
#         return EditMessage(
#             chat_id=self.chat.id,
#             text=text,
#             message_id=self.sent_message_id,
#             markup=markup
#         )


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
             'value': float_to_str(i['value']),
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


class ChatPhotoCalcCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/photo_calc/([0-9]+)/', self.cdata)
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
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_id'])
        text = Template(self.edit_texts['ChatPhotoCalcCommand']).substitute(
            sign='-' if res['sign'] is False else '+'
        )

        markup = markup_generate(
            self.buttons['ChatPhotoCalcCommand'],
            **kwargs
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class ChatPhotoCalc(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'chat/photo_calc/([0-9]+)/([+-])/', self.cdata)
            if rres:
                chat_id, sign = rres.groups()
                chat_id = int(chat_id)
                await self.process(chat_id=chat_id, sign=sign)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            set sign = $1
            WHERE id = $2;
        """, True if kwargs['sign'] == '+' else False, kwargs['chat_id'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['ChatPhotoCalc']).substitute(
            sign=kwargs['sign']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
        )


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
                    await self.bot.answer_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

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
            message_id=self.sent_message_id
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

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
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
            value=float_to_str(res['value']),
            postfix=res['postfix'] if res['postfix'] else ''
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

        story = story_generate(today_story)

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

        detail = detail_generate(today_story)

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
            value=float_to_str(kwargs['after_value']),
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
class AddressChangeMinValueCommand(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'address/change_min_value/([^/]+)/', self.cdata)
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
                    await self.bot.answer_query(self.callback.id, 'А прошлая команда? Про неё совсем забыл?')

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
            message_id=self.sent_message_id
        )


class AddressDelete(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'address/delete/([^/]+)/', self.cdata)
            if rres:
                address = rres.group(1)
                await self.process(address=address)
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
            address=kwargs['address']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AddressDeleteSecond(CallbackQueryCommand):
    async def define(self):
        if self.access_level in ['admin', 'employee']:
            rres = re.fullmatch(r'address/delete/([^/]+)/([^/]+)/', self.cdata)
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

        chat_list = [f'<b><a href="{i["link"]}">{i["title"]}</a></b>: <code>{i["code_name"]}</code>'
                     for i in res]

        chat_list_links = '\n'.join(chat_list)

        text = Template(self.edit_texts['AdminChats']).substitute(
            chat_list_links=chat_list_links
        )

        markup = markup_generate(
            buttons=self.buttons['AdminChats'],
            cycle=[{'title': i['title'], 'code_name': i['code_name'], 'chat_pk': i['id']} for i in res]
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
            markup=markup
        )


class AdminChat(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/', self.cdata)
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
        text = Template(self.edit_texts['AdminChat']).substitute(
            title=res['title'],
            code_name=res['code_name']
        )

        markup = markup_generate(
            buttons=self.buttons['AdminChat'],
            chat_pk=kwargs['chat_pk'],
            variable=['1'] if res['locked'] is False else []
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


class AdminChatLock(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/chat/([0-9]+)/lock/', self.cdata)
            if rres:
                chat_pk = int(rres.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE chat_table
            SET locked = TRUE
            WHERE id = $1;
        """, kwargs['chat_pk'])

        message_obj = await self.generate_edit_message(**kwargs)
        await self.bot.edit_text(message_obj)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM chat_table
            WHERE id = $1;
        """, kwargs['chat_pk'])

        text = Template(self.edit_texts['AdminChatLock']).substitute(
            title=res['title'],
            code_name=res['code_name']
        )

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
        )


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
        )


class AdminEmployees(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/employees/', self.cdata)
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
            SELECT * FROM user_table
            WHERE access_level == 'employee';
        """)

        employee_list = [f'<b>{i["first_name"] if i["first_name"] else "Без имени"}</b> ({"@" + i["username"] if i["username"] else i["user_id"]})'
                         for i in res]

        text = Template(self.edit_texts['AdminEmployees']).substitute(
            employee_list='\n'.join(employee_list)
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
            rres = re.fullmatch(r'admin/employees/add/', self.cdata)
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

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminEmployeesAdd']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
        )


class AdminEmployeesRemove(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/employees/remove/', self.cdata)
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

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminEmployeesRemove']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
        )


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
        text = Template(self.edit_texts['AdminDistribution']).substitute()

        markup = markup_generate(
            buttons=self.buttons['AdminDistribution']
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
            rres = re.fullmatch(r'admin/distribution/pin/', self.cdata)
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

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminDistributionPin']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
        )


class AdminDistributionUnpin(CallbackQueryCommand):
    async def define(self):
        if self.access_level == 'admin':
            rres = re.fullmatch(r'admin/distribution/unpin/', self.cdata)
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

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.edit_texts['AdminDistributionUnpin']).substitute()

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id,
        )


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

        return EditMessage(
            chat_id=self.chat.id,
            text=text,
            message_id=self.sent_message_id
        )


class Null(CallbackQueryCommand):
    async def define(self):
        pass

    async def process(self, *args, **kwargs) -> None:
        pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass