import discord
from discord.ext import commands
from discord.ui import Button, View

# --- 1. ตั้งค่าพื้นฐาน ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 2. ส่วนของระบบปุ่มกด (Interaction) ---
class MainMenuView(View):
    def __init__(self):
        super().__init__(timeout=None) # ปุ่มใช้งานได้ตลอด

    @discord.ui.button(label="เช็คยอดเงิน", style=discord.ButtonStyle.green, emoji="💰")
    async def balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ตรงนี้แก้ไขยอดเงินตาม Database ของคุณได้เลย
        await interaction.response.send_message("💰 ยอดเงินคงเหลือของคุณคือ: `9,950 ฿`", ephemeral=True)

    @discord.ui.button(label="เติมเงิน (QR)", style=discord.ButtonStyle.blurple, emoji="💳")
    async def topup(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💳 ช่องทางการเติมเงิน",
            description="สแกน QR Code แล้วส่งสลิปในแชทนี้\n━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.green()
        )
        embed.add_field(name="📱 พร้อมเพย์", value="`088-656-0336`", inline=True)
        # ลิงก์รูป QR Code ของคุณ (ถ้ามี URL อื่นเปลี่ยนได้เลย)
        embed.set_image(url="https://promptpay.io") 
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="รายละเอียด VIP", style=discord.ButtonStyle.danger, emoji="👑")
    async def vip_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👑 รายละเอียดสมาชิก VIP",
            description="🥉 **Bronze** : 50฿ (30 วัน)\n🥈 **Silver** : 150฿ (30 วัน)\n🥇 **Gold** : 300฿ (30 วัน)\n━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- 3. คำสั่งหลัก (!setup, !เมนู, !menu) ---
@bot.command(name="setup", aliases=["เมนู", "menu"]) # ใส่ Aliases ให้พิมพ์ได้หลายแบบ
async def main_menu(ctx):
    embed = discord.Embed(
        title="🤖 ระบบจัดการสมาชิก (MEMBER SYSTEM)",
        description=f"สวัสดีครับคุณ {ctx.author.mention} 👋\nเลือกทำรายการด้านล่างได้เลยครับ\n━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.blue()
    )
    # เพิ่มข้อมูลหน้าเมนู
    embed.add_field(name="💰 ยอดเงินปัจจุบัน", value="`9,950 ฿`", inline=True)
    embed.add_field(name="🎖️ ยศปัจจุบัน", value="`Standard`", inline=True)
    embed.set_footer(text="ระบบทำงานอัตโนมัติ 24 ชม.")
    
    # ส่งเมนูพร้อมปุ่ม
    await ctx.send(embed=embed, view=MainMenuView())

# --- 4. รันบอท ---
# นำ Token จาก Discord Developer Portal มาใส่ที่นี่
# bot.run('YOUR_BOT_TOKEN_HERE')
