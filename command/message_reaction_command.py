from command.command_interface import MessageReactionCommand


class CancelReaction(MessageReactionCommand):
    async def define(self):
        if self.emoji == '👎':
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
                AND chat_table.type = 'chat';
        """, self.chat.id)

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
