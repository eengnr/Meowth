import asyncio
import functools

import discord
from discord.ext import commands

from meowth import utils, checks

from meowth.exts import pokemon


class Trade(commands.Cog):

    icon_url = ("https://raw.githubusercontent.com/FoglyOgly/Meowth/"
                "discordpy-v1/images/misc/trade_icon_small.png")

    __slots__ = [
        'bot', '_data', 'lister_id', 'listing_id', 'report_channel_id',
        'guild_id', 'offers']

    def __init__(self, bot, lister_id, message_id, channel_id, guild_id,
                 wanted_pokemon, offered_pokemon):
        self.bot = bot
        trade_dict = bot.guild_dict[guild_id].setdefault('trade_dict', {})
        trade_channel_data = trade_dict.setdefault(channel_id, {})
        trade_channel_data[message_id] = {
            'lister_id'         : lister_id,
            'report_channel_id' : channel_id,
            'guild_id'          : guild_id,
            'wanted_pokemon'    : [str(want) for want in wanted_pokemon],
            'offered_pokemon'   : str(offered_pokemon),
            'offers'            : {}
        }
        self._data = trade_channel_data[message_id]
        self.lister_id = self._data['lister_id']
        self.listing_id = message_id
        self.report_channel_id = self._data['report_channel_id']
        self.guild_id = self._data['guild_id']
        self.offers = self._data['offers']

    async def on_raw_reaction_add(self, payload):

        emoji = payload.emoji.name

        # ignore if not relevant to this trade object
        if payload.message_id != self.listing_id:
            return

        emoji_check = [
            '\u20e3' in emoji, # keycap 1-9
            emoji == '\u23f9' # stop button
        ]

        if not any(emoji_check):
            return

        if payload.user_id != self.lister_id and payload.user_id != self.bot.user.id and '\u20e3' in emoji:
            wanted_pokemon = await self.wanted_pokemon()
            i = int(emoji[0])
            offer = wanted_pokemon[i-1]
            await self.make_offer(payload.user_id, offer)

        elif payload.user_id == self.lister_id and emoji == '\u23f9':
            await self.cancel_trade()

    @property
    def guild(self):
        return self.bot.get_guild(self.guild_id)

    @property
    def listing_channel(self):
        return self.guild.get_channel(self.report_channel_id)

    @property
    def lister(self):
        return self.guild.get_member(self.lister_id)

    @staticmethod
    def make_trade_embed(lister, wanted_pokemon, offered_pokemon):
        """Returns a formatted embed message with trade details."""

        wants = [
            f'{i+1}\u20e3: {pkmn}' for i, pkmn in enumerate(wanted_pokemon)
        ]

        return utils.make_embed(
            title="Pokémon-Tausch - {}".format(lister.display_name),
            msg_colour=0x63b2f7,
            icon=Trade.icon_url,
            fields={
                "Möchte":'\n'.join(wants),
                "Bietet": str(offered_pokemon)
                },
            inline=True,
            footer=lister.display_name,
            footer_icon=lister.avatar_url_as(format='png', size=256),
            thumbnail=offered_pokemon.img_url
        )

    @staticmethod
    def make_offer_embed(trader, listed_pokemon, offer):
        return utils.make_embed(
            title="Pokémon-Tauschangebot - {}".format(trader.display_name),
            msg_colour=0x63b2f7,
            icon=Trade.icon_url,
            fields={
                "Dein Angebot": str(listed_pokemon),
                "Gegenangebot": str(offer)
                },
            inline=True,
            footer=trader.display_name,
            footer_icon=trader.avatar_url_as(format='png', size=256),
            thumbnail=offer.img_url
        )

    @classmethod
    async def create_trade(cls, ctx, wanted_pokemon, offered_pokemon):
        """Creates a trade object and sends trade details in channel"""

        trade_embed = cls.make_trade_embed(
            ctx.author, wanted_pokemon, offered_pokemon)

        role = offered_pokemon.role(ctx.guild)
        if role:
            rolestr = role.mention + " - "
        else:
            rolestr = ""

        offer_str = ("{role}Miauz! {lister} bietet ein {pkmn} zum Tausch an!"
                     "").format(role=rolestr, lister=ctx.author.display_name,
                                pkmn=offered_pokemon)

        instructions = "Reagiere auf diese Nachricht um ein Angebot zu machen!"
        cancel_inst = ("{lister} kann den Tausch mit :stop_button: abbrechen."
                       "").format(lister=ctx.author.display_name)

        trade_msg = await ctx.send(
            f"{offer_str}\n\n{instructions}\n\n{cancel_inst}",
            embed=trade_embed)

        for i in range(len(wanted_pokemon)):
            await trade_msg.add_reaction(f'{i+1}\u20e3')
        await trade_msg.add_reaction('\u23f9')

        trade = cls(
            ctx.bot, ctx.author.id, trade_msg.id, ctx.channel.id, ctx.guild.id,
            wanted_pokemon, offered_pokemon
        )

        ctx.bot.add_listener(trade.on_raw_reaction_add)

        return trade

    @classmethod
    def from_data(cls, bot, message_id, data):
        trade = cls(
            bot, data['lister_id'], message_id, data['report_channel_id'],
            data['guild_id'], data['wanted_pokemon'], data['offered_pokemon']
        )

        bot.add_listener(trade.on_raw_reaction_add)

        return trade

    async def get_listmsg(self):
        return await self.listing_channel.get_message(self.listing_id)

    async def offered_pokemon(self):
        listingmsg = await self.get_listmsg()
        ctx = await self.bot.get_context(listingmsg)
        return pokemon.Pokemon.get_pokemon(ctx, self._data['offered_pokemon'])

    async def wanted_pokemon(self):
        listingmsg = await self.get_listmsg()
        ctx = await self.bot.get_context(listingmsg)
        return [pokemon.Pokemon.get_pokemon(ctx, want) for want in self._data['wanted_pokemon']]

    async def make_offer(self, trader_id, pkmn):
        offered_pokemon = await self.offered_pokemon()
        self.offers[trader_id] = str(pkmn)
        trader = self.guild.get_member(trader_id)
        offer_embed = self.make_offer_embed(trader, offered_pokemon, pkmn)

        offermsg = await self.lister.send(
            ("Miauz! {} will ein {} mit dir gegen dein {} tauschen! "
             "Reagiere mit :white_check_mark: um das Angebot zu akzeptieren oder "
             ":negative_squared_cross_mark: um es abzulehnen!").format(
                 trader.display_name, pkmn, offered_pokemon),
            embed=offer_embed)

        reaction, __ = await utils.ask(self.bot, offermsg, timeout=None)

        if reaction.emoji == '\u2705':
            await self.accept_offer(trader_id)

        elif reaction.emoji == '\u274e':
            await self.reject_offer(trader_id)
            await offermsg.delete()

    async def accept_offer(self, offer_id):
        offer = self.offers[offer_id]
        trader = self.guild.get_member(offer_id)
        lister = self.lister
        listingmsg = await self.get_listmsg()

        ctx = await self.bot.get_context(listingmsg)
        offer = pokemon.Pokemon.get_pokemon(ctx, offer)
        offered_pokemon = await self.offered_pokemon()

        acceptedmsg = (
            "Miauz! {} hat zugestimmt, ein {} gegen das {} von {} zu tauschen\n\n"
            "Bitte schreibe eine PN um den Tausch zu koordinieren! "
            "Reagiere mit :ballot_box_with_check:, wenn der Tauch stattgefunden hat!"
            "Um den Tausch abzubrechen, reagiere mit"
            ":stop_button:").format(
                self.lister.display_name,
                offered_pokemon,
                offer,
                trader.display_name)

        special_check = [
            offered_pokemon.shiny,
            offered_pokemon.legendary,
            offer.shiny,
            offer.legendary
        ]

        if any(special_check):
            acceptedmsg += (
                "\n\nDas ist ein Spezialtausch! Diese können nur "
                "einmal am Tag durchgeführt werden und bis zu 1 Million "
                "Sternenstaub! Wenn ihr euer Freunschaftslevel vor dem Tauschen erhöht "
                "wird der benötigte Sternenstaub verrringert!")

        tradermsg = await trader.send(acceptedmsg)
        listermsg = await lister.send(acceptedmsg)

        await tradermsg.add_reaction('\u2611')
        await tradermsg.add_reaction('\u23f9')
        await listermsg.add_reaction('\u2611')
        await listermsg.add_reaction('\u23f9')

        for offerid in self.offers.keys():
            if offerid != offer_id:
                reject = self.guild.get_member(offerid)
                try:
                    await reject.send((
                        "Miauz... {} hat ein anderes Angebot für das {} bekommen."
                        "").format(self.lister.display_name, offered_pokemon))
                except discord.HTTPException:
                    pass



        await listingmsg.edit(
            content="Miauz! {} hat ein Angebot angenommen!".format(
                self.lister.display_name),
            )

        await listingmsg.clear_reactions()

        trader_confirms = False
        lister_confirms = False

        def check(r, u):
            user_check = [u == trader, u == lister]
            msg_check = [r.message.id == tradermsg.id, r.message.id == listermsg.id]
            emoji_check = [r.emoji == '\u2611', r.emoji == '\u23f9']
            if not any(msg_check) or not any(user_check) or not any(emoji_check):
                return False
            else:
                return True

        while True:
            reaction, user = await self.bot.wait_for('reaction_add', check=check)
            if user.id == trader.id:
                if reaction.emoji == '\u2611':
                    trader_confirms = True
                elif reaction.emoji == '\u23f9':
                    await tradermsg.delete()
                    return await self.withdraw_offer(trader.id)
            elif user.id == lister.id:
                if reaction.emoji == '\u2611':
                    lister_confirms = True
                elif reaction.emoji == '\u23f9':
                    await listermsg.delete()
                    return await self.reject_offer(trader.id)
            if trader_confirms and lister_confirms:
                await listermsg.delete()
                await tradermsg.delete()
                return await self.confirm_trade()
            else:
                continue

        # update the listing message if it still exists
        # dm others who offered saying the trade was completed
        # dm the member with the successful offer with details for trade
        # maybe ask the lister to provide a friend code optionally before dm

    async def withdraw_offer(self, offer_id):
        offered_pokemon = await self.offered_pokemon()
        wanted_pokemon = await self.wanted_pokemon()
        listingmsg = await self.get_listmsg()
        trader = self.guild.get_member(offer_id)
        await self.lister.send(
            "Miauz... {} hat das Angebot für das {} zurückgezogen.".format(
                trader.display_name, self.offers[offer_id]))

        offer_str = "Miauz! {lister} bietet ein {pkmn} zum Tausch an!".format(
            lister=self.lister.display_name, pkmn=offered_pokemon)

        instructions = "Reagiere auf diese Nachricht um ein Angebot zu machen!"
        cancel_inst = "{lister} kann den Tausch mit :stop_button: abbrechen.".format(
            lister=self.lister.display_name)

        await listingmsg.edit(
            content=f"{offer_str}\n\n{instructions}\n\n{cancel_inst}",
            )

        for i in range(len(wanted_pokemon)):
            await listingmsg.add_reaction(f'{i+1}\u20e3')

        await listingmsg.add_reaction('\u23f9')
        del self.offers[offer_id]

    async def reject_offer(self, offer_id):
        listingmsg = await self.get_listmsg()
        trader = self.guild.get_member(offer_id)
        offered_pokemon = await self.offered_pokemon()
        wanted_pokemon = await self.wanted_pokemon()

        await trader.send(
            "Miauz... {} hat dein Angebot für das {} abgelehnt.".format(
                self.lister.display_name, offered_pokemon))

        offer_str = "Miauz! {lister} bietet ein {pkmn} zum Tausch an!".format(
            lister=self.lister.display_name, pkmn=offered_pokemon)

        instructions = "Reagiere auf diese Nachricht um ein Angebot zu machen!"
        cancel_inst = "{lister} kann den Tausch mit :stop_button: abbrechen.".format(
            lister=self.lister.display_name)

        await listingmsg.edit(
            content=f"{offer_str}\n\n{instructions}\n\n{cancel_inst}",
            )

        for i in range(len(wanted_pokemon)):
            await listingmsg.add_reaction(f'{i+1}\u20e3')

        await listingmsg.add_reaction('\u23f9')

        del self.offers[offer_id]

    async def cancel_trade(self):
        offered_pokemon = await self.offered_pokemon()
        for offerid in self.offers:
            reject = self.guild.get_member(offerid)

            await reject.send(
                "Miauz... {} hat das Tauschangebot für das {} abgebrochen.".format(
                    self.lister.display_name, offered_pokemon))

        await self.close_trade()

        # update the listing message if it still exists
        # dm those who offered saying the trade was cancelled

    async def confirm_trade(self):
        listingmsg = await self.get_listmsg()
        await listingmsg.edit(content='Meowth! This trade has been completed!', embed=None)
        await asyncio.sleep(5)
        await self.close_trade()

    async def close_trade(self):
        listingmsg = await self.get_listmsg()
        await listingmsg.delete()
        self.bot.remove_listener(self.on_raw_reaction_add)
        try:
            guild_trades = self.bot.guild_dict[self.guild_id]
            del guild_trades[self.report_channel_id][self.listing_id]
            await listingmsg.delete()
        except (KeyError, discord.HTTPException):
            pass

class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        for guild_id in self.bot.guild_dict:
            trade_dict = self.bot.guild_dict[guild_id].setdefault('trade_dict', {})
            for channel_id in trade_dict:
                trade_channel_data = trade_dict[channel_id]
                for message_id in trade_channel_data:
                    Trade.from_data(
                        self.bot, message_id, trade_channel_data[message_id])

    async def on_message(self, message):
        ctx = await self.bot.get_context(message)
        if not ctx.guild:
            return
        if checks.check_tradereport(ctx) and message.author != ctx.guild.me:
            await asyncio.sleep(1)
            try:
                await message.delete()
            except discord.HTTPException:
                pass

    @commands.command()
    @checks.allowtrade()
    async def trade(self, ctx, *, offer: pokemon.Pokemon):
        """Create a trade listing."""

        want_ask = await ctx.send(
            f"{ctx.author.display_name}, welches Pokémon würdest du im Tausch gegen "
            f"{str(offer)} annehmen?")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            want_reply = await ctx.bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await want_ask.delete()
            return

        wants = want_reply.content.lower().split(',')

        await want_ask.delete()
        await want_reply.delete()

        pkmn_convert = functools.partial(pokemon.Pokemon.get_pokemon, ctx)

        wants = map(str.strip, wants)
        wants = map(pkmn_convert, wants)
        wants = [str(want) for want in wants]

        await Trade.create_trade(ctx, wants, offer)


def setup(bot):
    bot.add_cog(Trading(bot))
