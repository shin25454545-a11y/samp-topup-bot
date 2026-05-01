import discord
from discord.ext import commands
from discord import ui
import os

TOKEN = os.getenv("DISCORD_TOKEN")

# ---------- ตั้งค่า QR ของท่าน ----------
QR_CODE_URL = "https://i.imgur.com/YourQRCode.png"  # เอาลิ้งค์รูป QR พร้อมเพย์ท่านมาใส่
PROMPTPAY_NAME = "นายเด็กชาย ทดสอบ"  # ชื่อบัญชีพร้อมเพย์
LOG_CHANNEL_ID = 1499809858680000712  # ห้องแจ้งเตือนแอดมิน

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Modal กรอกข้อมูล ----------
class TopupModal(ui.Modal, title="แจ้งเติมเงิน"):
    ingame_name = ui.TextInput(label="ชื่อในเกม", placeholder="เช่น Devil_Devil", max_length=32)
    amount = ui.TextInput(label="จำนวนเงินที่โอน (บาท)", placeholder="เช่น 50", max_length=5)

    async def on_submit(self, interaction: discord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        embed_log = discord.Embed(
            title="🔔 มีรายการแจ้งโอนใหม่",
            description=f"**คนแจ้ง:** {interaction.user.mention}\n**ชื่อในเกม:** {self.ingame_name}\n**ยอดแจ้ง:** {self.amount} บาท\n\n**แอดมินเช็คสลิปแล้วเติมให้ด้วย**",
            color=0xf39c12
        )
        if log_channel:
            await log_channel.send(embed=embed_log)
        
        await interaction.response.send_message(f"✅ แจ้งเติมเงินสำเร็จ กรุณาส่งสลิปในห้องนี้เพื่อยืนยัน\nแอดมินจะเติมให้ภายใน 5 นาที", ephemeral=True)

# ---------- View ปุ่ม ----------
class MenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="💵 เติมเงินสแกน QR", style=discord.ButtonStyle.green, custom_id="qr_button")
    async def qr_button(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="สแกน QR เพื่อเติมเงิน",
            description=f"**ชื่อบัญชี:** {PROMPTPAY_NAME}\n**สแกนเสร็จแล้วกดปุ่มด้านล่างเพื่อแจ้งโอน**",
            color=0x2ecc71
        )
        embed.set_image(url=QR_CODE_URL)
        await interaction.response.send_message(embed=embed, view=ConfirmView(), ephemeral=True)

class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @ui.button(label="📝 กดที่นี่หลังโอนเสร็จ", style=discord.ButtonStyle.blurple)
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TopupModal())

# ---------- คำสั่ง ----------
@bot.command()
async def เมนู(ctx):
    embed = discord.Embed(
        title="🎮 ระบบเติมเงิน SAMP",
        description="กดปุ่มด้านล่างเพื่อดู QR Code สำหรับเติมเงิน",
        color=0x1abc9c
    )
    await ctx.send(embed=embed, view=MenuView())

@bot.event
async def on_ready():
    bot.add_view(MenuView())
    print(f"บอท {bot.user} ออนไลน์แล้ว!")

bot.run(TOKEN)
