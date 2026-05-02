import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import json

# --- 1. จัดการข้อมูลเงิน ---
def load_data():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open('users.json', 'w') as f:
        json.dump(data, f, indent=4)

# --- 2. ตั้งค่าบอท ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. หน้าตาส่วนของ "ปุ่มกด" ---
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # ปุ่มเช็คเงิน
    @discord.ui.button(label="💰 เช็คยอดเงิน", style=discord.ButtonStyle.success, custom_id="check_balance")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        users = load_data()
        balance = users.get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 ยอดเงินของคุณคือ: **{balance}฿**", ephemeral=True)

    # ปุ่มเติมเงิน
    @discord.ui.button(label="💵 เติมเงิน (QR Code)", style=discord.ButtonStyle.primary, custom_id="topup")
    async def topup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        promptpay_number = "0886560336" # เบอร์ของพี่เรียบร้อยครับ
        embed = discord.Embed(
            title="🧧 ช่องทางการเติมเงิน", 
            description=f"แสกน QR Code ด้านล่างเพื่อเติมเงินครับ\n\n**เบอร์พร้อมเพย์:** `{promptpay_number}`\n**ชื่อบัญชี:** (โปรดตรวจสอบชื่อก่อนโอน)\n\n*หมายเหตุ: เมื่อโอนเสร็จแล้ว ให้ส่งสลิปยืนยันกับแอดมิน*", 
            color=0xFFD700
        )
        # สร้างลิงก์ QR Code อัตโนมัติ
        qr_url = f"https://promptpay.io{promptpay_number}.png"
        embed.set_image(url=qr_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ปุ่มซื้อยศ
    @discord.ui.button(label="👑 ซื้อยศ VIP", style=discord.ButtonStyle.danger, custom_id="buy_vip")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛒 ร้านค้า VIP", 
            description="**ยศที่มีจำหน่าย:**\n\n1. **VIP Gold** - 300฿\n2. **VIP Silver** - 150฿\n\n*(ระบบหักเงินอัตโนมัติกำลังเตรียมการ)*", 
            color=0x3498DB
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- 4. คำสั่ง !เมนู ---
@bot.command(name="เมนู")
async def menu(ctx):
    embed = discord.Embed(
        title="🤖 ระบบจัดการสมาชิก",
        description="สวัสดีครับพี่! เลือกกดปุ่มด้านล่างเพื่อทำรายการได้เลยครับ",
        color=discord.Color.purple()
    )
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)
    await ctx.send(embed=embed, view=MenuView())

# --- 5. เริ่มรันบอท ---
@bot.event
async def on_ready():
    print(f'น้องบอท {bot.user} พร้อมให้บริการปุ่มกดแล้วครับ!')

token = os.getenv('BOT_TOKEN')
bot.run(token)
