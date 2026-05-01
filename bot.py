import nextcord 
from nextcord.ext import commands 
import json 
import os 

TOKEN = os.getenv("DISCORD_TOKEN") 
PROMPTPAY_ID = "0886560336" 
DATA_FILE = "topup_data.json" 
QR_IMAGE_URL = f"https://promptpay.io/{PROMPTPAY_ID}.png"
ADMIN_CHANNEL_ID = 0  # ใส่ ID ห้อง Log แอดมิน ถ้าไม่มีใส่ 0

# โหลดข้อมูล
if os.path.exists(DATA_FILE): 
    with open(DATA_FILE, 'r', encoding='utf-8') as f: 
        topup_data = json.load(f) 
else: 
    topup_data = {}

def save_data(): 
    with open(DATA_FILE, 'w', encoding='utf-8') as f: 
        json.dump(topup_data, f, ensure_ascii=False, indent=4) 

def get_credit(user_id):
    return topup_data.get(str(user_id), 0)

def add_credit(user_id, amount):
    user_id = str(user_id)
    if user_id not in topup_data:
        topup_data[user_id] = 0
    topup_data[user_id] += amount
    save_data()

intents = nextcord.Intents.default() 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# ---------- Modal เติมเครดิตให้ User ----------
class AddCreditModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("เติมเครดิตให้สมาชิก")
        self.user_id = nextcord.ui.TextInput(
            label="ใส่ ID ผู้ใช้", 
            placeholder="คลิกขวาที่ชื่อ > Copy User ID",
            required=True
        )
        self.amount = nextcord.ui.TextInput(
            label="จำนวนเครดิต", 
            placeholder="ใส่ตัวเลข เช่น 100",
            required=True
        )
        self.add_item(self.user_id)
        self.add_item(self.amount)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            user_id = int(self.user_id.value)
            amount = int(self.amount.value)
            add_credit(user_id, amount)
            
            user = await bot.fetch_user(user_id)
            await interaction.response.send_message(f"เติม {amount}฿ ให้ {user.mention} สำเร็จ\nยอดปัจจุบัน: {get_credit(user_id)}฿", ephemeral=True)
            
            # ส่ง Log
            if ADMIN_CHANNEL_ID != 0:
                channel = bot.get_channel(ADMIN_CHANNEL_ID)
                if channel:
                    await channel.send(f"[ADMIN] {interaction.user.mention} เติม {amount}฿ ให้ {user.mention}")
        except:
            await interaction.response.send_message("ผิดพลาด! เช็ค ID กับจำนวนเงินอีกที", ephemeral=True)

# ---------- ปุ่มเมนูหลัก ----------
class MainMenu(nextcord.ui.View): 
    def __init__(self): 
        super().__init__(timeout=None) 
    
    @nextcord.ui.button(label="เติมเงิน", style=nextcord.ButtonStyle.green, custom_id="btn_topup", emoji="💰") 
    async def topup_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        await interaction.response.send_message(
            f"**สแกน QR เพื่อเติมเงิน**\n"
            f"PromptPay: `{PROMPTPAY_ID}`\n\n"
            f"**ลิงก์ QR:** {QR_IMAGE_URL}\n\n"
            f"โอนแล้วแนบสลิปในห้องนี้ แล้วแท็กแอดมิน",
            ephemeral=True
        )

    @nextcord.ui.button(label="เช็คเครดิต", style=nextcord.ButtonStyle.blurple, custom_id="btn_credit", emoji="💳") 
    async def credit_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        credit = get_credit(interaction.user.id)
        await interaction.response.send_message(f"**เครดิตของ {interaction.user.mention}**\n💵 ยอดคงเหลือ: `{credit}฿`", ephemeral=True)

    @nextcord.ui.button(label="ร้านค้า", style=nextcord.ButtonStyle.gray, custom_id="btn_shop", emoji="🛒") 
    async def shop_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        await interaction.response.send_message(embed=nextcord.Embed(title="🛒 ร้านค้า", description="เลือกสินค้าที่ต้องการ"), view=ShopMenu(), ephemeral=True)

    @nextcord.ui.button(label="แอดมินเติมเงิน", style=nextcord.ButtonStyle.red, custom_id="btn_admin", emoji="⚙️") 
    async def admin_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("ใช้ได้เฉพาะแอดมินเท่านั้น", ephemeral=True)
        await interaction.response.send_modal(AddCreditModal())

# ---------- ปุ่มร้านค้า ----------
class ShopMenu(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="ยศ VIP 100฿", style=nextcord.ButtonStyle.green, custom_id="buy_vip")
    async def buy_vip(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        price = 100
        credit = get_credit(interaction.user.id)
        if credit < price:
            return await interaction.response.send_message(f"เครดิตไม่พอ! ขาดอีก {price - credit}฿", ephemeral=True)
        
        add_credit(interaction.user.id, -price)
        vip_role = nextcord.utils.get(interaction.guild.roles, name="VIP")
        if vip_role:
            await interaction.user.add_roles(vip_role)
            await interaction.response.send_message(f"ซื้อ `ยศ VIP` สำเร็จ! หัก {price}฿ คงเหลือ {get_credit(interaction.user.id)}฿", ephemeral=True)
        else:
            await interaction.response.send_message("ซื้อสำเร็จ แต่หา @VIP ในเซิฟไม่เจอ แจ้งแอดมินสร้างยศชื่อ `VIP` ที", ephemeral=True)

    @nextcord.ui.button(label="สีชื่อรุ้ง 50฿", style=nextcord.ButtonStyle.green, custom_id="buy_rainbow")
    async def buy_rainbow(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        price = 50
        credit = get_credit(interaction.user.id)
        if credit < price:
            return await interaction.response.send_message(f"เครดิตไม่พอ! ขาดอีก {price - credit}฿", ephemeral=True)
        
        add_credit(interaction.user.id, -price)
        rainbow_role = nextcord.utils.get(interaction.guild.roles, name="สีรุ้ง")
        if rainbow_role:
            await interaction.user.add_roles(rainbow_role)
            await interaction.response.send_message(f"ซื้อ `สีชื่อรุ้ง` สำเร็จ! หัก {price}฿ คงเหลือ {get_credit(interaction.user.id)}฿", ephemeral=True)
        else:
            await interaction.response.send_message("ซื้อสำเร็จ แต่หา @สีรุ้ง ในเซิฟไม่เจอ แจ้งแอดมินสร้างยศชื่อ `สีรุ้ง` ที", ephemeral=True)

@bot.event 
async def on_ready(): 
    print(f'BOT ONLINE: {bot.user}') 
    bot.add_view(MainMenu())
    bot.add_view(ShopMenu())

@bot.command(name="เมนู") 
@commands.has_permissions(administrator=True) 
async def menu_command(ctx): 
    embed = nextcord.Embed( 
        title="🏦 ระบบเติมเงิน & ร้านค้า", 
        description="เลือกเมนูที่ต้องการด้านล่าง\nทั้งหมดเป็นระบบอัตโนมัติ",
        color=0x00ff00 
    ) 
    await ctx.send(embed=embed, view=MainMenu()) 

bot.run(TOKEN)
