from subprocess import Popen, PIPE, STDOUT
from pathlib import Path

from discord.ext import commands
from meowth import checks

class DevTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def __local_check(self, ctx):
        return checks.is_dev_check(ctx)

    @commands.group()
    async def git(self, ctx):
        ctx.git_path = Path(__file__).parent.parent.parent
        ctx.git_cmd = ['git']

    @git.command(name='status')
    async def gitstatus(self, ctx):
        ctx.git_cmd.append('status')
        p = Popen(ctx.git_cmd, stdout=PIPE, stderr=STDOUT, cwd=ctx.git_path)
        await ctx.codeblock(p.stdout.read().decode("utf-8"), syntax="")

    @git.command(name='pull')
    async def gitpull(self, ctx):
        ctx.git_cmd.append('pull')
        p = Popen(ctx.git_cmd, stdout=PIPE, stderr=STDOUT, cwd=ctx.git_path)
        await ctx.codeblock(p.stdout.read().decode("utf-8"), syntax="")

    @git.command(name='diff')
    async def gitdiff(self, ctx):
        ctx.git_cmd.append('diff')
        p = Popen(ctx.git_cmd, stdout=PIPE, stderr=STDOUT, cwd=ctx.git_path)
        await ctx.codeblock(p.stdout.read().decode("utf-8"), syntax="")

    @git.command(name='reset')
    async def gitreset(self, ctx):
        ctx.git_cmd.append('reset')
        ctx.git_cmd.append('--hard')
        p = Popen(ctx.git_cmd, stdout=PIPE, stderr=STDOUT, cwd=ctx.git_path)
        await ctx.codeblock(p.stdout.read().decode("utf-8"), syntax="")

def setup(bot):
    bot.add_cog(DevTools(bot))
