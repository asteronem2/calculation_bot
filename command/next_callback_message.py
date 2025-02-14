import asyncio
import json
import re
from string import Template

import aiogram
from aiogram import exceptions

import BotInteraction
from BotInteraction import EditMessage, TextMessage
from command.command_interface import NextCallbackMessageCommand
from main import message_command_cls
from utils import calculate, float_to_str, str_to_float, markup_generate, entities_to_html


class CurrChangeTitleCommand(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'curr/change_title/([0-9]+)/', self.cdata)
        if rres:
            curr_id = int(rres.group(1))
            await self.process(curr_id=curr_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs.get('error'):
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

            message_obj = self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

        else:
            res = await self.db.fetchrow("""
                SELECT * FROM currency_table
                WHERE id = $1;
            """, kwargs['curr_id'])

            await self.db.execute("""
                UPDATE currency_table
                SET title = $1
                WHERE id = $2;
            """, self.text_low, kwargs['curr_id'])

            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

            # message_obj = await self.generate_send_message(title1=res['title'], title2=self.text_low)
            # await self.bot.send_text(message_obj)
            # await self.bot.delete_message(
            #     chat_id=self.chat.id,
            #     message_id=self.press_message_id
            # )
            message_obj = await self.generate_send_message(stage=1, title1=res['title'], title2=self.text_low, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
            message_obj2 = await self.generate_send_message(stage=2, **kwargs)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['CurrChangeTitleCommand']).substitute(
                title1=kwargs['title1'].upper(),
                title2=kwargs['title2'].upper()
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic
            )
        else:
            text = Template(self.global_texts['message_command']['EditCurrencyCommand']).substitute(
                title=self.text_low.upper()
            )
            markup = markup_generate(
                self.buttons['EditCurrencyEdit'],
                curr_id=kwargs['curr_id']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['TitleCantWithSpace']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
        )


class CurrChangeValueCommand(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'curr/change_value/([0-9]+)/', self.cdata)
        if rres1:
            rres2 = re.fullmatch(r'[0-9,. -]+', self.text_low)
            if rres2:
                curr_id = int(rres1.group(1))
                await self.process(curr_id=curr_id)
                return True
            else:
                await self.process(error='error')

    async def process(self, *args, **kwargs) -> None:
        if kwargs.get('error'):
            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

            message_obj = self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM currency_table
                WHERE id = $1
            """, kwargs['curr_id'])

            new_value = calculate(self.text_low)

            await self.db.execute("""
                UPDATE currency_table
                SET value = $1
                WHERE id = $2;
            """, new_value, kwargs['curr_id'])

            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

            # message_obj = await self.generate_send_message(title=res['title'], value=new_value, res=res)
            # await self.bot.send_text(message_obj)
            # await self.bot.delete_message(
            #     chat_id=self.chat.id,
            #     message_id=self.press_message_id
            # )
            message_obj = await self.generate_send_message(stage=1, title=res['title'], value=new_value, res=res,
                                                           **kwargs)
            sent_message = await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
            message_obj2 = await self.generate_send_message(stage=2, title=res['title'], res=res, **kwargs)
            await self.bot.send_text(message_obj2)

            await self.db.add_story(
                curr_id=kwargs['curr_id'],
                user_id=self.db_user['id'],
                expr_type='update',
                before_value=res['value'],
                after_value=new_value,
                message_id=self.message.message_id,
                expression=self.text_low
            )

            await self.db.add_story(
                curr_id=kwargs['curr_id'],
                user_id=self.db_user['id'],
                expr_type='update',
                before_value=res['value'],
                after_value=new_value,
                message_id=self.message.message_id,
                expression=self.text_low,
                sent_message_id=sent_message.message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.texts['send']['CurrChangeValueCommand']).substitute(
                title=kwargs['title'],
                value=float_to_str(kwargs['value'], kwargs['res']['rounding'])
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
        else:
            text = Template(self.global_texts['message_command']['EditCurrencyCommand']).substitute(
                title=kwargs['title'].upper()
            )
            markup = markup_generate(
                self.buttons['EditCurrencyEdit'],
                curr_id=kwargs['res']['id']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['IncorrectValue']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
        )


class CurrChangePostfixCommand(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'curr/change_postfix/([0-9]+)/', self.cdata)
        if rres:
            if self.text_low.count(' ') == 0:
                curr_id = int(rres.group(1))
                await self.process(curr_id=curr_id)
                return True
            else:
                await self.process(error='error')

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM currency_table
                WHERE chat_pid = $1;
            """, self.db_chat['id'])

            new_postfix = self.text.strip() if self.text_low != '*' else None
            await self.db.execute("""
                UPDATE currency_table
                SET postfix = $1
                WHERE id = $2;
            """, new_postfix, kwargs['curr_id'])

            message_obj = await self.generate_send_message(stage=1, title=res['title'], postfix=new_postfix)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await self.generate_send_message(stage=2, res=res, **kwargs)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.texts['send']['CurrChangePostfixCommand']).substitute(
                title=kwargs['title'],
                postfix=kwargs['postfix']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic
            )
        else:
            text = Template(self.global_texts['message_command']['EditCurrencyCommand']).substitute(
                title=kwargs['res']['title'].upper()
            )
            markup = markup_generate(
                self.buttons['EditCurrencyEdit'],
                curr_id=kwargs['res']['id']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['PostfixCantWithSpace']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic,
        )


class CurrCalculationCommand(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'curr/calculation/([0-9]+)/', self.cdata)
        if rres1:
            rres2 = re.fullmatch(r'[+*%/0-9., -]+', self.text_low)
            if rres2:
                curr_id = int(rres1.group(1))
                calc_res = calculate(self.text_low)
                if calc_res is not False:
                    await self.process(curr_id=curr_id, calc_res=calc_res)
                    return True
                else:
                    await self.process(error='error')
            else:
                await self.process(error='error')

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM currency_table
                WHERE id = $1;
            """, kwargs['curr_id'])

            before_value = res['value']
            after_value = before_value + kwargs['calc_res']

            await self.db.execute("""
                UPDATE currency_table
                SET value = $1
                WHERE id = $2;
            """, after_value, kwargs['curr_id'])

            message_obj = await self.generate_send_message(stage=1, res=res, after_value=after_value, **kwargs)
            sent_message = await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await self.generate_send_message(stage=2, res=res, **kwargs)
            await self.bot.send_text(message_obj2)

            await self.db.add_story(
                curr_id=kwargs['curr_id'],
                user_id=self.db_user['id'],
                expr_type='add',
                before_value=before_value,
                after_value=after_value,
                message_id=self.message.message_id,
                expression=self.text_low,
                sent_message_id=sent_message.message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
                title=kwargs['res']['title'].upper(),
                value=float_to_str(kwargs['after_value'], kwargs['res']['rounding']),
                postfix=kwargs['res']['title'] or ''
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
        else:
            text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
                title=kwargs['res']['title'].upper(),
                value=float_to_str(kwargs['res']['value'], kwargs['res']['rounding']),
                postfix=kwargs['res']['postfix']
            )
            markup = markup_generate(
                self.buttons['CurrencyBalanceCommand'],
                curr_id=kwargs['res']['id'],
                chat_id=kwargs['res']['chat_pid'],
                rounding=kwargs['res']['rounding'],
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['IncorrectCalculation']).substitute()
        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
        )


class AddressChangeMinValueCommand(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'address/change_min_value/([^/]+)/', self.cdata)
        if rres1:
            rres2 = re.fullmatch(r'[0-9,. ]+', self.text_low)
            if rres2:
                address_id = int(rres1.group(1))
                await self.process(address_id=address_id)
                return True
            else:
                await self.process(error='error')
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            min_value = str_to_float(self.text_low)
            await self.db.execute("""
                UPDATE crypto_parsing_table
                SET min_value = $1
                WHERE id = $2;
            """, min_value, kwargs['address_id'])

            message_obj = await self.generate_send_message(min_value=min_value, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        res = await self.db.fetchrow("""
            SELECT * FROM crypto_parsing_table
            WHERE id = $1;
        """, kwargs['address_id'])

        text = Template(self.send_texts['AddressChangeMinValueCommand']).substitute(
            min_value=float_to_str(kwargs['min_value']),
            address=res['address']
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['MinValueMustBeFloat']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminChatChangeCodeName(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/chat/([0-9]+)/change_code_name/', self.cdata)
        if rres1:
            # if self.text_low.count(' '):
            #     await self.process(error='error')
            #     return True
            # else:
            chat_pk = int(rres1.group(1))
            await self.process(chat_pk=chat_pk)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            new_code_name = self.text
            await self.db.execute("""
                UPDATE chat_table
                SET code_name = $1
                WHERE id = $2;
            """, new_code_name, kwargs['chat_pk'])

            message_obj = await self.generate_send_message(stage=1, new_code_name=new_code_name, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await self.generate_send_message(stage=2, new_code_name=new_code_name, **kwargs)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            res = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, kwargs['chat_pk'])

            text = Template(self.send_texts['AdminChatChangeCodeName']).substitute(
                title=res['title'],
                code_name=res['code_name']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, kwargs['chat_pk'])

            res2 = await self.db.fetch("""
                SELECT * FROM currency_table
                WHERE chat_pid = $1
                ORDER BY title ASC;
            """, kwargs['chat_pk'])

            curr_info_list = ''

            for i in res2:
                curr_info_list += Template(self.global_texts['addition']['little_balance']).substitute(
                    title=i['title'].upper(),
                    value=float_to_str(i['value'], i['rounding']),
                    postfix=i['postfix'] if i['postfix'] else ''
                )

            text = Template(self.call_edit_texts['AdminChat']).substitute(
                title=res['title'],
                link=res['link'],
                code_name=res['code_name'],
                curr_info_list=curr_info_list
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

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['CodeNameCantWithSpace']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminChatSetTag(AdminChatChangeCodeName):
    async def define(self):
        rres1 = re.fullmatch(r'admin/chat/([^/]+)/set_tag/', self.cdata)
        if rres1:
            if len(self.text_low) > 32:
                await self.process(error='error')
                return True
            else:
                chat_pk = int(rres1.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            tag = self.text_low.replace('/', '\\')

            res = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE tag = $1;
            """, tag)

            if not res:
                await self.db.execute("""
                    INSERT INTO note_table
                    (id, user_pid, title, type, parent_id, tag)
                    VALUES
                    ((SELECT MAX(id) from note_table) + 1, $1, $2, 'folder', (SELECT MAX(id) from note_table) + 1, $3)
                """, self.db_user['id'], tag, tag)

            await self.db.execute("""
                UPDATE chat_table
                SET tag = $1
                WHERE id = $2;
            """, tag if tag != '*' else None, kwargs['chat_pk'])

            message_obj = await self.generate_send_message(stage=1, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await self.generate_send_message(stage=2, **kwargs)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            res = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, kwargs['chat_pk'])

            text = Template(self.send_texts['AdminChatSetTag']).substitute(
                title=res['title'],
                code_name=res['code_name'],
                tag=res['tag'] if res['tag'] else 'отсутствует'
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            return await AdminChatChangeCodeName.generate_send_message(self, **kwargs)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['TagMaxLen32']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminChatChangeTag(AdminChatChangeCodeName):
    async def define(self):
        rres1 = re.fullmatch(r'admin/chat/([^/]+)/change_tag/', self.cdata)
        if rres1:
            if len(self.text_low) > 32:
                await self.process(error='error')
                return True
            else:
                chat_pk = int(rres1.group(1))
                await self.process(chat_pk=chat_pk)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            tag = self.text_low.replace('/', '\\')

            res = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE tag = $1;
            """, tag)

            if not res:
                await self.db.execute("""
                    INSERT INTO note_table
                    (id, user_pid, title, type, parent_id, tag)
                    VALUES
                    ((SELECT MAX(id) from note_table) + 1, $1, $2, 'folder', (SELECT MAX(id) from note_table) + 1, $3)
                """, self.db_user['id'], tag, tag)

            await self.db.execute("""
                UPDATE chat_table
                SET tag = $1
                WHERE id = $2;
            """, tag if tag != '*' else None, kwargs['chat_pk'])

            message_obj = await self.generate_send_message(stage=1, tag=tag, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await self.generate_send_message(stage=2, **kwargs)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            res = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, kwargs['chat_pk'])

            text = Template(self.send_texts['AdminChatChangeTag']).substitute(
                title=res['title'],
                code_name=res['code_name'],
                tag=res['tag'] if res['tag'] else 'отсутствует'
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            return await AdminChatChangeCodeName.generate_send_message(self, **kwargs)

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['TagMaxLen32']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminTagChangeTag(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/([^/]+?)/change_tag/', self.cdata)
        if rres:
            if len(self.text_low) > 32:
                await self.process(error='error')
                return True
            else:
                tag = rres.group(1)
                await self.process(tag=tag)
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            new_tag = self.text_low.replace('/', '\\')
            old_tag = kwargs['tag']

            await self.db.execute("""
                UPDATE chat_table
                SET tag = $1
                WHERE tag = $2;
            """, new_tag, old_tag)

            await self.db.execute("""
                UPDATE note_table
                SET title = $1
                WHERE id = parent_id
                    AND tag = $2;
            """, new_tag, old_tag)

            await self.db.execute("""
                UPDATE note_table
                SET tag = $1
                WHERE tag = $2;
            """, new_tag, old_tag)

            message_obj = await self.generate_send_message(stage=1, new_tag=new_tag, old_tag=old_tag)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await self.generate_send_message(stage=2, tag=new_tag)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['AdminTagChangeTag']).substitute(
                old_tag=kwargs['old_tag'],
                new_tag=kwargs['new_tag']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            tag = kwargs['tag']
            text = Template(self.call_edit_texts['AdminTag']).substitute(
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

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup
            )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['TagMaxLen32']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminTagCreateTag(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/tag/create_tag/', self.cdata)
        if rres:
            if len(self.text_low) > 32:
                await self.process(error='to_many_symbols')
                return True
            else:
                await self.process()
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        tag = self.text_low.replace('/', '\\')

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            res = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE tag = $1;
            """, tag)

            if not res:
                await self.db.execute("""
                    INSERT INTO note_table
                    (id, user_pid, title, type, parent_id, tag)
                    VALUES
                    ((SELECT MAX(id) from note_table) + 1, $1, $2, 'folder', (SELECT MAX(id) from note_table) + 1, $3)
                """, self.db_user['id'], tag, tag)
                message_obj = await self.generate_send_message(stage=1, tag=tag)
                await self.bot.send_text(message_obj)
                await self.bot.delete_message(
                    chat_id=self.chat.id,
                    message_id=self.press_message_id
                )
            else:
                pass

        message_obj2 = await self.generate_send_message(stage=2, tag=tag)
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['AdminTagCreateTag']).substitute(
                tag=kwargs['tag']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            tag = kwargs['tag']
            text = Template(self.call_edit_texts['AdminTag']).substitute(
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

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup
            )

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['TagMaxLen32']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminEmployeesAdd(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/employees/add/([^/]+)/', self.cdata)
        if rres1:
            rres2 = re.findall(r'[^,./| ]+', self.text.replace('@', ''))
            if rres2:
                type_ = rres1.group(1)
                await self.process(username_list=rres2, type_=type_)
                return True
            else:
                await self.process(error='error')
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            for i in kwargs['username_list']:
                await self.db.execute("""
                        UPDATE user_table
                        SET access_level = $1
                        WHERE lower(username) = $2
                            AND access_level <> 'admin';
                    """, kwargs['type_'], i.lower())

                if kwargs['type_'] == 'client':
                    res1 = await self.db.fetchrow("""
                        SELECT * FROM user_table
                        WHERE lower(username) = $1;
                    """, i)
                    if not res1:
                        continue
                    res2 = await self.db.fetch("""
                        SELECT * FROM chat_table
                        WHERE type = 'chat'
                            AND id in (
                                SELECT DISTINCT chat_pid
                                FROM currency_table
                            );
                    """)
                    for chat in res2:
                        inside = False
                        try:
                            status = (await self.bot.bot.get_chat_member(
                                chat_id=chat['chat_id'],
                                user_id=res1['user_id']
                            )).status
                            if status != 'left':
                                inside = True
                        except aiogram.exceptions.TelegramBadRequest:
                            pass
                        if inside is True:
                            await self.db.execute("""
                                UPDATE user_table
                                SET bind_chat = $1
                                WHERE id = $2;
                            """, chat['id'], res1['id'])
                            break

            message_obj = await self.generate_send_message(stage=1, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await self.generate_send_message(stage=2, **kwargs)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['AdminEmployeesAdd']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetch("""
                SELECT * FROM user_table
                ORDER BY username ASC;
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

            text = Template(self.call_edit_texts['AdminEmployees']).substitute(
                employees=employees or 'Пока никого нет',
                employees_parsing=employees_parsing or 'Пока никого нет',
                clients=clients or 'Пока никого нет'
            )

            markup = markup_generate(
                buttons=self.buttons['AdminEmployees']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                message_thread_id=self.topic,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


class AdminEmployeesRemove(AdminEmployeesAdd):
    async def define(self):
        rres1 = re.fullmatch(r'admin/employees/remove/([^/]+)/', self.cdata)
        if rres1:
            rres2 = re.findall(r'[^,./| ]+', self.text.replace('@', ''))
            if rres2:
                type_ = rres1.group(1)
                await self.process(username_list=rres2, type_=type_)
                return True
            else:
                await self.process(error='error')
                return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs.get('error'):
            message_obj = await self.generate_error_message()
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
        else:
            for i in kwargs['username_list']:
                await self.db.execute("""
                        UPDATE user_table
                        SET access_level = 'zero'
                        WHERE username = $1
                            AND access_level <> 'admin'
                            AND access_level = $2;
                    """, i, kwargs['type_'])

            message_obj = await self.generate_send_message(stage=1, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

            message_obj2 = await AdminEmployeesAdd.generate_send_message(self, stage=2, **kwargs)
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.send_texts['AdminEmployeesRemove']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


class AdminDistributionPin(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/distribution/(pin|unpin)/([^/]+)/', self.cdata)
        if rres1:
            pin = True if rres1.group(1) == 'pin' else False
            tag = rres1.group(2)
            await self.process(tag=tag, pin=pin)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        if kwargs['tag'] != 'to_all':
            res = await self.db.fetch("""
                SELECT * FROM chat_table
                WHERE type = 'chat' 
                    AND super = FALSE
                    AND COALESCE(tag, '1') = COALESCE($1, '1');
            """, kwargs['tag'] if kwargs['tag'] != 'to_all' else None)
        else:
            res = await self.db.fetch("""
                SELECT * FROM chat_table
                WHERE super = FALSE;
            """)

        text = entities_to_html(self.message.text, self.message.entities) if self.message.text else \
            (entities_to_html(self.message.caption, self.message.caption_entities) if self.message.caption else '_')

        photo = self.message.photo
        for i in res:
            if photo:
                message_obj = TextMessage(chat_id=i['chat_id'], text=text, pin=kwargs['pin'], photo=photo[-1].file_id)
                await self.bot.send_text(message_obj)
            else:
                message_obj = TextMessage(chat_id=i['chat_id'], text=text, pin=kwargs['pin'])
                await self.bot.send_text(message_obj)

        message_obj = await self.generate_send_message(stage=1, **kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.press_message_id
        )

        message_obj2 = await self.generate_send_message(stage=2, **kwargs)
        await self.bot.send_text(message_obj2)

        await self.db.execute("""
            INSERT INTO distribution_table
            (user_pid, tag, text, pin, file_id)
            VALUES ($1, $2, $3, $4, $5);
        """,
                              self.db_user['id'],
                              kwargs['tag'],
                              text,
                              kwargs['pin'],
                              None
                              )

        res3 = await self.db.fetch("""
            SELECT * FROM message_table
            WHERE user_pid = $1
                AND type in ('distribution_last');
        """, self.db_user['id'])

        await self.db.execute("""
            SELECT * FROM message_table
            WHERE user_pid = $1
                AND type in ('distribution_last');
        """, self.db_user['id'])

        if res3:
            msg_ids = [i['message_id'] for i in res3]
            await self.bot.bot.delete_messages(self.chat.id, msg_ids)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts[f'AdminDistribution{"Pin" if kwargs["pin"] else "Unpin"}']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetch("""
                SELECT DISTINCT tag FROM 
                    (
                    SELECT * FROM chat_table
                    ORDER BY title ASC
                    )
                AS subquery;
            """)
            text = Template(self.call_edit_texts['AdminDistribution']).substitute()

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

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


class CreateFolder(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'folder/([0-9]+)/create_folder/', self.cdata)
        if rres1:
            folder_id = int(rres1.group(1))
            await self.process(folder_id=folder_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        await self.db.execute("""
            INSERT INTO note_table
            (user_pid, title, type, parent_id)
            VALUES
            ($1, $2, 'folder', $3);
        """, self.db_user['id'], self.text, kwargs['folder_id'])

        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE type = 'folder'
                AND title = $1;
        """, self.text)

        message_obj = await self.generate_send_message(stage=1, **kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.press_message_id
        )
        message_obj2 = await self.generate_send_message(stage=2, folder_id=res['id'])
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['CreateFolder']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM note_table
                WHERE id = $1;
            """, kwargs['folder_id'])

            child_notes = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE parent_id = $1
                    AND id <> parent_id
                    AND type = 'note'
                ORDER BY title ASC;
            """, kwargs['folder_id'])

            child_folders = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE parent_id = $1
                    AND id <> parent_id
                    AND type = 'folder'
                ORDER BY title ASC;
            """, kwargs['folder_id'])

            notes = ''

            if not res['expand']:
                for i in child_notes:
                    text = i['text']
                    notes += f'<blockquote expandable>{text}</blockquote>'
                    notes += '\n'

            text = Template(self.call_edit_texts['Folder']).substitute(
                folder_title=res['title'],
                notes=notes
            )

            variable = []

            if res['id'] == res['parent_id']:
                if res['id'] in (0, 1, 2):
                    variable.append('back_to_menu')
                else:
                    variable.append('back_to_tag')
            else:
                variable.append('to_menu')
                variable.append('back_to_parent_folder')

            if not child_notes and not child_folders and res['id'] != 0:
                variable.append('delete')

            message_obj_1 = TextMessage(
                chat_id=self.chat.id,
                text=Template(self.call_send_texts['FolderTopMessage']).substitute(title=res['title']),
                markup=markup_generate(
                    buttons=self.buttons['FolderTopMessage'],
                    folder_id=res['id']
                )
            )

            sent_message = await self.bot.send_text(message_obj_1)
            await self.db.execute("""
                INSERT INTO message_table
                (user_pid, message_id, text, type, is_bot_message)
                VALUES ($1, $2, $3, $4, TRUE);
            """,
                                  self.db_user['id'],
                                  sent_message.message_id,
                                  sent_message.text,
                                  'settings_folder'
                                  )

            if res['expand'] is True:
                variable.append('collapse')
                for i in child_notes:
                    message_obj = TextMessage(
                        chat_id=self.chat.id,
                        text=i['text'],
                        photo=i['file_id'],
                        disable_web_page_preview=i["disable_preview"]
                    )
                    file_rows = await self.db.fetch("""
                        SELECT * FROM note_files_table
                        WHERE note_pid = $1;
                    """, i["id"])
                    if file_rows:
                        message_obj.photo = [message_obj.photo] + [i["file_id"] for i in file_rows]
                        sent_message = await self.bot.send_text(message_obj)
                    else:
                        sent_message = [await self.bot.send_text(message_obj)]

                    if i['add_info']:
                        await self.bot.set_emoji(
                            chat_id=sent_message[0].chat.id,
                            message_id=sent_message[0].message_id,
                            emoji=self.global_texts['reactions']['HiddenInfo']
                        )
                    for ii in sent_message:
                        await self.db.execute("""
                            INSERT INTO message_table
                            (user_pid, message_id, text, type, is_bot_message, addition)
                            VALUES ($1, $2, $3, $4, TRUE, $5);
                        """,
                                              self.db_user['id'],
                                              ii.message_id,
                                              ii.text,
                                              'note',
                                              str(i['id'])
                                              )
            else:
                variable.append('expand')

            cycle_folder = [{
                'child_title': i['title'],
                'child_id': i['id']
            } for i in child_folders]

            markup = markup_generate(
                buttons=self.buttons['Folder'],
                folder_id=kwargs['folder_id'],
                cycle_folder=cycle_folder,
                parent_folder_id=res['parent_id'],
                variable=variable,
                tag=res['tag']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


class FolderChangeTitle(CreateFolder):
    async def define(self):
        rres1 = re.fullmatch(r'folder/([0-9]+)/change_title/', self.cdata)
        if rres1:
            folder_id = int(rres1.group(1))
            await self.process(folder_id=folder_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['folder_id'])

        await self.db.execute("""
            UPDATE note_table
            SET title = $1
            WHERE id = $2;
        """, self.text, kwargs['folder_id'])

        message_obj = await self.generate_send_message(stage=1, res=res, **kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.press_message_id
        )

        message_obj2 = await CreateFolder.generate_send_message(self, stage=2, folder_id=kwargs['folder_id'])
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['FolderChangeTitle']).substitute(
                old_title=kwargs['res']['title'],
                new_title=self.text
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM note_table
                WHERE id = $1;
            """, kwargs['folder_id'])

            child_notes = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE parent_id = $1
                    AND id <> parent_id
                    AND type = 'note'
                ORDER BY title ASC;
            """, kwargs['folder_id'])

            child_folders = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE parent_id = $1
                    AND id <> parent_id
                    AND type = 'folder'
                ORDER BY title ASC;
            """, kwargs['folder_id'])

            notes = ''

            if not res['expand']:
                for i in child_notes:
                    text = i['text']
                    notes += f'<blockquote expandable>{text}</blockquote>'
                    notes += '\n'

            text = Template(self.call_edit_texts['Folder']).substitute(
                folder_title=res['title'],
                notes=notes
            )

            variable = []

            if res['id'] == res['parent_id']:
                if res['id'] == 0:
                    variable.append('back_to_menu')
                else:
                    variable.append('back_to_tag')
            else:
                variable.append('to_menu')
                variable.append('back_to_parent_folder')

            if not child_notes and not child_folders and res['id'] != 0:
                variable.append('delete')

            message_obj_1 = TextMessage(
                chat_id=self.chat.id,
                text=Template(self.call_send_texts['FolderTopMessage']).substitute(title=res['title']),
                markup=markup_generate(
                    buttons=self.buttons['FolderTopMessage'],
                    folder_id=res['id']
                )
            )
            sent_message = await self.bot.send_text(message_obj_1)
            await self.db.execute("""
                INSERT INTO message_table
                (user_pid, message_id, text, type, is_bot_message)
                VALUES ($1, $2, $3, $4, TRUE);
            """,
                                  self.db_user['id'],
                                  sent_message.message_id,
                                  sent_message.text,
                                  'settings_folder'
                                  )

            if res['expand'] is True:
                variable.append('collapse')
                for i in child_notes:
                    message_obj = TextMessage(
                        chat_id=self.chat.id,
                        text=i['text'],
                        photo=i['file_id'],
                        disable_web_page_preview=i["disable_preview"]
                    )
                    file_rows = await self.db.fetch("""
                        SELECT * FROM note_files_table
                        WHERE note_pid = $1;
                    """, i["id"])
                    if file_rows:
                        message_obj.photo = [message_obj.photo] + [i["file_id"] for i in file_rows]
                        sent_message = await self.bot.send_text(message_obj)
                    else:
                        sent_message = [await self.bot.send_text(message_obj)]

                    if i['add_info']:
                        await self.bot.set_emoji(
                            chat_id=sent_message[0].chat.id,
                            message_id=sent_message[0].message_id,
                            emoji=self.global_texts['reactions']['HiddenInfo']
                        )
                    for ii in sent_message:
                        await self.db.execute("""
                            INSERT INTO message_table
                            (user_pid, message_id, text, type, is_bot_message, addition)
                            VALUES ($1, $2, $3, $4, TRUE, $5);
                        """,
                                              self.db_user['id'],
                                              ii.message_id,
                                              ii.text,
                                              'note',
                                              str(i['id'])
                                              )
            else:
                variable.append('expand')

            cycle_folder = [{
                'child_title': i['title'],
                'child_id': i['id']
            } for i in child_folders]

            markup = markup_generate(
                buttons=self.buttons['Folder'],
                folder_id=kwargs['folder_id'],
                cycle_folder=cycle_folder,
                parent_folder_id=res['parent_id'],
                variable=variable,
                tag=res['tag']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


class CreateNote(CreateFolder):
    async def define(self):
        rres1 = re.fullmatch(r'folder/([0-9]+)/create_note/', self.cdata)
        if rres1:
            folder_id = int(rres1.group(1))
            await self.process(folder_id=folder_id)
            return True

    async def process(self, *args, **kwargs) -> None:

        photo = None
        entities = self.message.entities
        if self.message.photo:
            photo = self.message.photo[-1].file_id
            entities = self.message.caption_entities

        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        disable_preview = False

        if self.message.link_preview_options:
            if self.message.link_preview_options.is_disabled is True:
                disable_preview = True

        await self.db.execute("""
            INSERT INTO note_table 
            (user_pid, title, text, type, parent_id, file_id, media_group_id, disable_preview)
            VALUES
            ($1, $2, $3, 'note', $4, $5, $6, $7);
        """, self.db_user['id'], self.text[:17] + '...', entities_to_html(self.text, entities), kwargs['folder_id'],
                              photo, self.message.media_group_id, disable_preview)

        if self.message.media_group_id:
            # noinspection PyAsyncCall
            asyncio.create_task(unit_media(self.message.media_group_id, self, kwargs["folder_id"]))
        else:
            message_obj = await self.generate_send_message(stage=1, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )
            message_obj2 = await CreateFolder.generate_send_message(self, stage=2, folder_id=kwargs['folder_id'])
            await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if not kwargs.get("folder_id"):
            rres1 = re.fullmatch(r'folder/([0-9]+)/create_note/', self.cdata)
            kwargs["folder_id"] = int(rres1.group(1))
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['CreateNote']).substitute()

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM note_table
                WHERE id = $1;
            """, kwargs['folder_id'])

            child_notes = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE parent_id = $1
                    AND id <> parent_id
                    AND type = 'note'
                ORDER BY title ASC;
            """, kwargs['folder_id'])

            child_folders = await self.db.fetch("""
                SELECT * FROM note_table
                WHERE parent_id = $1
                    AND id <> parent_id
                    AND type = 'folder'
                ORDER BY title ASC;
            """, kwargs['folder_id'])

            notes = ''

            if not res['expand']:
                for i in child_notes:
                    text = i['text']
                    notes += f'<blockquote expandable>{text}</blockquote>'
                    notes += '\n'

            text = Template(self.call_edit_texts['Folder']).substitute(
                folder_title=res['title'],
                notes=notes
            )

            variable = []

            if res['id'] == res['parent_id']:
                if res['id'] == 0:
                    variable.append('back_to_menu')
                else:
                    variable.append('back_to_tag')
            else:
                variable.append('to_menu')
                variable.append('back_to_parent_folder')

            if not child_notes and not child_folders and res['id'] != 0:
                variable.append('delete')

            message_obj_1 = TextMessage(
                chat_id=self.chat.id,
                text=Template(self.call_send_texts['FolderTopMessage']).substitute(title=res['title']),
                markup=markup_generate(
                    buttons=self.buttons['FolderTopMessage'],
                    folder_id=res['id']
                )
            )
            sent_message = await self.bot.send_text(message_obj_1)
            await self.db.execute("""
                INSERT INTO message_table
                (user_pid, message_id, text, type, is_bot_message)
                VALUES ($1, $2, $3, $4, TRUE);
            """,
                                  self.db_user['id'],
                                  sent_message.message_id,
                                  sent_message.text,
                                  'settings_folder'
                                  )

            if res['expand'] is True:
                variable.append('collapse')
                for i in child_notes:
                    message_obj = TextMessage(
                        chat_id=self.chat.id,
                        text=i['text'],
                        photo=i['file_id'],
                        disable_web_page_preview=i["disable_preview"]
                    )
                    file_rows = await self.db.fetch("""
                        SELECT * FROM note_files_table
                        WHERE note_pid = $1;
                    """, i["id"])
                    if file_rows:
                        message_obj.photo = [message_obj.photo] + [i["file_id"] for i in file_rows]
                        sent_message = await self.bot.send_text(message_obj)
                    else:
                        sent_message = [await self.bot.send_text(message_obj)]

                    if i['add_info']:
                        await self.bot.set_emoji(
                            chat_id=sent_message[0].chat.id,
                            message_id=sent_message[0].message_id,
                            emoji=self.global_texts['reactions']['HiddenInfo']
                        )
                    for ii in sent_message:
                        await self.db.execute("""
                            INSERT INTO message_table
                            (user_pid, message_id, text, type, is_bot_message, addition)
                            VALUES ($1, $2, $3, $4, TRUE, $5);
                        """,
                                              self.db_user['id'],
                                              ii.message_id,
                                              ii.text,
                                              'note',
                                              str(i['id'])
                                              )
            else:
                variable.append('expand')

            cycle_folder = [{
                'child_title': i['title'],
                'child_id': i['id']
            } for i in child_folders]

            markup = markup_generate(
                buttons=self.buttons['Folder'],
                folder_id=kwargs['folder_id'],
                cycle_folder=cycle_folder,
                parent_folder_id=res['parent_id'],
                variable=variable,
                tag=res['tag']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


async def unit_media(media_group_id: str, create_note_instance: CreateNote, folder_id: int):
    from utils import db
    await asyncio.sleep(1)
    rows = await db.fetch("""
        SELECT * FROM note_table
        WHERE media_group_id = $1;
    """, media_group_id)
    if rows and len(rows) > 1:
        note_row = rows[0]
        for row in rows[1:]:
            await db.execute("""
                DELETE FROM note_table WHERE id = $1;
            """, row["id"])
            await db.execute("""
                INSERT INTO note_files_table
                (note_pid, file_id)
            """, note_row["id"], row["file_id"])
    try:
        await create_note_instance.bot.delete_message(
            chat_id=create_note_instance.chat.id,
            message_id=create_note_instance.press_message_id
        )

        message_obj = await create_note_instance.generate_send_message(stage=1, folder_id=folder_id)
        await create_note_instance.bot.send_text(message_obj)
        message_obj2 = await CreateFolder.generate_send_message(create_note_instance, stage=2, folder_id=folder_id)
        await create_note_instance.bot.send_text(message_obj2)
    except:
        pass


class NoteChangeTitle(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'note/([0-9]+)/change_title/', self.cdata)
        if rres1:
            note_id = int(rres1.group(1))
            await self.process(note_id=note_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['note_id'])

        await self.db.execute("""
            UPDATE note_table
            SET title = $1
            WHERE id = $2;
        """, self.text, kwargs['note_id'])

        message_obj = await self.generate_send_message(stage=1, res=res, **kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.press_message_id
        )

        message_obj2 = await self.generate_send_message(stage=2, res=res, folder_id=res['parent_id'], **kwargs)
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['NoteChangeTitle']).substitute(
                old_title=kwargs['res']['title'],
                new_title=self.text
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM note_table
                WHERE id = $1;
            """, kwargs['note_id'])

            text = Template(self.global_texts['callback_command']['edit']['Note']).substitute(
                title=res['title'],
                text=res['text']
            )

            markup = markup_generate(
                buttons=self.buttons['Note'],
                note_id=res['id'],
                folder_id=res['parent_id']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


class NoteChangeText(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'note/([0-9]+)/change_text/', self.cdata)
        if rres1:
            note_id = int(rres1.group(1))
            await self.process(note_id=note_id)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        res = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, kwargs['note_id'])

        await self.db.execute("""
            UPDATE note_table
            SET text = $1
            WHERE id = $2;
        """, self.text, kwargs['note_id'])

        message_obj = await self.generate_send_message(stage=1, res=res, **kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.press_message_id
        )

        message_obj2 = await self.generate_send_message(stage=2, res=res, folder_id=res['parent_id'], **kwargs)
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['NoteChangeText']).substitute(
                title=kwargs['res']['title']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM note_table
                WHERE id = $1;
            """, kwargs['note_id'])

            text = Template(self.global_texts['callback_command']['edit']['Note']).substitute(
                title=res['title'],
                text=res['text']
            )

            markup = markup_generate(
                buttons=self.buttons['Note'],
                note_id=res['id'],
                folder_id=res['parent_id']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:

        return TextMessage(
            chat_id=self.chat.id,
            text='Что-то не так'
        )


class AdminChangeCommand(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/change_command/([^/]+)/', self.cdata)
        if rres:
            command = rres.group(1)
            await self.process(command=command)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        with open('locales.json', 'r') as read_file:
            data = json.load(read_file)

        before = data['ru']['keywords'][kwargs['command']]

        data['ru']['keywords'][kwargs['command']] = self.text_low.replace('*', '\*')

        with open('locales.json', 'w') as write_file:
            json.dump(data, write_file, ensure_ascii=False)

        message_obj = await self.generate_send_message(stage=1, before=before)
        await self.bot.delete_message(self.chat.id, self.press_message_id)
        await self.bot.send_text(message_obj)

        message_obj2 = await self.generate_send_message(stage=2, before=before)
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            text = Template(self.send_texts['AdminChangeCommand']).substitute(
                before=kwargs['before'].replace('\\', ''),
                after=self.text_low
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            instruction = {
                "AdminInstructionAdminPrivate": "",
                "AdminInstructionAdminChat": "",
                "AdminInstructionEmployeePrivate": "",
                "AdminInstructionEmployeeChat": ""
            }

            for key in list(instruction.keys()):
                instruction[key] = Template(self.call_edit_texts[key]).substitute(
                    **self.global_texts['keywords']
                )
            text = Template(self.call_edit_texts['AdminInstruction']).substitute(
                **instruction
            )

            markup = markup_generate(
                self.buttons['AdminCommands']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )


class AdminRevise(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/revise/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            UPDATE pressure_button_table
            SET callback_data = 'admin/revise/second/'
            WHERE id = $1;
        """, self.pressure_info['id'])

        revise_expr = self.text_low
        revise_expr = revise_expr.replace('\n', '+')
        revise_expr = revise_expr.replace('+-', '-').replace('++', '+').replace('+/', '/').replace('+*', '*').replace(
            '+%', '%')

        await self.db.execute("""
            UPDATE user_table
            SET revise_expr = $1
            WHERE id = $2;
        """, revise_expr, self.db_user['id'])

        message_obj = await self.generate_send_message()
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(self.chat.id, self.press_message_id)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.send_texts['AdminRevise']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
        )


class AdminReviseSecond(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'admin/revise/second/', self.cdata)
        if rres:
            await self.process()
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        await self.db.execute("""
            UPDATE user_table
            SET revise_expr = NULL
            WHERE id = $1;
        """, self.db_user['id'])

        message_obj = await self.generate_send_message(stage=1)
        await self.bot.send_text(message_obj)

        message_obj2 = await self.generate_send_message(stage=2)
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        if kwargs['stage'] == 1:
            def find_mistakes(expr1, expr2) -> str:
                expr1 = expr1.replace(' ', '')
                expr2 = expr2.replace(' ', '')

                split1 = [{'el': i, 'correct': True, 'type': 'sign' if i in '*+%/()-' else 'digital'}
                          for i in re.findall(r'[0-9,.]+|[*+%/()-]', expr1)]
                split2 = [{'el': i, 'correct': True, 'type': 'sign' if i in '*+%/()-' else 'digital'}
                          for i in re.findall(r'[0-9,.]+|[*+%/()-]', expr2)]

                removed1 = []
                removed2 = []

                ind = 0
                while ind != (len(split1) - 1):
                    if split1[ind]['type'] == 'sign':
                        removed1.append([split1[ind], ind])
                        del split1[ind]
                    else:
                        ind += 1

                ind = 0
                while ind != (len(split2) - 1):
                    if split2[ind]['type'] == 'sign':
                        removed2.append([split2[ind], ind])
                        del split2[ind]
                    else:
                        ind += 1

                ind = 0

                while ind != (len(split1) - 1):
                    # Проверка элементов на неравенство из списка 2
                    if split1[ind] != split2[ind]:
                        next_correct = False
                        # Проверка есть ли элементы после этого в списке 2
                        if len(split2) > (ind + 1):
                            if split1[ind] == split2[ind + 1]:
                                next_correct = True

                        if next_correct is True:
                            split2[ind]['correct'] = False
                            removed2.append([split2[ind], ind])
                            del split2[ind]
                            ind -= 1
                        else:
                            v = False
                            if ind < (len(split1) - 2) and ind < (len(split2) - 2):
                                if split1[ind + 1] == split2[ind + 1]:
                                    split1[ind]['correct'] = False
                                    split2[ind]['correct'] = False
                                else:
                                    v = True
                            else:
                                v = True

                            if v is True:
                                split1[ind]['correct'] = False
                                removed1.append([split1[ind], ind])
                                del split1[ind]
                                ind -= 1
                    ind += 1

                final_str1 = ''
                final_str2 = ''

                for i in reversed(removed1):
                    split1.insert(i[1], i[0])

                for i in reversed(removed2):
                    split2.insert(i[1], i[0])

                for i in split1:
                    if i['correct'] is False:
                        final_str1 += '<b><u>'
                    final_str1 += i['el']
                    if i['correct'] is False:
                        final_str1 += '</u></b>'
                for i in split2:
                    if i['correct'] is False:
                        final_str2 += '<b><u>'
                    final_str2 += i['el']
                    if i['correct'] is False:
                        final_str2 += '</u></b>'

                final_str1 = f'<blockquote>{final_str1}</blockquote>'
                final_str2 = f'<blockquote>{final_str2}</blockquote>'

                return '\n'.join((final_str1, final_str2))

            res1 = '❌'

            res2 = '❌'

            expr_1 = self.db_user['revise_expr'].replace(' ', '').replace(',', '.')
            expr_1 = expr_1.replace('\n', '+')
            expr_1 = expr_1.replace('+-', '-').replace('++', '+').replace('+/', '/').replace('+*', '*').replace('+%',
                                                                                                                '%')
            expr_2 = self.text_low.replace(' ', '').replace(',', '.')
            expr_2 = expr_2.replace('\n', '+')
            expr_2 = expr_2.replace('+-', '-').replace('++', '+').replace('+/', '/').replace('+*', '*').replace('+%',
                                                                                                                '%')

            try:
                res1 = float_to_str(eval(expr_1))
            except:
                pass

            try:
                res2 = float_to_str(eval(expr_2))
            except:
                pass

            if res1 == res2:
                sign = '='
            else:
                sign = '≠'

            text = f'<b>{res1} {sign} {res2}</b>\n\n' + find_mistakes(expr_1, expr_2)

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
            )
        else:
            text = Template(self.global_texts['message_command']['MenuCommand']).substitute()

            markup = markup_generate(
                buttons=self.buttons['MenuCommand']
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )


class Null(NextCallbackMessageCommand):
    async def define(self):
        pass

    async def process(self, *args, **kwargs) -> None:
        pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass
