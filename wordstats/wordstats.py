import discord, re
from redbot.core import commands
from redbot.core import Config
from redbot.core import checks
from redbot.core.data_manager import cog_data_path
from redbot.core.config import Group
from copy import deepcopy
from typing import Optional, Union, Dict
from random import randint
import time
import asyncio


class WordStats(commands.Cog):
	"""Tracks commonly used words."""
	def __init__(self, bot):
		self.bot = bot
		self.members_to_update = {}
		self.guilds_to_update = {}
		self.last_save = time.time()
		self.config = Config.get_conf(self, identifier=7345167905)
		self.config.register_guild(
			worddict = {},
			enableGuild = True,
			disabledChannels = []
		)
		self.config.register_member(
			worddict = {}
		)
	
	@commands.guild_only()
	@commands.command()
	async def wordstats(
		self,
		ctx,
		member: Optional[discord.Member]=None,
		amount: Optional[Union[int, str]]=30
	):
		"""
		Prints the most commonly used words.
		
		Use the optional paramater "member" to see the stats of a member.
		Use the optional paramater "amount" to change the number of words that are displayed, or to check the stats of a specific word.
		"""
		try:
			if amount <= 0:
				return await ctx.send('At least one word needs to be displayed.')
		except TypeError:
			pass
		async with ctx.typing():
			await self.update_data(members=self.members_to_update, guilds=self.guilds_to_update)
			if member is None:
				mention = 'the server'
				worddict = await self.config.guild(ctx.guild).worddict()
			else:
				mention = member.display_name
				worddict = await self.config.member(member).worddict()
			order = list(reversed(sorted(worddict, key=lambda w: worddict[w])))
		if isinstance(amount, str):
			try:
				ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
				if order.index(amount.lower()) != 0:
					mc = ordinal(order.index(amount.lower())+1)+'** most common'
				else:
					mc = 'most common**'
				return await ctx.send(
					f'The word **{amount}** has been said by {mention} '
					f'**{str(worddict[amount.lower()])}** '
					f'{"times" if worddict[amount.lower()] != 1 else "time"}.\n'
					f'It is the **{mc} word {mention} has said.'
				)
			except ValueError:
				return await ctx.send(
					f'The word **{amount}** has not been said by {mention} yet.'
				)
		result = ''
		smallresult = ''
		n = 0
		num = 0
		maxlen = False
		for word in order:
			if not maxlen:
				maxlen = len(str(worddict[word]))
			if n < amount:
				smallresult += (
					f'{str(worddict[word])}'
					f'{" ".join(["" for x in range(maxlen-(len(str(worddict[word])))+2)])}'
					f'{str(word)}\n'
				)
				n += 1
			result += f'{str(worddict[word])} {str(word)}\n'
			num += int(worddict[word])
		if smallresult == '':
			if mention == 'the server':
				mention = 'The server'
			await ctx.send(f'{mention} has not said any words yet.')
		else:
			try:
				await ctx.send(
					f'Out of **{num}** words and **{len(worddict)}** unique words, '
					f'the **{str(n) + "** most common words" if n != 1 else "most common** word"} '
					f'that {mention} has said {"are" if n != 1 else "is"}:\n'
					f'```{smallresult.rstrip()}```'
				)
			except discord.errors.HTTPException:
				await ctx.send('Message too long to send.')
	
	@commands.guild_only()
	@commands.command()
	async def topchatters(self, ctx, amount: int=10):
		"""
		Prints the members who have said the most words.
		
		Use the optional paramater "amount" to change the number of members that are displayed.
		"""
		if amount <= 0:
			return await ctx.send('At least one member needs to be displayed.')
		async with ctx.typing():
			await self.update_data(members=self.members_to_update, guilds=self.guilds_to_update)
			data = await self.config.all_members(ctx.guild)
			sumdict = {}
			for memid in data:
				n = 0
				for word in data[memid]['worddict']:
					n += data[memid]['worddict'][word]
				sumdict[memid] = n
			order = list(reversed(sorted(sumdict, key=lambda x: sumdict[x])))
		result = ''
		smallresult = ''
		n = 0
		num = 0
		maxlen = False
		for memid in order:
			if n < amount:
				if not maxlen:
					maxlen = len(str(sumdict[memid]))
				try:
					mem = ctx.guild.get_member(memid)
					name = mem.display_name
				except AttributeError:
					name = f'<removed member {memid}>'
				smallresult += (
					f'{str(sumdict[memid])}'
					f'{" ".join(["" for x in range(maxlen-len(str(sumdict[memid]))+2)])}'
					f'{name}\n'
				)
				n += 1
			result += f'{str(sumdict[memid])} {str(memid)}\n'
			num += int(sumdict[memid])
		try:
			await ctx.send(
				f'Out of **{num}** words, the {"**" + str(n) + "** " if n != 1 else ""}'
				f'{"members" if n != 1 else "member"} who {"have" if n != 1 else "has"} '
				f'said the most words {"are" if n != 1 else "is"}:\n```{smallresult}```'
			)
		except discord.errors.HTTPException:
			await ctx.send('Message too long to send.')
	
	@commands.guild_only()
	@checks.guildowner()
	@commands.group()
	async def wordstatsset(self, ctx):
		"""Config options for wordstats."""
		pass
			
	@commands.guild_only()
	@checks.guildowner()
	@wordstatsset.command()
	async def server(self, ctx, value: bool=None):
		"""
		Set if wordstats should record stats for this server.
		
		Defaults to True.
		This value is server specific.
		"""
		if ctx.guild not in self.guilds_to_update:
			self.guilds_to_update[ctx.guild] = await self.config.guild(ctx.guild).all()
		if value is None:
			v = self.guilds_to_update[ctx.guild]['enableGuild']
			if v:
				await ctx.send('Stats are being recorded in this server.')
			else:
				await ctx.send('Stats are not being recorded in this server.')
		else:
			self.guilds_to_update[ctx.guild]['enableGuild'] = value
			await self.update_data(members=self.members_to_update, guilds=self.guilds_to_update)
			if value:
				await ctx.send('Stats will now be recorded in this server.')
			else:
				await ctx.send('Stats will no longer be recorded in this server.')
			
	@commands.guild_only()
	@checks.guildowner()
	@wordstatsset.command()
	async def channel(self, ctx, value: bool=None):
		"""
		Set if wordstats should record stats for this channel.
		
		Defaults to True.
		This value is channel specific.
		"""
		if ctx.guild not in self.guilds_to_update:
			self.guilds_to_update[ctx.guild] = await self.config.guild(ctx.guild).all()
		v = self.guilds_to_update[ctx.guild]['disabledChannels']
		if value is None:
			if ctx.channel.id not in v:
				await ctx.send('Stats are being recorded in this channel.')
			else:
				await ctx.send('Stats are not being recorded in this channel.')
		else:
			if value:
				if ctx.channel.id not in v:
					await ctx.send('Stats are already being recorded in this channel.')
				else:
					v.remove(ctx.channel.id)
					self.guilds_to_update[ctx.guild]['disabledChannels'] = v
					await self.update_data(
						members=self.members_to_update,
						guilds=self.guilds_to_update
					)
					await ctx.send('Stats will now be recorded in this channel.')
			else:
				if ctx.channel.id in v:
					await ctx.send('Stats are already not being recorded in this channel.')
				else:
					v.append(ctx.channel.id)
					self.guilds_to_update[ctx.guild]['disabledChannels'] = v
					await self.update_data(
						members=self.members_to_update,
						guilds=self.guilds_to_update
					)
					await ctx.send('Stats will no longer be recorded in this channel.')
			
	async def update_data(
		self,
		members: Dict[discord.Member, dict],
		guilds: Dict[discord.Guild, dict]
	):
		"""Thanks to Sinbad for this dark magic."""
		self.last_save = time.time()
		base_group = Group(
			identifiers=(), 
			defaults={}, 
			driver=self.config.driver,
			force_registration=self.config.force_registration,
		)

		def nested_update(d, keys, value):
			partial = d
			for i in keys[:-1]:
				if i not in partial:
					partial.update({i: {}})
				partial = partial[i]
			partial[keys[-1]] = value

		async with base_group() as data:
			# this is a workaround for needing to switch contexts safely
			# to prevent heartbeat issues
			member_iterator = enumerate(list(members.items()), 1)
			guild_iterator = enumerate(list(guilds.items()), 1)
			for index, (member, member_data) in member_iterator:
				keys = (self.config.MEMBER, str(member.guild.id), str(member.id))
				value = deepcopy(member_data)
				nested_update(data, keys, value)
				if index % 10:
					await asyncio.sleep(0)
			for index, (guild, guild_data) in guild_iterator:
				keys = (self.config.GUILD, str(guild.id))
				value = deepcopy(guild_data)
				nested_update(data, keys, value)
				if index % 10:
					await asyncio.sleep(0)

		self.members_to_update = {}
		self.guilds_to_update = {}
	
	async def on_message(self, msg):
		"""Passively records all message contents."""
		if not msg.author.bot and isinstance(msg.channel, discord.TextChannel):
			enableGuild = await self.config.guild(msg.guild).enableGuild()
			disabledChannels = await self.config.guild(msg.guild).disabledChannels()
			if enableGuild and not msg.channel.id in disabledChannels:
				p = await self.bot.get_prefix(msg)
				if any([msg.content.startswith(x) for x in p]):
					return
				words = str(re.sub(r'[^a-zA-Z ]', '', msg.content.lower())).split(' ')
				if msg.guild not in self.guilds_to_update:
					self.guilds_to_update[msg.guild] = await self.config.guild(msg.guild).all()
				guilddict = self.guilds_to_update[msg.guild]['worddict']
				if msg.author not in self.members_to_update:
					self.members_to_update[msg.author] = await self.config.member(msg.author).all()
				memdict = self.members_to_update[msg.author]['worddict']
				for word in words:
					if not word:
						continue
					if word in guilddict:
						guilddict[word] += 1
					else:
						guilddict[word] = 1
					if word in memdict:
						memdict[word] += 1
					else:
						memdict[word] = 1
				self.guilds_to_update[msg.guild]['worddict'] = guilddict
				self.members_to_update[msg.author]['worddict'] = memdict
				if time.time() - self.last_save >= 600: #10 minutes per save
					await self.update_data(
						members=self.members_to_update,
						guilds=self.guilds_to_update
					)
