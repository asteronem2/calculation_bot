import re
from string import Template

import BotInteraction
from BotInteraction import EditMessage, TextMessage
from command.command_interface import NextCallbackMessageCommand
from utils import calculate, float_to_str, str_to_float


class CurrChangeTitleCommand(NextCallbackMessageCommand):
    async def define(self):
        rres = re.fullmatch(r'curr/change_title/([0-9]+)/', self.cdata)
        if rres:
            if self.text_low.count(' ') == 0:
                curr_id = int(rres.group(1))
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
                WHERE chat_pid = $1;
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

            message_obj = await self.generate_send_message(title1=res['title'], title2=self.text_low)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.send_texts['CurrChangeTitleCommand']).substitute(
            title1=kwargs['title1'].upper(),
            title2=kwargs['title2'].upper()
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
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

            await self.db.add_story(
                curr_id=kwargs['curr_id'],
                user_id=self.db_user['id'],
                expr_type='update',
                before_value=res['value'],
                after_value=new_value,
                message_id=self.message.message_id,
                expression=self.text_low
            )

            await self.db.execute("""
                UPDATE currency_table
                SET value = $1
                WHERE id = $2;
            """, new_value, kwargs['curr_id'])

            await self.db.execute("""
                DELETE FROM pressure_button_table
                WHERE id = $1;
            """, self.pressure_info['id'])

            message_obj = await self.generate_send_message(title=res['title'], value=new_value)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['send']['CurrChangeValueCommand']).substitute(
            title=kwargs['title'],
            value=float_to_str(kwargs['value'])
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
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

            message_obj = await self.generate_send_message(title=res['title'], postfix=new_postfix)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.texts['send']['CurrChangePostfixCommand']).substitute(
            title=kwargs['title'],
            postfix=kwargs['postfix']
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
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

            await self.db.add_story(
                curr_id=kwargs['curr_id'],
                user_id=self.db_user['id'],
                expr_type='add',
                before_value=before_value,
                after_value=after_value,
                message_id=self.message.message_id,
                expression=self.text_low
            )

            message_obj = await self.generate_send_message(res=res, after_value=after_value, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
            title=kwargs['res']['title'].upper(),
            value=float_to_str(kwargs['after_value']),
            postfix=kwargs['res']['title']
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            message_thread_id=self.topic
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
        rres1 = re.fullmatch(r'admin/chat/([^/]+)/change_code_name/', self.cdata)
        if rres1:
            if self.text_low.count(' '):
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
            new_code_name = self.text_low
            await self.db.execute("""
                UPDATE chat_table
                SET code_name = $1
                WHERE id = $2;
            """, new_code_name, kwargs['chat_pk'])

            message_obj = await self.generate_send_message(new_code_name=new_code_name, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
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

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['CodeNameCantWithSpace']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminChatSetTag(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/chat/([^/]+)/set_tag/', self.cdata)
        if rres1:
            if self.text_low.count(' '):
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
            tag = self.text_low
            await self.db.execute("""
                UPDATE chat_table
                SET tag = $1
                WHERE id = $2;
            """, tag, kwargs['chat_pk'])

            message_obj = await self.generate_send_message(**kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
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

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['TagCantWithSpace']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminChatChangeTag(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/chat/([^/]+)/change_tag/', self.cdata)
        if rres1:
            if self.text_low.count(' '):
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
            tag = self.text_low if self.text_low != '*' else None
            await self.db.execute("""
                UPDATE chat_table
                SET tag = $1
                WHERE id = $2;
            """, tag, kwargs['chat_pk'])

            message_obj = await self.generate_send_message(tag=tag, **kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
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

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_error_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.global_texts['error']['TagCantWithSpace']).substitute()

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminEmployeesAdd(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/employees/add/', self.cdata)
        if rres1:
            rres2 = re.findall(r'[^,./| ]+', self.text.replace('@', ''))
            if rres2:
                await self.process(username_list=rres2)
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
                        SET access_level = 'employee'
                        WHERE username = $1
                            AND access_level <> 'admin';
                    """, i)

            message_obj = await self.generate_send_message(**kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.send_texts['AdminEmployeesAdd']).substitute()

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


class AdminEmployeesRemove(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/employees/remove/', self.cdata)
        if rres1:
            rres2 = re.findall(r'[^,./| ]+', self.text.replace('@', ''))
            if rres2:
                await self.process(username_list=rres2)
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
                            AND access_level <> 'admin';
                    """, i)

            message_obj = await self.generate_send_message(**kwargs)
            await self.bot.send_text(message_obj)
            await self.bot.delete_message(
                chat_id=self.chat.id,
                message_id=self.press_message_id
            )

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
        rres1 = re.fullmatch(r'admin/distribution/pin/([^/]+)/', self.cdata)
        if rres1:
            tag = rres1.group(1)
            await self.process(tag=tag)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        res = await self.db.fetch("""
            SELECT * FROM chat_table
            WHERE type = 'chat' 
                AND super = FALSE
                AND COALESCE(tag, '1') = COALESCE($1, '1');
        """, kwargs['tag'] if kwargs['tag'] != 'to_all' else None)

        for i in res:
            message_obj = TextMessage(chat_id=i['chat_id'], text=self.message.text, pin=True)
            await self.bot.send_text(message_obj)

        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.press_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.send_texts['AdminDistributionPin']).substitute()

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


class AdminDistributionUnpin(NextCallbackMessageCommand):
    async def define(self):
        rres1 = re.fullmatch(r'admin/distribution/unpin/([^/]+)/', self.cdata)
        if rres1:
            tag = rres1.group(1)
            await self.process(tag=tag)
            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM pressure_button_table
            WHERE id = $1;
        """, self.pressure_info['id'])

        res = await self.db.fetch("""
            SELECT * FROM chat_table
            WHERE type = 'chat' 
                AND super = FALSE
                AND COALESCE(tag, '1') = COALESCE($1, '1');
        """, kwargs['tag'] if kwargs['tag'] != 'to_all' else None)

        for i in res:
            message_obj = TextMessage(chat_id=i['chat_id'], text=self.message.text, pin=False)
            await self.bot.send_text(message_obj)

        message_obj = await self.generate_send_message(**kwargs)
        await self.bot.send_text(message_obj)
        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.press_message_id
        )

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        text = Template(self.send_texts['AdminDistributionUnpin']).substitute()

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


class Null(NextCallbackMessageCommand):
    async def define(self):
        pass

    async def process(self, *args, **kwargs) -> None:
        pass

    async def generate_send_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass

    async def generate_edit_message(self, *args, **kwargs) -> BotInteraction.Message:
        pass
