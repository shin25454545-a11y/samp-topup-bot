import nextcord
from nextcord.ext import commands
import qrcode
import io
from flask import Flask
from threading import Thread
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PROMPTPAY_NUMBER = os.environ.get("PROMPTPAY_NUMBER")
ROLE_GOLD_ID = int(os.environ.get("ROLE_GOLD_ID"))
ROLE_SILVER_ID = int(os.environ.get("ROLE_SILVER_ID"))
ROLE_BRONZE_ID = int(os.environ.get("ROLE_BRONZE_ID"))

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def generate_qr(amount=None):
    pid = PROMPTPAY_NUMBER
    if len(pid) == 10 and pid.startswith('0'): pid = '66' + pid[1:]
    payload = f"00020101021229370016A0000006770101110113{pid}5303764"
    if amount:
        amt = f"{float(amount):.2f}"
        payload += f"54{len(amt):02d}{amt}"
    payload += "5802TH6304"
    crc = 0xFFFF
    for b in payload.encode('ascii'):
        crc ^= b << 8
        for _ in range(8): crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
    payload += f"{crc & 0xFFFF:04X}"
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

class VipView(nextcord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @nextcord.ui.button(label="Gold 300฿", style=nextcord.ButtonStyle.success)
    async def gold(self, _, i: nextcord.Interaction):
        role = i.guild.get_role(ROLE_GOLD_ID)
        await i.user.add_roles(role)
        await i.response.send_message(f"รับยศ **Gold** แล้ว", file=nextcord.File(generate_qr(300), "qr.png"), ephemeral=True)
    @nextcord.ui.button(label="Silver 200฿", style=nextcord.ButtonStyle.primary)
    async def silver(self, _, i: nextcord.Interaction):
        role = i.guild.get_role(ROLE_SILVER_ID)
        await i.user.add_roles(role)
        await i.response.send_message(f"รับยศ **Silver** แล้ว", file=nextcord.File(generate_qr(200), "qr.png"), ephemeral=True)
    @nextcord.ui.button(label="Bronze 100฿", style=nextcord.ButtonStyle.secondary)
    async def bronze(self, _, i: nextcord.Interaction):
        role = i.guild.get_role(ROLE_BRONZE_ID)
        await i.user.add_roles(role)
        await i.response.send_message(f"รับยศ **Bronze** แล้ว", file=nextcord.File(generate_qr(100), "qr.png"), ephemeral=True)

@bot.command()
async def เมนู(ctx):
    embed = nextcord.Embed(title="🏪 ร้านค้า VIP", description="กดปุ่มเลือกยศที่ต้องการ", color=0x00ff00)
    await ctx.send(embed=embed, view=VipView())

@bot.event
async def on_ready():
    bot.add_view(VipView())
    print(f"Bot {bot.user} Online แล้ว")

app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
bot.run(BOT_TOKEN)
