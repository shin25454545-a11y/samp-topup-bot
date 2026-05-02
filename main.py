import discord
from discord.ext import commands
import discord.ui
import sqlite3
import qrcode
from PIL import Image
import io
import os
from flask import Flask, request
from threading import Thread

# ===== ตั้งค่าเรียบร้อยตามที่ท่านให้ =====
TOKEN = os.getenv("BOT_TOKEN") # ใส่ใน Secrets ชื่อ BOT_TOKEN
PROMPTPAY_ID = "0886560336"
OWNER_ID = 1250051906076934154
GUILD_ID = 1499224151607738478

ROLE_PRICES = {
    "Bronze": 50,
    "Silver": 150,
    "Gold": 300
}

ROLE_IDS = {
    "Bronze": 1499228752234942566,
    "Silver": 1499228661335724072,
    "Gold": 1499228473095356597
}

BANNER_URL = "https://i.ibb.co/1Y1Lw8Yn/4d288aac3efa4911e5bb8ade7d5262b6.jpg"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask('')

# ===== ระบบ Database =====
def setup_database():
    conn = sqlite3.connect('vip.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, item TEXT, price INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS pending_topup (user_id INTEGER PRIMARY KEY, amount INTEGER)''')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('vip.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id =?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect('vip.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    cursor.execute("UPDATE users SET balance = balance +? WHERE user_id =?", (amount, user_id))
    conn.commit()
    conn.close()

def add_transaction(user_id, username, item, price):
    conn = sqlite3.connect('vip.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (user_id, username, item, price) VALUES (?,?,?,?)", (user_id, username, item, price))
    conn.commit()
    conn.close()

def set_pending_topup(user_id, amount):
    conn = sqlite3.connect('vip.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO pending_topup (user_id, amount) VALUES (?,?)", (user_id, amount))
    conn.commit()
    conn.close()

def get_pending_topup(user_id):
    conn = sqlite3.connect('vip.db')
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM pending_topup WHERE user_id =?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def clear_pending_topup(user_id):
    conn = sqlite3.connect('vip.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pending_topup WHERE user_id =?", (user_id,))
    conn.commit()
    conn.close()

# ===== สร้าง QR PromptPay =====
def generate_promptpay_qr(amount):
    from promptpay import qrcode as pp_qr
    payload = pp_qr.generate_payload(PROMPTPAY_ID, amount)
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="promptpay.png")

# ===== ปุ่มยืนยันสลิป =====
class ConfirmTopupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="✅ ยืนยันสลิป", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        amount = get_pending_topup(interaction.user.id)
        if amount == 0:
            return await interaction.response.send_message("❌ คุณไม่มีรายการเติมเงินที่รอดำเนินการ", ephemeral=True)

        owner = await bot.fetch_user(OWNER_ID)
        guild = bot.get_guild(GUILD_ID)
        approve_embed = discord.Embed(title="🔔 มีคนขอเติมเงิน", description=f"{interaction.user.mention} ขอเติม {amount}฿\nกรุณาตรวจสอบสลิปแล้วกดอนุมัติ", color=0xFFA500)
        approve_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await owner.send(embed=approve_embed, view=AdminApproveView(interaction.user.id, amount))
        await interaction.response.edit_message(content="✅ ส่งเรื่องให้แอดมินตรวจสอบแล้ว รอ 1-3 นาที", view=None)

# ===== ปุ่มแอดมินอนุมัติ =====
class AdminApproveView(discord.ui.View):
    def __init__(self, user_id, amount):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.amount = amount

    @discord.ui.button(label="✅ อนุมัติ", style=discord.ButtonStyle.green)
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= OWNER_ID:
            return await interaction.response.send_message("❌ คุณไม่ใช่แอดมิน", ephemeral=True)

        pending_amount = get_pending_topup(self.user_id)
        if pending_amount == 0:
            return await interaction.response.send_message("❌ รายการนี้ถูกจัดการไปแล้ว", ephemeral=True)

        update_balance(self.user_id, pending_amount)
        clear_pending_topup(self.user_id)

        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(self.user_id)
        if not member:
            member = await bot.fetch_user(self.user_id)

        # แจกยศออโต้ถ้าเติมถึง
        for role_name, price in sorted(ROLE_PRICES.items(), key=lambda x: x[1], reverse=True):
            if pending_amount >= price:
                role_id = ROLE_IDS[role_name]
                role = guild.get_role(role_id)
                if role and member and role not in member.roles:
                    await member.add_roles(role)
                    add_transaction(self.user_id, str(member), role_name, price)
                    try:
                        await member.send(f"🎉 **เติมเงินสำเร็จ!**\nคุณได้รับยศ {role_name} อัตโนมัติจากการเติม {pending_amount}฿\nเครดิตคงเหลือ: {get_balance(self.user_id)}฿")
                    except: pass
                    break

        await interaction.message.edit(content=f"✅ อนุมัติเงินให้ {member.mention} จำนวน **{pending_amount}**฿ สำเร็จ", embed=None, view=None)
        try:
            await member.send(f"✅ **แอดมินอนุมัติแล้ว!** เติมเงิน {pending_amount}฿ สำเร็จ\nเครดิตคงเหลือ: {get_balance(self.user_id)}฿")
        except: pass

    @discord.ui.button(label="❌ ปฏิเสธ", style=discord.ButtonStyle.red)
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= OWNER_ID:
            return await interaction.response.send_message("❌ คุณไม่ใช่แอดมิน", ephemeral=True)

        clear_pending_topup(self.user_id)
        member = await bot.fetch_user(self.user_id)
        await interaction.message.edit(content=f"❌ ปฏิเสธการเติมเงินของ {member.mention} แล้ว", embed=None, view=None)
        try:
            await member.send("❌ **แอดมินปฏิเสธการเติมเงิน** กรุณาติดต่อแอดมินหากมีข้อสงสัย")
        except: pass

# ===== Modal เติมเงิน =====
class TopupModal(discord.ui.Modal, title="💵 เติมเงินเข้าระบบ"):
    amount = discord.ui.TextInput(label="จำนวนเงิน (บาท)", placeholder="เช่น 300", max_length=5)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount_int = int(self.amount.value)
            if amount_int < 10:
                return await interaction.response.send_message("❌ เติมขั้นต่ำ 10฿", ephemeral=True)
            if amount_int > 30000:
                return await interaction.response.send_message("❌ เติมได้สูงสุด 30000฿", ephemeral=True)

            set_pending_topup(interaction.user.id, amount_int)
            qr_file = generate_promptpay_qr(amount_int)

            embed = discord.Embed(title=f"💰 เติมเงิน {amount_int}฿", description=f"1. สแกน QR เพื่อโอนเงิน\n2. โอนเสร็จแล้วกดปุ่ม `✅ยืนยันสลิป` ด้านล่าง", color=0x00FF00)
            embed.set_image(url="attachment://promptpay.png")
            embed.set_footer(text="ห้ามโอนยอดไม่ตรง บอทเช็คไม่ได้")
            await interaction.response.send_message(embed=embed, file=qr_file, view=ConfirmTopupView(), ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ใส่เป็นตัวเลขเท่านั้น", ephemeral=True)

# ===== Select Menu ซื้อ VIP =====
class VIPSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="BRONZE TIER", description=f"ราคา {ROLE_PRICES['Bronze']} บาท | 30 วัน", emoji="🥉", value="Bronze"),
            discord.SelectOption(label="SILVER TIER", description=f"ราคา {ROLE_PRICES['Silver']} บาท | 30 วัน", emoji="🥈", value="Silver"),
            discord.SelectOption(label="GOLD TIER", description=f"ราคา {ROLE_PRICES['Gold']} บาท | 30 วัน", emoji="🥇", value="Gold"),
        ]
        super().__init__(placeholder="เลือก VIP ที่ต้องการซื้อ...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        role_name = self.values[0]
        price = ROLE_PRICES[role_name]
        balance = get_balance(interaction.user.id)

        if balance < price:
            return await interaction.response.send_message(f"❌ เครดิตไม่พอ คุณมี {balance}฿ แต่ {role_name} ราคา {price}฿\nกด `เติมเงิน` ก่อน", ephemeral=True)

        update_balance(interaction.user.id, -price)
        role_id = ROLE_IDS[role_name]
        role = interaction.guild.get_role(role_id)

        if role:
            await interaction.user.add_roles(role)
            add_transaction(interaction.user.id, str(interaction.user), role_name, price)

            embed = discord.Embed(title="🎉 ซื้อ VIP สำเร็จ!", color=0xFFD700)
            embed.add_field(name="ยศที่ได้รับ", value=f"{role.mention}", inline=True)
            embed.add_field(name="ราคา", value=f"`{price}฿`", inline=True)
            embed.add_field(name="💰 เครดิตคงเหลือ", value=f"`{get_balance(interaction.user.id)}฿`", inline=True)
            embed.set_thumbnail(url=BANNER_URL)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            update_balance(interaction.user.id, price) # คืนเงิน
            await interaction.response.send_message("❌ ตั้งค่า ROLE_IDS ผิด หา Role ไม่เจอ คืนเงินให้แล้ว", ephemeral=True)

class VIPShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VIPSelect())

# ===== แผงควบคุมหลัก =====
class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เติมเงิน", style=discord.ButtonStyle.green, emoji="💵")
    async def topup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TopupModal())

    @discord.ui.button(label="เช็คยอดเงิน", style=discord.ButtonStyle.gray, emoji="💰")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        bal = get_balance(interaction.user.id)
        await interaction.response.send_message(f"💰 เครดิตคงเหลือของคุณ: `{bal}฿`", ephemeral=True)

    @discord.ui.button(label="ร้านค้า VIP", style=discord.ButtonStyle.blurple, emoji="💎")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        banner_embed = discord.Embed(color=0xFFD700)
        banner_embed.set_image(url=BANNER_URL)

        bronze_embed = discord.Embed(title="🥉 BRONZE TIER", description=f"<a:gem:0> **BASIC ACCESS**\n\n### เริ่มต้นการเป็น VIP ระดับเริ่มต้น\n**ราคา `{ROLE_PRICES['Bronze']} บาท / 30 วัน**`", color=0xCD7F32)
        bronze_embed.set_thumbnail(url=BANNER_URL)
        bronze_embed.add_field(name="</>", value="```\n- คูณ EXP x1.5\n- ห้องแชท VIP\n- ยศสีทองแดงเท่ๆ\n```", inline=False)

        silver_embed = discord.Embed(title="🥈 SILVER TIER", description=f"<a:gem:0> **ENHANCED PERKS**\n\n### สิทธิพิเศษที่เหนือกว่า\n**ราคา `{ROLE_PRICES['Silver']} บาท / 30 วัน**`", color=0xC0C0C0)
        silver_embed.set_thumbnail(url=BANNER_URL)
        silver_embed.add_field(name="</>", value="```\n- สิทธิ์ Bronze ทั้งหมด\n- คูณ EXP x2.0\n- คำสั่ง /fly\n- ยศสีเงินสุดหรู\n```", inline=False)

        gold_embed = discord.Embed(title="🥇 GOLD TIER", description=f"<a:gem:0> **PREMIUM MEMBERSHIP**\n\n### ปลดล็อคพลังทั้งหมด เป็นเจ้าของเซิร์ฟเวอร์\n**ราคา `{ROLE_PRICES['Gold']} บาท / 30 วัน**`", color=0xFFD700)
        gold_embed.set_thumbnail(url=BANNER_URL)
        gold_embed.add_field(name="</>", value="```\n- สิทธิ์ Silver ทั้งหมด\n- คูณ EXP x3.0\n- คำสั่ง /god\n- ห้องส่วนตัว\n- ยศสีทองอร่าม\n```", inline=False)

        await interaction.response.send_message(
            embeds=[banner_embed, bronze_embed, silver_embed, gold_embed],
            view=VIPShopView(),
            ephemeral=True
        )

# ===== คำสั่งเปิดร้าน =====
@bot.command()
async def menu(ctx):
    embed = discord.Embed(title="⚙️ CONTROL PANEL | ระบบร้าน VIP", description="**แผงควบคุมสำหรับลูกค้า กดปุ่มด้านล่างเพื่อใช้งาน**", color=0x2B2D31)
    embed.add_field(name="💵 เติมเงิน", value="เติมเครดิตเข้าระบบผ่าน PromptPay", inline=True)
    embed.add_field(name="💰 เช็คยอดเงิน", value="ดูเครดิตคงเหลือของคุณ", inline=True)
    embed.add_field(name="💎 ร้านค้า VIP", value="ดูรายละเอียด VIP และซื้อยศ", inline=True)
    embed.set_thumbnail(url=BANNER_URL)
    embed.set_footer(text="ร้านอาหรับคาบซิการ์ | ระบบอัตโนมัติ 24 ชม.")
    await ctx.send(embed=embed, view=ControlPanelView())

# ===== คำสั่งแอดมิน =====
@bot.command(name="addmoney")
@commands.has_permissions(administrator=True)
async def add_money(ctx, member: discord.Member, amount: int):
    if ctx.author.id!= OWNER_ID: return
    update_balance(member.id, amount)
    await ctx.send(f"✅ เพิ่มเงินให้ {member.mention} จำนวน {amount}฿ สำเร็จ ยอดคงเหลือ: {get_balance(member.id)}฿")

# ===== รันบอท =====
@bot.event
async def on_ready():
    print(f"บอท {bot.user} ออนไลน์แล้ว ✅")
    setup_database()
    bot.add_view(ControlPanelView())
    bot.add_view(VIPShopView())
    bot.add_view(AdminApproveView(0, 0))
    bot.add_view(ConfirmTopupView())

def run_flask(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_flask).start()
bot.run(TOKEN)
