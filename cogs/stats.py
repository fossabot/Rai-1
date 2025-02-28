import discord
from discord.ext import commands

from .utils import helper_functions as hf
from datetime import datetime, timedelta, timezone
import re

import os

from .utils.timeutil import format_interval

dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SPAM_CHAN = 275879535977955330


class Stats(commands.Cog):
    """A module for tracking stats of messages on servers for users to view. Enable/disable the module with `"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        try:
            category_id = ctx.channel.category.id
        except AttributeError:
            return
        if category_id in [685446008129585176, 685445852009201674]:
            try:
                if ctx.message.content != ";help":
                    await ctx.reply("Please use that command in <#247135634265735168>.")
                return
            except (discord.Forbidden, discord.HTTPException):
                return
        if ctx.guild:
            return True
        else:
            raise commands.NoPrivateMessage

    lang_codes_dict = {'af': 'Afrikaans', 'ga': 'Irish', 'sq': 'Albanian', 'it': 'Italian', 'ar': 'Arabic',
                       'ja': 'Japanese', 'az': 'Azerbaijani', 'kn': 'Kannada', 'eu': 'Basque', 'ko': 'Korean',
                       'bn': 'Bengali', 'la': 'Latin', 'be': 'Belarusian', 'lv': 'Latvian', 'bg': 'Bulgarian',
                       'lt': 'Lithuanian', 'ca': 'Catalan', 'mk': 'Macedonian', 'zh-CN': 'Chinese Simplified',
                       'ms': 'Malay', 'zh-TW': 'Chinese Traditional', 'mt': 'Maltese', 'hr': 'Croatian',
                       'no': 'Norwegian', 'cs': 'Czech', 'fa': 'Persian', 'da': 'Danish', 'pl': 'Polish',
                       'nl': 'Dutch', 'pt': 'Portuguese', 'en': 'English', 'ro': 'Romanian', 'eo': 'Esperanto',
                       'ru': 'Russian', 'et': 'Estonian', 'sr': 'Serbian', 'tl': 'Filipino', 'sk': 'Slovak',
                       'fi': 'Finnish', 'sl': 'Slovenian', 'fr': 'French', 'es': 'Spanish', 'gl': 'Galician',
                       'sw': 'Swahili', 'ka': 'Georgian', 'sv': 'Swedish', 'de': 'German', 'ta': 'Tamil',
                       'el': 'Greek', 'te': 'Telugu', 'gu': 'Gujarati', 'th': 'Thai', 'ht': 'Haitian Creole',
                       'tr': 'Turkish', 'iw': 'Hebrew', 'uk': 'Ukrainian', 'hi': 'Hindi', 'ur': 'Urdu',
                       'hu': 'Hungarian', 'vi': 'Vietnamese', 'is': 'Icelandic', 'cy': 'Welsh', 'id': 'Indonesian',
                       'yi': 'Yiddish'}

    @commands.command(aliases=['uc'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def uchannels(self, ctx, *, member: str = None):
        if not member:
            member = ctx.author
        else:
            member = await hf.member_converter(ctx, member)
            if not member:
                return
        try:
            config = self.bot.stats[str(ctx.guild.id)]['messages']
        except KeyError:
            return

        message_count = {}
        for day in config:
            if str(member.id) in config[day]:
                if 'channels' not in config[day][str(member.id)]:
                    continue
                user = config[day][str(member.id)]
                for channel in user.get('channels', []):
                    message_count[channel] = message_count.get(channel, 0) + user['channels'][channel]
        sorted_msgs = sorted(message_count.items(), key=lambda x: x[1], reverse=True)
        emb = discord.Embed(title=f'Usage stats for {member.name} ({member.nick})',
                            description="Last 30 days",
                            color=discord.Color(int('00ccFF', 16)),
                            timestamp=member.joined_at)
        lb = ''
        index = 1
        total = 0
        for channel_tuple in sorted_msgs:
            total += channel_tuple[1]
        for channel_tuple in sorted_msgs:
            if ctx.channel.id != 277511392972636161 and channel_tuple[0] == '277511392972636161':
                continue
            if str(ctx.channel.id) not in self.bot.stats[str(ctx.guild.id)]['hidden']:
                if channel_tuple[0] in self.bot.stats[str(ctx.guild.id)]['hidden']:
                    continue
            try:
                channel = ctx.guild.get_channel_or_thread(int(channel_tuple[0]))
                if not channel:
                    continue
                lb += f"**{index}) {channel.name}**: {round((channel_tuple[1]/total)*100, 2)}% ({channel_tuple[1]})\n"
                index += 1
            except discord.NotFound:
                pass
            if index == 26:
                break
        if not lb:
            await hf.safe_send(ctx, "This user has not said anything in the past 30 days.")
            return
        emb.add_field(name="Top channels", value=lb[:1024])
        await hf.safe_send(ctx, embed=emb)

    @commands.command(aliases=['u'])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def user(self, ctx, *, member: str = None, post_embed=True):
        """Gives info about a user.  Leave the member field blank to get info about yourself."""
        if not member:
            member = ctx.author
            member_id = ctx.author.id
        else:
            if re.findall(r"[JIMVN]\d{17,22}", member):
                member = re.sub('[JIMVN]', '', member)
            member_id = member
            member = await hf.member_converter(ctx, member)
            if member:
                member_id = member.id
            else:
                try:
                    user = await self.bot.fetch_user(member_id)
                    user_name = user.name
                except (discord.NotFound, discord.HTTPException):
                    await hf.safe_send(ctx, "I couldn't find the user.")
                    return
        try:
            config = self.bot.stats[str(ctx.guild.id)]['messages']
        except KeyError:
            return

        # If user in bot.db['joindates'], override their join date for users who have left and rejoined server
        if member:
            if str(member.id) in self.bot.db['joindates']:
                actual_joined_timestamp = self.bot.db['joindates'][str(member.id)]
                member.joined_at = datetime.fromtimestamp(actual_joined_timestamp, tz=timezone.utc)

        # ### Collect all the data from the database ###
        emoji_dict = {emoji.name: emoji for emoji in ctx.guild.emojis}
        message_count = {}
        emoji_count = {}
        lang_count = {}
        total_msgs_month = 0
        total_msgs_week = 0
        total_activity = hf.count_activity(member)
        for day in config:
            if str(member_id) in config[day]:
                user = config[day][str(member_id)]
                if 'channels' not in user:
                    continue
                for channel in user['channels']:
                    message_count[channel] = message_count.get(channel, 0) + user['channels'][channel]
                    days_ago = (discord.utils.utcnow() -
                                datetime.strptime(day, "%Y%m%d").replace(tzinfo=timezone.utc)).days
                    if days_ago <= 7:
                        total_msgs_week += user['channels'][channel]
                    total_msgs_month += user['channels'][channel]
                if 'emoji' in user:
                    for emoji in user['emoji']:
                        if emoji in emoji_dict:
                            name = emoji_dict[emoji]
                        else:
                            name = emoji
                        emoji_count[name] = emoji_count.get(name, 0) + user['emoji'][emoji]
                if 'lang' in user:
                    for lang in user['lang']:
                        lang_count[lang] = lang_count.get(lang, 0) + user['lang'][lang]

        # ### Sort the data ###
        sorted_msgs = sorted(message_count.items(), key=lambda x: x[1], reverse=True)
        # looks like [('284045742652260352', 15), ('296491080881537024', 3), ('296013414755598346', 1)]
        sorted_emojis = sorted(emoji_count.items(), key=lambda x: x[1], reverse=True)
        sorted_langs = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)

        # ### Make embed ###
        if member:
            title = f'Usage stats for {str(member)}'
            if member.nick:
                title += f" ({member.nick})"
        else:
            title = f'Usage stats for {member_id} ({user_name}) (user left server)'
        emb = discord.Embed(title=title,
                            description="Last 30 days",
                            color=discord.Color(int('00ccFF', 16)))
        if member:
            emb.timestamp = member.joined_at
        emb.add_field(name="Messages sent M | W",
                      value=f"{total_msgs_month} | {total_msgs_week}")
        emb.add_field(name="Activity score",
                      value=f"{total_activity} ([?](https://pastebin.com/raw/07xKpDpy))")

        # ### Find top 3 most active channels ###
        good_channels = 0
        hidden = self.bot.stats[str(ctx.guild.id)]['hidden']
        if ctx.channel.id != 277511392972636161 and ctx.guild.id == 243838819743432704:
            for channel in sorted_msgs:
                if channel[0] == '277511392972636161':
                    sorted_msgs.remove(channel)
                    break
        for channel in sorted_msgs.copy():
            if str(ctx.channel.id) in hidden:  # you're in a hidden channel, keep all
                break
            if channel[0] in hidden:  # one of the top channels is a hidden channel, remove
                sorted_msgs.remove(channel)
            else:  # it's not a hidden channel, keep
                good_channels += 1
            if good_channels == 3:  # you have three kept channels
                break

        # ### Format top 3 channels text field / Add field to embed ###
        channeltext = ''
        try:
            channel1 = (self.bot.get_channel(int(sorted_msgs[0][0])),
                        round(100 * sorted_msgs[0][1] / total_msgs_month, 2))
            channeltext += f"**#{channel1[0]}**: {channel1[1]}%⠀\n"
            channel2 = (self.bot.get_channel(int(sorted_msgs[1][0])),
                        round(100 * sorted_msgs[1][1] / total_msgs_month, 2))
            channeltext += f"**#{channel2[0]}**: {channel2[1]}%⠀\n"
            channel3 = (self.bot.get_channel(int(sorted_msgs[2][0])),
                        round(100 * sorted_msgs[2][1] / total_msgs_month, 2))
            channeltext += f"**#{channel3[0]}**: {channel3[1]}%⠀\n"
        except IndexError:  # will stop automatically if there's not three channels in the list
            pass
        if channeltext:
            emb.add_field(name="Top Channels:",
                          value=f"{channeltext}")

        # ### Calculate voice time / Add field to embed ###
        voice_time: int = hf.calculate_voice_time(member_id, ctx.guild.id)  # number of minutes
        if voice_time:
            emb.add_field(name="Time in voice chats",
                          value=format_interval(voice_time))

        # ### If no messages or voice in last 30 days ###
        if (not total_msgs_month or not sorted_msgs) and not voice_time:
            emb = discord.Embed(title='',
                                description="This user hasn't said anything in the past 30 days",
                                color=discord.Color(int('00ccFF', 16)))
            if member:
                emb.title = f"Usage stats for {member.name}"
                if member.nick:
                    emb.title += f" ({member.nick})"
                emb.timestamp = member.joined_at
            else:
                emb.title += f"Usage stats for {member_id} {user_name} (this user was not found)"

        # ### Add emojis field ###
        if sorted_emojis:
            value = ''
            counter = 0
            for emoji_tuple in sorted_emojis:
                value += f"{str(emoji_tuple[0])} {str(emoji_tuple[1])} times\n"
                counter += 1
                if counter == 3:
                    break
            if value:
                emb.add_field(name='Most used emojis', value=value)

        # ### Add top langauges field ###
        if sorted_langs:
            value = ''
            counter = 0
            total = 0
            for lang_tuple in sorted_langs:
                total += lang_tuple[1]
            for lang_tuple in sorted_langs:
                if lang_tuple[0] not in self.lang_codes_dict:
                    continue
                percentage = round((lang_tuple[1] / total) * 100, 1)
                if (counter in [0, 1] and percentage > 2.5) or (percentage > 5):
                    value += f"**{self.lang_codes_dict[lang_tuple[0]]}**: {percentage}%\n"
                if counter == 5:
                    break
            if value:
                emb.add_field(name='Most used languages', value=value)

        # ### Calculate join position ###
        if member:
            member_list = ctx.guild.members
            for member_in_list in list(member_list).copy():
                if not member_in_list.joined_at:
                    member_list.remove(member_in_list)
            sorted_members_by_join = sorted([(member, member.joined_at) for member in member_list],
                                            key=lambda x: x[1],
                                            reverse=False)
            join_order = 0
            for i in sorted_members_by_join:
                if i[0].id == member.id:
                    join_order = sorted_members_by_join.index(i)
                    break
            if join_order + 1:
                emb.set_footer(text=f"(#{join_order+1} to join this server) Joined on:")

        # ### Send ###
        if post_embed:
            try:
                await hf.safe_send(ctx, embed=emb)
            except discord.Forbidden:
                try:
                    await hf.safe_send(ctx, "I lack the permissions to send embeds in this channel")
                    await hf.safe_send(ctx.author, embed=emb)
                except discord.Forbidden:
                    await hf.safe_send(ctx.author, "I lack the permission to send messages in that channel")
        return emb

    @staticmethod
    def make_leaderboard_embed(ctx, channel_in, dict_in, title):
        sorted_dict = sorted(dict_in.items(), reverse=True, key=lambda x: x[1])
        emb = discord.Embed(title=title,
                            description="Last 30 days",
                            color=discord.Color(int('00ccFF', 16)),
                            timestamp=discord.utils.utcnow())

        if "Activity Score" in title:
            emb.set_footer(text="Try `;lb` or `;chlb` for the message count leaderboard")
        else:
            emb.set_footer(text="Try `;alb` or `;achlb` for the activity score leaderboard")

        if channel_in:
            if isinstance(channel_in, list):
                emb.title += " for #" + ', #'.join([c.name for c in channel_in])
            else:
                emb.title += " for #{channel_in.name}"
        number_of_users_found = 0
        found_yourself = False
        for i in range(len(sorted_dict)):
            member = ctx.guild.get_member(int(sorted_dict[i][0]))
            if member:
                if number_of_users_found < 24 or \
                        (number_of_users_found == 24 and (found_yourself or member == ctx.author)) or \
                        number_of_users_found > 24 and member == ctx.author:
                    value = sorted_dict[i][1]
                    if title.startswith("Voice"):
                        value = format_interval(value * 60)  # value is counted in minutes
                    emb.add_field(name=f"{number_of_users_found+1}) {member.name}",
                                  value=value)
                number_of_users_found += 1
                if member == ctx.author:
                    found_yourself = True
            if number_of_users_found >= 25 and found_yourself:
                break
        return emb

    async def make_lb(self, ctx, channels_in, db_target='channels'):
        try:
            config = self.bot.stats[str(ctx.guild.id)]['messages']
        except KeyError:
            return
        msg_count = {}

        # if channels_in is passed, calculate the proper list of channels:
        # if it comes from ;lb, it will be "False"
        # if it comes from ;chlb, it will be a (possibly empty) tuple of channel link strings
        if channels_in is False:  # came from ;lb, take all channels
            channel_obs = []
        elif not channels_in:  # came from ;chlb but no channel specification, take ctx as specified channel
            if isinstance(ctx.channel, discord.Thread):
                channel_obs = [ctx.channel.parent]
            else:
                channel_obs = [ctx.channel]
        else:  # came from ;chlb with channel specification, take specified channels
            channel_ids = []
            channel_obs = []
            for channel in channels_in:
                channel_ids.append(channel[2:-1])
            for channel_id in channel_ids:
                try:
                    c = ctx.guild.get_channel_or_thread(int(channel_id))
                    if c:
                        if isinstance(c, discord.Thread):
                            c = c.parent
                        channel_obs.append(c)
                    else:
                        await hf.safe_send(ctx, f"I couldn't find the channel `{channel_id}`.")
                        continue
                except ValueError:
                    await hf.safe_send(ctx,
                                       "Please provide a link to a channel, not just the channel name "
                                       "(e.g. `;chlb #general`), or if you just type `;chlb` "
                                       "it will show the leaderboard for the current channel.")
                    return
            if not channel_obs:
                await hf.safe_send(ctx, "I couldn't find any valid channels.")
                return

        if channel_obs:
            channel_ids = [c.id for c in channel_obs]
        else:
            channel_ids = []
        for day in config:
            for user in config[day]:
                if db_target not in config[day][user]:
                    continue
                for channel in config[day][user][db_target]:
                    if channel_obs:
                        if int(channel) not in channel_ids:
                            continue
                    try:
                        msg_count[user] += config[day][user][db_target][channel]
                    except KeyError:
                        msg_count[user] = config[day][user][db_target][channel]
        try:
            if db_target == 'channels':
                title = "Messages Leaderboard"
            else:
                title = "Activity Score Leaderboard"
            await hf.safe_send(ctx,
                               embed=self.make_leaderboard_embed(ctx, channel_obs, msg_count, title))
        except discord.Forbidden:
            try:
                await hf.safe_send(ctx, "I lack the permissions to send embeds in this channel")
            except discord.Forbidden:
                pass

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def lb(self, ctx, *channels):
        """Shows a leaderboard of the top 25 most active users this month"""
        if channels:
            await self.make_lb(ctx, channels)
        else:
            await self.make_lb(ctx, False)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def alb(self, ctx, *channels):
        """Shows a leaderboard of the users with the top 25 highest activity scores"""
        if channels:
            await self.make_lb(ctx, channels, "activity")
        else:
            await self.make_lb(ctx, False, "activity")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def chlb(self, ctx, *channels):
        await self.make_lb(ctx, channels)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def achlb(self, ctx, *channels):
        await self.make_lb(ctx, channels, "activity")

    @commands.command(aliases=['vclb', 'vlb', 'voicechat'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def vc(self, ctx):
        """Prints a leaderboard of who has the most time in voice"""
        try:
            config = self.bot.stats[str(ctx.guild.id)]['voice']['total_time']
        except KeyError:
            return
        lb_dict = {}
        for day in config:
            for user in config[day]:
                if user in lb_dict:
                    lb_dict[user] += config[day][user]
                else:
                    lb_dict[user] = config[day][user]
        await hf.safe_send(ctx, embed=self.make_leaderboard_embed(ctx, None, lb_dict, "Voice Leaderboard"))

    @commands.command(aliases=['emojis', 'emoji'])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(3, 5, commands.BucketType.user)
    async def emotes(self, ctx, args=None):
        """Shows top emojis usage of the server.
        `;emojis` - Displays the top 25
        `;emojis -a` - Shows usage stats on all emojis
        `;emojis -l` - Shows least used emojis.
        `;emojis -s` - Same as `-a` but it scales the usage of emojis created in the last 30 days
        `;emojis -me` - Shows only your emoji stats"""
        if str(ctx.guild.id) not in self.bot.stats:
            return
        config = self.bot.stats[str(ctx.guild.id)]['messages']
        emojis: dict[str, int] = {}

        if args == '-me':
            me = True
        else:
            me = False

        for date in config:
            for user_id in config[date]:
                if me:
                    if int(user_id) != ctx.author.id:
                        continue
                if 'emoji' not in config[date][user_id]:
                    continue
                for emoji in config[date][user_id]['emoji']:
                    emoji: str
                    if emoji in emojis:
                        emojis[emoji] += config[date][user_id]['emoji'][emoji]
                    else:
                        emojis[emoji] = config[date][user_id]['emoji'][emoji]

        emoji_dict: dict[str, discord.Emoji] = {emoji.name: emoji for emoji in ctx.guild.emojis}
        msg = 'Top Emojis:\n'
        
        if args == '-s':
            for emoji in emojis:
                if emoji not in emoji_dict:
                    continue
                emoji_obj = emoji_dict[emoji]
                x = discord.utils.utcnow() - emoji_obj.created_at
                if x < timedelta(days=30):
                    emojis[emoji] = int(emojis[emoji] * 30 / (x.days + 1))
            args = '-a'
            msg = 'Scaled Emoji Counts (last 30 days, emojis created in the last 30 days have ' \
                  'numbers scaled to 30 days):\n'
        top_emojis = sorted(list(emojis.items()), key=lambda x: x[1], reverse=True)

        saved_msgs = []

        if args == '-a':
            for emoji in top_emojis:
                if emoji[0] in emoji_dict:
                    emoji_obj = emoji_dict[emoji[0]]
                    addition = f"{str(emoji_obj)}: {emoji[1]}\n"
                    if len(msg + addition) < 2000:
                        msg += addition
                    else:
                        saved_msgs.append(msg)
                        msg = addition
            if saved_msgs:
                if saved_msgs[-1] != msg:
                    saved_msgs.append(msg)
                for msg in saved_msgs:
                    await hf.safe_send(ctx, msg)
            else:
                await hf.safe_send(ctx, msg)

        elif args == '-l':
            emb = hf.red_embed("Least Used Emojis (last 30 days)")

            zero_use_emoji_list = [e for e in ctx.guild.emojis if not e.animated and '_kana_' not in e.name]
            uses_to_emoji_list_dict = {}
            for emoji in top_emojis:
                try:
                    emoji_obj = emoji_dict[emoji[0]]
                except KeyError:
                    continue
                if emoji_obj.animated or '_kana_' in emoji_obj.name:
                    continue

                if emoji_obj in zero_use_emoji_list:
                    zero_use_emoji_list.remove(emoji_obj)  # now a list of emojis with zero uses

                uses_to_emoji_list_dict.setdefault(emoji[1], []).append(emoji_obj)

            if zero_use_emoji_list:
                uses_to_emoji_list_dict[0] = zero_use_emoji_list

            total_emojis = 0
            field_counter = 0
            while field_counter <= len(uses_to_emoji_list_dict) and (field_counter < 6 or total_emojis < 50):
                if field_counter in uses_to_emoji_list_dict:
                    if field_counter == 1:
                        field_name = f"{field_counter} use"
                    else:
                        field_name = f"{field_counter} uses"
                    field_value = ''
                    for emoji in uses_to_emoji_list_dict[field_counter]:
                        if emoji.animated:
                            continue
                        new_addition = f"{str(emoji)} "
                        if len(field_value + new_addition) < 1024:
                            field_value += new_addition
                        else:
                            emb.add_field(name=field_name, value=field_value, inline=True)

                            if field_counter == 1:
                                field_name = f"{field_counter} use (cont.)"
                            else:
                                field_name = f"{field_counter} uses (cont.)"

                            field_value = new_addition
                        total_emojis += 1

                    if 'cont' in field_name:
                        emb.add_field(name=field_name, value=field_value, inline=True)
                    else:
                        emb.add_field(name=field_name, value=field_value, inline=False)

                field_counter += 1

            await hf.safe_send(ctx, embed=emb)

        else:
            emb = hf.green_embed("Most Used Emojis (last 30 days)")
            field_counter = 0
            for emoji in top_emojis:
                if field_counter < 25:
                    if emoji[0] in emoji_dict:
                        emoji_obj = emoji_dict[emoji[0]]
                        emb.add_field(name=f"{field_counter + 1}) {str(emoji_obj)}", value=emoji[1])
                        field_counter += 1
                else:
                    break
            await hf.safe_send(ctx, embed=emb)

    @commands.group(invoke_without_command=True)
    @hf.is_admin()
    async def stats(self, ctx):
        """Enable/disable keeping of statistics for users (`;u`)"""
        guild = str(ctx.guild.id)
        if guild in self.bot.stats:
            self.bot.stats[guild]['enable'] = not self.bot.stats[guild]['enable']
        else:
            self.bot.stats[guild] = {'enable': True,
                                     'messages': {},
                                     'hidden': [],
                                     'voice':
                                         {'in_voice': {},
                                          'total_time': {}}
                                     }
        await hf.safe_send(ctx, f"Logging of stats is now set to {self.bot.stats[guild]['enable']}.")

    @stats.command()
    @hf.is_admin()
    async def hide(self, ctx, flag=None):
        """Hides the current channel from being shown in user stat pages.  Type `;stats hide view/list` to view a
        list of the current channels being hidden."""
        try:
            config = self.bot.stats[str(ctx.guild.id)]['hidden']
        except KeyError:
            return
        if not flag:
            channel = str(ctx.channel.id)
            if channel in config:
                config.remove(channel)
                await hf.safe_send(ctx,
                                   f"Removed {ctx.channel.mention} from the list of hidden channels.  It will now "
                                   f"be shown when someone calls their stats page.")
            else:
                config.append(channel)
                await hf.safe_send(ctx, f"Hid {ctx.channel.mention}.  "
                                        f"When someone calls their stats page, it will not be shown.")
        elif flag in ['list', 'view'] and config:
            msg = 'List of channels currently hidden:\n'
            for channel_id in config:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    config.remove(channel_id)
                    continue
                msg += f"{channel.mention} ({channel.id})\n"
            await hf.safe_send(ctx, msg)
        else:
            if re.findall(r"^<#\d{17,22}>$", flag):
                flag = flag[2:-1]
            channel = self.bot.get_channel(int(flag))
            if channel:
                if str(channel.id) in config:
                    config.remove(str(channel.id))
                    await hf.safe_send(ctx,
                                       f"Removed {channel.mention} from the list of hidden channels. It will now "
                                       f"be shown when someone calls their stats page.")
                else:
                    config.append(str(channel.id))
                    await hf.safe_send(ctx,
                                       f"Hid {channel.mention}. When someone calls their stats page, "
                                       f"it will not be shown.")


async def setup(bot):
    await bot.add_cog(Stats(bot))
