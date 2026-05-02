import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import json
import redis

# --- เชื่อมต่อ Redis ---
REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None

def load_data():
    if r:
        data = r.get("users_data")
        return json.loads(data) if data else {}
    return {}

def save_data(data):
    if r:
        r.set("users_data", json.dumps(data))

# --- บอทเริ่มต้นทำงาน ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class Menu(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 เช็คยอดเงิน", style=discord.ButtonStyle.success, custom_id="check_balance")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        users = load_data()
        balance = users.get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💵 ยอดเงินคงเหลือของคุณคือ: **{balance}** บาท", ephemeral=True)

    @discord.ui.button(label="🧧 เติมเงิน (QR)", style=discord.ButtonStyle.primary, custom_id="deposit_qr")
    async def deposit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🧧 ช่องทางการเติมเงิน (PromptPay)",
            description="**แสกน QR Code เพื่อเติมเงินได้ทันที**\n\n**เบอร์พร้อมเพย์:** `0886560336`\n**ชื่อบัญชี:** [ชื่อพร้อมเพย์ของพี่]",
            color=0xffd700
        )
        # บรรทัดนี้จะบังคับให้รูป QR ขึ้นครับ
        embed.set_image(url="https://promptpay.io")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👑 รายละเอียด VIP", style=discord.ButtonStyle.danger, custom_id="vip_info")
    async def vip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛒 รายการยศ VIP", description="เลือกซื้อยศที่ต้องการสะสมแต้มได้เลย", color=0x00ff00)
        embed.add_field(name="🥉 VIP Bronze", value="ราคา 50 บาท | เท่กว่าใคร", inline=False)
        embed.add_field(name="🥈 VIP Silver", value="ราคา 100 บาท | สุดยอดความไว", inline=False)
        embed.add_field(name="🥇 VIP Gold", value="ราคา 200 บาท | ระดับตำนาน", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user}")
    bot.add_view(Menu())

@bot.command()
async def setup(ctx):
    embed = discord.Embed(title="🤖 ระบบจัดการสมาชิก", description="ยินดีต้อนรับครับ! เลือกทำรายการด้านล่างได้เลย", color=0x5865f2)
    await ctx.send(embed=embed, view=Menu())

bot.run(os.getenv("BOT_TOKEN"))
