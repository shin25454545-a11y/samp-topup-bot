import discord
from discord.ext import commands
from discord.ui import Button, View
import os

# ตั้งค่า Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- ส่วนของปุ่มกดในร้านค้า ---
class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None) # ปุ่มไม่หมดอายุ

    @discord.ui.button(label="VIP Gold 300฿", style=discord.ButtonStyle.primary, custom_id="buy_gold")
    async def gold_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ในอนาคตเราจะใส่ระบบเช็คเงินตรงนี้
        await interaction.response.send_message("คุณเลือกซื้อ VIP Gold (ฟีเจอร์นี้กำลังพัฒนา)", ephemeral=True)

    @discord.ui.button(label="VIP Silver 150฿", style=discord.ButtonStyle.secondary, custom_id="buy_silver")
    async def silver_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("คุณเลือกซื้อ VIP Silver (ฟีเจอร์นี้กำลังพัฒนา)", ephemeral=True)

# --- คำสั่งเรียกเมนูร้านค้า ---
@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🏪 ร้านค้า VIP",
        description="กดปุ่มด้านล่างเพื่อซื้อยศที่ต้องการได้เลยครับ\n\n**VIP Gold** - ราคา 300฿\n**VIP Silver** - ราคา 150฿",
        color=discord.Color.blue()
    )
    # ใส่รูปภาพประกอบถ้ามี
    embed.set_thumbnail(url="https://flaticon.com") 
    await ctx.send(embed=embed, view=ShopView())

@bot.event
async def on_ready():
    print(f'น้องบอท {bot.user} ออนไลน์แล้วจ้า!')

# ดึง Token จาก Railway Variables
token = os.getenv('BOT_TOKEN')
bot.run(token)
