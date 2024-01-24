import logging
import typing
import disnake
from disnake.ext import plugins
import aiohttp  
import config
from O365 import Account, FileSystemTokenBackend

from lib.db.db import guild_config

plugin = plugins.Plugin(name="dev", slash_command_attrs={"guild_ids": [1179264564374798406], "default_member_permissions": 32})

scopes = ["mailbox", "basic"]
credentials = (config.CLIENT_ID, config.SECRET_ID)
token_backend = FileSystemTokenBackend(token_filename="o365_token.txt")
account = Account(credentials, scopes=scopes, token_backend=token_backend)


@plugin.slash_command(name="key")
async def gen_key(inter: disnake.ApplicationCommandInteraction, member: disnake.Member, expiry: typing.Literal["30", "999999"]):
    await inter.response.defer(with_message=True, ephemeral=True)
    if member is None:
        return await inter.response.send_message("Member not found.", ephemeral=True)
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"https://keyauth.win/api/seller/?sellerkey={config.KEYAUTH}&type=add&format=JSON&expiry={expiry}&mask=***-***-***&level=1&amount=1&owner=SellerAPI&character=1&note=devgen", headers = {"accept": "application/json"}) as resp:
            data = await resp.json()
            if data["success"]:
                key = data["key"]
                await session.close()
    embed = disnake.Embed(title="Key Generated", description=f"Key: {key}\n\n Use /redeem to redeem your license.", color=disnake.Color.green())
    await member.send(embed=embed)
    await inter.edit_original_message(f"Generated key: {key}")

@plugin.slash_command(name="email_auth", default_member_permissions=disnake.Permissions(administrator=True))
async def email_auth(inter: disnake.ApplicationCommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)
    if not account.is_authenticated:
        await inter.edit_original_message("Please wait while we authenticate....")
        url = account.authenticate()
        embed = disnake.Embed(title="Authenticate", description=f"Please click [here]({url}) to authenticate your account!", color=disnake.Color.green())
        await inter.edit_original_message(embed=embed)
        account.authenticate()
        await inter.edit_original_message("Authenticated!")
    else:
        await inter.edit_original_message("Already authenticated!")  

@plugin.listener()
async def on_slash_command_completion(inter: disnake.ApplicationCommandInteraction):
    try:
        channel1 = await plugin.bot.fetch_channel(1194566951662522389)
        embed = disnake.Embed(title="Slash Command Used", color=0x00FF00)
        embed.add_field(name="User", value=f"{inter.author} ({inter.author.id})")
        embed.add_field(name="Channel", value=f"{inter.channel} ({inter.channel.id})")
        embed.add_field(name="Command", value=f"{inter.application_command.qualified_name}")
        if inter.filled_options:
            embed.add_field(name="Options", value="\n".join([f"**{k.capitalize()}**: `{v}`" for k, v in inter.filled_options.items()]), inline=False)
        await channel1.send(embed=embed)
    except Exception as e:
        logging.exception(e)

setup, teardown = plugin.create_extension_handlers()