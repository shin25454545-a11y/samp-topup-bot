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

# --- 2. หน้าต่างกรอกจำนวนเงิน (Modal) ---
class AddMoneyModal(Modal, title='เติมเงินให้สมาชิก'):
    money = TextInput(label='จำนวนเงินที่ต้องการเติม', placeholder='ตัวอย่าง: 100', min_length=1, max_length=10)

    def __init__(self, member):
        super().__init__()
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.money.value)
            users = load_data()
            user_id = str(self.member.id)
            users[user_id] = users.get(user_id, 0) + amount
            save_data(users)
            await interaction.response.send_message(f"✅ เติมเงินให้ {self.member.mention} จำนวน **{amount}฿** สำเร็จ!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ กรุณากรอกเป็นตัวเลขเท่านั้นครับพี่!", ephemeral=True)

# --- 3. หน้าตาส่วนของ "ปุ่มกด" ---
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 เช็คยอดเงิน", style=discord.ButtonStyle.success, custom_id="check_balance")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        users = load_data()
        balance = users.get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 ยอดเงินของคุณคือ: **{balance}฿**", ephemeral=True)

    @discord.ui.button(label="💵 เติมเงิน (QR Code)", style=discord.ButtonStyle.primary, custom_id="topup")
    async def topup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        promptpay_number = "0886560336"
        qr_url = f"https://promptpay.io{promptpay_number}.png"
        embed = discord.Embed(title="🧧 ช่องทางการเติมเงิน", description=f"แสกน QR Code นี้แล้วส่งสลิปให้แอดมินนะครับ\nเบอร์: `{promptpay_number}`", color=0xFFD700)
        embed.set_image(url=qr_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ปุ่มแอดเงิน (เฉพาะ Admin)
    @discord.ui.button(label="⚙️ แอดมินจัดการเงิน", style=discord.ButtonStyle.secondary, custom_id="admin_manage")
    async def admin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ ปุ่มนี้สำหรับแอดมินเท่านั้นครับพี่!", ephemeral=True)
        
        # สร้าง View ใหม่สำหรับเลือกคนที่จะแอดเงิน (จะเด้งมาเฉพาะหน้าแอดมิน)
        view = discord.ui.View()
        select = discord.ui.UserSelect(placeholder="เลือกสมาชิกที่ต้องการเติมเงินให้...")
        
        async def select_callback(inter: discord.Interaction):
            target_user = select.values[0]
            await inter.response.send_modal(AddMoneyModal(target_user))
        
        select.callback = select_callback
        view.add_item(select)
        await interaction.response.send_message("โปรดเลือกสมาชิกที่ต้องการเติมเงิน:", view=view, ephemeral=True)

# --- 4. ตั้งค่าบอทและคำสั่ง ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="เมนู")
async def menu(ctx):
    embed = discord.Embed(title="🤖 ระบบจัดการสมาชิก", description="เลือกกดปุ่มด้านล่างได้เลยครับ", color=discord.Color.purple())
    await ctx.send(embed=embed, view=MenuView())

@bot.event
async def on_ready():
    print(f'บอท {bot.user} พร้อมระบบแอดมินมือถือแล้ว!')

token = os.getenv('BOT_TOKEN')
bot.run(token)
