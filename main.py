# PyPI Modules
import os, sys
import argparse
import asyncio

import json
import logging

# Custom Modules
from lunabot import LunaBot
import database
from models import *

# Get Current File Location as Working Directory
operation_directory = os.path.dirname(os.path.realpath(__file__))

# Initial Environment Variable Setup
environment_variable = json.load(open(operation_directory + os.path.sep + '.env', 'r'))
for key in environment_variable.keys():
  os.environ[key] = environment_variable[key]

# Commandline Parser
parser = argparse.ArgumentParser(description='LunaBot Command Line Arguments')
parser.add_argument('-d', '--debug', metavar='level', choices=['CRITICAL','ERROR','WARNING','INFO','DEBUG'], help='Debug Logs Level')
logging_level = {
  'CRITICAL': logging.CRITICAL,
  'ERROR': logging.ERROR,
  'WARNING': logging.WARNING,
  'INFO': logging.INFO,
  'DEBUG': logging.DEBUG,
}

if __name__ == '__main__':
  args = parser.parse_args()

  # Logging Setup (This is not actually activated)
  logger = logging.getLogger('discord')
  if args.debug:
    logger.setLevel(logging_level[args.debug])
  debug_handler = logging.FileHandler(filename=operation_directory + os.path.sep + 'discord.log', encoding='utf-8', mode='w')
  debug_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
  logger.addHandler(debug_handler)

  # Create Database
  manager = database.Manager(operation_directory + os.path.sep + 'lunabot.sqlite3')

  # Confirm Windows?
  asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

  # Get Event Loops 
  loop = asyncio.new_event_loop()
  bot = LunaBot(os.environ['DISCORD_BOT_TOKEN'], loop)
  bot.setGuildID(542602456132091904)
  bot.setCommandChannels([995751812437119036])
  bot.linkDatabase(manager)

  try:
    loop.run_until_complete(bot.start())
  except KeyboardInterrupt:
    loop.run_until_complete(bot.stop())
  finally:
    if bot.isRunning():
      loop.run_until_complete(bot.stop())

    loop.close()
  
  