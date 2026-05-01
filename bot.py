import discord
from discord.ext import commands
from discord import ui
import os
from dotenv import load_dotenv
import aiohttp
import asyncio

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('DISCORD_OWNER_ID', 0))
TRUEWALLET_BOT_ID = 1499646135944609872  # ID บอทซอง TrueWallet ใส่ให้แล้ว

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class TopupIngameModal(ui.Modal, title='💵 เติมเงินเข้าเกม'):
    ingame_name = ui.TextInput(label='ชื่อในเกม', placeholder='ใส่ชื่อตัวละครใน SAMP')
    amount = ui.TextInput(label='จำนวนเงิน', placeholder='เช่น 50')

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✅ สร้างรายการเติมเงินแล้ว",
            description=f"**ชื่อในเกม:** {self.ingame_name.value}\n**ยอดเงิน:** {self.amount.value} บาท\n\nกดซองจากบอท TrueWallet แล้วแคปหลักฐานมาตอบกลับข้อความนี้",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BuyVipModal(ui.Modal, title='👑 ซื้อ VIP เข้าเกม'):
    ingame_name = ui.TextInput(label='ชื่อในเกม', placeholder='ใส่ชื่อตัวละครใน SAMP')
    vip_level = ui.TextInput(label='ระดับ VIP', placeholder='เช่น VIP 1, VIP 2')

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✅ สร้างรายการสั่งซื้อ VIP แล้ว",
            description=f"**ชื่อในเกม:** {self.ingame_name.value}\n**VIP:** {self.vip_level.value}\n\nกดซองจากบอท TrueWallet แล้วแคปหลักฐานมาตอบกลับข้อความนี้",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TopupMenu(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="💵 เติมเงินเข้าเกม", style=discord.ButtonStyle.success, custom_id="topup_ingame")
    async def topup_ingame(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TopupIngameModal())

    @ui.button(label="👑 ซื้อ VIP เข้าเกม", style=discord.ButtonStyle.primary, custom_id="buy_vip")
    async def buy_vip(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BuyVipModal())

@bot.event
async def on_ready():
    bot.add_view(TopupMenu())
    print(f'Logged in as {bot.user}')
    print('------')

@bot.command()
async def เมนู(ctx):
    embed = discord.Embed(
        title="🎮 ระบบเติมเงิน SAMP เซิร์ฟท่าน",
        description="เลือกบริการที่ต้องการด้านล่างได้เลย\nเติมเงินไว ปลอดภัย ระบบออโต้",
        color=discord.Color.blue()
    )
    embed.set_footer(text="SAMP Topup Bot")
    await ctx.send(embed=embed, view=TopupMenu())

@bot.command()
async def sync(ctx):
    if ctx.author.id == OWNER_ID:
        await ctx.defer()
        await bot.tree.sync()
        await ctx.send("✅ Synced commands แล้ว", delete_after=5)
    else:
        await ctx.send("ไม่มีสิทธิ์ใช้คำสั่งนี้", delete_after=5)

@bot.event
async def on_message(message):
    if message.author.bot and message.author.id == TRUEWALLET_BOT_ID:
        if "ได้รับซอง" in message.content or "รับเงิน" in message.content:
            await message.channel.send("🧾 ตรวจเจอซอง TrueWallet! แอดมินกำลังตรวจสอบ...")
    
    await bot.process_commands(message)

bot.run(TOKEN)
