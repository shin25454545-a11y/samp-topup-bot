import nextcord
from nextcord.ext import commands
import json
import os
import random
import datetime
import asyncio
from threading import Thread
from flask import Flask, render_template_string, request, redirect, url_for, session

TOKEN = os.getenv("DISCORD_TOKEN")
PROMPTPAY_ID = "0886560336"
DATA_FILE = "topup_data.json"
QR_IMAGE_URL = f"https://promptpay.io/{PROMPTPAY_ID}.png"
BANNER_URL = "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1200"
ADMIN_CHANNEL_ID = 0
ANNOUNCE_CHANNEL_ID = 1499809858680000712
DASHBOARD_PASSWORD = "admin123" # เปลี่ยนรหัสผ่านเว็บตรงนี้

# --- ระบบข้อมูล ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
else:
    data = {}

if "users" not in data: data["users"] = {}
if "codes" not in data: data["codes"] = {}
if "stock" not in data: data["stock"] = {"VIP Gold": 5, "VIP Silver": 10, "VIP Bronze": 20}
if "logs" not in data: data["logs"] = [] # เก็บล็อกการเติมเงิน

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user(user_id):
    user_id = str(user_id)
    if user_id not in data["users"]:
        data["users"][user_id] = {"credit": 0, "ingame": "", "last_daily": "", "total_topup": 0}
    return data["users"][user_id]

def add_credit(user_id, amount, is_topup=False, by_admin=False):
    user = get_user(user_id)
    user["credit"] += amount
    if is_topup and amount > 0:
        user["total_topup"] += amount
        # บันทึกล็อก
        data["logs"].append({
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "amount": amount,
            "type": "เติมโดยแอดมิน" if by_admin else "เติมเครดิต"
        })
    save_data()

def get_stock(item_name):
    return data["stock"].get(item_name, 0)

def update_stock(item_name, amount):
    if item_name in data["stock"]:
        data["stock"][item_name] += amount
        save_data()

# --- เริ่ม Flask Web ---
app = Flask('')
app.secret_key = os.urandom(24)

HTML_TEMPLATE = """
<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SAMP Topup Dashboard</title><script src="https://cdn.tailwindcss.com"></script>
<meta http-equiv="refresh" content="10"></head>
<body class="bg-gray-900 text-white p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold text-yellow-400">🏦 SAMP Dashboard</h1>
            <a href="/logout" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg">ออกจากระบบ</a>
        </div>

        <!-- ยอดรวม -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-gray-800 p-6 rounded-xl"><h2 class="text-gray-400">ยอดเติมวันนี้</h2><p class="text-4xl font-bold text-green-400">{{ today_total }}฿</p></div>
            <div class="bg-gray-800 p-6 rounded-xl"><h2 class="text-gray-400">ยอดเติมเดือนนี้</h2><p class="text-4xl font-bold text-blue-400">{{ month_total }}฿</p></div>
            <div class="bg-gray-800 p-6 rounded-xl"><h2 class="text-gray-400">ยอดเติมทั้งหมด</h2><p class="text-4xl font-bold text-yellow-400">{{ all_total }}฿</p></div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- ท็อป 10 -->
            <div class="bg-gray-800 p-6 rounded-xl">
                <h2 class="text-xl font-bold mb-4">🏆 ท็อป 10 สายเปย์</h2>
                <table class="w-full">
                    {% for user in top_users %}
                    <tr class="border-b border-gray-700"><td class="py-2">{{ loop.index }}. {{ user.name }}</td><td class="text-right font-bold text-yellow-400">{{ user.total }}฿</td></tr>
                    {% endfor %}
                </table>
            </div>

            <!-- สต็อก -->
            <div class="bg-gray-800 p-6 rounded-xl">
                <h2 class="text-xl font-bold mb-4">📦 สต็อกสินค้า VIP</h2>
                {% for item, amount in stock.items() %}
                <div class="flex justify-between items-center mb-2"><span>{{ item }}</span><span class="font-bold {{ 'text-green-400' if amount > 0 else 'text-red-400' }}">{{ amount }} ชิ้น</span></div>
                {% endfor %}
            </div>
        </div>

        <!-- Log ล่าสุด -->
        <div class="bg-gray-800 p-6 rounded-xl mt-8">
            <h2 class="text-xl font-bold mb-4">📜 ประวัติเติมเงินล่าสุด</h2>
            <table class="w-full text-sm">
                <thead><tr class="text-left text-gray-400"><th class="pb-2">เวลา</th><th class="pb-2">User ID</th><th class="pb-2">จำนวน</th><th class="pb-2">ประเภท</th></tr></thead>
                <tbody>
                    {% for log in logs %}
                    <tr class="border-t border-gray-700"><td class="py-2">{{ log.time }}</td><td>{{ log.user_id }}</td><td class="text-green-400 font-bold">+{{ log.amount }}฿</td><td>{{ log.type }}</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div></body></html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8"><title>Login</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-900 flex items-center justify-center h-screen">
    <form method="post" class="bg-gray-800 p-8 rounded-xl shadow-lg w-80">
        <h1 class="text-2xl font-bold text-center text-yellow-400 mb-6">Dashboard Login</h1>
        <input type="password" name="password" placeholder="รหัสผ่านแอดมิน" class="w-full bg-gray-700 p-3 rounded-lg mb-4 text-white" required>
        <button type="submit" class="w-full bg-yellow-500 hover:bg-yellow-600 text-gray-900 font-bold p-3 rounded-lg">เข้าสู่ระบบ</button>
        {% if error %}<p class="text-red-500 text-center mt-4">{{ error }}</p>{% endif %}
    </form></body></html>
"""

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session: return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        if request.form['password'] == DASHBOARD_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'รหัสผ่านไม่ถูกต้อง'
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session: return redirect(url_for('login'))

    # คำนวณยอด
    today = datetime.date.today().isoformat()
    month = datetime.date.today().strftime("%Y-%m")
    today_total, month_total, all_total = 0, 0, 0

    for log in data["logs"]:
        if log["amount"] > 0:
            all_total += log["amount"]
            if log["time"].startswith(today): today_total += log["amount"]
            if log["time"].startswith(month): month_total += log["amount"]

    # ท็อป 10
    sorted_users = sorted(data["users"].items(), key=lambda x: x[1].get("total_topup", 0), reverse=True)[:10]
    top_users = [{"name": user_id, "total": user_data.get('total_topup', 0)} for user_id, user_data in sorted_users]

    return render_template_string(HTML_TEMPLATE,
        today_total=today_total, month_total=month_total, all_total=all_total,
        top_users=top_users, stock=data["stock"], logs=reversed(data["logs"][-10:])
    )

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

def run_flask():
  app.run(host='0.0.0.0', port=8080)

# --- เริ่ม Discord Bot ---
intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class AddCreditModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("เติมเครดิตให้สมาชิก")
        self.user_id = nextcord.ui.TextInput(label="ใส่ ID ผู้ใช้", required=True)
        self.amount = nextcord.ui.TextInput(label="จำนวนเครดิต", required=True)
        self.add_item(self.user_id)
        self.add_item(self.amount)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            user_id = int(self.user_id.value)
            amount = int(self.amount.value)
            add_credit(user_id, amount, is_topup=True, by_admin=True)
            user = await bot.fetch_user(user_id)
            await interaction.response.send_message(f"เติม {amount}฿ ให้ {user.mention} สำเร็จ\nยอดปัจจุบัน: {get_user(user_id)['credit']}฿", ephemeral=True)
        except: await interaction.response.send_message("ผิดพลาด! เช็ค ID กับจำนวนเงินอีกที", ephemeral=True)

async def buy_role(interaction, role_name, price):
    if get_stock(role_name) <= 0:
        return await interaction.response.send_message(f"❌ `ยศ {role_name}` สินค้าหมดแล้ว รอแอดมินเติมสต็อกนะ", ephemeral=True)
    user = get_user(interaction.user.id)
    if user["credit"] < price: return await interaction.response.send_message(f"เครดิตไม่พอ! ขาดอีก {price - user['credit']}฿", ephemeral=True)
    role = nextcord.utils.get(interaction.guild.roles, name=role_name)
    if not role: return await interaction.response.send_message(f"ซื้อสำเร็จ แต่หา @{role_name} ในเซิฟไม่เจอ", ephemeral=True)
    if role in interaction.user.roles: return await interaction.response.send_message(f"ท่านมี `ยศ {role_name}` อยู่แล้ว", ephemeral=True)
    add_credit(interaction.user.id, -price)
    update_stock(role_name, -1)
    await interaction.user.add_roles(role)
    await interaction.response.send_message(f"ซื้อ `ยศ {role_name}` สำเร็จ! หัก {price}฿ คงเหลือ {get_user(interaction.user.id)['credit']}฿\n📦 คงเหลือ: {get_stock(role_name)} สิทธิ์", ephemeral=True)
    if ANNOUNCE_CHANNEL_ID!= 0:
        channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if channel:
            embed = nextcord.Embed(title="🎉 มีคนอัพเกรด VIP!", description=f"{interaction.user.mention} เพิ่งซื้อ `ยศ {role_name}` สุดโหด!", color=0xFFD700)
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            embed.set_footer(text=f"เหลืออีกแค่ {get_stock(role_name)} สิทธิ์เท่านั้น!")
            await channel.send(embed=embed)

class MainMenu(nextcord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @nextcord.ui.button(label="เติมเงิน", style=nextcord.ButtonStyle.green, custom_id="btn_topup", emoji="💰")
    async def topup_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(f"**สแกน QR เพื่อเติมเงิน**\nPromptPay: `{PROMPTPAY_ID}`\n\n**ลิงก์ QR:** {QR_IMAGE_URL}\n\nโอนแล้วแนบสลิปในห้องนี้ แล้วแท็กแอดมิน", ephemeral=True)
    @nextcord.ui.button(label="เช็คเครดิต", style=nextcord.ButtonStyle.blurple, custom_id="btn_credit", emoji="💳")
    async def credit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        user = get_user(interaction.user.id)
        await interaction.response.send_message(f"**เครดิตของ {interaction.user.mention}**\n💵 ยอดคงเหลือ: `{user['credit']}฿`\n💎 ยอดเติมสะสม: `{user['total_topup']}฿`", ephemeral=True)
    @nextcord.ui.button(label="ร้านค้า VIP", style=nextcord.ButtonStyle.gray, custom_id="btn_shop", emoji="🛒")
    async def shop_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(title="🛒 ร้านค้า VIP [LIMITED]", description="**สินค้ามีจำนวนจำกัด หมดแล้วหมดเลย!**\nเลือกยศที่ต้องการ หรือกด `ดูสิทธิ์` เพื่อดูความสามารถ", color=0xFFD700)
        embed.add_field(name="🥇 VIP Gold - 300฿", value=f"📦 คงเหลือ: `{get_stock('VIP Gold')}` สิทธิ์", inline=True)
        embed.add_field(name="🥈 VIP Silver - 200฿", value=f"📦 คงเหลือ: `{get_stock('VIP Silver')}` สิทธิ์", inline=True)
        embed.add_field(name="🥉 VIP Bronze - 100฿", value=f"📦 คงเหลือ: `{get_stock('VIP Bronze')}` สิทธิ์", inline=True)
        await interaction.response.send_message(embed=embed, view=ShopMenu(), ephemeral=True)
    @nextcord.ui.button(label="แอดมินเติมเงิน", style=nextcord.ButtonStyle.red, custom_id="btn_admin", emoji="⚙️", row=1)
    async def admin_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("ใช้ได้เฉพาะแอดมินเท่านั้น", ephemeral=True)
        await interaction.response.send_modal(AddCreditModal())

class ShopMenu(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.buy_gold.disabled = get_stock("VIP Gold") <= 0
        self.buy_silver.disabled = get_stock("VIP Silver") <= 0
        self.buy_bronze.disabled = get_stock("VIP Bronze") <= 0
    @nextcord.ui.button(label="VIP Gold 300฿", style=nextcord.ButtonStyle.green, custom_id="buy_gold", emoji="🥇", row=0)
    async def buy_gold(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): await buy_role(interaction, "VIP Gold", 300)
    @nextcord.ui.button(label="VIP Silver 200฿", style=nextcord.ButtonStyle.gray, custom_id="buy_silver", emoji="🥈", row=0)
    async def buy_silver(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): await buy_role(interaction, "VIP Silver", 200)
    @nextcord.ui.button(label="VIP Bronze 100฿", style=nextcord.ButtonStyle.red, custom_id="buy_bronze", emoji="🥉", row=0)
    async def buy_bronze(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): await buy_role(interaction, "VIP Bronze", 100)
    @nextcord.ui.button(label="กล่องสุ่ม 50฿", style=nextcord.ButtonStyle.blurple, custom_id="gacha", emoji="🎁", row=1)
    async def gacha(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        user = get_user(interaction.user.id)
        if user["credit"] < 50: return await interaction.response.send_message("เครดิตไม่พอ! ต้องใช้ 50฿", ephemeral=True)
        add_credit(interaction.user.id, -50)
        roll = random.randint(1, 100)
        if roll <= 5:
            role = nextcord.utils.get(interaction.guild.roles, name="VIP Bronze")
            if role and role not in interaction.user.roles and get_stock("VIP Bronze") > 0:
                await interaction.user.add_roles(role); update_stock("VIP Bronze", -1); msg = "🎉 แจ็คพอต! คุณได้รับ `VIP Bronze` ไปใช้ฟรี!"
            else: msg = "🎉 แจ็คพอต! แต่ของหมด/มี VIP แล้ว คืนเงิน 100฿ แทน"; add_credit(interaction.user.id, 100)
        elif roll <= 20: add_credit(interaction.user.id, 100); msg = "💰 โชคดี! ได้รับเครดิตคืน 100฿"
        elif roll <= 50: add_credit(interaction.user.id, 50); msg = "😮 เกือบไป! ได้เครดิต 50฿ คืน"
        else: msg = "😢 เสียใจด้วย รอบนี้ไม่ได้อะไรเลย ลองใหม่!"
        await interaction.response.send_message(msg, ephemeral=True)
    @nextcord.ui.button(label="ดูสิทธิ์ VIP", style=nextcord.ButtonStyle.gray, custom_id="view_perks", emoji="📜", row=1)
    async def view_perks(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(title="📜 สิทธิพิเศษ VIP [สำหรับเซิฟ SAMP]", color=0x00FFFF)
        embed.add_field(name="🥉 VIP Bronze - 100฿", value="```1. คำสั่ง /vipheal ฮีลเลือด CD 10 นาที\n2. เปลี่ยนป้ายทะเบียนฟรี /vipplate\n3. เงินเดือน Payday +20%\n4. เกิดโรงบาลไม่เสียเงิน```", inline=False)
        embed.add_field(name="🥈 VIP Silver - 200฿", value="```ได้สิทธิ์ Bronze ทั้งหมด +\n1. เสกรถ VIP /vipcar ใช้ได้ 24 ชม.\n2. ได้ปืนพกตอนเกิด /vipweapons\n3. ใช้สกินพิเศษ /vipskin\n4. ช่องเก็บของ +10```", inline=False)
        embed.add_field(name="🥇 VIP Gold - 300฿", value="```ได้สิทธิ์ Silver ทั้งหมด +\n1. เสกเกราะ /viparmor CD 15 นาที\n2. เจ็ทแพ็ค /vipjetpack 5 นาที\n3. ไนตรัสฟรี /vipnos\n4. วาป /gotols /gotosf /gotolv\n5. ชื่อทอง [GOLD] ในเกม```", inline=False)
        embed.set_footer(text="*สิทธิ์จะมีผลเมื่อเซิฟ SAMP เปิดให้บริการ")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="daily", description="รับเครดิตรายวัน 10฿")
async def daily(interaction: nextcord.Interaction):
    user = get_user(interaction.user.id); today = datetime.date.today().isoformat()
    if user["last_daily"] == today: await interaction.response.send_message("วันนี้รับไปแล้ว มาใหม่พรุ่งนี้นะ", ephemeral=True)
    else: user["last_daily"] = today; add_credit(interaction.user.id, 10); await interaction.response.send_message(f"รับเครดิตรายวัน 10฿ สำเร็จ! ยอดคงเหลือ: {user['credit']}฿", ephemeral=True)

@bot.slash_command(name="code", description="ใช้โค้ดรับเครดิต")
async def code(interaction: nextcord.Interaction, code: str):
    code = code.upper()
    if code in data["codes"]:
        amount = data["codes"][code]; add_credit(interaction.user.id, amount, is_topup=True); del data["codes"][code]; save_data()
        await interaction.response.send_message(f"ใช้โค้ด `{code}` สำเร็จ! ได้รับ {amount}฿ ยอดคงเหลือ: {get_user(interaction.user.id)['credit']}฿", ephemeral=True)
    else: await interaction.response.send_message("โค้ดไม่ถูกต้อง หรือถูกใช้ไปแล้ว", ephemeral=True)

@bot.slash_command(name="createcode", description="[แอดมิน] สร้างโค้ดเติมเงิน")
@commands.has_permissions(administrator=True)
async def createcode(interaction: nextcord.Interaction, code: str, amount: int):
    code = code.upper(); data["codes"][code] = amount; save_data()
    await interaction.response.send_message(f"สร้างโค้ด `{code}` มูลค่า {amount}฿ สำเร็จ", ephemeral=True)

@bot.slash_command(name="topuprank", description="ดู 10 อันดับคนเติมเงินเยอะสุด")
async def topuprank(interaction: nextcord.Interaction):
    sorted_users = sorted(data["users"].items(), key=lambda x: x[1].get("total_topup", 0), reverse=True)[:10]
    embed = nextcord.Embed(title="🏆 ท็อป 10 สายเปย์เซิฟเวอร์", color=0xFFD700); desc = ""
    for i, (user_id, user_data) in enumerate(sorted_users):
        try: user = await bot.fetch_user(int(user_id)); name = user.name
        except: name = f"User ID: {user_id}"
        desc += f"**{i+1}.** {name} - `{user_data.get('total_topup', 0)}฿`\n"
    embed.description = desc if desc else "ยังไม่มีข้อมูล"; await interaction.response.send_message(embed=embed)

@bot.slash_command(name="addstock", description="[แอดมิน] เติมสต็อกสินค้า")
@commands.has_permissions(administrator=True)
async def addstock(interaction: nextcord.Interaction, item: str, amount: int):
    if item not in data["stock"]: return await interaction.response.send_message(f"ไม่มีสินค้าชื่อ `{item}` ในระบบ", ephemeral=True)
    update_stock(item, amount)
    await interaction.response.send_message(f"เติมสต็อก `{item}` +{amount} สำเร็จ\nคงเหลือตอนนี้: {get_stock(item)} ชิ้น", ephemeral=True)

@bot.slash_command(name="stock", description="เช็คสต็อกสินค้าทั้งหมด")
async def stock(interaction: nextcord.Interaction):
    embed = nextcord.Embed(title="📦 สต็อกสินค้า VIP ปัจจุบัน", color=0x00D9FF)
    for item, amount in data["stock"].items():
        status = "✅ พร้อมขาย" if amount > 0 else "❌ สินค้าหมด"
        embed.add_field(name=item, value=f"คงเหลือ: `{amount}` ชิ้น\n{status}", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.slash_command(name="sync", description="[แอดมิน] ซิงค์คำสั่งใหม่")
@commands.has_permissions(administrator=True)
async def sync(interaction: nextcord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await bot.sync_application_commands()
        await interaction.followup.send("✅ Sync คำสั่งสำเร็จแล้ว", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Sync ล้มเหลว: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'BOT ONLINE: {bot.user}')
    bot.add_view(MainMenu())
    bot.add_view(ShopMenu())
    await asyncio.sleep(5)
    try:
        await bot.sync_application_commands()
        print('Slash Commands Synced Successfully!')
    except Exception as e:
        print(f'Sync Failed: {e}')

@bot.command(name="เมนู")
@commands.has_permissions(administrator=True)
async def menu_command(ctx):
    embed = nextcord.Embed(title="🏦 ระบบเติมเงิน & ร้านค้า VIP", description="**ยินดีต้อนรับสู่ร้านค้าเซิฟเรา**\nเติมเงิน รับยศ อัพเกรดได้ทันที ระบบออโต้ 24 ชม.", color=0xFFD700)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="🔥 โปรโมชั่นเปิดเซิฟ | ใช้ /daily รับฟรี 10฿ ทุกวัน | สินค้ามีจำนวนจำกัด!")
    await ctx.send(embed=embed, view=MainMenu())

# รันเว็บ + บอทพร้อมกัน
Thread(target=run_flask).start()
bot.run(TOKEN)
