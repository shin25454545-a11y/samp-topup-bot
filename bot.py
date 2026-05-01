import discord
from discord.ext import commands
from discord import ui
import os

TOKEN = os.getenv("DISCORD_TOKEN")

# ---------- ตั้งค่าให้ครบ ----------
QR_CODE_URL = "https://i.imgur.com/ใส่ลิ้งQRท่าน.png"  # 1. เปลี่ยนเป็น QR ท่าน
BANNER_URL = "https://i.imgur.com/L8y9Q5q.jpeg"  # 2. รูปรถ Porsche ใช้ได้เลย
WEBSITE_URL = "https://google.com"  # 3. เปลี่ยนเป็นเว็บเซิร์ฟท่าน
LOG_CHANNEL_ID = 1499809858680000712  # 4. ห้องแจ้งเตือนแอดมิน
ADMIN_ROLE_ID = 123456789012345678  # 5. ใส่ ID Role แอดมิน

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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
            await log_channel.send(content="@here", embed=embed_log)
        await interaction.response.send_message("✅ แจ้งเติมเงินสำเร็จ ส่งสลิปในแชทนี้ได้เลย", ephemeral=True)

class ConfirmTopupView(ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @ui.button(label="📝 กดที่นี่หลังโอนเสร็จ", style=discord.ButtonStyle.blurple)
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TopupModal())

class MainMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="เติมเงิน", style=discord.ButtonStyle.green, emoji="💰", custom_id="topup_btn")
    async def topup(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(title="สแกน QR เพื่อเติมเงิน", description="สแกนเสร็จแล้วกดปุ่มด้านล่างเพื่อแจ้งโอน", color=0x2ecc71)
        embed.set_image(url=QR_CODE_URL)
        await interaction.response.send_message(embed=embed, view=ConfirmTopupView(), ephemeral=True)

    @ui.button(label="เช็คเครดิต", style=discord.ButtonStyle.blurple, emoji="💳", custom_id="credit_btn")
    async def credit(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"**{interaction.user.display_name}**\nเครดิตคงเหลือ: 0 บาท", ephemeral=True)

    @ui.button(label="ร้านค้า VIP", style=discord.ButtonStyle.gray, emoji="🛒", custom_id="vip_btn", row=1)
    async def vip(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="👑 ร้านค้า VIP",
            description="**VIP 30 วัน** - 99 บาท\n**VIP 90 วัน** - 259 บาท\n\nเติมเงินแล้วแจ้งแอดมินเพื่อรับยศ",
            color=0x9b59b6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="แอดมินเติมเงิน", style=discord.ButtonStyle.red, emoji="⚙️", custom_id="admin_btn", row=1)
    async def admin(self, interaction: discord.Interaction, button: ui.Button):
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("❌ ปุ่มนี้สำหรับแอดมินเท่านั้น", ephemeral=True)
        await interaction.response.send_message("แผงแอดมิน: เดี๋ยวทำคำสั่ง `!addmoney @user จำนวน` ให้", ephemeral=True)

    @ui.button(label="เว็บไซต์", style=discord.ButtonStyle.link, emoji="🌐", url=WEBSITE_URL, row=2)
    async def website(self, interaction: discord.Interaction, button: ui.Button):
        pass

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
    bot.add_view(MainMenuView())
    print(f"บอท {bot.user} ออนไลน์แล้ว!")

bot.run(TOKEN)
