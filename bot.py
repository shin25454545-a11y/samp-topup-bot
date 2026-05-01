import nextcord
from nextcord.ext import commands
from nextcord import ui
import os
from flask import Flask, render_template_string
import threading
import json
from datetime import datetime
import qrcode
import io

TOKEN = os.getenv("DISCORD_TOKEN")

# ---------- ตั้งค่า 3 จุดนี้พอ ใช้ชื่อยศแทน ID ----------
PROMPTPAY_NUMBER = "0886560336"
BANNER_URL = ""
LOG_CHANNEL_ID = 1499809858680000712 # ID ห้องแจ้งโอน อันนี้ยังต้องใช้
ADMIN_ROLE_NAME = "Admin👑" # ใส่ชื่อยศแอดมินให้ตรงเป๊ะ
VIP_GOLD_ROLE_NAME = "VIP Gold" # ใส่ชื่อยศให้ตรงเป๊ะ
VIP_SILVER_ROLE_NAME = "VIP Silver"
VIP_BRONZE_ROLE_NAME = "VIP Bronze"
DATA_FILE = "topup_data.json"

# ---------- ฟังก์ชันเจน QR PromptPay ----------
def generate_promptpay_qr(amount=None):
    from promptpay import qrcode as ppqr
    payload = ppqr.generate_payload(PROMPTPAY_NUMBER, amount)
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# ---------- ส่วนเว็บ Dashboard ----------
app = Flask(__name__)

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"today": 0, "month": 0, "total": 0, "users": {}, "vip": {}}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route('/')
def dashboard():
    data = load_data()
    top_users = sorted(data["users"].items(), key=lambda x: x[1], reverse=True)[:10]
    html = '''
    <!DOCTYPE html><html lang="th"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SAMP Dashboard</title><style>
    *{margin:0;padding:0;box-sizing:border-box}body{font-family:Kanit,sans-serif;background:#0f1419;color:#fff;padding:20px}
.header h1{color:#ffd700;font-size:28px;margin-bottom:25px}.card{background:#1a2332;border-radius:15px;padding:20px;margin-bottom:15px}
.card-label{color:#8899a6;font-size:14px;margin-bottom:8px}.card-value{font-size:36px;font-weight:700}
.green{color:#2ecc71}.blue{color:#3498db}.yellow{color:#f1c40f}.top-item{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #2c3e50}
    </style><link href="https://fonts.googleapis.com/css2?family=Kanit:wght@400;600;700&display=swap" rel="stylesheet"></head><body>
    <div class="header"><h1>🏛️ SAMP Dashboard</h1></div>
    <div class="card"><div class="card-label">ยอดเติมวันนี้</div><div class="card-value green">{{ data.today }}฿</div></div>
    <div class="card"><div class="card-label">ยอดเติมเดือนนี้</div><div class="card-value blue">{{ data.month }}฿</div></div>
    <div class="card"><div class="card-label">ยอดเติมทั้งหมด</div><div class="card-value yellow">{{ data.total }}฿</div></div>
    <div class="card"><div class="card-label">🏆 ท็อป 10 สายเปย์</div>
    {% for user_id, amount in top_users %}
    <div class="top-item"><span>{{ loop.index }}. <@{{ user_id }}></span><span class="yellow">{{ amount }}฿</span></div>
    {% endfor %}</div></body></html>
    '''
    return render_template_string(html, data=data, top_users=top_users)

# ---------- ส่วนบอท Discord ----------
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class TopupModal(ui.Modal):
    def __init__(self):
        super().__init__(title="แจ้งเติมเงิน")
        self.ingame_name = ui.TextInput(label="ชื่อในเกม", max_length=32)
        self.amount = ui.TextInput(label="จำนวนเงินที่โอน (บาท)", max_length=5)
        self.add_item(self.ingame_name); self.add_item(self.amount)

    async def callback(self, interaction: nextcord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(f"🔔 {interaction.user.mention} แจ้งโอน\nชื่อเกม: {self.ingame_name.value}\nยอด: {self.amount.value}฿")
        await interaction.response.send_message("✅ แจ้งโอนแล้ว รอแอดมินเช็คสลิป", ephemeral=True)

class ConfirmTopupView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📝 กดที่นี่หลังโอนเสร็จ", style=nextcord.ButtonStyle.blurple)
    async def confirm(self, button, interaction): await interaction.response.send_modal(TopupModal())

class VIPShopView(ui.View):
    def __init__(self): super().__init__(timeout=180)

    async def buy_vip(self, interaction: nextcord.Interaction, name: str, price: int, role_name: str, days: int):
        data = load_data()
        uid = str(interaction.user.id)
        user_credit = data["users"].get(uid, 0)
        if user_credit < price:
            return await interaction.response.send_message(f"❌ เครดิตไม่พอ! คุณมี {user_credit} บาท แต่ {name} ราคา {price} บาท", ephemeral=True)

        data["users"][uid] = user_credit - price
        data["vip"][uid] = datetime.now().timestamp() + (days * 86400)
        save_data(data)

        vip_role = nextcord.utils.get(interaction.guild.roles, name=role_name)
        if vip_role:
            await interaction.user.add_roles(vip_role)
            await interaction.response.send_message(f"✅ ซื้อ **{name}** สำเร็จ! หัก {price} เครดิต คงเหลือ {data['users'][uid]} บาท", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ หาบทบาท `{role_name}` ไม่เจอ แจ้งแอดมินเช็คชื่อยศให้ตรงกับในโค้ด", ephemeral=True)
            return

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(f"🛒 {interaction.user.mention} ซื้อ {name} ราคา {price} บาท")

    @ui.button(label="VIP Gold 300฿", style=nextcord.ButtonStyle.green, emoji="🥇", row=0)
    async def vip_gold(self, button, interaction): await self.buy_vip(interaction, "VIP Gold", 300, VIP_GOLD_ROLE_NAME, 30)

    @ui.button(label="VIP Silver 200฿", style=nextcord.ButtonStyle.gray, emoji="🥈", row=1)
    async def vip_silver(self, button, interaction): await self.buy_vip(interaction, "VIP Silver", 200, VIP_SILVER_ROLE_NAME, 30)

    @ui.button(label="VIP Bronze 100฿", style=nextcord.ButtonStyle.red, emoji="🥉", row=2)
    async def vip_bronze(self, button, interaction): await self.buy_vip(interaction, "VIP Bronze", 100, VIP_BRONZE_ROLE_NAME, 30)

class MainMenuView(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="เติมเงิน", style=nextcord.ButtonStyle.green, emoji="💰")
    async def topup(self, button, interaction):
        qr_image = generate_promptpay_qr()
        file = nextcord.File(qr_image, filename="promptpay.png")
        embed = nextcord.Embed(title="สแกน QR เพื่อเติมเงิน", description=f"PromptPay: `{PROMPTPAY_NUMBER}`\nโอนเสร็จแล้วกดปุ่มด้านล่าง", color=0x2ecc71)
        embed.set_image(url="attachment://promptpay.png")
        await interaction.response.send_message(embed=embed, file=file, view=ConfirmTopupView(), ephemeral=True)

    @ui.button(label="เช็คเครดิต", style=nextcord.ButtonStyle.blurple, emoji="💳")
    async def credit(self, button, interaction):
        credit = load_data()["users"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"**{interaction.user.display_name}**\nเครดิตคงเหลือ: {credit} บาท", ephemeral=True)

    @ui.button(label="ร้านค้า VIP", style=nextcord.ButtonStyle.gray, emoji="🛒", row=1)
    async def vip(self, button, interaction):
        embed = nextcord.Embed(title="🛒 ร้านค้า VIP", description="เลือกยศที่ต้องการ กดซื้อได้เลย", color=0xf1c40f)
        await interaction.response.send_message(embed=embed, view=VIPShopView(), ephemeral=True)

    @ui.button(label="แอดมินเติมเงิน", style=nextcord.ButtonStyle.red, emoji="⚙️", row=1)
    async def admin(self, button, interaction):
        admin_role = nextcord.utils.get(interaction.guild.roles, name=ADMIN_ROLE_NAME)
        if not admin_role or admin_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ คำสั่งสำหรับแอดมินเท่านั้น", ephemeral=True)
        await interaction.response.send_message("ใช้ `!addmoney @user จำนวน` เพื่อเติมเครดิตให้สมาชิก", ephemeral=True)

@bot.command()
async def เมนู(ctx):
    embed = nextcord.Embed(title="🏛️ ระบบเติมเงิน & ร้านค้า VIP", description="**ยินดีต้อนรับสู่ร้านค้าเซิฟเรา**\n🔥 โปรโมชั่นเปิดเซิฟ | ใช้ /daily รับฟรี 10฿ ทุกวัน", color=0xf1c40f)
    if BANNER_URL: embed.set_image(url=BANNER_URL)
    await ctx.send(embed=embed, view=MainMenuView())

@bot.command()
async def addmoney(ctx, member: nextcord.Member, amount: int):
    admin_role = nextcord.utils.get(ctx.guild.roles, name=ADMIN_ROLE_NAME)
    if not admin_role or admin_role not in ctx.author.roles:
        return await ctx.send("❌ คำสั่งสำหรับแอดมินเท่านั้น")
    data = load_data()
    data["today"] += amount; data["month"] += amount; data["total"] += amount
    uid = str(member.id); data["users"][uid] = data["users"].get(uid, 0) + amount
    save_data(data)
    await ctx.send(f"✅ เติมให้ {member.mention} {amount}฿ | เครดิตคงเหลือ: {data['users'][uid]}฿")

@bot.event
async def on_ready():
    bot.add_view(MainMenuView())
    print(f"บอท {bot.user} ออนไลน์แล้ว!")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)).start()
    bot.run(TOKEN)
