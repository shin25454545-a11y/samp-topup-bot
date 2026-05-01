import discord
from discord.ext import commands
from discord import ui
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("DISCORD_OWNER_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== Config ตรงนี้ ======
TRUEWALLET_BOT_ID = 123456789012345678 # ใส่ ID บอทซองอั่งเปา
LOG_CHANNEL_ID = 0 # ใส่ ID ห้อง Log ถ้ามี
# ==========================

class VIPShop(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="VIP Gold 100฿", style=discord.ButtonStyle.success, emoji="👑")
    async def vip_gold(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="👑 VIP Gold 100 บาท",
            description="**สิทธิพิเศษ:**\n> ✅ /fix 5 ครั้ง/วัน\n> ✅ /skin พิเศษ\n> ✅ ชื่อสีทองในเกม\n\n**วิธีชำระ:**\n1. สร้างซอง TrueWallet 100 บาท\n2. ส่งลิงก์ซองในห้องนี้\n3. รอแอดมินตรวจสอบ 1-5 นาที",
            color=0xFFD700
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="VIP Diamond 300฿", style=discord.ButtonStyle.primary, emoji="💎")
    async def vip_diamond(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="💎 VIP Diamond 300 บาท",
            description="**สิทธิพิเศษ:**\n> ✅ /fix ไม่จำกัด\n> ✅ /skin พิเศษ + /mask\n> ✅ ชื่อสีเพชร + แท็ก [VIP]\n> ✅ /tp ฟรี 3 ครั้ง/วัน\n\n**วิธีชำระ:**\n1. สร้างซอง TrueWallet 300 บาท\n2. ส่งลิงก์ซองในห้องนี้\n3. รอแอดมินตรวจสอบ 1-5 นาที",
            color=0x00FFFF
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class TopupMenu(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="เติมเงินเข้าเกม", style=discord.ButtonStyle.success, emoji="💵")
    async def topup(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="💵 เติมเงินเข้าเกม SAMP",
            description="**เรท:** 1 บาท = 10,000$ ในเกม\n**ขั้นต่ำ:** 20 บาท\n\n**วิธีเติม:**\n1. สร้างซองอั่งเปา TrueWallet\n2. แท็ก <@{}> พร้อมจำนวนเงิน\n3. ส่งลิงก์ซองในห้องนี้\n4. รอระบบเติมอัตโนมัติ 1-2 นาที".format(TRUEWALLET_BOT_ID),
            color=0x2ECC71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="ซื้อ VIP เข้าเกม", style=discord.ButtonStyle.primary, emoji="👑")
    async def buy_vip(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("เลือกแพ็คเกจ VIP ที่ต้องการ:", view=VIPShop(), ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    bot.add_view(TopupMenu())
    bot.add_view(VIPShop())
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

@bot.command()
async def เมนู(ctx):
    embed = discord.Embed(
        title="🎮 ระบบเติมเงิน SAMP เซิร์ฟท่าน",
        description="เลือกเมนูที่ต้องการด้านล่าง\nเติมเงินออโต้ 24 ชม. ผ่าน TrueWallet",
        color=0x3498DB
    )
    embed.set_footer(text="ซัพพอร์ตโดย AI Bot")
    await ctx.send(embed=embed, view=TopupMenu())

@bot.tree.command(name="sync", description="Sync commands")
async def sync(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("ไม่มีสิทธิ์", ephemeral=True)
        return
    await bot.tree.sync()
    await interaction.response.send_message("Synced commands แล้ว", ephemeral=True)

bot.run(TOKEN)
