import discord
from discord.ext import commands
import os
import sqlite3
import asyncio
from datetime import datetime
import qrcode
import io

# --- ตั้งค่าส่วนตัว ---
OWNER_ID = 1250051906076934154
PROMPTPAY_ID = "0886560336"

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

def get_pending_topup(user_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM pending_topup WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def delete_pending_topup(user_id):
    conn = sqlite3.connect('shop.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_topup WHERE user_id=?", (user_id,))
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

# --- ปุ่มอนุมัติสำหรับแอดมิน ---
class AdminApproveView(discord.ui.View):
    def __init__(self, user_id, amount):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.amount = amount

    @discord.ui.button(label="✅ อนุมัติ", style=discord.ButtonStyle.green, custom_id="admin_approve_topup")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= OWNER_ID:
            return await interaction.response.send_message("❌ ปุ่มนี้สำหรับเจ้าของร้านเท่านั้น", ephemeral=True)

        pending_amount = get_pending_topup(self.user_id)
        if pending_amount == 0:
            await interaction.response.edit_message(content="⚠️ รายการนี้ถูกอนุมัติไปแล้ว", embed=None, view=None)
            return await interaction.followup.send("รายการนี้อนุมัติไปแล้ว", ephemeral=True)

        update_balance(self.user_id, pending_amount)
        delete_pending_topup(self.user_id)

        member = await bot.fetch_user(self.user_id)
        await interaction.response.edit_message(content=f"✅ อนุมัติเติมเงินให้ {member.mention} จำนวน **{pending_amount}฿** สำเร็จแล้ว", embed=None, view=None)

        try:
            await member.send(f"🎉 เติมเงินสำเร็จ! คุณได้รับเครดิต **{pending_amount}฿** แล้ว\nเครดิตปัจจุบัน: **{get_balance(self.user_id)}฿**")
        except:
            pass

    @discord.ui.button(label="❌ ปฏิเสธ", style=discord.ButtonStyle.red, custom_id="admin_reject_topup")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= OWNER_ID:
            return await interaction.response.send_message("❌ ปุ่มนี้สำหรับเจ้าของร้านเท่านั้น", ephemeral=True)

        pending_amount = get_pending_topup(self.user_id)
        if pending_amount == 0:
            await interaction.response.edit_message(content="⚠️ รายการนี้ถูกจัดการไปแล้ว", embed=None, view=None)
            return

        delete_pending_topup(self.user_id)
        member = await bot.fetch_user(self.user_id)
        await interaction.response.edit_message(content=f"❌ ปฏิเสธรายการเติมเงินของ {member.mention} จำนวน **{pending_amount}฿** แล้ว", embed=None, view=None)

        try:
            await member.send(f"❌ รายการเติมเงิน **{pending_amount}฿** ของคุณถูกปฏิเสธ กรุณาติดต่อแอดมิน")
        except:
            pass

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
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ ฉันโอนแล้ว", style=discord.ButtonStyle.green, custom_id="confirm_topup")
    async def confirm_topup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📨 แจ้งแอดมินแล้ว! กรุณารอตรวจสอบยอด 1-3 นาที\nหากเงินเข้าแล้วบอทจะ DM ไปหาท่านทันที", ephemeral=True)

        owner = await bot.fetch_user(OWNER_ID)
        amount = get_pending_topup(interaction.user.id)

        embed = discord.Embed(
            title="🔔 แจ้งเตือนเติมเงิน",
            description=f"ลูกค้า: {interaction.user.mention} `{interaction.user.id}`\nยอด: **{amount}฿**\n\nเช็คสลิปแล้วกดปุ่มด้านล่างเพื่ออนุมัติ",
            color=discord.Color.orange()
        )
        await owner.send(embed=embed, view=AdminApproveView(interaction.user.id, amount))

# --- ระบบซื้อ VIP แบบ Select Menu ---
class VIPSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="VIP Bronze - 50฿", description="เริ่มต้น EXP x1.5 | 30 วัน", emoji="🥉"),
            discord.SelectOption(label="VIP Silver - 150฿", description="ยอดนิยม EXP x2.0 + /fly | 30 วัน", emoji="🥈"),
            discord.SelectOption(label="VIP Gold - 300฿", description="ตัวท็อป EXP x3.0 + /god | 30 วัน", emoji="🥇")
        ]
        super().__init__(placeholder="เลือกแพ็กเกจ VIP ที่ต้องการ...", min_values=1, max_values=1, options=options, custom_id="vip_select")

    async def callback(self, interaction: discord.Interaction):
        role_name = self.values[0].split(' - ')[0]
        await self.view.handle_purchase(interaction, role_name)

class VIPShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VIPSelect())

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

            embed = discord.Embed(
                title="<a:verify:123> ซื้อสำเร็จ!",
                description=f"ยินดีด้วย {user.mention} คุณได้รับ **{role_name}** แล้ว!",
                color=0x2ECC71
            )
            embed.add_field(name="💰 เครดิตคงเหลือ", value=f"`{balance - price}฿`", inline=True)
            embed.add_field(name="⏰ หมดอายุ", value="`30 วัน`", inline=True)
            embed.set_footer(text="DM หาแอดมินเพื่อรับโค้ด VIP ในเกม")
            embed.set_thumbnail(url="https://i.imgur.com/uB6fE8Q.png")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ บอทไม่มีสิทธิ์ให้ยศ! ลากยศบอทไว้บนสุด", ephemeral=True)

# --- แผงควบคุมหลัก ---
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
        # Embed 1: แบนเนอร์หลัก
        banner_embed = discord.Embed(
            description="# <a:gem:1234567890> **PREMIUM MEMBERSHIP**\n### ปลดล็อคขีดจำกัด ขึ้นเป็นผู้ปกครองเซิร์ฟเวอร์",
            color=0x000000
        )
        banner_embed.set_image(url="https://i.imgur.com/your_banner.gif") # เปลี่ยนเป็นแบนเนอร์เกมท่าน

        # Embed 2: Bronze Card
        bronze_embed = discord.Embed(
            title="🥉 BRONZE TIER",
            description="```yaml\nราคา: 50฿ | อายุ: 30 วัน\n```",
            color=0xCD7F32
        )
        bronze_embed.add_field(
            name="PERKS",
            value="> `⚡` **EXP Multiplier** `x1.5`\n"
                  "> `🍀` **Drop Rate** `+20%`\n"
                  "> `🎁` **Daily Kit** `/kit bronze`\n"
                  "> `📍` **VIP Warp** `/vip`\n"
                  "> `🎨` **Chat Color** `น้ำตาล`",
            inline=False
        )
        bronze_embed.set_thumbnail(url="https://i.imgur.com/bronze_icon.png")

        # Embed 3: Silver Card
        silver_embed = discord.Embed(
            title="🥈 SILVER TIER",
            description="```yaml\nราคา: 150฿ | อายุ: 30 วัน\n```",
            color=0xC0C0C0
        )
        silver_embed.add_field(
            name="PERKS",
            value="> `⚡` **EXP Multiplier** `x2.0`\n"
                  "> `🍀` **Drop Rate** `+50%`\n"
                  "> `✈️` **Flight** `/fly`\n"
                  "> `💀` **Back** `/back`\n"
                  "> `🎒` **Inventory** `+2 Rows`\n"
                  "> `🎨` **Chat Prefix** `[VIP]`",
            inline=False
        )
        silver_embed.set_thumbnail(url="https://i.imgur.com/silver_icon.png")

        # Embed 4: Gold Card
        gold_embed = discord.Embed(
            title="🥇 GOLD TIER — BEST VALUE",
            description="```yaml\nราคา: 300฿ | อายุ: 30 วัน\n```",
            color=0xFFD700
        )
        gold_embed.add_field(
            name="PERKS",
            value="> `⚡` **EXP Multiplier** `x3.0` **MAX**\n"
                  "> `🍀` **Drop Rate** `+100%`\n"
                  "> `🛡️` **God Mode** `/god 5m`\n"
                  "> `❤️` **Heal** `/heal`\n"
                  "> `🔧` **Repair** `/repair` ฟรี\n"
                  "> `🗝️` **Exclusive** `ดันเจี้ยน VIP`\n"
                  "> `🎨` **Chat Prefix** `[GOLD VIP]`",
            inline=False
        )
        gold_embed.set_thumbnail(url="https://i.imgur.com/gold_icon.png")
        gold_embed.set_footer(text="เลือกแพ็กเกจด้านล่างเพื่อสั่งซื้อทันที", icon_url=interaction.guild.icon.url)

        await interaction.response.send_message(
            embeds=[banner_embed, bronze_embed, silver_embed, gold_embed],
            view=VIPShopView(),
            ephemeral=True
        )

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
    bot.add_view(ControlPanelView())
    bot.add_view(ConfirmTopupView())
    bot.add_view(VIPShopView())
    bot.add_view(AdminApproveView(0, 0))
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
    amount = get_pending_topup(member.id)
    if amount == 0:
        return await ctx.send(f"❌ ไม่พบรายการเติมเงินที่รออนุมัติของ {member.mention}")

    update_balance(member.id, amount)
    delete_pending_topup(member.id)

    await ctx.send(f"✅ อนุมัติเติมเงินให้ {member.mention} จำนวน **{amount}฿** สำเร็จ!")
    try:
        await member.send(f"🎉 เติมเงินสำเร็จ! คุณได้รับเครดิต **{amount}฿** แล้ว\nเครดิตปัจจุบัน: **{get_balance(member.id)}฿**")
    except:
        pass

# --- รันบอท ---
setup_database()
TOKEN = os.getenv("BOT_TOKEN")
if TOKEN is None:
    print("❌ ไม่เจอ BOT_TOKEN ใน Environment Variables")
else:
    bot.run(TOKEN)
