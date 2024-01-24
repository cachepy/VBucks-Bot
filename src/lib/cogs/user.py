import disnake
from disnake.ext import plugins
import aiohttp
import config

from lib.db.db import keyauth

plugin = plugins.Plugin(name="user")

@plugin.slash_command(name="redeem")
async def redeem_key(inter: disnake.ApplicationCommandInteraction, key: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"https://keyauth.win/api/seller/?sellerkey={config.KEYAUTH}&type=activate&user={inter.author.name}&key={key}&pass={inter.author.name}", headers = {"accept": "application/json"}) as resp:
            data = await resp.json()
            if resp.status == 200:
                if data["success"]:
                    await session.close()
                    await keyauth.create(user_id=inter.author.id, key=key)
                    return await inter.response.send_message("Key redeemed.", ephemeral=True)
            else:
                await session.close()
                return await inter.response.send_message("Invalid key.", ephemeral=True)

@plugin.slash_command(name="rename")
async def rename(inter: disnake.ApplicationCommandInteraction, name: str):
    staff_role = inter.guild.get_role(1147385196174385242)
    if any(staff_role.id == role.id for role in inter.author.roles):
        await inter.channel.edit(name=name)
    await inter.send("Renamed channel.", ephemeral=True)

setup, teardown = plugin.create_extension_handlers()