import os, sys

# Get Current File Location as Working Directory
operation_directory = os.path.dirname(os.path.realpath(__file__))

import asyncio
import discord
import requests
from bs4 import BeautifulSoup
import json
import datetime

role_ids = json.load(open('roles.json', encoding='utf-8'))
data_centers = json.load(open(operation_directory + os.path.sep + 'data-centers.json', encoding='utf-8'))

class LunaBot:
  __token = ''
  __background_task = set()
  
  guild_id = ''
  command_channels = []
  channels_to_delete = dict()
  reaction_message = dict()

  manager = None

  unverified_members = []

  def __init__(self, token, loop):
    intents = discord.Intents.default()
    intents.members = True

    self.__token = token
    self.__loop = loop
    self.__client = discord.Client(intents=intents, chunk_guilds_at_startup=True, loop=self.__loop)
  
  def linkDatabase(self, manager):
    self.manager = manager
  
  def setGuildID(self, guild):
    self.guild_id = guild

  def setCommandChannels(self, channels):
    self.command_channels = channels

  def setTextChannelsForDeletion(self, channels):
    for key in channels.keys():
      self.channels_to_delete[key] = channels[key]

  def formatEmbedMessage(self, title, message, thumbnail=None, fields=[]):
    embed=discord.Embed(title=title, 
                        description=message, color=discord.Color.blurple())
    if thumbnail:
      embed.set_thumbnail(url=thumbnail)
    
    for i in range(len(fields)):
      embed.add_field(name=fields[i]["Title"], value=fields[i]["Message"], inline=fields[i]["Inline"])
    
    embed.set_footer(text="© Aether Hunt LunaBot")
    return embed

  async def start(self):
    await self.__client.login(self.__token, bot=True)
    
    # Link Events
    self.__client.event(self.on_message)

    # Main Task, Establish WS Connection with Discord
    connection_task = self.__loop.create_task(self.__client.connect())
    self.__background_task.add(connection_task)
    connection_task.add_done_callback(self.__background_task.discard)

    # Message Checking Task
    message_check_task = self.__loop.create_task(self.messageCheck())
    self.__background_task.add(message_check_task)
    message_check_task.add_done_callback(self.__background_task.discard)

    # Member Checking Task
    member_check_task = self.__loop.create_task(self.memberCheck())
    self.__background_task.add(member_check_task)
    member_check_task.add_done_callback(self.__background_task.discard)

    await member_check_task
    await message_check_task
    await connection_task

  async def stop(self):
    await self.__client.close()
    for task in self.__background_task:
      task.cancel()

  def isRunning(self):
    return not self.__client.is_closed()

  # Still need testing on this one
  async def on_member_join(self, member):
    print(member.joined_at.isoformat() + ' ' + member.name)
    self.unverified_members.append(member.id)

  # Naming convention is different because this is Discord.py event handler
  async def on_message(self, message):
    if message.guild == self.__client.get_guild(self.guild_id):
      if message.channel.id in self.command_channels:
        if message.content.startswith('+link '):
          args = message.content.replace('+link ','').split(' ')
          if not len(args) == 3:
            reply = await message.channel.send('Command Failed: Incorrect format for linking character.')
            await reply.delete(delay=10)
            await message.delete(delay=10)

          else:
            await self.handleCharacterSearch(message, args)

        if message.content.startswith('+link_id '):
          args = message.content.replace('+link_id ','').split(' ')
          if not len(args) == 1:
            reply = await message.channel.send('Command Failed: Incorrect format for linking character.')
            await reply.delete(delay=10)
            await message.delete(delay=10)
          else:
            await self.handleVerification(message, args[0])

        if message.content.startswith('+conductor '):
          await self.handlePromotion("Conductor", message)

        if message.content.startswith('+spawner '):
          await self.handlePromotion("Spawner", message)

        if message.content.startswith('+unverified '):
          await self.purging()
  
  # This is not really a true function. Designed for reference of a periodic task in Python with Event Loop
  async def messageCheck(self):
    while True:
      try: 
        if self.__client.is_ready():
          guild = self.__client.get_guild(self.guild_id)
          pass

        else:
          print('Not ready')

        await asyncio.sleep(60)

      except asyncio.CancelledError:
        print('Interrupted')
        return

  # It is recently decided that this should be changed. I will look more into it 
  async def memberCheck(self):
    while True:
      try: 
        if self.__client.is_ready():
          guild = self.__client.get_guild(self.guild_id)
          
          # First Try to Update Database on initial runs
          if len(self.unverified_members) == 0:
            await guild.chunk()
            for member in guild.members:
              verified = len(member.roles) > 1
              if not verified: 
                self.unverified_members.append(member.id)

              """ Database Method, not used.
              await self.manager.insertRecord('Members', {
                'JoinAt': member.joined_at,
                'Verified': verified,
                'ID': member.id
              })
              """
          
          # Once Updated, check if anyone need to be kicked
          for member_id in list(self.unverified_members):
            # Refresh Member Object periodically to check for roles
            try:
              member = await guild.fetch_member(member_id)
              verified = len(member.roles) > 1
              if verified:
                # Remove from unverified list
                self.unverified_members.remove(member_id)

              elif (datetime.datetime.utcnow() - member.joined_at).total_seconds() > 7*24*3600:
                # Kick Member
                pass
              
            except:
              # Can't find member, because the member left the guild already?
              self.unverified_members.remove(member_id)

        else:
          print('Not ready')

        await asyncio.sleep(5)

      except asyncio.CancelledError:
        print('Interrupted')
        return
  
  async def handleCharacterSearch(self, message, args):
    player_dc = ''
    for dc in data_centers.keys():
      if args[2].capitalize() in data_centers[dc]['Names']:
        player_dc = dc
    
    if player_dc in ['Aether','Crystal','Primal']:
      character_search_string = 'https://xivapi.com/character/search?name=' + args[0] + '+' + args[1] + '&server=' + args[2]
      response = requests.get(character_search_string)
      if (response.status_code == 200):
        data = response.json()
        if len(data['Results']) == 0:
          reply = await message.channel.send('Command Failed: Player not found. Make sure your name and world are typed correctly')
          await reply.delete(delay=10)
          await message.delete(delay=10)

        else:
          for result in data['Results']:
            if result['Name'].lower() == (args[0] + ' ' + args[1]).lower():
              await self.handleVerification(message, str(result['ID']))
    
    elif player_dc == '':
      reply = await message.channel.send('Command Failed: World Name not recognized.')
      await reply.delete(delay=10)
      await message.delete(delay=10)

    else:
      reply = await message.channel.send('We are very sorry, Aether Hunt Discord only support NA Data Centers right now.')
      await reply.delete(delay=10)
      await message.delete(delay=10)

  async def handleVerification(self, message, id):
    character_search_string = 'https://xivapi.com/character/' + id
    response = requests.get(character_search_string)
    if (response.status_code == 200):
      data = response.json()
      player_dc = data['Character']['DC']
      if player_dc in ['Aether','Crystal','Primal']:

        classes = data['Character']['ClassJobs']
        highestLevel = 0
        for character_class in classes:
          if character_class['Level'] > highestLevel:
            highestLevel = character_class['Level']
            
        if highestLevel > 50:
          self.__loop.create_task(self.handleRoleChange(message.guild, message.author, player_dc, data['Character']['Server']))
          self.__loop.create_task(message.author.edit(nick=data['Character']['Name'] + ' [' + data['Character']['Server'] + ']'))

          fields = []
          fields.append({"Title": "First Step", "Message": "You can get more role options at <#865129809452728351>", "Inline": False})
          fields.append({"Title": "Added Role", "Message": f"<@&{role_ids['LicensedHunter']}>\n<@&{role_ids[data['Character']['Server']]}>\n<@&{role_ids[player_dc]}>", "Inline": True})

          embed = self.formatEmbedMessage(title= 'Verification Success', message= data['Character']['Name'] + ' [' + data['Character']['Server'] + '] of [' + player_dc + ']', fields=fields, thumbnail=data['Character']["Avatar"])
          reply = await message.channel.send(embed=embed)
          await reply.delete(delay=30)

        else:
          reply = await message.channel.send('Can not verify due to low level: ' + data['Character']['Name'] + ' [' + data['Character']['Server'] + '] of [' + player_dc + ']')
          await reply.delete(delay=10)
    
      else:
        reply = await message.channel.send('We are very sorry, Aether Hunt Discord only support NA Data Centers right now.')
        await reply.delete(delay=10)
  
    await message.delete(delay=10)

  # This is not a full scraper, I only coded enough to get what we need. (This is also no longer being used but kept as backup in case if XIVAPI goes down)
  def extractPlayerLevels(self, id):
    classes = dict()

    url = 'https://na.finalfantasyxiv.com/lodestone/character/' + str(id) + '/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    character = soup.find(id='character')
    character_lists = character.find_all('div', class_='character__level clearfix')
    for character_list in character_lists:
      character_classes = character_list.find_all('li')
      for character_class in character_classes:
          level = int(character_class.text.strip().replace('-','0'))
          content = str(character_class)
          substrings = content.split('"')
          for i in range(len(substrings)):
              if substrings[i].find('data-tooltip') > 0:
                  role = substrings[i+1]
                  break
          classes[role] = level

    return classes
  
  async def handleRoleChange(self, guild, member, dc, home_world):
    # Query World/Datacenter IDs. This is actually static, should it be cached?
    datacenter_ids = []
    world_ids = []
    for datacenter in data_centers.keys():
      if datacenter in role_ids.keys():
        datacenter_ids.append(guild.get_role(role_ids[datacenter]))
        for world in data_centers[datacenter]["Names"]:
          if world in role_ids.keys():
            world_ids.append(guild.get_role(role_ids[world]))
    await member.remove_roles(*datacenter_ids)
    await member.remove_roles(*world_ids)

    # Add Standard Roles of DC / World / Licensed Hunter
    roles_to_add = []
    for key in ["LicensedHunter", dc, home_world]:
      if key in role_ids.keys():
        roles_to_add.append(guild.get_role(role_ids[key]))
    await member.add_roles(*roles_to_add)

    pass 
          
  async def handlePromotion(self, promote_type, message):
    if promote_type == "Conductor":
      args = message.content.replace('+conductor ','').split(' ')
    else:
      args = message.content.replace('+spawner ','').split(' ')

    try:
      if len(args) == 1:
        requester = message.author
        # Verify requester.roles. Only admin is allowed?

        arg = int(args[0].replace('<@','').replace('>',''))
        guild = self.__client.get_guild(self.guild_id)
        member = await guild.fetch_member(arg)

        self.__loop.create_task(member.add_roles(guild.get_role(role_ids[promote_type])))
        embed = self.formatEmbedMessage(title= 'Command Success', message= promote_type + f' is being added to <@{arg}>')
        reply = await message.channel.send(embed=embed)
        await reply.delete(delay=10)

      else:
        embed = self.formatEmbedMessage(title= 'Command Failed', message= 'Too many input. Remember to only add player ping after your command.')
        reply = await message.channel.send(embed=embed)
        await reply.delete(delay=10)

    except Exception as e:
      embed = self.formatEmbedMessage(title= 'Command Failed', message= 'Processing Error.')
      reply = await message.channel.send(embed=embed)
      await reply.delete(delay=10)
    
    await message.delete(delay=10)

  async def purging(self):
    pass
    '''
    guild = self.__client.get_guild(self.guild_id)
    members = await guild.chunk()

    members_to_be_removes = []
    await message.channel.send(f'Chunk Complete, looping over {len(members)} members')

    for member in guild.members:
      reason = []
      white_list = False
      for role in member.roles: 
        if role.name == "Aether":
          white_list = True

        if role.name == "Materia":
          reason.append("User In Materia")

        if role.name == "Light":
          reason.append("User In Light")

        if role.name == "Chaos":
          reason.append("User In Chaos")

        if role.name == "Elemental":
          reason.append("User In Elemental")

        if role.name == "Gaia": 
          reason.append("User In Gaia")

        if role.name == "Mana":
          reason.append("User In Mana")

        if role.name == "Meteor":
          reason.append("User In Meteor")
      
      if len(member.roles) <= 1 and member.joined_at < datetime.datetime.fromtimestamp(1656903541):
        reason.append("No Roles")
        await message.channel.send(f'{member} has no role and older than 7 days')
      
      if len(reason) > 0 and not white_list:
        members_to_be_removes.append(member)

    await message.channel.send(f'Total Members to be removed: {len(members_to_be_removes)}')

    for member in members_to_be_removes:
      await guild.kick(member)

    await message.channel.send(f'All purged')
    '''

