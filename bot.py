import nextcord 
from nextcord.ext import commands 
import json 
import os 

TOKEN = os.getenv("DISCORD_TOKEN") 
PROMPTPAY_ID = "0886560336" 
DATA_FILE = "topup_data.json" 
QR_IMAGE_URL = f"https://promptpay.io/{PROMPTPAY_ID}.png"
ADMIN_CHANNEL_ID = 0 

if os.path.exists(DATA_FILE): 
    with open(DATA_FILE, 'r', encoding='utf-8') as f: 
        topup_data = json.load(f) 
else: 
    topup_data = {}

def save_data(): 
    with open(DATA_FILE, 'w', encoding='utf-8') as f: 
        json.dump(topup_data, f, ensure_ascii=False, indent=4) 

def get_credit(user_id):
    user_data = topup_data.get(str(user_id), 0)
    return user_data if isinstance(user_data, int) else user_data.get("credit", 0)

def add_credit(user_id, amount):
    user_id = str(user_id)
    if user_id not in topup_data or isinstance(topup_data[user_id], int):
        old_credit = get_credit(user_id)
        topup_data[user_id] = {"credit": old_credit, "ingame": ""}
    topup_data[user_id]["credit"] += amount
    save_data()

intents = nextcord.Intents.default() 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

class AddCreditModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("เติมเครดิตให้สมาชิก")
        self.user_id = nextcord.ui.TextInput(label="ใส่ ID ผู้ใช้", placeholder="คลิกขวาที่ชื่อ > Copy User ID", required=True)
        self.amount = nextcord.ui.TextInput(label="จำนวนเครดิต", placeholder="ใส่ตัวเลข เช่น 100", required=True)
        self.add_item(self.user_id)
        self.add_item(self.amount)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            user_id = int(self.user_id.value)
            amount = int(self.amount.value)
            add_credit(user_id, amount)
            user = await bot.fetch_user(user_id)
            await interaction.response.send_message(f"เติม {amount}฿ ให้ {user.mention} สำเร็จ\nยอดปัจจุบัน: {get_credit(user_id)}฿", ephemeral=True)
            if ADMIN_CHANNEL_ID != 0:
                channel = bot.get_channel(ADMIN_CHANNEL_ID)
                if channel: await channel.send(f"[ADMIN] {interaction.user.mention} เติม {amount}฿ ให้ {user.mention}")
        except: await interaction.response.send_message("ผิดพลาด! เช็ค ID กับจำนวนเงินอีกที", ephemeral=True)

async def buy_role(interaction, role_name, price):
    credit = get_credit(interaction.user.id)
    if credit < price: return await interaction.response.send_message(f"เครดิตไม่พอ! ขาดอีก {price - credit}฿", ephemeral=True)
    role = nextcord.utils.get(interaction.guild.roles, name=role_name)
    if not role: return await interaction.response.send_message(f"ซื้อสำเร็จ แต่หา @{role_name} ในเซิฟไม่เจอ แจ้งแอดมินเช็คชื่อยศที", ephemeral=True)
    if role in interaction.user.roles: return await interaction.response.send_message(f"ท่านมี `ยศ {role_name}` อยู่แล้ว", ephemeral=True)
    add_credit(interaction.user.id, -price)
    await interaction.user.add_roles(role)
    await interaction.response.send_message(f"ซื้อ `ยศ {role_name}` สำเร็จ! หัก {price}฿ คงเหลือ {get_credit(interaction.user.id)}฿", ephemeral=True)

class MainMenu(nextcord.ui.View): 
    def __init__(self): super().__init__(timeout=None) 
    
    @nextcord.ui.button(label="เติมเงิน", style=nextcord.ButtonStyle.green, custom_id="btn_topup", emoji="💰") 
    async def topup_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        await interaction.response.send_message(f"**สแกน QR เพื่อเติมเงิน**\nPromptPay: `{PROMPTPAY_ID}`\n\n**ลิงก์ QR:** {QR_IMAGE_URL}\n\nโอนแล้วแนบสลิปในห้องนี้ แล้วแท็กแอดมิน", ephemeral=True)

    @nextcord.ui.button(label="เช็คเครดิต", style=nextcord.ButtonStyle.blurple, custom_id="btn_credit", emoji="💳") 
    async def credit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        credit = get_credit(interaction.user.id)
        await interaction.response.send_message(f"**เครดิตของ {interaction.user.mention}**\n💵 ยอดคงเหลือ: `{credit}฿`", ephemeral=True)

    @nextcord.ui.button(label="ร้านค้า VIP", style=nextcord.ButtonStyle.gray, custom_id="btn_shop", emoji="🛒") 
    async def shop_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        embed = nextcord.Embed(title="🛒 ร้านค้า VIP", description="เลือกยศที่ต้องการ หรือกด `ดูสิทธิ์` เพื่อดูความสามารถ", color=0xFFD700)
        await interaction.response.send_message(embed=embed, view=ShopMenu(), ephemeral=True)

    @nextcord.ui.button(label="แอดมินเติมเงิน", style=nextcord.ButtonStyle.red, custom_id="btn_admin", emoji="⚙️") 
    async def admin_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        if not interaction.user.guild_permissions.administrator: return await interaction.response.send_message("ใช้ได้เฉพาะแอดมินเท่านั้น", ephemeral=True)
        await interaction.response.send_modal(AddCreditModal())

class ShopMenu(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="VIP Gold 300฿", style=nextcord.ButtonStyle.green, custom_id="buy_gold", emoji="🥇", row=0)
    async def buy_gold(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await buy_role(interaction, "VIP Gold", 300)

    @nextcord.ui.button(label="VIP Silver 200฿", style=nextcord.ButtonStyle.gray, custom_id="buy_silver", emoji="🥈", row=0)
    async def buy_silver(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await buy_role(interaction, "VIP Silver", 200)

    @nextcord.ui.button(label="VIP Bronze 100฿", style=nextcord.ButtonStyle.red, custom_id="buy_bronze", emoji="🥉", row=0)
    async def buy_bronze(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await buy_role(interaction, "VIP Bronze", 100)

    @nextcord.ui.button(label="ดูสิทธิ์ VIP", style=nextcord.ButtonStyle.blurple, custom_id="view_perks", emoji="📜", row=1)
    async def view_perks(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(title="📜 สิทธิพิเศษ VIP [สำหรับเซิฟ SAMP]", color=0x00FFFF)
        embed.add_field(
            name="🥉 VIP Bronze - 100฿", 
            value="```1. คำสั่ง /vipheal ฮีลเลือด CD 10 นาที\n2. เปลี่ยนป้ายทะเบียนฟรี /vipplate\n3. เงินเดือน Payday +20%\n4. เกิดโรงบาลไม่เสียเงิน```", 
            inline=False
        )
        embed.add_field(
            name="🥈 VIP Silver - 200฿", 
            value="```ได้สิทธิ์ Bronze ทั้งหมด +\n1. เสกรถ VIP /vipcar ใช้ได้ 24 ชม.\n2. ได้ปืนพกตอนเกิด /vipweapons\n3. ใช้สกินพิเศษ /vipskin\n4. ช่องเก็บของ +10```", 
            inline=False
        )
        embed.add_field(
            name="🥇 VIP Gold - 300฿", 
            value="```ได้สิทธิ์ Silver ทั้งหมด +\n1. เสกเกราะ /viparmor CD 15 นาที\n2. เจ็ทแพ็ค /vipjetpack 5 นาที\n3. ไนตรัสฟรี /vipnos\n4. วาป /gotols /gotosf /gotolv\n5. ชื่อทอง [GOLD] ในเกม```", 
            inline=False
        )
        embed.set_footer(text="*สิทธิ์จะมีผลเมื่อเซิฟ SAMP เปิดให้บริการ")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event 
async def on_ready(): 
    print(f'BOT ONLINE: {bot.user}') 
    bot.add_view(MainMenu())
    bot.add_view(ShopMenu())

@bot.command(name="เมนู") 
@commands.has_permissions(administrator=True) 
async def menu_command(ctx): 
    embed = nextcord.Embed(title="🏦 ระบบเติมเงิน & ร้านค้า", description="เลือกเมนูที่ต้องการด้านล่าง", color=0x00ff00) 
    await ctx.send(embed=embed, view=MainMenu()) 

bot.run(TOKEN)
