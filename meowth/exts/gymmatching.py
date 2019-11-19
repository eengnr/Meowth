import os
import json
import urllib

from discord.ext import commands

from meowth import utils
from meowth import checks

class GymMatching(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gym_data = self.init_json()

    def __local_check(self, ctx):
        return checks.is_owner_check(ctx)

    def init_json(self):
        with open(os.path.join('data', 'gym_data.json')) as fd:
            return json.load(fd)

    def get_gyms(self, guild_id):
        return self.gym_data.get(str(guild_id))

    def gym_match(self, gym_name, gyms, channel):
        match, score = utils.get_match(list(gyms.keys()), gym_name)
        if match:
            # check if area is set for gym, necessary for gyms with same name in different areas
            area = gyms[match].get('area', channel.name)
            if area == channel.name:
                return (match, score)
            else:
                gyms_less = gyms.copy()
                del gyms_less[match]
                match, score = self.gym_match(gym_name, gyms_less, channel)
                gyms_less.clear()
                return (match, score)
        else:
            return (None, None)

    @commands.group(case_insensitive=True, invoke_without_command=True, aliases=['gymmatching', 'gm'])
    async def gymmatch(ctx):
        if ctx.invoked_subcommand == None:
            raise commands.BadArgument()
            return

    @gymmatch.command(name='test')
    async def gym_match_test(self, ctx, gym_name):
        gyms = self.get_gyms(ctx.guild.id)
        if not gyms:
            await ctx.send('Gymmatching wurde für diesen Server nicht aktiviert.')
            return
        match, score = self.gym_match(gym_name, gyms, ctx.message.channel)
        if match:
            gym_info = gyms[match]
            coords = gym_info['coordinates']
            notes = gym_info.get('notes', 'Keine Infos für diese Arena.')
            original = gym_info.get('original', '')
            gym_info_str = (f"**Koordinaten:** {coords}\n"
                            f"**Infos:** {notes}")
            if original != '':
                gym_info_str += (f"\n**Originalname:** {original}")
            await ctx.send(f"Übereinstimmung mit `{match}` "
                           f"mit einem Wert von `{score}`\n{gym_info_str}")
        else:
            await ctx.send("Keine Übereinstimmung gefunden.")

    @gymmatch.command(name='import', aliases=['update'])
    async def importgyms(self, ctx):
        attachment = ctx.message.attachments
        if not attachment:
            await ctx.send('Kein Anhang.')
        else:
            try:
                newgymsurl = attachment[0].url
                req = urllib.request.Request(newgymsurl)
                req.add_header('User-Agent', 'Mozilla/5.0')
                self.gym_data = json.load(urllib.request.urlopen(req))
                await ctx.message.add_reaction('\u2705')
            except:
                await ctx.message.add_reaction('❌')

    @gymmatch.command(name='save', aliases=['commit'])
    async def savegyms(self, ctx):
        with open(os.path.join('data', 'gym_data.json'), 'w') as fd:
            json.dump(self.gym_data, fd, indent=4)
        await ctx.message.add_reaction('\u2705')

def setup(bot):
    bot.add_cog(GymMatching(bot))
