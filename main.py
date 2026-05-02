import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os
import json
import redis

# --- เชื่อมต่อ Redis ของ Railway ---
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    r = redis.from_url(REDIS_URL, decode_responses=True)
else:
    r = None

def load_data():
    if r:
        data = r.get("users_data")
        return json.loads(data) if data else {}
    if not os.path.exists("users.json"):
        return {}
    with open("users.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    if r:
        r.set("users_data", json.dumps(data))
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- บอทเริ่มต้นทำงาน ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_content="!", intents=intents)

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
            description="แสกน QR Code เพื่อเติมเงินได้ทันที\n\n**เบอร์พร้อมเพย์:** `0886560336`\n**ชื่อบัญชี:** [กรุณาใส่ชื่อพี่ตรงนี้]",
            color=discord.Color.gold()
        )
        # --- เพิ่มรูป QR Code ---
        embed.set_image(url="https://promptpay.io")
        embed.set_footer(text="เมื่อโอนเสร็จแล้ว กรุณารอสักครู่ระบบจะอัปเดตยอดเงิน")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👑 ซื้อยศ VIP", style=discord.ButtonStyle.danger, custom_id="buy_vip")
    async def vip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛒 เลือกซื้อยศ VIP", description="คลิกเลือกยศที่ต้องการซื้อได้เลยครับ", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.add_view(Menu())

@bot.command()
async def setup(ctx):
    embed = discord.Embed(title="🤖 ระบบจัดการสมาชิก", description="ยินดีต้อนรับครับ! เลือกทำรายการด้านล่างได้เลย", color=discord.Color.green())
    await ctx.send(embed=embed, view=Menu())

bot.run(os.getenv("BOT_TOKEN"))
