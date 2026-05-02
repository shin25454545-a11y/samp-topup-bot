import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os
import json

# --- 1. จัดการข้อมูลเงิน ---
def load_data():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open('users.json', 'w') as f:
        json.dump(data, f, indent=4)

# --- 2. หน้าต่างกรอกเงินสำหรับแอดมิน ---
class AddMoneyModal(Modal, title='เติมเงินให้สมาชิก'):
    money = TextInput(label='จำนวนเงินที่ต้องการเติม', placeholder='เช่น 100')

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.money.value)
            users = load_data()
            uid = str(self.member.id)
            users[uid] = users.get(uid, 0) + amount
            save_data(users)
            await interaction.response.send_message(f"✅ เติมเงินให้ {self.member.mention} เรียบร้อย! (+{amount}฿)", ephemeral=True)
        except:
            await interaction.response.send_message("❌ กรุณากรอกเป็นตัวเลขเท่านั้น!", ephemeral=True)

# --- 3. หน้าตาส่วนของ "ปุ่มกด" ---
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 เช็คยอดเงิน", style=discord.ButtonStyle.success, custom_id="check_balance")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        users = load_data()
        balance = users.get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 ยอดเงินปัจจุบันของคุณ: **{balance}฿**", ephemeral=True)

    @discord.ui.button(label="💵 เติมเงิน (QR Code)", style=discord.ButtonStyle.primary, custom_id="topup")
    async def topup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        promptpay = "0886560336"
        embed = discord.Embed(title="🧧 เติมเงิน", description=f"แสกน QR Code เบอร์ `{promptpay}`\nแล้วแจ้งสลิปแอดมินครับ", color=0xFFD700)
        embed.set_image(url=f"https://promptpay.io{promptpay}.png")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚙️ แอดมินแอดเงิน", style=discord.ButtonStyle.secondary, custom_id="admin_add")
    async def admin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้น!", ephemeral=True)
        
        view = View()
        select = discord.ui.UserSelect(placeholder="เลือกคนที่จะเติมเงินให้...")
        async def callback(inter: discord.Interaction):
            await inter.response.send_modal(AddMoneyModal(select.values[0]))
        select.callback = callback
        view.add_item(select)
        await interaction.response.send_message("เลือกสมาชิก:", view=view, ephemeral=True)

    @discord.ui.button(label="👑 ซื้อยศ VIP", style=discord.ButtonStyle.danger, custom_id="buy_vip")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        
        async def buy_logic(inter, role_name, price):
            users = load_data()
            uid = str(inter.user.id)
            if users.get(uid, 0) < price:
                return await inter.response.send_message(f"❌ เงินไม่พอ! (ต้องการ {price}฿)", ephemeral=True)
            
            role = discord.utils.get(inter.guild.roles, name=role_name)
            if not role:
                return await inter.response.send_message(f"❌ ไม่พบยศ '{role_name}' ในเซิร์ฟเวอร์", ephemeral=True)
            
            users[uid] -= price
            save_data(users)
            await inter.user.add_roles(role)
            await inter.response.send_message(f"✅ ซื้อยศ {role_name} สำเร็จ! (หัก {price}฿)", ephemeral=True)

        btn1 = Button(label="VIP Gold (300฿)", style=discord.ButtonStyle.secondary)
        btn1.callback = lambda i: buy_logic(i, "VIP Gold", 300)
        btn2 = Button(label="VIP Silver (150฿)", style=discord.ButtonStyle.secondary)
        btn2.callback = lambda i: buy_logic(i, "VIP Silver", 150)
        
        view.add_item(btn1)
        view.add_item(btn2)
        await interaction.response.send_message("เลือกยศที่ต้องการซื้อ:", view=view, ephemeral=True)

# --- 4. เริ่มบอท ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="เมนู")
async def menu(ctx):
    embed = discord.Embed(title="🤖 ระบบอัตโนมัติ", description="เลือกทำรายการด้านล่างได้เลยครับ", color=0x9B59B6)
    await ctx.send(embed=embed, view=MenuView())

bot.run(os.getenv('BOT_TOKEN'))
