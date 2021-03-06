class Commands(object):

    simple_commands = dict()
    commands = dict()

    def _clean_cmd_name(self, name):
        return name.replace('_', '')

    def command(self, func):
        name = self._clean_cmd_name(func.__name__)
        self.commands[name] = func

    def simple_command(self, func):
        name = self._clean_cmd_name(func.__name__)
        self.simple_commands[name] = func


cmd = Commands()
