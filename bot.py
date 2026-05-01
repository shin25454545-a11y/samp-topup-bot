from flask import Flask, render_template_string
import json
import os
from datetime import datetime
import discord
from discord.ext import commands
from discord import ui
import threading

TOKEN = os.getenv("DISCORD_TOKEN")

# ---------- ตั้งค่า ----------
QR_CODE_URL = "https://i.imgur.com/ใส่ลิ้งQRท่าน.png"
BANNER_URL = "https://i.imgur.com/L8y9Q5q.jpeg"
LOG_CHANNEL_ID = 1499809858680000712
ADMIN_ROLE_ID = 123456789012345678 # ใส่ ID Role แอดมิน
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
    html = '''...ใส่ HTML ตัวเดิมจากเมื่อกี้...''' # ย่อไว้ เอาตัวเต็มจากเมื่อกี้มาใส่
    return render_template_string(html, data=data, top_users=top_users)

# ---------- ส่วนบอท Discord ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Modal แจ้งโอน
class TopupModal(ui.Modal, title="แจ้งเติมเงิน"):
    ingame_name = ui.TextInput(label="ชื่อในเกม", max_length=32)
    amount = ui.TextInput(label="จำนวนเงินที่โอน (บาท)", max_length=5)
    async def on_submit(self, interaction: discord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        await log_channel.send(f"🔔 {interaction.user.mention} แจ้งโอน\nชื่อเกม: {self.ingame_name}\nยอด: {self.amount}฿")
        await interaction.response.send_message("✅ แจ้งโอนแล้ว รอแอดมินเช็คสลิป", ephemeral=True)

# View 4 ปุ่มเหมือนเดิม
class MainMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="เติมเงิน", style=discord.ButtonStyle.green, emoji="💰")
    async def topup(self, interaction, button):
        embed = discord.Embed(title="สแกน QR เพื่อเติมเงิน", color=0x2ecc71)
        embed.set_image(url=QR_CODE_URL)
        await interaction.response.send_message(embed=embed, view=ConfirmTopupView(), ephemeral=True)

    @ui.button(label="เช็คเครดิต", style=discord.ButtonStyle.blurple, emoji="💳")
    async def credit(self, interaction, button):
        data = load_data()
        user_credit = data["users"].get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"**{interaction.user.display_name}**\nเครดิตคงเหลือ: {user_credit} บาท", ephemeral=True)

    @ui.button(label="ร้านค้า VIP", style=discord.ButtonStyle.gray, emoji="🛒", row=1)
    async def vip(self, interaction, button):
        await interaction.response.send_message("**VIP 30 วัน** - 99 บาท\n**VIP 90 วัน** - 259 บาท", ephemeral=True)

    @ui.button(label="แอดมินเติมเงิน", style=discord.ButtonStyle.red, emoji="⚙️", row=1)
    async def admin(self, interaction, button):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ สำหรับแอดมินเท่านั้น", ephemeral=True)
        await interaction.response.send_message("ใช้คำสั่ง `!addmoney @user จำนวน` เพื่อเติมเงิน", ephemeral=True)

class ConfirmTopupView(ui.View):
    @ui.button(label="📝 กดที่นี่หลังโอนเสร็จ", style=discord.ButtonStyle.blurple)
    async def confirm(self, interaction, button):
        await interaction.response.send_modal(TopupModal())

@bot.command()
async def เมนู(ctx):
    embed = discord.Embed(title="🏛️ ระบบเติมเงิน & ร้านค้า VIP", description="**ยินดีต้อนรับสู่ร้านค้าเซิฟเรา**", color=0xf1c40f)
    embed.set_image(url=BANNER_URL)
    await ctx.send(embed=embed, view=MainMenuView())

@bot.command()
@commands.has_role(ADMIN_ROLE_ID)
async def addmoney(ctx, member: discord.Member, amount: int):
    data = load_data()
    data["today"] += amount
    data["month"] += amount
    data["total"] += amount
    user_id = str(member.id)
    data["users"][user_id] = data["users"].get(user_id, 0) + amount
    save_data(data)
    await ctx.send(f"✅ เติมให้ {member.mention} {amount}฿ | ยอดรวม: {data['users'][user_id]}฿")

@bot.event
async def on_ready():
    bot.add_view(MainMenuView())
    print(f"บอท {bot.user} ออนไลน์แล้ว!")

# รันคู่กัน
def run_flask(): app.run(host='0.0.0.0', port=8080)
def run_bot(): bot.run(TOKEN)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()
