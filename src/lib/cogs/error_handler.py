from __future__ import annotations

import functools
import logging
import re
import traceback
import typing

import disnake
from disnake.ext import commands
from disnake.ext import plugins


if typing.TYPE_CHECKING:
    AnyContext = typing.Union[commands.Context, disnake.Interaction]
    AnyChannel = typing.Union[disnake.TextChannel,
                              disnake.DMChannel, disnake.GroupChannel]

logger = logging.getLogger()


ERROR_COLOUR = disnake.Colour.red()

plugin = plugins.Plugin()


#@plugin.listener("on_command_error")
#@plugin.listener("on_slash_command_error")
#@plugin.listener("on_message_command_error")
async def on_any_command_error(ctx: AnyContext, error: Exception) -> None:
    """Handle all errors with one mega error handler."""
    # add the support button
    channel = await plugin.bot.fetch_channel(1179264566392270895)
    components = disnake.ui.MessageActionRow()
    components.add_button(
        style=disnake.ButtonStyle.url, label="Support Server", url="https://discord.gg/cache"
    )

    embed = disnake.Embed(
    description="An error has occured and has been reported to the developers. Please try again later or feel free to join the support server for help.",
    colour=ERROR_COLOUR,
    )

    error = getattr(error, "original", error)

    if isinstance(error, commands.CommandOnCooldown):
        embed = disnake.Embed(
            description=f"Please wait {error.retry_after:.2f} seconds before using this command again.",
            colour=ERROR_COLOUR,
        )
        return await ctx.send(embed=embed, components=components)


    elif isinstance(error, commands.CheckFailure):
        embed = disnake.Embed(
            description="Access Denied. Join @ discord.gg/cache to purchase a key for access.",
            colour=ERROR_COLOUR,
        )
        return await ctx.send(embed=embed, components=components)

    elif isinstance(error, commands.MissingPermissions):
        embed = disnake.Embed(
            description=f"You are missing permissions.\n`{error.missing_permissions}`",
            colour=ERROR_COLOUR,
        )
        return await ctx.send(embed=embed, components=components)
    
    elif isinstance(error, disnake.HTTPException):
        if error.code == 10014:
            embed = disnake.Embed(
                description="Unable to find this emoji, please make sure the bot has access to this emoji. If it's not in your server you can use /emoji to add it.",
                colour=ERROR_COLOUR,
            )
            return await ctx.send(embed=embed, components=components)
    
        elif error.code == 50001:
            embed = disnake.Embed(
                description="I am missing required access to run this command. Please make sure I have the `send_messages` and `view_channel` permissions to this channel.",
                colour=ERROR_COLOUR,
            )
            return await ctx.send(embed=embed, components=components)

        elif error.code == 50013:
            embed = disnake.Embed(
                description="I am missing required access to run this command. Please make sure I have the `send_messages` and `view_channel` permissions to this channel.",
                colour=ERROR_COLOUR,
            )
            return await ctx.send(embed=embed, components=components)

    elif isinstance(error, commands.MessageNotFound):
        embed = disnake.Embed(
            description="Unable to find this message, please make sure the bot has access to this message and channel and that the message still exists.",
            colour=ERROR_COLOUR,
        )
        return await ctx.send(embed=embed, components=components)

    try:
        await ctx.send(embed=embed, components=components)
        embed.title = f"Server ID: {ctx.guild.id}"
        embed.add_field(name="Command", value=f"`{ctx.application_command.name}`")
        embed.add_field(name="User", value=f"{ctx.author}")
        embed.add_field(name="Guild", value=f"{ctx.guild}")
        embed.description = f"`{error}`"
        await channel.send(embed=embed)

    except Exception:
        await ctx.edit_original_response(embed=embed, components=components)
        embed.title = f"Server ID: {ctx.guild.id}"
        embed.add_field(name="Command", value=f"`{ctx.application_command.name}`")
        embed.add_field(name="User", value=f"{ctx.author}")
        embed.add_field(name="Guild", value=f"{ctx.guild}")
        embed.description = f"`{error}`"
        await channel.send(embed=embed)

setup, teardown = plugin.create_extension_handlers()
