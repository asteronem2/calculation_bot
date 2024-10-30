import re
import time
import traceback
import datetime

from aiogram.types import InlineQueryResultArticle, InputTextMessageContent

from command.command_interface import InlineQueryCommand
from utils import float_to_str


def mega_eval(expression: str):
    try:
        try:
            return {
                'result': float_to_str(float(expression)),
                'expression': expression,
                'expression_and_percents': expression
            }
        except:
            pass

        def bracket_calc(expr: str) -> tuple:
            bracket_nested_2 = []
            bracket_nested_1 = []

            while True:
                search = re.search(r'(\([^(]*\([^(]*)(\(.*?\))([^)]*\)[^)]*\))', expr)
                if not search:
                    break

                eval_res = str(eval(search.group(2)))
                expr = expr[:search.start()] + search.group(1) + eval_res + search.group(3) + expr[search.end():]
                bracket_nested_2.append([
                    search.group(2),
                    eval_res
                ])

            while True:
                search = re.search(r'(\([^(]*)(\(.+?\))([^)]*\))', expr)
                if not search:
                    break

                eval_res = str(eval(search.group(2)))
                expr = expr[:search.start()] + search.group(1) + eval_res + search.group(3) + expr[search.end():]
                bracket_nested_1.append([
                    search.group(2),
                    eval_res
                ])

            reply = ['', expr]

            if bracket_nested_2:
                reply[0] += '<blockquote>' + ' | '.join([f'{i[0]} = {i[1]}' for i in bracket_nested_2]) + '</blockquote>\n'

            if bracket_nested_1:
                reply[0] += '<blockquote>' + ' | '.join([f'{i[0]} = {i[1]}' for i in bracket_nested_1]) + '</blockquote>\n'

            bracket_list = [[i.strip(), None] for i in re.findall(r'(\([^)]*\))', expr)]

            for i in bracket_list:
                res = f'{eval(i[0])}'
                i[1] = res

                reply[1] = reply[1].replace(i[0], i[1], 1)

            reply[0] += '<blockquote>' +  ' | '.join([f'{i[0]} = {i[1]}' for i in bracket_list]) + '</blockquote>'

            return tuple(reply)

        def mul_div_calc(expr: str) -> tuple:
            reply = [None, expr]

            pattern1 = r'([0-9.%]+[*/0-9.%]+[*/%][0-9.%]+)'
            split_expr = [[i, None, None, None] for i in re.findall(pattern1, expr) if not i.count('%')]

            for i in split_expr:
                pattern2 = r'[^*/][0-9.]+|[*/][0-9.]+|[0-9.]+'
                i[1] = re.findall(pattern2, i[0])
            for i in split_expr:
                var_value = None
                iter_amt = -1
                for a in i[1]:
                    iter_amt += 1
                    if iter_amt == 0:
                        i[2] = a
                        var_value = a
                    else:
                        i[2] += a
                        var_value = f'{eval(var_value + a)}'
                        if len(i[1]) == (iter_amt + 1):
                            i[2] += f'= {var_value}'
                            i[3] = var_value
                        else:
                            i[2] += f'( = {var_value} )'

                reply[1] = reply[1].replace(i[0], i[3], 1)
            reply[0] = ' | '.join([i[2] for i in split_expr])

            return tuple(reply)

        def plus_minus_calc(expr: str) -> tuple:
            reply = [None, expr]

            var_list = []

            pattern1 = r'[^*+/-][0-9.]+|[*+/-][0-9%.]+'

            split_expr = re.findall(pattern1, expr)

            var_value = None
            item_amt = -1

            for i in split_expr:
                item_amt += 1
                if item_amt == 0:
                    var_list.append(i)
                    var_value = i
                else:
                    var_list.append(i)

                    if '%' in i:
                        znak = re.search(r'([*/+-])', i).group(1)
                        i = i.replace(znak, '')
                        var_value = var_value.replace(znak, '')
                        calc = str(abs(float(var_value) * 0.01 * float(i.replace("%", ""))))
                        var_value = f'{eval(var_value + znak + str(float(var_value) * 0.01 * float(i.replace("%", ""))))}'
                        if len(split_expr) == (item_amt + 1):
                            var_list.append(f'(<i>{calc}</i>) = {var_value}')
                        else:
                            var_list.append(f'(<i>{calc}</i>)')
                    else:
                        var_value = f'{eval(var_value + i)}'
                        if len(split_expr) == (item_amt + 1):
                            var_list.append(f'={var_value}')
                        else:
                            var_list.append(f'(={var_value})')

            reply[1] = var_value

            reply[0] = ''.join(var_list)

            return tuple(reply)

        pure_expression = expression

        expression = expression.replace(',', '.').replace(' ', '')

        solution_list = []

        if expression.count('(') != expression.count(')'):
            return {'result': False}

        if re.fullmatch(r'[^0-9-+/*%.)(]', expression):
            return {'result': False}

        if expression.count('('):
            res = bracket_calc(expression)
            expression = res[1]
            solution_list.append(res[0])
            print(expression)
            print(solution_list[-1])

        if expression.count('/') or expression.count('*'):
            res = mul_div_calc(expression)
            expression = res[1]
            solution_list.append(f'<blockquote>{res[0]}</blockquote>')
            print(expression)
            print(solution_list[-1])

        if expression.count('-') or expression.count('+') or expression.count('%'):
            expression = expression.replace('--', '+').replace('++', '+').replace('+-', '-').replace('-+', '-')
            expression = expression.replace('--', '+').replace('++', '+').replace('+-', '-').replace('-+', '-')
            res = plus_minus_calc(expression)
            expression = res[1]
            solution_list.append(f'<blockquote>{res[0]}</blockquote>')
            print(expression)
            print(solution_list[-1])

        for i in range(len(solution_list)):
            solution_list[i] = re.sub(
                pattern=r'[0-9.]+',
                repl=lambda x: float_to_str(float(x.group())),
                string=solution_list[i]
            )

            solution_list[i] = re.sub(
                pattern=r'(?=[^ ])([*+%/=-])(?=[^ ib])',
                repl=lambda match: f" {match.group()} ",
                string=solution_list[i]
            )

            solution_list[i] = re.sub(
                pattern=r'\((?=[^ <])',
                repl=lambda match: f"{match.group()} ",
                string=solution_list[i]
            )

            solution_list[i] = re.sub(
                pattern=r'(?=[^ ])[)(]',
                repl=lambda match: f" {match.group()}",
                string=solution_list[i]
            )

            solution_list[i] = re.sub(
                pattern=r'> ',
                repl=lambda match: f"{match.group()[0]}",
                string=solution_list[i]
            )

        def bold(expr):
            return f'<>b/{expr.group()}>b<'

        solution_list[-1] = solution_list[-1][::-1]
        solution_list[-1] = re.sub(r'<[0-9 ,]+', bold, solution_list[-1], 1)
        solution_list[-1] = solution_list[-1][::-1]

        solution = '\n'.join(solution_list)
        solution = re.sub(r' *= *', ' = ', solution)

        expression_and_percents = pure_expression.replace(' ', '')

        find_percents = re.findall(r'[^|](([0-9, ]+%)[(0-9, </i>]+\))', solution)

        for i in find_percents:
            i = list(i)
            i[1] = i[1].replace(' ', '')
            expression_and_percents = expression_and_percents.replace(i[1], f'|{i[0]}', 1)

        expression_and_percents = (expression_and_percents.replace('|', '').replace(' ', '').
                                   replace('<i>', '').replace('</i>', ''))

        return {'solution': solution, 'expression_and_percents': expression_and_percents,
                'result': float_to_str(float(expression))}

    except:
        return {'result': False}


class InlineCalculation(InlineQueryCommand):
    async def define(self):
        await self.process()
        return True

    async def process(self, *args, **kwargs):
        if self.query:
            db_res = await self.db.fetchrow("""
                SELECT * FROM inline_query
                WHERE user_id = $1
                ORDER BY id DESC
            """, self.inline.from_user.id)

            if db_res:
                now_timestamp = datetime.datetime.utcnow().timestamp()
                res_timestamp = db_res['datetime'].timestamp()

                if now_timestamp-res_timestamp > 60:
                    await self.db.execute("""
                        INSERT INTO inline_query 
                        (user_id, query, username, datetime)
                        VALUES ($1, $2, $3, $4);
                    """, self.inline.from_user.id, self.query, self.inline.from_user.username, datetime.datetime.utcnow())
            else:
                await self.db.execute("""
                    INSERT INTO inline_query 
                    (user_id, query, username, datetime)
                    VALUES ($1, $2, $3, $4);
                """, self.inline.from_user.id, self.query, self.inline.from_user.username, datetime.datetime.utcnow())

        try:
            results = await self.generate_results()
            await self.bot.answer_inline_query(results=results, query_id=self.inline.id)
        except:
            pass

    async def generate_results(self, *args, **kwargs) -> [InlineQueryResultArticle]:
        result = mega_eval(self.query)
        if result['result'] is False:
            return [InlineQueryResultArticle(id=self.inline.id, title='Результат: 0', description=self.query,
                                             input_message_content=
                                             InputTextMessageContent(message_text='0', parse_mode='html'))]
        else:
            return [InlineQueryResultArticle(id=self.inline.id,
                                             title=f'Результат: {result["result"]}',
                                             description=result['expression_and_percents'],
                                             input_message_content=InputTextMessageContent(
                                                 message_text=f'{self.query} = <code>{result["result"]}</code>\n'
                                                              f'- - - - - - - - - - - - - - - - - - - -\n'
                                                              f'<u>Этапы вычисления:</u>\n'
                                                              f'{result["solution"]}',
                                                 parse_mode='html'
                                             ))]
