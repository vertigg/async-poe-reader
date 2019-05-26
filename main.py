import argparse
import asyncio as aio
import configparser
import logging
import os
import re
import sys

import aioconsole
import aiofiles
import pyttsx3

from utils.commands import cmd


class ClientPathNotSet(Exception):
    pass


class ChatReader(object):

    from_pattern = r'(?P<guild><.*?>?)\s(?P<name>[^<]\w*)(?:\:\s)(?P<text>.*)'

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.paused = False
        self.logger.setLevel(logging.DEBUG)

        self.logger.info('Async ChatReader initializing...')
        self._setup_tts_engine()
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.client_txt = self.get_conf_value('client_txt_path')
        self._check_path()

        self.tags = self._get_tags()
        self.ignored_users = self._get_ignored_users()
        self.logger.info('ChatReader is working')
    
    def _setup_tts_engine(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)
        self.engine.setProperty('volume', 1)
        self.engine.setProperty('rate', 150)

    def _get_ignored_users(self):
        raw_string = self.get_conf_value('ignored_users')
        return [] if not raw_string else raw_string.split(',')

    def _get_tags(self):
        raw_string = self.get_conf_value('search_words')
        tags = [] if not raw_string else raw_string.split(',')
        if not tags:
            self.logger.info('Searching tags are not set')
        return tags

    def _check_path(self):
        if not self.client_txt or not os.path.isfile(self.client_txt):
            raise ClientPathNotSet(
                'Client.txt path is not set or path is wrong')

    def get_conf_value(self, key, section='default'):
        return self.config[section][key]

    def _concat_string(self, iterable):
        return ' '.join(iterable)

    @cmd.simple_command
    def q(self):
        self.logger.info('Quitting...')
        try:
            sys.exit(1)
        except RuntimeError:
            pass

    @cmd.simple_command
    def words(self):
        self.logger.info(f'Current searching tags: {self.tags}')

    @cmd.simple_command
    def clear(self):
        self.tags = []
        self.save_config()
        self.logger.info('Search list cleared')

    @cmd.simple_command
    def _pause(self, *args):
        self.paused = not self.paused
        self.logger.info(f'Pause set to {self.paused}')

    @cmd.command
    def add(self, args):
        self.tags.append(self._concat_string(args))
        self.save_config()
        self.logger.info(f'{args} added')

    @cmd.command
    def remove(self, args):
        words = self._concat_string(args)
        if words in self.tags:
            self.tags.remove(words)
            self.logger.info(f'{words} removed')
            self.save_config()
        else:
            self.logger.info(
                f"Can't find search tag {words}. Current tags are {self.tags}")

    @cmd.command
    def block(self, args):
        name = args[0]
        if not name in self.ignored_users:
            self.ignored_users.append(name)
            self.save_config()
            self.logger.info(f'User {name} ignored')
        else:
            self.logger.info(f'{name} is already blocked')

    @cmd.command
    def unblock(self, args):
        name = args[0]
        if name in self.ignored_users:
            self.ignored_users.remove(name)
            self.save_config()
        else:
            self.logger.info(f'No user {name}')

    def save_config(self):
        with open('config.ini', 'w', encoding='utf-8') as config_file:
            self.config['default']['ignored_users'] = ','.join(
                self.ignored_users)
            self.config['default']['search_words'] = ','.join(self.tags)
            self.config.write(config_file)

    async def __call__(self):
        await aio.gather(self.reader_task(), self.input_task())

    async def input_task(self):
        while True:
            msg = await aioconsole.ainput('')
            if msg:
                args = msg.split()
                command = args[0]
                if len(args) >= 2 and command in cmd.commands.keys():
                    cmd.commands[command](self, args[1:])
                if len(args) == 1 and command in cmd.simple_commands.keys():
                    cmd.simple_commands[command](self)

    async def reader_task(self):
        async with aiofiles.open(self.client_txt, 'r', encoding='utf-8') as client_file:
            await client_file.seek(0, 2)
            while True:
                line = await client_file.readline()
                if not line or line == '\n' or self.paused:
                    await aio.sleep(0.25)
                    continue
                elif self.tags and any(s.upper() in line.upper() for s in self.tags) or '@From' in line:
                    message = re.search(self.from_pattern, line, flags=re.I)
                    if message:
                        data = message.groupdict()
                        name = data.get('name', None)
                        text = data.get('text', None)
                        if name and name not in self.ignored_users:
                            self.engine.say(text)
                            self.logger.info(f'Matched message: {name}: {text}')
                            self.engine.runAndWait()
                    continue


if __name__ == '__main__':
    logging.basicConfig()
    chat_reader = ChatReader()
    aio.run(chat_reader())
