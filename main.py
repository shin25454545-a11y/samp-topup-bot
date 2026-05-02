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

# --- ตั้งค่าบอท ---
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
        # สร้าง Embed แบบไม่มีรูป
        embed = discord.Embed(
            title="🧧 ช่องทางการเติมเงิน (PromptPay)",
            description="**แสกน QR Code ด้านล่างเพื่อเติมเงิน**\n\n**เบอร์พร้อมเพย์:** `0886560336`",
            color=0xffd700
        )
        # ส่งแบบมีลิ้งก์ข้อความเพื่อให้ Discord ดึงรูปมาพรีวิวเอง
        qr_url = "https://promptpay.io"
        await interaction.response.send_message(content=qr_url, embed=embed, ephemeral=True)

    @discord.ui.button(label="👑 รายละเอียด VIP", style=discord.ButtonStyle.danger, custom_id="vip_info")
    async def vip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛒 รายการยศ VIP", description="🥉 VIP Bronze: 50฿\n🥈 VIP Silver: 100฿\n🥇 VIP Gold: 200฿", color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว")
    bot.add_view(Menu())

@bot.command()
async def setup(ctx):
    embed = discord.Embed(title="🤖 ระบบจัดการสมาชิก", description="เลือกรายการด้านล่างได้เลยครับ", color=0x5865f2)
    await ctx.send(embed=embed, view=Menu())

@bot.command()
@commands.has_permissions(administrator=True)
async def addmoney(ctx, member: discord.Member, amount: int):
    users = load_data()
    users[str(member.id)] = users.get(str(member.id), 0) + amount
    save_data(users)
    await ctx.send(f"✅ เพิ่มเงินให้ {member.mention} จำนวน {amount} บาท!")

bot.run(os.getenv("BOT_TOKEN"))
