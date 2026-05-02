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
from promptpay import qrcode as pp_qr

# --- ตั้งค่า 3 จุดนี้เท่านั้น ---
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 125005190607694154
PROMPTPAY_ID = "0886560336"
BANNER_URL = "https://i.ibb.co/1Y1Lw8Yn/4d288aac3efa4911e5bb8ade7d5262b6.jpg"
ADMIN_CHANNEL_ID = 1500036196703797308 # <-- เปลี่ยนตรงนี้เป็นเลขห้องแอดมิน

ROLE_IDS = {
    "VIP Bronze": 1499228752234942566,
    "VIP Silver": 1499228661335724072,
    "VIP Gold": 1499228473095356597
}

ROLE_PRICES = {"VIP Bronze": 50, "VIP Silver": 150, "VIP Gold": 300}

# --- ตั้งค่าบอท ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- ฐานข้อมูล ---
def setup_database():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, item TEXT, price INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

def add_transaction(user_id, username, item, price):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transactions (user_id, username, item, price, timestamp) VALUES (?,?,?,?,?)", (user_id, username, item, price, timestamp))
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
            return await interaction.response.send_message("คุณไม่มีสิทธิ์", ephemeral=True)

        member = interaction.guild.get_member(self.user_id)
        role = interaction.guild.get_role(ROLE_IDS[self.role_name])

        if member and role:
            await member.add_roles(role)
            add_transaction(self.user_id, member.name, self.role_name, self.price)
            await member.send(f"✅ การซื้อ {self.role_name} ของคุณได้รับการอนุมัติแล้ว ยินดีต้อนรับ!")
            await interaction.response.edit_message(content=f"อนุมัติ {self.role_name} ให้ {member.mention} เรียบร้อย", view=None, embed=None)
        else:
            await interaction.response.send_message("ไม่พบผู้ใช้หรือยศนี้ในเซิร์ฟเวอร์", ephemeral=True)

# --- หน้าร้านค้า VIP ---
class VIPShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_qr(self, interaction: discord.Interaction, role_name: str):
        price = ROLE_PRICES[role_name]
        payload = pp_qr.generate_payload(PROMPTPAY_ID, price)
        img = qrcode.make(payload)
        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)

        file = discord.File(buffer, filename="qr.png")
        embed = discord.Embed(title=f"ชำระเงิน {role_name} - {price}฿", description="1. สแกน QR ด้านล่างเพื่อจ่ายเงิน\n2. เมื่อโอนเสร็จ กดปุ่ม `แจ้งโอนเงินแล้ว`\n3. รอแอดมินตรวจสอบ 1-5 นาที", color=0x57F287)
        embed.set_image(url="attachment://qr.png")

        notify_view = discord.ui.View(timeout=600)
        notify_btn = discord.ui.Button(label="แจ้งโอนเงินแล้ว", style=discord.ButtonStyle.success, emoji="📢")

        async def notify_cb(btn_interaction: discord.Interaction):
            admin_ch = bot.get_channel(ADMIN_CHANNEL_ID)
            if admin_ch:
                admin_embed = discord.Embed(title="🔔 ออเดอร์ใหม่รอตรวจ", description=f"**ลูกค้า:** {btn_interaction.user.mention}\n**สินค้า:** {role_name}\n**ยอด:** {price}฿", color=0xFEE75C)
                await admin_ch.send(embed=admin_embed, view=AdminApproveView(btn_interaction.user.id, role_name, price))
            await btn_interaction.response.edit_message(content="✅ ส่งเรื่องให้แอดมินแล้ว กรุณารอแอดมินอนุมัติ", embed=None, attachments=[], view=None)

        notify_btn.callback = notify_cb
        notify_view.add_item(notify_btn)
        await interaction.response.send_message(embed=embed, file=file, view=notify_view, ephemeral=True)

    @discord.ui.button(label="Bronze 50฿", style=discord.ButtonStyle.secondary, emoji="🥉")
    async def bronze(self, i: discord.Interaction, b: discord.ui.Button): await self.create_qr(i, "VIP Bronze")

    @discord.ui.button(label="Silver 150฿", style=discord.ButtonStyle.secondary, emoji="🥈")
    async def silver(self, i: discord.Interaction, b: discord.ui.Button): await self.create_qr(i, "VIP Silver")

    @discord.ui.button(label="Gold 300฿", style=discord.ButtonStyle.secondary, emoji="🥇")
    async def gold(self, i: discord.Interaction, b: discord.ui.Button): await self.create_qr(i, "VIP Gold")

# --- แผงควบคุมหลัก ---
class ControlPanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)

    @discord.ui.button(label="🛍️ เปิดร้านค้า VIP", style=discord.ButtonStyle.blurple)
    async def shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="💎 PREMIUM MEMBERSHIP", description="ปลดล็อคขีดจำกัด ขึ้นเป็นผู้ปกครองเซิร์ฟเวอร์", color=0x2B2D31)
        embed.set_image(url=BANNER_URL)
        embed.add_field(name="🥉 BRONZE - 50฿ / 30 วัน", value="```EXP x1.5 | Drop Rate +20%```", inline=False)
        embed.add_field(name="🥈 SILVER - 150฿ / 30 วัน", value="```EXP x2.0 | Drop Rate +40%```", inline=False)
        embed.add_field(name="🥇 GOLD - 300฿ / 30 วัน", value="```EXP x3.0 | Drop Rate +70%```", inline=False)
        await interaction.response.send_message(embed=embed, view=VIPShopView(), ephemeral=True)

# --- คำสั่งบอท ---
@bot.event
async def on_ready():
    setup_database()
    bot.add_view(ControlPanelView())
    bot.add_view(VIPShopView())
    print(f'บอท {bot.user} ออนไลน์แล้ว!')
    await bot.change_presence(activity=discord.Game(name="🛍️ พิมพ์!menu"))

@bot.command()
async def menu(ctx):
    if ctx.author.id!= OWNER_ID: return
    embed = discord.Embed(title="แผงควบคุมร้านค้า", description="กดปุ่มด้านล่างเพื่อเปิดร้าน", color=0x3498DB)
    await ctx.send(embed=embed, view=ControlPanelView())

# --- กัน Railway หลับ ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"

def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
Thread(target=run).start()

bot.run(TOKEN)
