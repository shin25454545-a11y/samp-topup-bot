import nextcord
from nextcord.ext import commands
from nextcord import ui
import os
from flask import Flask, render_template_string
import threading
import json

TOKEN = os.getenv("DISCORD_TOKEN")

# ---------- ตั้งค่า ----------
QR_CODE_URL = "https://i.imgur.com/ใส่ลิ้งQRท่าน.png" # เปลี่ยนเป็น QR ท่าน
BANNER_URL = "https://i.imgur.com/L8y9Q5q.jpeg" # รูปรถเดิม
LOG_CHANNEL_ID = 1499809858680000712 # ห้องแจ้งโอน
ADMIN_ROLE_ID = 123456789012345678 # ID Role แอดมิน
DATA_FILE = "topup_data.json"

# ---------- ส่วนเว็บ Dashboard ----------
app = Flask(__name__)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"today": 0, "month": 0, "total": 0, "users": {}}
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
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SAMP Dashboard</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box}body{font-family:Kanit,sans-serif;background:#0f1419;color:#fff;padding:20px}
       .header h1{color:#ffd700;font-size:28px;margin-bottom:25px}.card{background:#1a2332;border-radius:15px;padding:20px;margin-bottom:15px}
       .card-label{color:#8899a6;font-size:14px;margin-bottom:8px}.card-value{font-size:36px;font-weight:700}
       .green{color:#2ecc71}.blue{color:#3498db}.yellow{color:#f1c40f}.top-item{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #2c3e50}
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@400;600;700&display=swap" rel="stylesheet">
    </head>
    <body>
        <div class="header"><h1>🏛️ SAMP Dashboard</h1></div>
        <div class="card"><div class="card-label">ยอดเติมวันนี้</div><div class="card-value green">{{ data.today }}฿</div></div>
        <div class="card"><div class="card-label">ยอดเติมเดือนนี้</div><div class="card-value blue">{{ data.month }}฿</div></div>
        <div class="card"><div class="card-label">ยอดเติมทั้งหมด</div><div class="card-value yellow">{{ data.total }}฿</div></div>
        <div class="card"><div class="card-label">🏆 ท็อป 10 สายเปย์</div>
            {% for user_id, amount in top_users %}
            <div class="top-item"><span>{{ loop.index }}. <@{{ user_id }}></span><span class="yellow">{{ amount }}฿</span></div>
            {% endfor %}
        </div>
    </body></html>
    '''
    return render_template_string(html, data=data, top_users=top_users)

# ---------- ส่วนบอท Discord ใช้ nextcord ----------
intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class TopupModal(ui.Modal):
    def __init__(self):
        super().__init__(title="แจ้งเติมเงิน")
        self.ingame_name = ui.TextInput(label="ชื่อในเกม", max_length=32)
        self.amount = ui.TextInput(label="จำนวนเงินที่โอน (บาท)", max_length=5)
        self.add_item(self.ingame_name)
        self.add_item(self.amount)

    async def callback(self, interaction: nextcord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(f"🔔 {interaction.user.mention} แจ้งโอน\nชื่อเกม: {self.ingame_name.value}\nยอด: {self.amount.value}฿")
        await interaction.response.send_message("✅ แจ้งโอนแล้ว รอแอดมินเช็คสลิป", ephemeral=True)

class ConfirmTopupView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="📝 กดที่นี่หลังโอนเสร็จ", style=nextcord.ButtonStyle.blurple)
    async def confirm(self, button, interaction): await interaction.response.send_modal(TopupModal())

class MainMenuView(ui.View):
    def __init__(self): super().__init__(timeout=None)
    @ui.button(label="เติมเงิน", style=nextcord.ButtonStyle.green, emoji="💰")
    async def topup(self, button, interaction):
        embed = nextcord.Embed(title="สแกน QR เพื่อเติมเงิน", color=0x2ecc71).set_image(url=QR_CODE_URL)
        await interaction.response.send_message(embed=embed, view=ConfirmTopupView(), ephemeral=True)
    @ui.button(label="เช็คเครดิต", style=nextcord.ButtonStyle.blurple, emoji="💳")
    async def credit(self, button, interaction):
        credit = load_data()["users"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"**{interaction.user.display_name}**\nเครดิตคงเหลือ: {credit} บาท", ephemeral=True)
    @ui.button(label="ร้านค้า VIP", style=nextcord.ButtonStyle.gray, emoji="🛒", row=1)
    async def vip(self, button, interaction): await interaction.response.send_message("**VIP 30 วัน** - 99 บาท\n**VIP 90 วัน** - 259 บาท", ephemeral=True)
    @ui.button(label="แอดมินเติมเงิน", style=nextcord.ButtonStyle.red, emoji="⚙️", row=1)
    async def admin(self, button, interaction):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles): return await interaction.response.send_message("❌ สำหรับแอดมิน", ephemeral=True)
        await interaction.response.send_message("ใช้ `!addmoney @user จำนวน` เพื่อเติมเงิน", ephemeral=True)

@bot.command()
async def เมนู(ctx):
    embed = nextcord.Embed(title="🏛️ ระบบเติมเงิน & ร้านค้า VIP", description="**ยินดีต้อนรับสู่ร้านค้าเซิฟเรา**", color=0xf1c40f).set_image(url=BANNER_URL)
    await ctx.send(embed=embed, view=MainMenuView())

@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def addmoney(ctx, member: nextcord.Member, amount: int):
    data = load_data()
    data["today"] += amount; data["month"] += amount; data["total"] += amount
    uid = str(member.id); data["users"][uid] = data["users"].get(uid, 0) + amount
    save_data(data)
    await ctx.send(f"✅ เติมให้ {member.mention} {amount}฿ | ยอดรวม: {data['users'][uid]}฿")

@bot.event
async def on_ready():
    bot.add_view(MainMenuView())
    print(f"บอท {bot.user} ออนไลน์แล้ว!")

# ---------- จุดที่แก้: สลับให้ Flask รันใน Thread แทน ----------
if __name__ == '__main__':
    # ให้ Flask รันใน Thread แยก
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)).start()
    # ให้บอทรันใน Main Thread เพราะ nextcord บังคับ
    bot.run(TOKEN)
