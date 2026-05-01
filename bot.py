import discord
from discord.ext import commands
from discord import ui
import os

TOKEN = os.getenv("DISCORD_TOKEN")

# ---------- ตั้งค่า ----------
QR_CODE_URL = "https://i.imgur.com/YourQRCode.png"  # เปลี่ยนเป็นลิ้งค์ QR ท่าน
BANNER_URL = "https://i.imgur.com/yourcarimage.png" # เปลี่ยนเป็นลิ้งค์รูปรถในภาพ
WEBSITE_URL = "https://yoursampserver.com"  # ใส่เว็บเซิร์ฟท่าน
LOG_CHANNEL_ID = 1499809858680000712
ADMIN_ROLE_ID = ใส่ไอดีRoleแอดมิน # ใส่ ID Role แอดมิน ถึงจะกดปุ่มแดงได้

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Modal แจ้งโอน ----------
class TopupModal(ui.Modal, title="แจ้งเติมเงิน"):
    ingame_name = ui.TextInput(label="ชื่อในเกม", placeholder="เช่น Devil_Devil", max_length=32)
    amount = ui.TextInput(label="จำนวนเงินที่โอน (บาท)", placeholder="เช่น 50", max_length=5)

    async def on_submit(self, interaction: discord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        embed_log = discord.Embed(
            title="🔔 มีรายการแจ้งโอนใหม่",
            description=f"**คนแจ้ง:** {interaction.user.mention}\n**ชื่อในเกม:** {self.ingame_name}\n**ยอดแจ้ง:** {self.amount} บาท",
            color=0xf39c12
        )
        if log_channel:
            await log_channel.send(embed=embed_log)
        await interaction.response.send_message("✅ แจ้งเติมเงินสำเร็จ ส่งสลิปในแชทนี้ได้เลย แอดมินจะเติมให้ไวที่สุด", ephemeral=True)

# ---------- View หลัก 4 ปุ่ม ----------
class MainMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="เติมเงิน", style=discord.ButtonStyle.green, emoji="💰", custom_id="topup")
    async def topup_button(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(title="สแกน QR เพื่อเติมเงิน", color=0x2ecc71)
        embed.set_image(url=QR_CODE_URL)
        await interaction.response.send_message(embed=embed, view=ConfirmTopupView(), ephemeral=True)

    @ui.button(label="เช็คเครดิต", style=discord.ButtonStyle.blurple, emoji="💳", custom_id="check_credit")
    async def credit_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"**{interaction.user.display_name}**\nเครดิตคงเหลือ: 0 บาท\n\nเติมเงินเพื่อเพิ่มเครดิตได้เลย", ephemeral=True)

    @ui.button(label="ร้านค้า VIP", style=discord.ButtonStyle.gray, emoji="🛒", custom_id="vip_shop", row=1)
    async def vip_button(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="👑 ร้านค้า VIP",
            description="**VIP 30 วัน** - 99 บาท\n**VIP 90 วัน** - 259 บาท\n\nกดปุ่ม `เติมเงิน` เพื่อซื้อ แล้วแจ้งแอดมิน",
            color=0x9b59b6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="แอดมินเติมเงิน", style=discord.ButtonStyle.red, emoji="⚙️", custom_id="admin_topup", row=1)
    async def admin_button(self, interaction: discord.Interaction, button: ui.Button):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ คำสั่งนี้สำหรับแอดมินเท่านั้น", ephemeral=True)
        await interaction.response.send_message("แผงแอดมิน: ใช้คำสั่ง `!addmoney @ชื่อ จำนวน` เพื่อเติมเงิน", ephemeral=True)

    @ui.button(label="เว็บไซต์เซิร์ฟ", style=discord.ButtonStyle.link, emoji="🌐", url=WEBSITE_URL, row=2)
    async def website_button(self, interaction: discord.Interaction, button: ui.Button):
        pass # ปุ่ม Link กดแล้วเด้งไปเว็บเอง

class ConfirmTopupView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @ui.button(label="📝 กดที่นี่หลังโอนเสร็จ", style=discord.ButtonStyle.blurple)
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TopupModal())

# ---------- คำสั่ง !เมนู ----------
@bot.command()
async def เมนู(ctx):
    embed = discord.Embed(
        title="🏛️ ระบบเติมเงิน & ร้านค้า VIP",
        description="**ยินดีต้อนรับสู่ร้านค้าเซิฟเรา**\nเติมเงิน รับยศ อัพเกรดได้ทันที ระบบออโต้ 24 ชม.",
        color=0xf1c40f
    )
    embed.set_image(url=BANNER_URL)
    embed.add_field(
        name="🔥 โปรโมชั่นเปิดเซิฟ | ใช้ /daily รับฟรี 10฿ ทุกวัน",
        value="| สินค้ามีจำนวนจำกัด!",
        inline=False
    )
    await ctx.send(embed=embed, view=MainMenuView())

@bot.event
async def on_ready():
    bot.add_view(MainMenuView()) # ทำให้ปุ่มกดได้ตลอดแม้รีบอท
    print(f"บอท {bot.user} ออนไลน์แล้ว!")

bot.run(TOKEN)
