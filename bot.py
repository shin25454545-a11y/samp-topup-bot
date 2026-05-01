import discord
from discord.ext import commands
import qrcode
import os
from io import BytesIO
import aiosqlite

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ===== ตั้งค่าจาก Railway Variables =====
PROMPTPAY_NUMBER = os.getenv("PROMPTPAY_NUMBER")
ROLE_GOLD_ID = int(os.getenv("ROLE_GOLD_ID"))
ROLE_SILVER_ID = int(os.getenv("ROLE_SILVER_ID"))
ROLE_BRONZE_ID = int(os.getenv("ROLE_BRONZE_ID"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", 0)) # ใส่ ID ยศแอดมิน เพิ่มใน Railway
# ======================================

DB_PATH = "data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, credit INTEGER DEFAULT 0)")
        await db.commit()

async def get_credit(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT credit FROM users WHERE user_id =?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_credit(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users (user_id, credit) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET credit = credit +?", (user_id, amount, amount))
        await db.commit()

async def remove_credit(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET credit = credit -? WHERE user_id =?", (amount, user_id))
        await db.commit()

def create_qr(amount):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"promptpay://{PROMPTPAY_NUMBER}/{amount}")
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return discord.File(buffer, filename="qr.png")

@bot.event
async def on_ready():
    await init_db()
    print(f'Bot {bot.user} Online แล้ว')

@bot.command()
async def เมนู(ctx):
    embed = discord.Embed(title="🏪 ร้านค้า VIP - ระบบเติมเงิน", description="เลือกเมนูที่ต้องการด้านล่าง", color=0x00ff00)
    view = MainMenuView(ctx.author.id)
    await ctx.send(embed=embed, view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def เติม(ctx, member: discord.Member, amount: int):
    await add_credit(member.id, amount)
    await ctx.send(f"✅ เติมเงิน {amount}฿ ให้ {member.mention} สำเร็จ")

class MainMenuView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="💰 เติมเงิน", style=discord.ButtonStyle.green)
    async def topup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("💰 **ระบบเติมเงิน**\n1. โอนมาที่พร้อมเพย์: `0886560336`\n2. แจ้งสลิปที่แชทนี้พร้อม @แอดมิน\n3. รอแอดมินเติมเครดิตให้ 1-5 นาที", ephemeral=True)

    @discord.ui.button(label="💵 เช็คเครดิต", style=discord.ButtonStyle.blurple)
    async def check_credit(self, interaction: discord.Interaction, button: discord.ui.Button):
        credit = await get_credit(interaction.user.id)
        await interaction.response.send_message(f"💵 **เครดิตของคุณ:** {credit}฿", ephemeral=True)

    @discord.ui.button(label="🏪 ร้านค้า VIP", style=discord.ButtonStyle.gray)
    async def shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🏪 ร้านค้า VIP", description="เลือกยศที่ต้องการซื้อ ระบบจะหักเครดิตอัตโนมัติ", color=0xffd700)
        view = ShopView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def buy_role(self, interaction, role_id, price, role_name):
        credit = await get_credit(interaction.user.id)
        if credit < price:
            await interaction.response.send_message(f"❌ เครดิตไม่พอ ต้องการ {price}฿ แต่คุณมี {credit}฿\nกด `💰 เติมเงิน` ก่อน", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if role in interaction.user.roles:
            await interaction.response.send_message(f"❌ คุณมียศ {role_name} อยู่แล้ว", ephemeral=True)
            return

        await remove_credit(interaction.user.id, price)
        await interaction.user.add_roles(role)
        new_credit = await get_credit(interaction.user.id)
        await interaction.response.send_message(f"✅ ซื้อ {role_name} สำเร็จ! หัก {price}฿\n💵 เครดิตคงเหลือ: {new_credit}฿", ephemeral=True)

    @discord.ui.button(label="VIP Gold 300฿", style=discord.ButtonStyle.yellow)
    async def gold(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_role(interaction, ROLE_GOLD_ID, 300, "VIP Gold")

    @discord.ui.button(label="VIP Silver 200฿", style=discord.ButtonStyle.grey)
    async def silver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_role(interaction, ROLE_SILVER_ID, 200, "VIP Silver")

    @discord.ui.button(label="VIP Bronze 100฿", style=discord.ButtonStyle.blurple)
    async def bronze(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.buy_role(interaction, ROLE_BRONZE_ID, 100, "VIP Bronze")

bot.run(os.getenv("BOT_TOKEN"))
