import discord
from discord import ui
from discord.ext import commands
import os
import aiohttp
from aiohttp import web
import aiosqlite
import datetime
import asyncio
import aiomysql  # เตรียมไว้ต่อ SAMP

# ---------- ตั้งค่า ----------
TOKEN = os.getenv('DISCORD_TOKEN')
PROMPTPAY_ID = "0886560336"
ADMIN_ROLE_ID = 0  # TODO: ใส่ ID ยศแอดมิน ให้ใช้ปุ่มแอดมินได้

# ราคา VIP + ID ยศในดิส
VIP_DATA = {
    "Gold":   {"price": 100, "role_id": 0, "ingame_level": 3},  # TODO: ใส่ ID ยศ
    "Silver": {"price": 50,  "role_id": 0, "ingame_level": 2},
    "Bronze": {"price": 20,  "role_id": 0, "ingame_level": 1}
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Database ----------
async def init_db():
    async with aiosqlite.connect("shop.db") as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
            amount INTEGER, type TEXT, timestamp TEXT)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS stock (
            item TEXT PRIMARY KEY, amount INTEGER)''')
        await db.execute("INSERT OR IGNORE INTO stock VALUES ('Gold', 5)")
        await db.execute("INSERT OR IGNORE INTO stock VALUES ('Silver', 10)")
        await db.execute("INSERT OR IGNORE INTO stock VALUES ('Bronze', 20)")
        await db.commit()

# ---------- ฟังก์ชันเชื่อม SAMP ----------
async def give_ingame_cash(discord_id, amount):
    print(f"[SAMP] เติมเงินให้ DiscordID:{discord_id} จำนวน {amount}$")
    # --- มีเซิฟจริงแล้วลบ print ใช้โค้ดนี้ ---
    # try:
    #     conn = await aiomysql.connect(host=os.getenv('MYSQL_HOST'), user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASS'), db=os.getenv('MYSQL_DB'))
    #     async with conn.cursor() as cur:
    #         await cur.execute("UPDATE users SET Cash = Cash + %s WHERE discord_id = %s", (amount, discord_id))
    #         await conn.commit()
    #     conn.close()
    #     return True
    # except: return False
    return True

async def give_ingame_vip(discord_id, vip_level):
    print(f"[SAMP] แจก VIP Level {vip_level} ให้ DiscordID:{discord_id}")
    # --- มีเซิฟจริงแล้วลบ print ใช้โค้ดนี้ ---
    # try:
    #     conn = await aiomysql.connect(host=os.getenv('MYSQL_HOST'), user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASS'), db=os.getenv('MYSQL_DB'))
    #     async with conn.cursor() as cur:
    #         await cur.execute("UPDATE users SET VIP = %s WHERE discord_id = %s", (vip_level, discord_id))
    #         await conn.commit()
    #     conn.close()
    #     return True
    # except: return False
    return True

# ---------- ปุ่มเมนูหลัก !เมนู ----------
class MainMenu(ui.View):
    def __init__(self): super().__init__(timeout=None)

    @ui.button(label="เติมเงินเข้าเกม", style=discord.ButtonStyle.green, emoji="💵")
    async def topup_ingame(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TopupModal())

    @ui.button(label="ซื้อ VIP เข้าเกม", style=discord.ButtonStyle.blurple, emoji="👑")
    async def buy_vip(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("เลือก VIP ที่ต้องการซื้อ:", view=VIPShop(), ephemeral=True)

    @ui.button(label="เช็คยอดเงิน", style=discord.ButtonStyle.gray, emoji="💰")
    async def check_bal(self, interaction: discord.Interaction, button: ui.Button):
        async with aiosqlite.connect("shop.db") as db:
            cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (interaction.user.id,))
            bal = await cur.fetchone()
        await interaction.response.send_message(f"ยอดเงินคงเหลือ: **{bal[0] if bal else 0}฿**", ephemeral=True)

    @ui.button(label="แอดมินเติมเงิน", style=discord.ButtonStyle.red, emoji="⚙️")
    async def admin_add(self, interaction: discord.Interaction, button: ui.Button):
        if not any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("ใช้ได้แค่แอดมิน", ephemeral=True)
        await interaction.response.send_modal(AdminTopupModal())

# ---------- Modal เติมเงินเข้าเกม ----------
class TopupModal(ui.Modal, title="เติมเงินเข้าเกม SAMP"):
    amount = ui.TextInput(label="ใส่จำนวนเงินที่ต้องการเติม", placeholder="เช่น 100")
    async def on_submit(self, i: discord.Interaction):
        amt = int(self.amount.value)
        async with aiosqlite.connect("shop.db") as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (i.user.id,))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, i.user.id))
            await db.execute("INSERT INTO transactions VALUES (NULL, ?, ?, ?, ?)", (i.user.id, amt, "topup_ingame", datetime.datetime.now().isoformat()))
            await db.commit()
        
        await give_ingame_cash(i.user.id, amt)  # ยิงเข้าเกม
        embed = discord.Embed(title="✅ เติมเงินสำเร็จ", description=f"เติมเงิน **{amt}฿** เข้าเกมเรียบร้อยแล้ว\nเช็คเงินในเกมได้เลย!", color=0x00ff00)
        await i.response.send_message(embed=embed, ephemeral=True)

# ---------- ร้าน VIP ----------
class VIPShop(ui.View):
    def __init__(self): super().__init__(timeout=None)
    
    async def buy_process(self, i: discord.Interaction, vip_name: str):
        data = VIP_DATA[vip_name]
        price = data["price"]
        
        async with aiosqlite.connect("shop.db") as db:
            cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (i.user.id,))
            bal = (await cur.fetchone() or [0])[0]
            cur = await db.execute("SELECT amount FROM stock WHERE item = ?", (vip_name,))
            stock = (await cur.fetchone())[0]
            
            if bal < price: return await i.response.send_message(f"เงินไม่พอ ต้องการ {price}฿ มี {bal}฿", ephemeral=True)
            if stock <= 0: return await i.response.send_message("VIP นี้หมดแล้ว!", ephemeral=True)
            
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, i.user.id))
            await db.execute("UPDATE stock SET amount = amount - 1 WHERE item = ?", (vip_name,))
            await db.commit()
        
        # 1. แจกยศในดิส
        if data["role_id"] != 0:
            role = i.guild.get_role(data["role_id"])
            if role: await i.user.add_roles(role)
        
        # 2. ยิง VIP เข้าเกม
        await give_ingame_vip(i.user.id, data["ingame_level"])
        
        await i.response.send_message(f"ซื้อ **VIP {vip_name}** สำเร็จ! ยศในดิส + VIP ในเกมเข้าแล้ว ✅", ephemeral=True)

    @ui.button(label="VIP Gold 100฿", style=discord.ButtonStyle.yellow, emoji="🥇")
    async def gold(self, i, b): await self.buy_process(i, "Gold")
    
    @ui.button(label="VIP Silver 50฿", style=discord.ButtonStyle.gray, emoji="🥈")
    async def silver(self, i, b): await self.buy_process(i, "Silver")
    
    @ui.button(label="VIP Bronze 20฿", style=discord.ButtonStyle.red, emoji="🥉")
    async def bronze(self, i, b): await self.buy_process(i, "Bronze")

# ---------- Modal แอดมินเติมเงิน ----------
class AdminTopupModal(ui.Modal, title="แอดมินเติมเงินให้ลูกค้า"):
    user_id = ui.TextInput(label="User ID Discord")
    amount = ui.TextInput(label="จำนวนเงิน")
    async def on_submit(self, i):
        uid, amt = int(self.user_id.value), int(self.amount.value)
        async with aiosqlite.connect("shop.db") as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
            await db.execute("INSERT INTO transactions VALUES (NULL, ?, ?, ?, ?)", (uid, amt, "admin_add", datetime.datetime.now().isoformat()))
            await db.commit()
        await give_ingame_cash(uid, amt)
        await i.response.send_message(f"เติม {amt}฿ ให้ <@{uid}> + ส่งเข้าเกมแล้ว", ephemeral=True)

# ---------- คำสั่ง !เมนู ----------
@bot.command(name="เมนู")
async def menu(ctx):
    embed = discord.Embed(title="🎮 ร้านเติมเงิน SAMP", description="กดปุ่มด้านล่างเพื่อทำรายการ", color=0x00b0f4)
    embed.add_field(name="💵 เติมเงินเข้าเกม", value="เติมเงินบาทเข้าเกมทันที", inline=False)
    embed.add_field(name="👑 ซื้อ VIP เข้าเกม", value="ซื้อ VIP ได้ยศดิส + VIP ในเกม", inline=False)
    await ctx.send(embed=embed, view=MainMenu())

# ---------- คำสั่งอื่นๆ ----------
@bot.command(name="stock")
async def stock(ctx):
    async with aiosqlite.connect("shop.db") as db:
        cur = await db.execute("SELECT item, amount FROM stock")
        data = await cur.fetchall()
    txt = "\n".join([f"**{r[0]}**: {r[1]} ชิ้น" for r in data])
    await ctx.send(f"**สต็อก VIP ปัจจุบัน**\n{txt}")

@bot.tree.command(name="sync", description="ซิงค์คำสั่ง")
async def sync(i: discord.Interaction):
    if not i.user.guild_permissions.administrator: return
    await bot.tree.sync()
    await i.response.send_message("ซิงค์แล้ว!", ephemeral=True)

# ---------- Web Dashboard ----------
async def handle_dashboard(request):
    async with aiosqlite.connect("shop.db") as db:
        cur = await db.execute("SELECT SUM(amount) FROM transactions WHERE type IN ('admin_add','topup_ingame')")
        total = (await cur.fetchone())[0] or 0
        cur = await db.execute("SELECT item, amount FROM stock")
        stock = await cur.fetchall()
    
    html = f"""
    <html><head><title>Dashboard</title><meta name="viewport" content="width=device-width">
    <style>body{{font-family:sans-serif;background:#2c2f33;color:#fff;padding:20px}} .card{{background:#23272a;padding:15px;border-radius:8px;margin:10px 0}}</style></head>
    <body><h1>Dashboard ร้านเติมเงิน</h1>
    <div class="card"><h3>ยอดเติมทั้งหมด: {total}฿</h3></div>
    <div class="card"><h3>สต็อก VIP</h3>{''.join([f'<p>{r[0]}: {r[1]} ชิ้น</p>' for r in stock])}</div>
    </body></html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_web():
    app = web.Application()
    app.router.add_get('/', handle_dashboard)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()

@bot.event
async def on_ready():
    await init_db()
    bot.add_view(MainMenu())
    bot.add_view(VIPShop())
    print(f'บอท {bot.user} ออนไลน์แล้ว')
    await start_web()

bot.run(TOKEN)
