import os
import json
import urllib

from discord.ext import commands

from meowth import utils
from meowth import checks

class GymMatching:
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

    def gym_match(self, gym_name, gyms):
        return utils.get_match(list(gyms.keys()), gym_name)

    @commands.group(case_insensitive=True, invoke_without_command=True, aliases=['gymmatching', 'gm'])
    async def gymmatch(ctx):
        if ctx.invoked_subcommand == None:
            raise commands.BadArgument()
            return
        
    @gymmatch.command(name='test')
    async def gym_match_test(self, ctx, gym_name):
        gyms = self.get_gyms(ctx.guild.id)
        if not gyms:
            await ctx.send('Gym matching has not been set up for this server.')
            return
        match, score = self.gym_match(gym_name, gyms)
        if match:
            gym_info = gyms[match]
            coords = gym_info['coordinates']
            notes = gym_info.get('notes', 'No notes for this gym.')
            gym_info_str = (f"**Coordinates:** {coords}\n"
                            f"**Notes:** {notes}")
            await ctx.send(f"Successful match with `{match}` "
                           f"with a score of `{score}`\n{gym_info_str}")
        else:
            await ctx.send("No match found.")            
    
    @gymmatch.command(name='import', aliases=['update'])
    async def importgyms(self, ctx):
        attachment = ctx.message.attachments
        if not attachment:
            await ctx.send('No attachment.')
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
