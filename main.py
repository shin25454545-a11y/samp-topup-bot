import discord
from discord.ext import commands
import os
import sqlite3
import asyncio
import io
import qrcode
from datetime import datetime
from flask import Flask
from threading import Thread
from promptpay import generate_payload # <-- แก้ตรงนี้

# --- ตั้งค่าเริ่มต้น ---
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 125005190607694154
PROMPTPAY_ID = "0886560336"
BANNER_URL = "https://i.ibb.co/1Y1Lw8Yn/4d288aac3efa4911e5bb8ade7d5262b6.jpg"
ADMIN_CHANNEL_ID = ใส่ไอดีห้องแอดมิน # <-- เปลี่ยนตรงนี้เป็นเลขห้องแอดมิน

ROLE_IDS = {
    "VIP Gold": 1499228473095356597,
    "VIP Silver": 1499228661335724072,
    "VIP Bronze": 1499228752234942566
}

ROLE_PRICES = {
    "VIP Gold": 300,
    "VIP Silver": 150,
    "VIP Bronze": 50
}

# --- ตั้งค่าบอท ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- ฐานข้อมูล ---
def setup_database():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, item TEXT, price INTEGER, timestamp TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS pending_topup (user_id INTEGER PRIMARY KEY, amount INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

def add_transaction(user_id, username, item, price):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transactions (user_id, username, item, price, timestamp) VALUES (?, ?, ?, ?, ?)", (user_id, username, item, price, timestamp))
    conn.commit()
    conn.close()

def set_pending_topup(user_id, amount):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("REPLACE INTO pending_topup (user_id, amount, timestamp) VALUES (?, ?, ?)", (user_id, amount, timestamp))
    conn.commit()
    conn.close()

# --- ปุ่มอนุมัติของแอดมิน ---
class AdminApproveView(discord.ui.View):
    def __init__(self, user_id, role_name, price):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.role_name = role_name
        self.price = price

    @discord.ui.button(label="อนุมัติ", style=discord.ButtonStyle.green, emoji="✅")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("คุณไม่มีสิทธิ์", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(self.user_id)
        role = guild.get_role(ROLE_IDS[self.role_name])
        
        if member and role:
            await member.add_roles(role)
            add_transaction(self.user_id, member.name, self.role_name, self.price)
            await member.send(f"✅ การซื้อ {self.role_name} ของคุณได้รับการอนุมัติแล้ว!")
            await interaction.response.edit_message(content=f"อนุมัติ {self.role_name} ให้ {member.mention} เรียบร้อย", view=None)
        else:
            await interaction.response.send_message("ไม่พบผู้ใช้หรือยศ", ephemeral=True)

# --- หน้าร้านค้า VIP ---
class VIPShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_qr_callback(self, interaction: discord.Interaction, role_name: str):
        price = ROLE_PRICES[role_name]
        payload = generate_payload(PROMPTPAY_ID, price)
        img = qrcode.make(payload)
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)

        file = discord.File(buffer, filename="promptpay.png")
        embed = discord.Embed(title=f"ชำระเงินสำหรับ {role_name}", description=f"ยอดชำระ: **{price}฿**\n\n1. สแกน QR ด้านล่าง\n2. เมื่อโอนเสร็จ กดปุ่ม `แจ้งโอนเงินแล้ว`", color=0x00ff00)
        embed.set_image(url="attachment://promptpay.png")
        
        notify_view = discord.ui.View(timeout=300)
        notify_button = discord.ui.Button(label="แจ้งโอนเงินแล้ว", style=discord.ButtonStyle.success, emoji="📢")
        
        async def notify_callback(notify_interaction: discord.Interaction):
            set_pending_topup(notify_interaction.user.id, price)
            admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                admin_embed = discord.Embed(title="🔔 มีรายการรอตรวจสอบ", description=f"ผู้ใช้: {notify_interaction.user.mention}\nรายการ: {role_name}\nยอด: {price}฿", color=0xffa500)
                await admin_channel.send(embed=admin_embed, view=AdminApproveView(notify_interaction.user.id, role_name, price))
            
            await notify_interaction.response.edit_message(content="ส่งเรื่องให้แอดมินตรวจสอบแล้ว กรุณารอ", embed=None, attachments=[], view=None)

        notify_button.callback = notify_callback
        notify_view.add_item(notify_button)
        await interaction.response.send_message(embed=embed, file=file, view=notify_view, ephemeral=True)

    @discord.ui.button(label="VIP Bronze", style=discord.ButtonStyle.secondary, emoji="🥉")
    async def bronze_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_qr_callback(interaction, "VIP Bronze")

    @discord.ui.button(label="VIP Silver", style=discord.ButtonStyle.secondary, emoji="🥈")
    async def silver_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_qr_callback(interaction, "VIP Silver")

    @discord.ui.button(label="VIP Gold", style=discord.ButtonStyle.secondary, emoji="🥇")
    async def gold_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_qr_callback(interaction, "VIP Gold")

# --- แผงควบคุมหลัก ---
class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛍️ ร้านค้า VIP", style=discord.ButtonStyle.primary)
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💎 PREMIUM MEMBERSHIP",
            description="ปลดล็อคขีดจำกัด ขึ้นเป็นผู้ปกครองเซิร์ฟเวอร์",
            color=0x2b2d31
        )
        embed.set_image(url=BANNER_URL)
        
        embed.add_field(name="🥉 BRONZE TIER", value="**ราคา:** 50฿ | **อายุ:** 30 วัน\n\n**PERKS**\n⚡ EXP Multiplier x1.5\n🍀 Drop Rate +20%", inline=False)
        embed.add_field(name="🥈 SILVER TIER", value="**ราคา:** 150฿ | **อายุ:** 30 วัน\n\n**PERKS**\n⚡ EXP Multiplier x2.0\n🍀 Drop Rate +40%", inline=False)
        embed.add_field(name="🥇 GOLD TIER", value="**ราคา:** 300฿ | **อายุ:** 30 วัน\n\n**PERKS**\n⚡ EXP Multiplier x3.0\n🍀 Drop Rate +70%", inline=False)
        
        await interaction.response.send_message(embed=embed, view=VIPShopView(), ephemeral=True)

# --- คำสั่งบอท ---
@bot.event
async def on_ready():
    setup_database()
    print(f'ออนไลน์แล้ว! {bot.user}')
    await bot.change_presence(activity=discord.Game(name="🛍️ พิมพ์ !menu"))

@bot.command()
async def menu(ctx):
    if ctx.author.id != OWNER_ID:
        return
    embed = discord.Embed(title="แผงควบคุมร้านค้า", description="กดปุ่มด้านล่างเพื่อจัดการระบบ", color=0x3498db)
    await ctx.send(embed=embed, view=ControlPanelView())

# --- กัน Railway หลับ ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

Thread(target=run_flask).start()

bot.run(TOKEN)
