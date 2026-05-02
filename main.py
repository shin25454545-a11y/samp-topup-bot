import discord
from discord.ext import commands
import os
import sqlite3
import asyncio
from datetime import datetime
import qrcode
import io

# --- ตั้งค่าส่วนตัว ---
OWNER_ID = 1250051906076934154 # ID เจ้าของดิส
PROMPTPAY_ID = "0886560336" # เบอร์พร้อมเพย์ท่าน ใส่ให้แล้ว

ROLE_IDS = {
    "VIP Gold": 1499228473095356597,
    "VIP Silver": 1499228661335724072,
    "VIP Bronze": 1499228752234942566
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS pending_topup (user_id INTEGER PRIMARY KEY, amount INTEGER, timestamp TEXT)''')
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

def set_pending_topup(user_id, amount):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("REPLACE INTO pending_topup (user_id, amount, timestamp) VALUES (?,?,?)", (user_id, amount, timestamp))
    conn.commit()
    conn.close()

# --- สร้าง QR PromptPay ---
def generate_promptpay_qr(amount):
    from promptpay import qrcode as pp_qr
    payload = pp_qr.generate_payload(PROMPTPAY_ID, amount)
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="promptpay.png")

# --- Modal ใส่จำนวนเงิน ---
class TopupModal(discord.ui.Modal, title="เติมเงินเข้ากระเป๋า"):
    amount = discord.ui.TextInput(
        label="จำนวนเงินที่ต้องการเติม",
        placeholder="ใส่แค่ตัวเลข เช่น 100",
        required=True,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_int = int(self.amount.value)
            if amount_int <= 0:
                return await interaction.response.send_message("❌ จำนวนเงินต้องมากกว่า 0", ephemeral=True)
            if amount_int > 5000:
                return await interaction.response.send_message("❌ เติมได้สูงสุดครั้งละ 5000฿", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ กรุณาใส่เฉพาะตัวเลข", ephemeral=True)

        set_pending_topup(interaction.user.id, amount_int)
        qr_file = generate_promptpay_qr(amount_int)

        embed = discord.Embed(
            title="💵 สแกน QR เพื่อเติมเงิน",
            description=f"**ยอดที่ต้องชำระ: {amount_int}฿**\n**เลขพร้อมเพย์: {PROMPTPAY_ID}**\n\n1. สแกน QR ด้านล่างด้วยแอพธนาคาร\n2. โอนเงินให้เรียบร้อย\n3. กดปุ่ม `✅ ฉันโอนแล้ว` ด้านล่าง\n4. รอแอดมินตรวจสอบ 1-3 นาที",
            color=discord.Color.green()
        )
        embed.set_image(url="attachment://promptpay.png")
        embed.set_footer(text="ระบบจะแจ้งเตือนเมื่อแอดมินอนุมัติยอดแล้ว")

        await interaction.response.send_message(embed=embed, file=qr_file, view=ConfirmTopupView(), ephemeral=True)

# --- ปุ่มยืนยันโอนแล้ว ---
class ConfirmTopupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.button(label="✅ ฉันโอนแล้ว", style=discord.ButtonStyle.green)
    async def confirm_topup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📨 แจ้งแอดมินแล้ว! กรุณารอตรวจสอบยอด 1-3 นาที\nหากเงินเข้าแล้วบอทจะ DM ไปหาท่านทันที", ephemeral=True)

        owner = await bot.fetch_user(OWNER_ID)
        conn = sqlite3.connect('shop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT amount FROM pending_topup WHERE user_id=?", (interaction.user.id,))
        result = cursor.fetchone()
        conn.close()
        amount = result[0] if result else 0

        await owner.send(f"🔔 **แจ้งเตือนเติมเงิน**\nลูกค้า: {interaction.user.mention} `{interaction.user.id}`\nยอด: **{amount}฿**\n\nเช็คสลิปแล้วพิมพ์ `!อนุมัติ {interaction.user.id}` เพื่อเติมเงินให้ลูกค้า")

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

    @discord.ui.button(label="💵 เติมเงิน", style=discord.ButtonStyle.green, custom_id="topup", row=0)
    async def topup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopupModal())

    @discord.ui.button(label="💰 เช็คเครดิต", style=discord.ButtonStyle.gray, custom_id="check_balance", row=0)
    async def check_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        balance = get_balance(interaction.user.id)
        await interaction.response.send_message(f"💰 {interaction.user.mention} ท่านมีเครดิต **{balance}฿**", ephemeral=True)

    @discord.ui.button(label="🛒 ร้านค้า VIP", style=discord.ButtonStyle.blurple, custom_id="open_shop", row=1)
    async def open_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🏪 ร้านค้า VIP", description="กดปุ่มด้านล่างเพื่อซื้อยศที่ต้องการได้เลย", color=discord.Color.gold())
        for role_name, price in ROLE_PRICES.items():
            embed.add_field(name=role_name, value=f"ราคา {price}฿", inline=True)
        await interaction.response.send_message(embed=embed, view=ShopView(), ephemeral=True)

    @discord.ui.button(label="📜 ประวัติการซื้อ", style=discord.ButtonStyle.gray, custom_id="check_history", row=1)
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
    bot.add_view(ConfirmTopupView())
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
    embed.set_footer(text="ร้าน VIP เปิด 24 ชม. | เติมเงินออโต้ผ่าน QR")
    await ctx.send(embed=embed, view=ControlPanelView())

@bot.command(name='อนุมัติ')
@commands.has_permissions(administrator=True)
async def approve_topup(ctx, member: discord.Member):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM pending_topup WHERE user_id=?", (member.id,))
    result = cursor.fetchone()
    if not result:
        return await ctx.send(f"❌ ไม่พบรายการเติมเงินที่รออนุมัติของ {member.mention}")

    amount = result[0]
    update_balance(member.id, amount)
    cursor.execute("DELETE FROM pending_topup WHERE user_id=?", (member.id,))
    conn.commit()
    conn.close()

    await ctx.send(f"✅ อนุมัติเติมเงินให้ {member.mention} จำนวน **{amount}฿** สำเร็จ!")
    try:
        await member.send(f"🎉 เติมเงินสำเร็จ! คุณได้รับเครดิต **{amount}฿** แล้ว\nเครดิตปัจจุบัน: **{get_balance(member.id)}฿**")
    except:
        pass

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
