import discord
from discord.ext import commands
import os
import sqlite3
import asyncio
from datetime import datetime

# --- ตั้งค่าส่วนตัว ---
OWNER_ID = 1250051906076934154 # ID เจ้าของดิส

ROLE_IDS = {
    "VIP Gold": 1417791717300133958,
    "VIP Silver": 1417791801475440650,
    "VIP Bronze": 1417791858399715348
}

ROLE_PRICES = {
    "VIP Gold": 300,
    "VIP Silver": 150,
    "VIP Bronze": 50
}
# ---------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- ระบบฐานข้อมูล ---
def setup_database():
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, item TEXT, price INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id =?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    cursor.execute("UPDATE users SET balance = balance +? WHERE user_id =?", (amount, user_id))
    conn.commit()
    conn.close()

def add_transaction(user_id, username, item, price):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO transactions (user_id, username, item, price, timestamp) VALUES (?,?,?,?,?)", (user_id, username, item, price, timestamp))
    conn.commit()
    conn.close()

# --- ส่วนของปุ่มกด ---
class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for role_name, price in ROLE_PRICES.items():
            self.add_item(discord.ui.Button(label=f"{role_name} {price}฿", style=discord.ButtonStyle.primary, custom_id=f"buy_{role_name}"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data['custom_id']
        if custom_id.startswith('buy_'):
            role_name = custom_id.split('_')[1]
            await self.handle_purchase(interaction, role_name)
        return True

    async def handle_purchase(self, interaction: discord.Interaction, role_name: str):
        user = interaction.user
        guild = interaction.guild
        price = ROLE_PRICES[role_name]
        role_id = ROLE_IDS[role_name]
        role = guild.get_role(role_id)

        if not role:
            return await interaction.response.send_message(f"❌ ไม่พบยศ {role_name} ในเซิร์ฟเวอร์", ephemeral=True)

        balance = get_balance(user.id)
        if balance < price:
            return await interaction.response.send_message(f"❌ เครดิตไม่พอ! คุณมี {balance}฿ แต่ยศนี้ราคา {price}฿", ephemeral=True)

        try:
            await user.add_roles(role)
            update_balance(user.id, -price)
            add_transaction(user.id, str(user), role_name, price)
            await interaction.response.send_message(f"✅ ซื้อยศ {role_name} สำเร็จ! เครดิตคงเหลือ {balance - price}฿", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ บอทไม่มีสิทธิ์ให้ยศ! ลากยศบอทไว้บนสุด", ephemeral=True)

class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 เช็คเครดิต", style=discord.ButtonStyle.green, custom_id="check_balance")
    async def check_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        balance = get_balance(interaction.user.id)
        await interaction.response.send_message(f"💰 {interaction.user.mention} ท่านมีเครดิต **{balance}฿**", ephemeral=True)

    @discord.ui.button(label="🛒 ร้านค้า VIP", style=discord.ButtonStyle.blurple, custom_id="open_shop")
    async def open_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🏪 ร้านค้า VIP", description="กดปุ่มด้านล่างเพื่อซื้อยศที่ต้องการได้เลย", color=discord.Color.gold())
        for role_name, price in ROLE_PRICES.items():
            embed.add_field(name=role_name, value=f"ราคา {price}฿", inline=True)
        await interaction.response.send_message(embed=embed, view=ShopView(), ephemeral=True)

    @discord.ui.button(label="📜 ประวัติการซื้อ", style=discord.ButtonStyle.gray, custom_id="check_history")
    async def check_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT item, price, timestamp FROM transactions WHERE user_id =? ORDER BY id DESC LIMIT 5", (interaction.user.id,))
        results = cursor.fetchall()
        conn.close()
        if not results:
            return await interaction.response.send_message("❌ คุณยังไม่มีประวัติการซื้อ", ephemeral=True)

        embed = discord.Embed(title=f"📜 ประวัติการซื้อ 5 รายการล่าสุดของ {interaction.user.display_name}", color=discord.Color.blue())
        history_text = ""
        for item, price, timestamp in results:
            history_text += f"**{item}** - {price}฿ `เมื่อ {timestamp}`\n"
        embed.description = history_text
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- คำสั่งบอท ---
@bot.event
async def on_ready():
    bot.add_view(ShopView())
    bot.add_view(ControlPanelView())
    print(f'บอท {bot.user} ออนไลน์แล้ว!')
    print('------')

@bot.command(name='เมนู')
async def menu(ctx):
    if ctx.author.id!= OWNER_ID:
        return await ctx.send("❌ คำสั่งนี้ใช้ได้เฉพาะเจ้าของเซิร์ฟเวอร์เท่านั้น", delete_after=5)

    embed = discord.Embed(
        title="🎛️ แผงควบคุมสมาชิก",
        description="ยินดีต้อนรับสู่ร้าน VIP! กดปุ่มด้านล่างเพื่อทำรายการต่างๆได้เลย",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    embed.set_footer(text="ร้าน VIP เปิด 24 ชม.")
    await ctx.send(embed=embed, view=ControlPanelView())

@bot.command(name='เติม')
@commands.has_permissions(administrator=True)
async def add_money(ctx, member: discord.Member, amount: int):
    if amount <= 0: return await ctx.send("❌ จำนวนเงินต้องมากกว่า 0")
    update_balance(member.id, amount)
    await ctx.send(f"✅ เติมเงินให้ {member.mention} จำนวน **{amount}฿** สำเร็จ!")

@bot.command(name='ยอดขาย')
@commands.has_permissions(administrator=True)
async def sales_report(ctx):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(price), COUNT(id) FROM transactions")
    result = cursor.fetchone()
    conn.close()
    total_sales = result[0] if result[0] else 0
    total_items = result[1] if result[1] else 0
    embed = discord.Embed(title="💰 สรุปยอดขายร้าน", color=discord.Color.green())
    embed.add_field(name="ยอดขายรวม", value=f"{total_sales}฿")
    embed.add_field(name="จำนวนที่ขายได้", value=f"{total_items} ยศ")
    await ctx.send(embed=embed)

# --- รันบอท ---
setup_database()
TOKEN = os.getenv("BOT_TOKEN")
if TOKEN is None:
    print("❌ ไม่เจอ BOT_TOKEN ใน Environment Variables")
else:
    bot.run(TOKEN)
