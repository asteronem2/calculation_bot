import json
import re
from cmath import phase
from pdb import post_mortem
from pyexpat.errors import messages
from string import Template

from dotenv.main import DotEnv

import utils
from BotInteraction import TextMessage, Message, EditMessage
from command.command_interface import MessageReactionCommand
from command.message_command import CurrencyCalculationCommand, CalculationCommand
from utils import markup_generate, calculate, float_to_str, story_generate, detail_generate


class Cancel(MessageReactionCommand):
    async def define(self):
        if self.new:
            if self.chat.type == 'supergroup':
                if self.db_user['access_level'] in ['admin', 'employee']:
                    if self.emoji == self.reactions_text['Cancel']:
                        await self.process()
                        return True

    async def process(self, *args, **kwargs) -> None:
        res = await self.db.fetch("""
            SELECT 
                story_table.expr_type AS story__expr_type,
                story_table.before_value AS story__before_value,
                story_table.after_value AS story__after_value,
                story_table.expression AS story__expression,
                story_table.message_id AS story__message_id,
                story_table.id AS story__id,
                currency_table.title AS currency__title,
                currency_table.postfix AS currency__postfix,
                currency_table.value AS currency__value,
                currency_table.id AS currency__id

            FROM story_table
            JOIN currency_table ON story_table.currency_pid = currency_table.id
            JOIN chat_table ON currency_table.chat_pid = chat_table.id 
            WHERE chat_table.chat_id = $1
                AND story_table.status = TRUE
                AND chat_table.type = 'chat'
                AND story_table.message_id = $2;
        """, self.chat.id, self.message_id)

        if len(res) == 0:
            return
        else:
            last_res = res[-1]
            if last_res['story__expr_type'] == 'create':
                return
            else:
                new_value = last_res['currency__value'] - (last_res['story__after_value'] - last_res['story__before_value'])
                await self.db.execute("""
                    UPDATE currency_table
                    SET value = $1
                    WHERE title = $2
                    AND chat_pid = (SELECT id FROM chat_table WHERE type = 'chat' AND chat_id = $3);
                """, new_value, last_res['currency__title'], self.chat.id)

                await self.db.execute("""
                    UPDATE story_table
                    SET status = FALSE
                    WHERE id = $1 AND status = TRUE;
                """, last_res['story__id'])

                expr_link = 'https://t.me/c/{chat_id}/{msg_id}'.format(
                    chat_id=str(self.chat.id)[4:],
                    msg_id=str(last_res['story__message_id'])
                )

                text = Template(self.global_texts['message_command']['CancelCommand']).substitute(
                    expr_link=expr_link,
                    expression=last_res['story__expression'],
                    title=last_res['currency__title'].upper(),
                    value=float_to_str(new_value),
                    postfix=last_res['currency__postfix'] or ''
                )

                message_obj = TextMessage(
                    chat_id=self.chat.id,
                    text=text,
                )

                await self.bot.send_text(message_obj)


class DeleteNote(MessageReactionCommand):
    async def define(self):
        if self.new:
            if self.db_user['access_level'] == 'admin':
                if self.emoji == self.reactions_text['DeleteNote']:
                    res = await self.db.fetchrow("""
                        SELECT * FROM message_table
                        WHERE type in ('note', 'hidden_note') AND message_id = $1;
                    """, self.message_id)
                    if res:
                        await self.process(res=res)
                        return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['res']['type'] == 'note':
            await self.db.execute("""
                DELETE FROM note_table
                WHERE id = $1;
            """, int(kwargs['res']['addition']))
        else:
            await self.db.execute("""
                UPDATE note_table
                SET add_info = NULL
                WHERE id = $1;
            """, int(kwargs['res']['addition']))

        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.message_id
        )


class ReplyReaction(MessageReactionCommand):
    async def define(self):
        if self.new:
            if self.chat.type == 'supergroup':
                super_chat = await self.db.fetchrow("""
                    SELECT * FROM chat_table
                    WHERE super = TRUE;
                """)
                if super_chat:
                    if self.db_user['access_level'] in ['admin', 'employee']:
                        if self.emoji == self.reactions_text['ReplyReaction']:
                            res = await self.db.fetchrow("""
                                SELECT * FROM chat_table
                                WHERE id = $1;
                            """, self.db_chat['id'])

                            if res['super'] is False:
                                await self.process(stage=1, res=res, super_chat=super_chat)
                                return True
                            else:
                                res2 = await self.db.fetchrow("""
                                    SELECT * FROM message_table
                                    WHERE message_id = $1
                                        AND type = 'reply2';
                                """, self.message_id)
                                if res2:
                                    # noinspection PyTypeChecker
                                    await self.process(stage=2, res=res, res2=res2, super_chat=super_chat)
                                    return True

    async def process(self, *args, **kwargs) -> None:
        super_chat = kwargs['super_chat']
        if kwargs['stage'] == 1:
            sent_message = await self.bot.bot.copy_message(super_chat['chat_id'], self.chat.id, self.message_id)

            await self.db.execute("""
                INSERT INTO message_table
                (user_pid, chat_pid, message_id, type, addition)
                VALUES ($1, $2, $3, $4, $5);
            """, self.db_user['id'], self.db_chat['id'], sent_message.message_id, 'reply1', str(self.message_id))
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM message_table
                WHERE id = $1;
            """, int(kwargs['res2']['addition']))

            res2 = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, int(res['chat_pid']))

            from utils import DED
            sent = await self.bot.bot.forward_message(DED.DEBUG_CHAT_ID, self.chat.id, self.message_id, disable_notification=True)

            await self.bot.delete_message(sent.chat.id, sent.message_id)

            text = sent.text if sent.text else (sent.caption if sent.caption else 'ошибка')
            photo = sent.photo[-1].file_id if sent.photo else None

            text = text.split('\n')[0]

            if text.count('='):
                expr_list = text.split('=')
                if len(expr_list) > 2:
                    message_obj = await self.generate_error_message(error='CalculationIncorrect', expr=text)
                    await self.bot.send_text(message_obj)
                    return
                try:
                    ev1 = eval(expr_list[0].replace(',', '.'))
                except:
                    message_obj = await self.generate_error_message(error='CalculationIncorrect', expr=text)
                    await self.bot.send_text(message_obj)
                    return

                if ev1 != float(expr_list[1].replace(',', '.').replace(' ', '')):
                    if ev1 != float(expr_list[1].replace(',', '').replace('.', '').replace(' ', '')):
                        message_obj = await self.generate_error_message(error='CalculationIncorrect', expr=text)
                        await self.bot.send_text(message_obj)
                        return
                    else:
                        text = expr_list[1].replace(',', '').replace('.', '').replace(' ', '')
                else:
                    text = expr_list[1].replace(',', '.').replace(' ', '')

            # text = '\n'.join(text.split('\n', 1)[:-1])
            #
            # if not text:
            #     text = sent.text if sent.text else (sent.caption if sent.caption else 'ошибка')

            message_obj = TextMessage(
                chat_id=int(res2['chat_id']),
                text=text,
                photo=photo,
                reply_to_message_id=int(res['addition'])
            )

            sent_msg = await self.bot.send_text(message_obj)

            await self.bot.set_emoji(res2['chat_id'], int(res['addition']), self.reactions_text['ReplyReaction2'])

            await self.db.execute("""
                DELETE FROM message_table
                WHERE id = $1
                    OR addition = $2;
            """, int(kwargs['res2']['addition']), kwargs['res2']['addition'])

            class_ = CalculationCommand(sent_msg)
            await class_.async_init()
            await class_.define()

    async def generate_error_message(self, *args, **kwargs):
        text = Template(self.global_texts['error'][kwargs['error']]).substitute(
            expression=kwargs['expr'].replace('=', '≠')
        )

        return TextMessage(
            chat_id=self.chat.id,
            text=text
        )


class AdminChangeEmoji(MessageReactionCommand):
    async def define(self):
        if self.new:
            if self.db_user['access_level'] == 'admin':
                res = await self.db.fetchrow("""
                    SELECT * FROM message_table
                    WHERE message_id = $1 AND type = 'change_emoji';
                """, self.message_id)
                if res:
                    command = res['addition']
                    await self.process(command=command)
                    return True

    async def process(self, *args, **kwargs) -> None:
        with open('locales.json', 'r') as read_file:
            data = json.load(read_file)

        before = data['ru']['reactions'][kwargs['command']]

        data['ru']['reactions'][kwargs['command']] = self.emoji

        with open('locales.json', 'w') as write_file:
            json.dump(data, write_file, ensure_ascii=False)

        await self.bot.delete_message(self.chat.id, self.message_id)

        message_obj = await self.generate_send_message(stage=1, before=before, **kwargs)
        await self.bot.send_text(message_obj)

        message_obj2 = await self.generate_send_message(stage=2, **kwargs)
        await self.bot.send_text(message_obj2)

    async def generate_send_message(self, *args, **kwargs) -> TextMessage:
        if kwargs['stage'] == 1:
            text = Template(self.texts['AdminChangeEmoji']).substitute(
                before=kwargs['before'],
                after=self.emoji
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text
            )
        else:
            gl_text = utils.GetLocales().global_texts

            text = Template(gl_text['callback_command']['edit']['AdminEmojiSettings']).substitute()

            cycle = []

            command_texts = {
                'Cancel': 'Отмена операции',
                'DeleteNote': 'Удаление заметки',
                'ReplyReaction': 'Пересыл сообщений',
                'ReplyReaction2': 'Реакция бота на пересыл',
                'HiddenInfo': 'Скрытая информация заметок',
                'ChangeCalculation': "Изменение калькуляции"
            }

            for key, value in gl_text['reactions'].items():
                cycle.append({
                    'text': command_texts[key],
                    'emoji': value,
                    'command': key
                })

            markup = markup_generate(
                buttons=self.buttons['AdminEmojiSettings'],
                cycle=cycle
            )

            return TextMessage(
                chat_id=self.chat.id,
                text=text,
                markup=markup
            )


class AdminHiddenInfo(MessageReactionCommand):
    async def define(self):
        if self.new:
            if self.emoji == self.reactions_text['HiddenInfo']:
                res1 = await self.db.fetchrow("""
                    SELECT * FROM message_table
                    WHERE message_id = $1
                        AND type = 'note';
                """, self.message_id)
                if res1:
                    await self.process(res1=res1)
                    return True

    async def process(self, *args, **kwargs) -> None:
        res2 = await self.db.fetchrow("""
            SELECT * FROM note_table
            WHERE id = $1;
        """, int(kwargs['res1']['addition']))

        message_obj = await self.generate_send_message(res2=res2, **kwargs)
        sent_message = await self.bot.send_text(message_obj)

        await self.db.execute("""
            INSERT INTO message_table
            (user_pid, message_id, text, type, is_bot_message, addition)
            VALUES ($1, $2, $3, $4, TRUE, $5)
        """, self.db_user['id'], sent_message.message_id, sent_message.text, 'hidden_note', str(res2['id']))

    async def generate_send_message(self, *args, **kwargs) -> TextMessage:
        text = kwargs['res2']['add_info']

        return TextMessage(
            chat_id=self.chat.id,
            text=text,
            reply_to_message_id=self.message_id
        )


class AdminHideHiddenInfo(MessageReactionCommand):
    async def define(self):
        if self.old:
            if self.emoji == self.reactions_text['HiddenInfo']:
                res1 = await self.db.fetchrow("""
                    SELECT * FROM message_table
                    WHERE type = 'note'
                        AND message_id = $1;
                """, self.message_id)

                if res1:
                    res2 = await self.db.fetchrow("""
                        SELECT * FROM note_table
                        WHERE id = $1;
                    """, int(res1['addition']))

                    if res2:
                        res3 = await self.db.fetchrow("""
                            SELECT * FROM message_table
                            WHERE type = 'hidden_note'
                                AND addition = $1;
                        """, str(res2['id']))

                        if res3:
                            await self.process(res3=res3)
                            return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM message_table
            WHERE id = $1;
        """, kwargs['res3']['id'])

        await self.bot.delete_message(self.chat.id, kwargs['res3']['message_id'])


class ChangeCalculation(MessageReactionCommand):
    async def define(self):
        if self.new:
            if self.emoji == self.reactions_text['ChangeCalculation']:
                if self.db_chat:
                    if self.db_user['access_level'] in ('admin', 'employee'):
                        res = await self.db.fetchrow("""
                            SELECT story_table.* FROM story_table
                            JOIN currency_table ON story_table.currency_pid = currency_table.id
                            WHERE message_id = $1 AND currency_table.chat_pid = $2;
                        """, self.message_id, self.db_chat['id'])
                        if res:
                            from utils import DED
                            try:
                                forwarded = await self.bot.bot.forward_message(DED.DEBUG_CHAT_ID, self.chat.id, self.message_id)
                            except:
                                return
                            f_text = forwarded.text or forwarded.caption
                            await self.bot.delete_message(forwarded.chat.id, forwarded.message_id)
                            rres = re.fullmatch(r'[*+%/0-9., ()=-]+', f_text)
                            if rres:
                                expr = rres.group()
                                calc_res = calculate(expr)
                                if calc_res is not False:
                                    await self.process(expr=expr, calc_res=calc_res, res=res)
                                    return True
                            else:
                                rres2 = re.fullmatch(r'(.+) +([*+%/0-9., ()-]+)', f_text.lower())
                                if rres2:
                                    curr, expr = rres2.groups()
                                    calc_res = calculate(expr)
                                    if calc_res is not False:
                                        res2 = await self.db.fetch("""
                                            SELECT currency_table.*
                                            FROM currency_table
                                            JOIN chat_table ON chat_table.id = currency_table.chat_pid
                                            WHERE type = 'chat' AND chat_table.chat_id = $1
                                            ORDER BY currency_table.title ASC; 
                                        """, self.chat.id)

                                        for i in res2:
                                            if curr == i['title']:
                                                await self.process(
                                                    curr=i,
                                                    calc_res=calc_res,
                                                    expr=expr,
                                                    res=res
                                                )
                                                return True

    async def process(self, *args, **kwargs) -> None:
        curr = kwargs.get('curr')
        expr = kwargs['expr']
        res_expr = kwargs['res']['expression']
        if res_expr and len(res_expr) > 1 and res_expr[:2] == '-(' and res_expr[-1] == ')':
            expr = f'-({expr})'

        if not curr:
            curr = await self.db.fetchrow("""
                SELECT * FROM currency_table
                WHERE id = $1;
            """, kwargs['res']['currency_pid'])

        res3 = await self.db.fetch("""
            SELECT * FROM story_table
            WHERE id > $1 AND currency_pid = $2 AND status = TRUE;
        """, kwargs['res']['id'], curr['id'])

        plus = calculate(expr)
        real_plus = plus - (kwargs['res']['after_value'] - kwargs['res']['before_value'])

        await self.db.execute("""
            UPDATE story_table
            SET expression = $1, after_value = $2
            WHERE id = $3; 
        """, expr, kwargs['res']['before_value'] + plus, kwargs['res']['id'])

        f_text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
            title=curr['title'].upper(),
            value=float_to_str(kwargs['res']['after_value'] + real_plus, curr['rounding']),
            postfix=curr['postfix'] or ''
        )
        try:
            await self.bot.edit_text(EditMessage(
                chat_id=self.chat.id,
                text=f_text,
                message_id=kwargs['res']['sent_message_id']
            ))
        except:
            pass

        latest_curr_value = res3[-1]['after_value'] + real_plus

        for i in res3:
            await self.db.execute("""
                UPDATE story_table
                SET before_value = $1, after_value = $2
                WHERE id = $3;
            """, i['before_value'] + real_plus, i['after_value'] + real_plus, i['id'])

            f_text = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
                title=curr['title'].upper(),
                value=float_to_str(i['after_value'] + real_plus, curr['rounding']),
                postfix=curr['postfix'] or ''
            )
            try:
                await self.bot.edit_text(EditMessage(
                    chat_id=self.chat.id,
                    text=f_text,
                    message_id=i['sent_message_id']
                ))
            except:
                continue

        await self.db.execute("""
            UPDATE currency_table
            SET value = $1
            WHERE id = $2;
        """, latest_curr_value, curr['id'])

        res4 = await self.db.fetch("""
            SELECT * FROM message_table
            WHERE chat_pid = $1
                AND message_id > $2
                AND type in ('story', 'detail')
                AND addition = $3;
        """, self.db_chat['id'], self.message_id, str(curr['id']))

        story_list = await self.db.fetch("""
            SELECT * FROM story_table
            WHERE currency_pid = $1
                AND status = TRUE;
        """, curr['id'])

        for i in res4:
            if i['type'] == 'story':
                story = story_generate(story_list, self.chat.id, rounding=curr['rounding'])
                f_text = Template(self.global_texts['message_command']['CurrencyStoryCommand']).substitute(
                    title=curr['title'].upper(),
                    story=story,
                    postfix=((curr['postfix'] or '') if story else '')
                )
            else:
                detail = detail_generate(story_list, self.chat.id)
                f_text = Template(self.global_texts['message_command']['CurrencyDetailCommand']).substitute(
                    title=curr['title'].upper(),
                    detail=detail,
                    postfix=((curr['postfix'] or '') if detail else '')
                )
            await self.bot.edit_text(EditMessage(
                chat_id=self.chat.id,
                text=f_text,
                message_id=i['message_id']
            ))

        text = Template(self.texts['ChangeCalculation']).substitute(
            before_expr=kwargs['res']['expression'],
            after_expr=expr
        )

        await self.bot.send_text(TextMessage(
            chat_id=self.chat.id,
            text=text,
            reply_to_message_id=self.message_id
        ))

        text2 = Template(self.global_texts['message_command']['CurrencyBalance']).substitute(
            title=curr['title'].upper(),
            value=float_to_str(latest_curr_value, curr['rounding']),
            postfix=curr['postfix'] or ''
        )

        await self.bot.send_text(TextMessage(
            chat_id=self.chat.id,
            text=text2
        ))

