from BotInteraction import TextMessage
from command.command_interface import MessageReactionCommand


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


class ReplyReaction1(MessageReactionCommand):
    async def define(self):
        if self.chat.type == 'supergroup':
            if self.db_user['access_level'] in ['admin', 'employee']:
                if self.emoji == self.reactions_text['ReplyReaction']:
                    res = await self.db.fetchrow("""
                        SELECT * FROM chat_table
                        WHERE id = $1;
                    """, self.db_chat['id'])

                    if res['bind_chat']:
                        res2 = await self.db.fetchrow("""
                            SELECT * FROM message_table
                            WHERE message_id = $1
                                AND type = 'reply2';
                        """, self.message_id)
                        if res2:
                            # noinspection PyTypeChecker
                            await self.process(stage=2, res=res, res2=res2)
                            return True
                        else:
                            await self.process(stage=1, res=res)
                            return True

    async def process(self, *args, **kwargs) -> None:
        if kwargs['stage'] == 1:
            res = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, kwargs['res']['bind_chat'])

            sent_message = await self.bot.bot.copy_message(res['chat_id'], self.chat.id, self.message_id)
            await self.bot.set_emoji(self.chat.id, self.message_id, self.reactions_text['ReplyReaction'])
            await self.db.execute("""
                INSERT INTO message_table
                (user_pid, chat_pid, message_id, type, addition)
                VALUES ($1, $2, $3, $4, $5);
            """, self.db_user['id'], self.db_chat['id'], sent_message.message_id, 'reply1', str(self.message_id))
        else:
            res = await self.db.fetchrow("""
                SELECT * FROM chat_table
                WHERE id = $1;
            """, kwargs['res']['bind_chat'])

            res2 = await self.db.fetchrow("""
                SELECT * FROM message_table
                WHERE id = $1;
            """, int(kwargs['res2']['addition']))

            await self.bot.bot.copy_message(
                res['chat_id'],
                self.chat.id,
                self.message_id,
                reply_to_message_id=int(res2['addition'])
            )

            await self.db.execute("""
                DELETE FROM message_table
                WHERE id = $1
                    OR addition = $2;
            """, int(kwargs['res2']['addition']), kwargs['res2']['addition'])