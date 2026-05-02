import discord
from discord.ext import commands
from discord.ui import Button, View

# --- ตั้งค่า Bot ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- ส่วนของปุ่มกด (Interaction) ---
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None) # ปุ่มอยู่ได้ตลอดกาล

    @discord.ui.button(label="เช็คยอดเงิน", style=discord.ButtonStyle.green, emoji="💰")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ตรงนี้ดึงข้อมูลจาก Database ของคุณมาใส่แทนเลขสมมติได้เลย
        await interaction.response.send_message(f"💰 ยอดเงินปัจจุบันของคุณคือ: `9,950 ฿`", ephemeral=True)

    @discord.ui.button(label="เติมเงิน (QR)", style=discord.ButtonStyle.blurple, emoji="💳")
    async def topup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💳 ช่องทางการเติมเงิน (TOP-UP)",
            description="สแกน QR เพื่อเติมเงิน แล้วส่งสลิปในแชทได้เลย\n━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.green()
        )
        embed.add_field(name="📱 พร้อมเพย์", value="`088-656-0336`", inline=True)
        embed.set_image(url="https://promptpay.io") # ใส่ URL รูป QR ของคุณ
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="ซื้อยศ VIP", style=discord.ButtonStyle.danger, emoji="👑")
    async def vip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👑 เลือกแพ็กเกจ VIP ที่ต้องการ",
            description="🥉 **Bronze** : 50฿\n🥈 **Silver** : 150฿\n🥇 **Gold** : 300฿\n━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- คำสั่ง !เมนู หรือ !menu ---
@bot.command(name="เมนู", aliases=["menu"])
async def menu_command(ctx):
    embed = discord.Embed(
        title="🤖 ระบบจัดการสมาชิก (MEMBER SYSTEM)",
        description=f"สวัสดีครับคุณ {ctx.author.mention} 👋\nยินดีต้อนรับ! เลือกทำรายการที่ต้องการด้านล่าง\n━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.blue()
    )
    embed.add_field(name="💰 ยอดเงิน", value="`9,950 ฿`", inline=True)
    embed.add_field(name="🎖️ สถานะ", value="`VIP Gold`", inline=True)
    embed.set_footer(text="ระบบทำงานอัตโนมัติ 24 ชม.")
    # embed.set_thumbnail(url="ใส่ลิงก์โลโก้ร้าน")

    await ctx.send(embed=embed, view=MenuView())

# --- รัน Bot ---
# bot.run('ใส่_TOKEN_บอท_ของคุณที่นี่')
