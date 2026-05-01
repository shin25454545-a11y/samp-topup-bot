import nextcord
from nextcord.ext import commands
import qrcode
import io
from flask import Flask
from threading import Thread
import os

# ---------- ตั้งค่าบอท ----------
BOT_TOKEN = "ใส่TOKEN_บอทของท่านตรงนี้"
PROMPTPAY_NUMBER = "0886560336"  # เบอร์พร้อมเพย์ท่าน
ROLE_GOLD_ID = 123456789012345678   # แก้เป็น ID ยศ Gold
ROLE_SILVER_ID = 123456789012345679 # แก้เป็น ID ยศ Silver  
ROLE_BRONZE_ID = 123456789012345670 # แก้เป็น ID ยศ Bronze

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- ฟังก์ชันเจน QR PromptPay แบบไม่พึ่งไลบรารี่นอก ----------
def generate_promptpay_qr(amount=None):
    promptpay_id = PROMPTPAY_NUMBER
    if len(promptpay_id) == 10 and promptpay_id.startswith('0'):
        promptpay_id = '66' + promptpay_id[1:]
    
    payload_format = '000201'
    poi_method = '010212'
    merchant_info = f'0016A0000006770101110113{promptpay_id}'
    merchant_len = f'29{len(merchant_info):02d}'
    currency = '5303764'
    country = '5802TH'
    
    payload_list = [payload_format, poi_method, merchant_len + merchant_info, currency]
    
    if amount:
        amt_str = f'{float(amount):.2f}'
        payload_list.append(f'54{len(amt_str):02d}{amt_str}')
        
    payload_list.append(country)
    payload_list.append('6304')
    
    data_for_crc = ''.join(payload_list)
    
    crc = 0xFFFF
    for b in data_for_crc.encode('ascii'):
        crc ^= b << 8
        for _ in range(8):
            if (crc & 0x8000) != 0:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
    crc &= 0xFFFF
    
    payload_final = data_for_crc + f'{crc:04X}'
    img = qrcode.make(payload_final)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# ---------- ปุ่มร้านค้า VIP ----------
class VipShopView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="Gold 300฿", style=nextcord.ButtonStyle.gold, custom_id="vip_gold")
    async def gold_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        role = interaction.guild.get_role(ROLE_GOLD_ID)
        if role:
            await interaction.user.add_roles(role)
            qr_buffer = generate_promptpay_qr(300)
            await interaction.response.send_message(
                f"{interaction.user.mention} ซื้อ **VIP Gold 300฿** สำเร็จ\nสแกน QR เพื่อชำระเงิน ยศจะอยู่ถาวร",
                file=nextcord.File(qr_buffer, "promptpay.png"),
                ephemeral=True
            )
        else:
            await interaction.response.send_message("ไม่พบยศ Gold ตั้งค่า ROLE_GOLD_ID ก่อน", ephemeral=True)

    @nextcord.ui.button(label="Silver 200฿", style=nextcord.ButtonStyle.secondary, custom_id="vip_silver")
    async def silver_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        role = interaction.guild.get_role(ROLE_SILVER_ID)
        if role:
            await interaction.user.add_roles(role)
            qr_buffer = generate_promptpay_qr(200)
            await interaction.response.send_message(
                f"{interaction.user.mention} ซื้อ **VIP Silver 200฿** สำเร็จ\nสแกน QR เพื่อชำระเงิน ยศจะอยู่ถาวร",
                file=nextcord.File(qr_buffer, "promptpay.png"),
                ephemeral=True
            )
        else:
            await interaction.response.send_message("ไม่พบยศ Silver ตั้งค่า ROLE_SILVER_ID ก่อน", ephemeral=True)

    @nextcord.ui.button(label="Bronze 100฿", style=nextcord.ButtonStyle.success, custom_id="vip_bronze")
    async def bronze_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        role = interaction.guild.get_role(ROLE_BRONZE_ID)
        if role:
            await interaction.user.add_roles(role)
            qr_buffer = generate_promptpay_qr(100)
            await interaction.response.send_message(
                f"{interaction.user.mention} ซื้อ **VIP Bronze 100฿** สำเร็จ\nสแกน QR เพื่อชำระเงิน ยศจะอยู่ถาวร",
                file=nextcord.File(qr_buffer, "promptpay.png"),
                ephemeral=True
            )
        else:
            await interaction.response.send_message("ไม่พบยศ Bronze ตั้งค่า ROLE_BRONZE_ID ก่อน", ephemeral=True)

# ---------- ปุ่มเมนูหลัก ----------
class MainMenuView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="เติมเงิน", style=nextcord.ButtonStyle.blurple, emoji="💵")
    async def topup_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        qr_buffer = generate_promptpay_qr()
        await interaction.response.send_message(
            f"**เติมเงินเข้าบัญชี**\nพร้อมเพย์: `{PROMPTPAY_NUMBER}`\nสแกน QR ด้านล่างได้เลย",
            file=nextcord.File(qr_buffer, "promptpay.png"),
            ephemeral=True
        )

    @nextcord.ui.button(label="ร้านค้า VIP", style=nextcord.ButtonStyle.green, emoji="👑")
    async def shop_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title="👑 ร้านค้า VIP",
            description="เลือกยศที่ต้องการ กดแล้วรับยศทันที + ได้ QR สำหรับชำระเงิน\n**ยศอยู่ถาวร ไม่มีการลบ**",
            color=0xffd700
        )
        embed.add_field(name="Gold", value="300 บาท", inline=True)
        embed.add_field(name="Silver", value="200 บาท", inline=True)
        embed.add_field(name="Bronze", value="100 บาท", inline=True)
        await interaction.response.send_message(embed=embed, view=VipShopView(), ephemeral=True)

# ---------- คำสั่ง !เมนู ----------
@bot.command()
async def เมนู(ctx):
    embed = nextcord.Embed(
        title="💎 ระบบเติมเงิน & VIP",
        description="ยินดีต้อนรับ เลือกเมนูที่ต้องการได้เลย",
        color=0x00ff00
    )
    await ctx.send(embed=embed, view=MainMenuView())

# ---------- Event บอทพร้อมทำงาน ----------
@bot.event
async def on_ready():
    bot.add_view(MainMenuView())
    bot.add_view(VipShopView())
    print(f"✅ บอท {bot.user} ออนไลน์แล้ว!")

# ---------- เว็บเซิร์ฟเวอร์ให้ Railway ตรวจ ----------
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
bot.run(BOT_TOKEN)
