import os


class EnvData:
    __slots__ = ['BOT_TOKEN', 'ADMIN_LIST']

    def __init__(self):
        environ = os.environ
        self.BOT_TOKEN = environ.get('BOT_TOKEN')
        self.ADMIN_LIST = environ.get('ADMIN_LIST').split(' ')
