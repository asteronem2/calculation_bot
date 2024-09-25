import json
from cmath import phase
from string import Template

from BotInteraction import TextMessage
from command.command_interface import MessageReactionCommand
from command.message_command import CurrencyCalculationCommand, CalculationCommand
from utils import markup_generate, calculate


class CancelReaction(MessageReactionCommand):
    async def define(self):
        if self.chat.type == 'supergroup':
            if self.db_user['access_level'] in ['admin', 'employee']:
                if self.emoji == self.reactions_text['CancelReaction']:
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

                await self.bot.delete_message(
                    chat_id=self.chat.id,
                    message_id=self.message_id
                )


class DeleteNote(MessageReactionCommand):
    async def define(self):
        if self.db_user['access_level'] == 'admin':
            if self.emoji == self.reactions_text['DeleteNote']:
                res = await self.db.fetchrow("""
                    SELECT * FROM message_table
                    WHERE type = 'note' AND message_id = $1;
                """, self.message_id)
                if res:
                    await self.process(res=res)
                    return True

    async def process(self, *args, **kwargs) -> None:
        await self.db.execute("""
            DELETE FROM note_table
            WHERE id = $1;
        """, int(kwargs['res']['addition']))

        await self.bot.delete_message(
            chat_id=self.chat.id,
            message_id=self.message_id
        )


class ReplyReaction(MessageReactionCommand):
    async def define(self):
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

            sent = await self.bot.bot.forward_message(self.chat.id, self.chat.id, self.message_id)

            await self.bot.delete_message(self.chat.id, sent.message_id)

            text = sent.text if sent.text else (sent.caption if sent.caption else 'ошибка')
            photo = sent.photo[-1].file_id if sent.photo else None

            text = '\n'.join(text.split('\n', 1)[:-1])

            if not text:
                text = sent.text if sent.text else (sent.caption if sent.caption else 'ошибка')

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


class AdminChangeEmoji(MessageReactionCommand):
    async def define(self):
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
            text = Template(self.global_texts['callback_command']['edit']['AdminEmojiSettings']).substitute()

            cycle = []

            command_texts = {
                'CancelReaction': 'Отмена операции',
                'DeleteNote': 'Удаление заметки',
                'ReplyReaction': 'Пересыл сообщений',
                'ReplyReaction2': 'Реакция бота на пересыл'
            }

            for key, value in self.global_texts['reactions'].items():
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
