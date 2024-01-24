import asyncio
import datetime
import io
import logging
import os
import random
import aiohttp
import disnake
from lib.db.db import addons, banks, guild_config, categories, keyauth, orders, prices
from datetime import datetime, timezone
from disnake.ext import plugins
import typing as t
import chat_exporter
import config
from cryptography.fernet import Fernet
from playwright.async_api import async_playwright, ProxySettings
from O365 import Account, FileSystemTokenBackend

now = datetime.now(timezone.utc)
plugin = plugins.Plugin(slash_command_attrs={"default_member_permissions": disnake.Permissions(administrator=True)})

scopes = ["mailbox", "basic"]
credentials = (config.CLIENT_ID, config.SECRET_ID)
token_backend = FileSystemTokenBackend(token_filename="o365_token.txt")
account = Account(credentials, scopes=scopes, token_backend=token_backend)

tzinfo = datetime.now().astimezone().tzinfo

year_dicts = {
    24: 2,
    25: 3,
    26: 4,
    27: 5,
    28: 6,
    29: 7,
    30: 8,
    31: 9,
    32: 10,
    33: 11,
    34: 12,
    35: 13,
    36: 14,
    37: 15,
    38: 16,
    39: 17,
    40: 18,
    41: 19,
    42: 20,
}

urls = {
    "1000": "https://www.xbox.com/es-AR/games/store/fortnite-1000-v-bucks/C0F5HT9NV86P/0X3J",
    "2800": "https://www.xbox.com/es-AR/games/store/fortnite-2800-v-bucks/C4BPBTQG5C1B/0X3J",
    "5000": "https://www.xbox.com/es-AR/games/store/fortnite-5000-v-bucks/C20FM0B4Q9KC/0X3J",
    "13500": "https://www.xbox.com/es-AR/games/store/fortnite-13500-monedas-v/BWD299HXCXQK/0X3J",
}


vbucks = {
    "17": 13500,
    "25": 18500,
    "30": 27000,
    "38": 32000,
    "47": 40500,
    "52": 45500,
    "59": 54000,
    "64": 59000,
    "71": 67500,
    "77": 72500,
    "83": 81000,
    "88": 86000,
    "96": 94500,
    "101": 99500,
    "110": 108000,
}

@plugin.slash_command_check
async def perm_check(inter: disnake.ApplicationCommandInteraction):
    data = await keyauth.all()
    if any(user.user_id == inter.author.id for user in data) or inter.author.id == 216855686028591104:
        return True

@plugin.slash_command(name="claim", default_member_permissions=disnake.Permissions(administrator=True))
async def claim(inter: disnake.ApplicationCommandInteraction, email: str, password: str):
    data = await addons.get_or_none(user_id=inter.author.id)
    if data is None:
        return await inter.send("You do not have the claimer addon. Please purchase it from discord.gg/cache.", ephemeral=True)
    embed = disnake.Embed(title="Starting claim process...", color=disnake.Color.green())
    await inter.response.send_message(embed=embed)
    msg = await inter.original_message()
    await vbucks_claimer(email=email, password=password, channel_id=msg.channel.id, msg_id=msg.id)



@plugin.listener("on_button_click")
async def on_button_click(inter: disnake.MessageInteraction):
    if "vbucks-auto" in inter.component.custom_id:
        await inter.response.send_modal(
            title="Cashapp",
            custom_id="cashapp",
            components=[
                disnake.ui.TextInput(
                    label="Email",
                    placeholder="Enter the account email",
                    custom_id="email",
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Password",
                    placeholder="Enter the account password",
                    custom_id="password",
                    required=True,
                ),
            ]
        )

        try:
            modal_inter: disnake.ModalInteraction = await plugin.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "cashapp"
                and i.author.id == inter.author.id,
                timeout=300,
            )

        except asyncio.TimeoutError:
            return
        
        code = "".join(str(random.choice(range(0, 9))) for _ in range(4))
        await orders.create(email=modal_inter.text_values["email"], password=modal_inter.text_values["password"], guild_id=inter.guild.id, code=code)

        data = await prices.filter(guild_id=inter.guild.id).all()
        buck_options = []
        for price in data:
            buck_options.append(disnake.SelectOption(label=f"{price.vbucks} V-Bucks - ${price.cost}", value=price.vbucks, emoji="💰"))

        select = disnake.ui.Select(
        custom_id=f"vbucks-auto:{code}",
        options=buck_options,
        placeholder="Choose a ticket option...",
        min_values=1,
        max_values=1,
        )
        embed = disnake.Embed(
            title="V-Bucks",
            description="Choose the amount of V-Bucks you would like to purchase.",
            color=0xFFFFFF,
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/117094711622764545/1170947422436982846/fortnite-v-bucks-logo-5.png"
        )
        
        for option in buck_options:
            embed.add_field(name='Amount', value=option.label, inline=True)

        return await modal_inter.send(embed=embed, components=[select], ephemeral=True)
    
    if "cashapp" in inter.component.custom_id:
        await inter.response.send_modal(
            title="Cashapp",
            custom_id="cashapp",
            components=[
                disnake.ui.TextInput(
                    label="Email",
                    placeholder="Enter the account email",
                    custom_id="email",
                    required=True,
                ),
                disnake.ui.TextInput(
                    label="Password",
                    placeholder="Enter the account password",
                    custom_id="password",
                    required=True,
                ),
            ]
        )

        try:
            modal_inter: disnake.ModalInteraction = await plugin.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "cashapp"
                and i.author.id == inter.author.id,
                timeout=300,
            )

        except asyncio.TimeoutError:
            return
        
        data = await guild_config.get_or_none(id=inter.guild.id)
        amount = inter.component.custom_id.split(":")[1]
        generated_note = "".join(str(random.choice(range(0, 9))) for _ in range(4))
        embed = disnake.Embed(title="Pay with CashApp", description=f"**REQUIRED NOTE:** ```{generated_note}```\n**AMOUNT**: ```${amount}```", color=disnake.Color.green())
        embed.set_image(url=data.cashapp_pic)
        embed.set_footer(text="You must add the note or else the payment will\nnot be verifed! Once payment is complete you\nwill be notified!")
        await modal_inter.send(embed=embed, ephemeral=True)
        await init_cashapp(amount=amount, note=generated_note, acc_email=modal_inter.text_values["email"], acc_password=modal_inter.text_values["password"], vbuck=vbucks[amount], channel_id=inter.channel.id, msg_id=inter.message.id)

    if "claim" in inter.component.custom_id:
        data = await guild_config.filter(id=inter.guild.id).first()
        for role in data.staff_role:
            if any(r.id == role for r in inter.author.roles):
                author = inter.guild.get_member(
                    int(inter.component.custom_id.split(":")[1])
                )
                overwrites = {
                    inter.guild.default_role: disnake.PermissionOverwrite(
                        view_channel=False
                    ),
                    inter.author: disnake.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    ),
                    inter.guild.me: disnake.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    ),
                    author: disnake.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    ),
                }
        await inter.channel.edit(name=inter.author.name, overwrites=overwrites)
        await inter.send(f"{inter.author.mention} has claimed this ticket.")


@plugin.listener("on_dropdown")
async def on_dropdown(inter: disnake.MessageInteraction):
    data = await categories.get_or_none(type=inter.values[0])
    
    buttons = []

    if data is None:
        if inter.component.custom_id == "vbucks":
            channel_name = f"V-Bucks - {vbucks[inter.values[0]]}"
            buttons.append(
                disnake.ui.Button(
                    label="Automated Delivery",
                    style=disnake.ButtonStyle.green,
                    custom_id=f"cashapp:{inter.values[0]}",
                ))
            category = inter.guild.get_channel(1193431048059629621)
        
        elif inter.component.custom_id == "banks":
            category = inter.guild.get_channel(1189039263103320134)

        elif inter.component.custom_id == "credits":
            category = inter.guild.get_channel(1193436862145101917)
        
        elif inter.component.custom_id == "accounts":
            category = inter.guild.get_channel(1193437357362401350)

    if data:
        category = inter.guild.get_channel(data.cat_id)

    if "vbucks-auto" in inter.component.custom_id:
        db_prices = await prices.get_or_none(vbucks=inter.values[0])
        data = await guild_config.get_or_none(id=inter.guild.id)
        code = inter.component.custom_id.split(":")[1]
        await orders.filter(code=code).update(vbucks=db_prices.vbucks, cost=db_prices.cost)
        order = await orders.get_or_none(code=code)
        logging.info(order)
        cards = await banks.get_or_none(guild_id=inter.guild.id, default=True)
        if cards is None:
            return await inter.send("No default card found. Notify staff please.", ephemeral=True)
        embed = disnake.Embed(title="Pay with CashApp", description=f"**REQUIRED NOTE:** ```{code}```\n**AMOUNT**: ```${db_prices.cost}```", color=disnake.Color.green())
        embed.set_image(url=data.cashapp_pic)
        embed.set_footer(text="You must add the note or else the payment will\nnot be verifed! Once payment is complete you\nwill be notified!")
        await inter.response.edit_message(embed=embed, view=None)
        return await init_cashapp(amount=order.cost, note=code, inter=inter, acc_email=order.email, acc_password=order.password, vbucks=str(vbucks[(order.cost)]), card=cards.card_num)
        

    if inter.values[0] == "V-Bucks":
        data = await prices.filter(guild_id=inter.guild.id).all()
        options = []
        for price in data:
            options.append(disnake.SelectOption(label=f"{price.vbucks} V-Bucks - ${price.cost}", value=price.vbucks, emoji="💰"))
        options = [
            disnake.SelectOption(
                label="13,500 V-Bucks - $17.00", value="17", emoji="💰"
            ),
            disnake.SelectOption(
                label="18,500 V-Bucks - $25.00", value="25", emoji="💰"
            ),
            disnake.SelectOption(
                label="27,000 V-Bucks - $30.00", value="30", emoji="💰"
            ),
            disnake.SelectOption(
                label="32,000 V-Bucks - $38.00", value="38", emoji="💰"
            ),
            disnake.SelectOption(
                label="40,500 V-Bucks - $47.00", value="47", emoji="💰"
            ),
            disnake.SelectOption(
                label="45,500 V-Bucks - $52.00", value="52", emoji="💰"
            ),
            disnake.SelectOption(
                label="54,000 V-Bucks - $59.00", value="59", emoji="💰"
            ),
            disnake.SelectOption(
                label="59,000 V-Bucks - $64.00", value="64", emoji="💰"
            ),
            disnake.SelectOption(
                label="67,500 V-Bucks - $71.00", value="71", emoji="💰"
            ),
            disnake.SelectOption(
                label="72,500 V-Bucks - $77.00", value="77", emoji="💰"
            ),
            disnake.SelectOption(
                label="81,000 V-Bucks - $83.00", value="83", emoji="💰"
            ),
            disnake.SelectOption(
                label="86,000 V-Bucks - $88.00", value="88", emoji="💰"
            ),
            disnake.SelectOption(
                label="94,500 V-Bucks - $96.00", value="96", emoji="💰"
            ),
            disnake.SelectOption(
                label="99,500 V-Bucks - $101.00", value="101", emoji="💰"
            ),
            disnake.SelectOption(
                label="108,000 V-Bucks - $110.00", value="110", emoji="💰"
            ),
        ]
        select = disnake.ui.Select(
            custom_id="vbucks",
            options=options,
            placeholder="Choose a ticket option...",
            min_values=1,
            max_values=1,
        )
        embed = disnake.Embed(
            title="V-Bucks",
            description="Choose the amount of V-Bucks you would like to purchase.",
            color=0xFFFFFF,
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/117094711622764545/1170947422436982846/fortnite-v-bucks-logo-5.png"
        )
        for option in options:
            embed.add_field(name='Amount', value=option.label, inline=True)
        return await inter.send(embed=embed, components=[select], ephemeral=True)

    elif inter.values[0] == "Banks":
        #  Belo:  Prex:  Mercado Pago: Letsbit 
        options = [
            disnake.SelectOption(
                label="Belo", emoji="🏦"
            ),
            disnake.SelectOption(
                label="Prex", emoji="🏦"
            ),
            disnake.SelectOption(
                label="Mercado Pago", emoji="🏦"
            ),
            disnake.SelectOption(
                label="Letsbit", emoji="🏦"
            ),
        ]
        select = disnake.ui.Select(
            custom_id="banks",
            options=options,
            placeholder="Choose a ticket option...",
            min_values=1,
            max_values=1,
        )
        embed = disnake.Embed(
            title="Banks",
            description="Choose the bank you would like to purchase.",
            color=0xFFFFFF,
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/117094711622764545/1170947278148743260/unnamed.png"
        )
        for option in options:
            embed.add_field(name='Bank', value=option.value, inline=True)
        return await inter.send(embed=embed, components=[select], ephemeral=True)
    
    buttons.append(
            disnake.ui.Button(
            label="Close",
            style=disnake.ButtonStyle.danger,
            custom_id=f"close:{inter.author.id}",
        ),
    )

@plugin.slash_command(name="add_bank")
async def add_bank(inter: disnake.ApplicationCommandInteraction, card_num: str, cvv: str, exp_month: str, exp_year: str, name: str):
    """Add a bank to the database"""
    await banks.create(card_num=card_num, ccv=cvv, exp_month=exp_month, exp_year=exp_year, name=name, guild_id=inter.guild.id, user_id=inter.author.id)
    await inter.send(f"Bank added to database", ephemeral=True)

@plugin.slash_command(name="set_cashapp_pic", default_member_permissions=disnake.Permissions(administrator=True))
async def set_cashapp_pic(inter: disnake.ApplicationCommandInteraction, url: str):
    """Set the cashapp pic"""
    await guild_config.filter(id=inter.guild.id).update(cashapp_pic=url)
    await inter.send(f"Cashapp pic set to {url}")

@plugin.slash_command(name="clear_cards")
async def clear_cards(inter: disnake.ApplicationCommandInteraction):
    """Clear all cards
    """
    data = await banks.filter(user_id=inter.author.id).all()
    for card in data:
        await banks.filter(card_num=card.card_num).delete()
    await inter.send(f"Cleard all cards for {inter.author.mention}")

@plugin.slash_command(name="give_vbucks")
async def give_vbucks(inter: disnake.ApplicationCommandInteraction, email: str, password: str, vbucks: t.Literal["1000", "2800", "5000", "13500"], card: str, amount: int = 1):
    """Give a member vbucks
    
    Parameters
    ----------
    email: Account email
    password: Account password
    vbucks: Amount of vbucks
    card: Card to use
    amount: How many times to purchase these vbucks
    """
    embed = disnake.Embed(title="VBucks Automated Delivery!", description=f"Starting account delivery...", color=disnake.Color.green())
    await inter.send(embed=embed)
    msg: disnake.Message = await inter.original_message()
    await vbucks_auto(acc_email=email, acc_password=password, msg_id=msg.id, channel_id=inter.channel.id, vbucks=vbucks, card_num=card, amount=amount)  

@plugin.slash_command(name="set_default")
async def set_default(inter: disnake.ApplicationCommandInteraction, card: str):
    """Set the default ticket type"""
    await banks.filter(card_num=card).update(default=True)
    await inter.send(f"Default card set to {card}")

@plugin.slash_command(name="add_price")
async def add_price(inter: disnake.ApplicationCommandInteraction, vbucks: int, price: int):
    if "," in str(vbucks):
        vbucks = str(vbucks).replace(",", "")
    elif "," in str(price):
        price = str(price).replace(",", "")

    await prices.create(vbucks=vbucks, cost=price, guild_id=inter.guild.id)
    await inter.send(f"Added {vbucks} for {price}")

@plugin.slash_command(name="cashapp_embed")
async def setup_cashapp_embed(inter: disnake.ApplicationCommandInteraction):
    """
    Send Cashapp Integration Embed
    """
    embed = disnake.Embed(title="Automated Cashapp Delivery", description="Click the button below to start the process.\n\n*Note:* Only for orders for 13500. Contact support for other options", color=0xFFFFFF)
    await inter.channel.send(embed=embed, components=[disnake.ui.Button(style=disnake.ButtonStyle.primary, label="Auto Delivery", custom_id="vbucks-auto")])
    await inter.send("sent")

@set_default.autocomplete("card")
@give_vbucks.autocomplete("card")
async def cash_app_auto(inter: disnake.ApplicationCommandInteraction, card: str):
    data = await banks.filter(guild_id=inter.guild.id, user_id=inter.author.id).all()
    cards = []
    for bank_num in data:
        cards.append(bank_num.card_num)
    return cards

class Code_Button(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=600.0)
        self.value: t.Optional[bool] = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @disnake.ui.button(label="Code", style=disnake.ButtonStyle.green)
    async def button_code(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            disnake.ui.Modal(
                title="Code",
                components=[
                    disnake.ui.TextInput(
                        label="Enter Code",
                        custom_id="code",
                        placeholder="Enter code here",
                        required=True,
                    )
                ],
                custom_id="code"
            )
        )

        try:
            modal_inter: disnake.ModalInteraction = await plugin.bot.wait_for(
            "modal_submit",
            check=lambda i: i.custom_id == "code"
            and i.author.id == inter.author.id,
            timeout=600,
        )
        except asyncio.TimeoutError:
            return
        
        for custom_id, value in modal_inter.text_values.items():
            if custom_id == "code":
                self.value = value
        logging.info(self.value)
        await modal_inter.send("Code received. Please wait while we verify..", ephemeral=True)
        self.stop()

class Phone_Button(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=600.0)
        self.value: t.Optional[bool] = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @disnake.ui.button(label="Phone", style=disnake.ButtonStyle.green)
    async def button_code(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            disnake.ui.Modal(
                title="Phone",
                components=[
                    disnake.ui.TextInput(
                        label="Enter Code",
                        custom_id="phone",
                        placeholder="Enter phone # here",
                        required=True,
                    )
                ],
                custom_id="phone"
            )
        )

        try:
            modal_inter: disnake.ModalInteraction = await plugin.bot.wait_for(
            "modal_submit",
            check=lambda i: i.custom_id == "phone"
            and i.author.id == inter.author.id,
            timeout=600,
        )
        except asyncio.TimeoutError:
            return
        
        for custom_id, value in modal_inter.text_values.items():
            if custom_id == "phone":
                self.value = value
        logging.info(self.value)
        await modal_inter.send("Phone # received. Please wait while we verify..", ephemeral=True)
        self.stop()

class Email_Button(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=600.0)
        self.value: t.Optional[bool] = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @disnake.ui.button(label="Email", style=disnake.ButtonStyle.green)
    async def button_code(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            disnake.ui.Modal(
                title="Email",
                components=[
                    disnake.ui.TextInput(
                        label="Enter Email",
                        custom_id="email",
                        placeholder="Enter email here",
                        required=True,
                    )
                ],
                custom_id="email"
            )
        )

        try:
            modal_inter: disnake.ModalInteraction = await plugin.bot.wait_for(
            "modal_submit",
            check=lambda i: i.custom_id == "email"
            and i.author.id == inter.author.id,
            timeout=600,
        )
        except asyncio.TimeoutError:
            return
        
        for custom_id, value in modal_inter.text_values.items():
            if custom_id == "email":
                self.value = value
        logging.info(self.value)
        await modal_inter.send("Email entered. Please wait for code and press code button when received.", ephemeral=True)
        self.stop()     

async def verify_payment(code: str, amount: int):    
    mailbox = account.mailbox()
    query = mailbox.new_query().on_attribute('from').contains('cash@square.com')
    inbox = mailbox.inbox_folder()
    for message in inbox.get_messages(limit=100, query=query):
        message = message.subject.split("for ")[-1]
        amount = message.split("you $")[-1]
        if code.lower() == message.lower() and amount == amount:
            return True
        else:
            continue

async def init_cashapp(amount: str, note: str, inter: disnake.ApplicationCommandInteraction, acc_email: str, acc_password: str, vbucks: t.Literal["1000", "2800", "5000", "13500"], card: str):
    while not await verify_payment(note, int(amount)):
        await asyncio.sleep(5)
    embed = disnake.Embed(title="Payment Successful!", description=f"Payment of ${amount} was successful! Starting account delivery.", color=disnake.Color.green())
    msg: disnake.Message = inter.original_message()
    await vbucks_auto(acc_email=acc_email, acc_password=acc_password, msg_id=msg.id, channel_id=inter.channel.id, vbucks=vbucks, card_num=card)
    await msg.edit(embed=embed) 

async def vbucks_claimer(email: str, password: str, channel_id: str, msg_id: str):
    logging.info("Starting vbucks claimer")
    channel = await plugin.bot.fetch_channel(channel_id)
    msg = await channel.fetch_message(msg_id)
    embed = msg.embeds[0]
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
        "./lib/data",
        headless=False,
        args=[
            f"--disable-extensions-except=lib/extensions/dhdgffkkebhmkfjojejmpbldmpobfkfo/5.0.1_0",
            f"--load-extension=lib/extensions/dhdgffkkebhmkfjojejmpbldmpobfkfo/5.0.1_0",
        ],
    )
    #browser = await playwright.chromium.launch(headless=False)
        page = await context.new_page()
        await asyncio.sleep(1.2)
        await page.goto("https://www.xbox.com/en-US/play/games/fortnite/BT5P2X999VH2", wait_until="load")
        await asyncio.sleep(5)      
        if await page.locator('xpath=//*[@id="gamepass-root"]/div/div/header/div/div[1]/div/div[2]/button[2]/div[2]').is_visible():
            await page.locator('xpath=//*[@id="gamepass-root"]/div/div/header/div/div[1]/div/div[2]/button[2]/div[2]').click()
            logging.info("logging out")
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Tab")
            await page.keyboard.press("Tab")
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)
            await page.keyboard.press("Space")
            await asyncio.sleep(1.2)
            await page.goto('https://www.xbox.com/en-US/play/games/fortnite/BT5P2X999VH2', wait_until="load")
        await page.locator('xpath=//*[@id="gamepass-root"]/div/div/div/div/div/div[2]/div[1]/div[2]/a').click()
        await page.get_by_role("textbox").fill(email)
        await page.get_by_role("button", name="Next").click()
        await asyncio.sleep(1.5)
        await page.get_by_role("textbox").fill(password)
        await page.get_by_role("button", name="Sign in").click()
        await asyncio.sleep(1.0)
        if await page.locator('xpath=//*[@id="idBtn_Back"]').is_visible():
            await page.locator('xpath=//*[@id="idBtn_Back"]').click()
        await page.goto('https://www.xbox.com/en-US/play/launch/fortnite/BT5P2X999VH2', wait_until="load")
        await asyncio.sleep(0.5)
        await page.locator('xpath=//*[@id="gamepass-root"]/div/div/div/div/div/div[2]/div[1]/div[2]/button').click()
        await page.reload(wait_until="load")
        #await asyncio.sleep(500)
        await page.keyboard.press("Space")
        await asyncio.sleep(60)
        if await page.locator('xpath=/html/div[7]').is_visible():
            logging.info("Clicking")
            await page.locator("xpath=/html/div[7]").click()
            await asyncio.sleep(3)
            await page.keyboard.press("Space")
            await asyncio.sleep(3)
            await page.keyboard.press("Space")
            await asyncio.sleep(3)
            await page.keyboard.press("Space")
            await asyncio.sleep(3)
            await page.keyboard.press("Space")
            await asyncio.sleep(3)
            await page.keyboard.press("Space")
        await asyncio.sleep(60)
        await page.screenshot(path=f"{msg.guild.id}screenshot.png")
        await asyncio.sleep(2)
        embed.title = "VBucks successfully claimed!"
        embed.set_image(file=disnake.File(f"{msg.guild.id}screenshot.png"))
        await msg.edit(embed=embed)


async def vbucks_auto(acc_email: str, acc_password: str, msg_id: int, channel_id: int, vbucks: str, card_num, amount: int):
    try:
        logging.info(f"Purchasing {vbucks} vbucks {amount}")
        #cards = await banks.all()
        #for card in cards:
        #    token = card.token
        #    cc = Fernet(token)
        #    _card = (str(cc.decrypt(card.card_num).decode('utf-8')))
        #    if _card == card_num:
        #        data = card
        data = await banks.get_or_none(card_num=card_num)
        channel = await plugin.bot.fetch_channel(channel_id)
        msg = await channel.fetch_message(msg_id)
        embed = msg.embeds[0]
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://account.microsoft.com/billing/payments?lang=en-US&refd=account.microsoft.com", wait_until="load")
        await asyncio.sleep(1.2)
        await page.get_by_role("textbox").fill(acc_email)
        await page.get_by_role("button", name="Next").click()
        await asyncio.sleep(1.5)
        await page.get_by_role("textbox").fill(acc_password)
        await page.get_by_role("button", name="Sign in").click()
        await asyncio.sleep(2.5)
        if await page.locator('xpath=//*[@id="iProofPhone"]').is_visible():
            await page.screenshot(path=f"{msg.guild.id}screenshot.png")
            await asyncio.sleep(2.2)
            embed.description = "Please enter your phone #"
            embed.set_image(url=f"attachment://{msg.guild.id}screenshot.png")
            view = Code_Button()
            view2 = Phone_Button()
            await msg.edit(embed=embed, view=view2)
            await view2.wait()
            logging.info("Received phone #")
            phone = str(view2.value)[:4]
            logging.info("Entering Phone")
            await page.get_by_role("textbox").fill(phone)
            await page.get_by_role("button", name="Send code").click()
            await asyncio.sleep(1.5)
            embed.description = "Please check your phone for a verification code then hit the button below."
            await msg.edit(embed=embed, view=view)
            await view.wait()
            logging.info("Received code")

            await page.get_by_role("textbox").fill(view.value)
            await page.locator('xpath=//*[@id="iVerifyCodeAction"]').click()

        #if await page.locator('xpath=//*[@id="iLandingViewAction"]').is_visible():
        #    await page.locator('xpath=//*[@id="iLandingViewAction"]').click()

        if await page.locator('xpath=//*[@id="iProofLbl0"]').is_visible() and not await page.get_by_role("textbox").is_visible():
            await page.locator('xpath=//*[@id="iProofLbl0"]').click()
            await page.screenshot(path=f"{msg.guild.id}screenshot.png")
            await asyncio.sleep(2.2)
            embed.description = "Please enter your email below"
            view = Code_Button()
            view2 = Email_Button()
            await msg.edit(embed=embed, view=view2)
            await view2.wait()
            logging.info("Received email")
            email = str(view2.value).lower()
            if "@" in email:
                email = email.split("@")[0]
            logging.info("Entering email")
            await page.get_by_role("textbox").fill(email)
            await page.get_by_role("button", name="Send code").click()
            await asyncio.sleep(1.5)
            embed.description = "Please check your email for a verification code then hit the button below."
            await msg.edit(embed=embed, view=view,)
            await view.wait()
            logging.info("Received code")

            await page.get_by_role("textbox").fill(view.value)
            await page.locator('xpath=//*[@id="iVerifyCodeAction"]').click()

        if await page.locator('xpath=//*[@id="iProofEmail"]').is_visible():
            #await page.get_by_role("textbox").fill(acc_email.split("@")[0])
            #await page.get_by_role("button", name="Send code").click()
            #await asyncio.sleep(1.5)
            ##await page.screenshot(path=f"{msg.guild.id}screenshot.png")
            #await asyncio.sleep(1.2)
            ##embed.set_image(file=disnake.File(f"{msg.guild.id}screenshot.png"))
            embed.description = "Please enter your email below"
            await page.screenshot(path=f"{msg.guild.id}screenshot.png")
            await asyncio.sleep(2)
            view = Code_Button()
            view2 = Email_Button()
            await msg.edit(embed=embed, view=view2)
            await view2.wait()
            logging.info("Received email")
            email = str(view2.value).lower()
            if "@" in email:
                email = email.split("@")[0]
            logging.info("Entering email")
            await page.get_by_role("textbox").fill(email)
            await page.get_by_role("button", name="Send code").click()
            await asyncio.sleep(1.5)
            embed.description = "Please check your email/phone for a verification code then hit the button below."
            await msg.edit(embed=embed, view=view)
            await view.wait()
            logging.info("Received code")

            await page.get_by_role("textbox").fill(view.value)
            await page.locator('xpath=//*[@id="iVerifyCodeAction"]').click()
            #await page.screenshot(path=f"{msg.guild.id}screenshot.png")
        #if await page.locator('xpath=//*[@id="idSIButton9"]').is_visible():
        #    await page.locator('xpath=//*[@id="idSIButton9"]').click()
        #    await asyncio.sleep(1.5)
        #    embed.description = "Please check your email for a verification code!"
        #    view = Code_Button()
        #    await msg.edit(embed=embed, view=view)
        #    await view.wait()
        #    while view.value is None:
        #        await asyncio.sleep(30)
#
        #    await page.get_by_role("textbox").fill(view.value)
        #    await page.locator('xpath=//*[@id="iVerifyCodeAction"]').click()
        #    await msg.edit(view=None)
        #if await page.locator('xpath=//*[@id="iProofLbl0"]').is_visible():
        #    await page.locator('xpath=//*[@id="iProofLbl0"]').click()
        #if await page.locator('xpath=//*[@id="iProofEmail"]').is_visible():
        #    await page.get_by_role("textbox").fill(acc_email.split("@")[0])
        #    await page.get_by_role("button", name="Send code").click()
        #    await asyncio.sleep(1.5)
        #    #await page.screenshot(path=f"{msg.guild.id}screenshot.png")
        #    await asyncio.sleep(1.2)
        #    #embed.set_image(file=disnake.File(f"{msg.guild.id}screenshot.png"))
        #    embed.description = "Please check your email for a verification code!"
        #    view = Code_Button()
        #    await msg.edit(embed=embed, view=view)
        #    await view.wait()
        #    while view.value is None:
        #        await asyncio.sleep(30)
#
        #    await page.get_by_role("textbox").fill(view.value)
        #    await page.locator('xpath=//*[@id="iVerifyCodeAction"]').click()
        #    await msg.edit(view=None)
        #    #await page.screenshot(path=f"{msg.guild.id}screenshot.png")
            
        embed.description = "Logged in!"
        #embed.set_image(file=disnake.File(f"{msg.guild.id}screenshot.png"))
        await msg.edit(embed=embed)
        if await page.get_by_role("button", name="Continue").is_visible():
            await page.get_by_role("button", name="Continue").click()
        if await page.locator('xpath=//*[@id="idBtn_Back"]').is_visible():
            await page.locator('xpath=//*[@id="idBtn_Back"]').click()
        await asyncio.sleep(2)
        #await page.locator('Remove card').scroll_into_view_if_needed()
        #while await page.locator('Remove card').first.is_visible():
        #    logging.info("hehe")
        #    await page.get_by_label("Remove card").first.click()
        #    #await page.get_by_role("button", name="Remove").click()
        #    await asyncio.sleep(0.5)
        #    await page.goto("https://account.microsoft.com/billing/payments?lang=en-US&refd=account.microsoft.com", wait_until="load")

        await page.get_by_role("button", include_hidden=True, name="Add a new payment method").click()
        await asyncio.sleep(1.5)
        await page.locator('xpath=//*[@id="market-selector-dropdown-option"]').click()
        await asyncio.sleep(1.5)
        await page.locator('xpath=//*[@id="market-selector-dropdown-list9"]').scroll_into_view_if_needed()
        await asyncio.sleep(1.5)
        await page.locator('xpath=//*[@id="market-selector-dropdown-list9"]/span/span').click()
        await asyncio.sleep(1.5)
        if await page.get_by_role("button", name="Credit card or debit card").is_visible():
            await page.get_by_role("button", name="Credit card or debit card").click()
        await asyncio.sleep(1.5)
        await page.get_by_role("textbox", name="Cardholder Name").fill(data.name)
        await page.get_by_role("textbox", name="Card Number").fill(str(data.card_num))
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.keyboard.type(data.ccv)
        await page.keyboard.press("Tab")
        await page.keyboard.type("111 Main St")
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        await page.keyboard.type("La Plata")
        await page.keyboard.press("Tab")
        await page.keyboard.type("Buenos Aires")
        await page.keyboard.press("Tab")
        await page.keyboard.type("C1200")
        if await page.locator('xpath=//*[@id="expiryMonth"]').is_visible():
            await page.locator('xpath=//*[@id="expiryMonth"]').fill(f'0{str(data.exp_month)}')
            await asyncio.sleep(1.5)
            await page.locator('xpath=//*[@id="expiryYear"]').fill(data.exp_year)
            await asyncio.sleep(0.5)
        else:
            await page.locator('xpath=//*[@id="input_expiryMonth"]').click()
            await page.locator(f'xpath=//*[@id="input_expiryMonth-list{str(data.exp_month)}"]').click()
            await page.locator('xpath=//*[@id="input_expiryYear"]').click()
            await page.locator(f'xpath=//*[@id="input_expiryYear-list{year_dicts[int(data.exp_year)]}"]').click()
        await asyncio.sleep(0.5)
        await page.get_by_role("button", name="Save").click()
        #//*[@id="input_expiryMonth-list6"]
        await asyncio.sleep(7.5)
        embed.description = "Payment method added!"
        #embed.set_image(file=disnake.File(f"{msg.guild.id}screenshot.png"))
        await msg.edit(embed=embed)
        for i in range(amount):
            vbucks = str(vbucks)
            await page.goto(urls[vbucks], wait_until="load")
            await asyncio.sleep(2.5)
            await page.locator('xpath=//*[@id="PageContent"]/div/div[1]/div[1]/div[6]/div/div[1]/button/div[1]').click()
            await asyncio.sleep(5.5)
            #await page.mouse.click(655, 666)
            frame = page.frame(name="purchase-sdk-hosted-iframe")
            if await frame.locator('xpath=//*[@id="first_name"]').is_visible():
                await frame.locator('xpath=//*[@id="first_name"]').fill(data.name)
                await frame.locator('xpath=//*[@id="last_name"]').fill(data.name)
                await frame.locator('xpath=//*[@id="pidlddc-button-saveButton"]').click()
            await asyncio.sleep(1.5)
            frame = page.frame(name="purchase-sdk-hosted-iframe")
            if await frame.get_by_role("button", name="COMPRAR").is_visible():
                await frame.get_by_role("button", name="COMPRAR").click()
            frame = page.frame(name="purchase-sdk-hosted-iframe")
            if await frame.get_by_role("button", name="SIGUIENTE").is_visible():
                await frame.get_by_role('button', name="SIGUIENTE").click()
                await frame.locator('xpath=//*[@id="address_line1"]').type("111 Main St")
                await frame.locator('xpath=//*[@id="city"]').type("La Plata")
                await frame.locator('xpath=//*[@id="region"]').type("Buenos Aires")
                await frame.locator('xpath=//*[@id="postal_code"]').type("C1200")
                await frame.locator('xpath=//*[@id="pidlddc-button-saveButton"]').click()
                await frame.locator('xpath=//*[@id="store-cart-root"]/div/div/div[2]/div/div[4]/button[2]').click()

            await asyncio.sleep(2)
            await frame.locator('xpath=//*[@id="cvvToken"]').type(str(data.ccv))
            await asyncio.sleep(1.5)
            await frame.locator('xpath=//*[@id="pidlddc-button-okButton"]').click()
            await asyncio.sleep(15)
            await page.screenshot(path=f"{msg.guild.id}screenshot.png")
            await asyncio.sleep(1.2)
            embed.set_image(file=disnake.File(f"{msg.guild.id}screenshot.png"))
            embed.description = f"Purchased {vbucks} VBucks {i + 1} time"
            await msg.edit(embed=embed)
            os.remove(f"{msg.guild.id}screenshot.png")
        #await page.goto("https://account.microsoft.com/billing/payments?lang=en-US&refd=account.microsoft.com", wait_until="load")
        #await page.locator('button').scroll_into_view_if_needed()
        #while await page.locator('button').first.is_visible():
        #    logging.info("Removed card")
        #    await page.get_by_label("Remove card").first.click()
        #    await page.get_by_role("button", name="Remove").click()
        #    await asyncio.sleep(0.5)
        await page.close()
    except Exception as e:
        logging.info(e)
        if page.url != "https://account.microsoft.com/billing/payments":
            await page.screenshot(path=f"{msg.guild.id}screenshot.png")
            embed.set_image(file=disnake.File(f"{msg.guild.id}screenshot.png"))
        embed.description = "Error!"
        await msg.edit(embed=embed)
        await asyncio.sleep(5)
        await page.close()




setup, teardown = plugin.create_extension_handlers()
