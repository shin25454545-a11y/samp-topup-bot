import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import os
import json

# --- 1. จัดการข้อมูลเงิน (เหมือนเดิม) ---
def load_data():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open('users.json', 'w') as f:
        json.dump(data, f, indent=4)

# --- 2. หน้าต่างแอดมินเติมเงิน (เหมือนเดิม) ---
class AddMoneyModal(Modal, title='เติมเงินให้สมาชิก'):
    money = TextInput(label='จำนวนเงินที่ต้องการเติม', placeholder='ตัวอย่าง: 100')
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

# --- 3. หน้าตาส่วนของ "ปุ่มกด" (รวมฟีเจอร์ใหม่) ---
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💰 เช็คยอดเงิน", style=discord.ButtonStyle.success, custom_id="check_balance")
    async def balance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        users = load_data()
        balance = users.get(str(interaction.user.id), 0)
        await interaction.response.send_message(f"💰 ยอดเงินปัจจุบันของคุณ: **{balance}฿**", ephemeral=True)

    @discord.ui.button(label="📋 รายละเอียด VIP", style=discord.ButtonStyle.secondary, custom_id="vip_info")
    async def vip_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="✨ สิทธิพิเศษระดับ VIP", description="รายละเอียดสิทธิพิเศษแต่ละระดับ", color=0xF1C40F)
        embed.add_field(name="👑 VIP Gold (300฿)", value="• สีชื่อสีทอง\n• เข้าห้องลับ Gold\n• ส่งไฟล์/รูปภาพได้ทุกห้อง", inline=False)
        embed.add_field(name="🥈 VIP Silver (150฿)", value="• สีชื่อสีเงิน\n• เข้าห้องนั่งเล่น VIP\n• เปลี่ยนชื่อตัวเองได้", inline=False)
        embed.add_field(name="🥉 VIP Bronze (50฿)", value="• สีชื่อสีทองแดง\n• ยศประดับหน้าชื่อ", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👑 ซื้อยศ VIP", style=discord.ButtonStyle.danger, custom_id="buy_vip")
    async def shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = View()
        async def buy_logic(inter, role_name, price):
            users = load_data()
            uid = str(inter.user.id)
            role = discord.utils.get(inter.guild.roles, name=role_name)
            if not role:
                return await inter.response.send_message(f"❌ ไม่พบยศ '{role_name}' ในเซิร์ฟเวอร์", ephemeral=True)
            if role in inter.user.roles:
                return await inter.response.send_message(f"⚠️ พี่มียศ **{role_name}** อยู่แล้วครับ!", ephemeral=True)
            if users.get(uid, 0) < price:
                return await inter.response.send_message(f"❌ เงินไม่พอ! (ยศนี้ {price}฿)", ephemeral=True)
            
            users[uid] -= price
            save_data(users)
            await inter.user.add_roles(role)
            announce = discord.Embed(title="🎉 สมาชิก VIP คนใหม่!", description=f"ยินดีกับคุณ {inter.user.mention} ที่ได้ซื้อยศ **{role_name}** 👑", color=0x00FF00)
            await inter.channel.send(embed=announce)
            await inter.response.send_message(f"✅ ซื้อยศ {role_name} สำเร็จ!", ephemeral=True)

        btn1 = Button(label="VIP Gold (300฿)", style=discord.ButtonStyle.secondary)
        btn1.callback = lambda i: buy_logic(i, "VIP Gold", 300)
        btn2 = Button(label="VIP Silver (150฿)", style=discord.ButtonStyle.secondary)
        btn2.callback = lambda i: buy_logic(i, "VIP Silver", 150)
        btn3 = Button(label="VIP Bronze (50฿)", style=discord.ButtonStyle.secondary)
        btn3.callback = lambda i: buy_logic(i, "VIP Bronze", 50)
        
        view.add_item(btn1); view.add_item(btn2); view.add_item(btn3)
        await interaction.response.send_message("เลือกยศที่ต้องการซื้อ:", view=view, ephemeral=True)

    @discord.ui.button(label="💵 เติมเงิน (QR)", style=discord.ButtonStyle.primary, custom_id="topup")
    async def topup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        promptpay = "0886560336"
        qr_url = f"https://promptpay.io{promptpay}.png"
        embed = discord.Embed(title="🧧 ช่องทางการเติมเงิน", description=f"แสกน QR เพื่อเติมเงิน\nเบอร์พร้อมเพย์: `{promptpay}`", color=0xFFD700)
        embed.set_image(url=qr_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚙️ จัดการเงิน", style=discord.ButtonStyle.secondary, custom_id="admin_manage")
    async def admin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้น!", ephemeral=True)
        view = View()
        select = discord.ui.UserSelect(placeholder="เลือกสมาชิก...")
        async def callback(inter: discord.Interaction):
            await inter.response.send_modal(AddMoneyModal(select.values[0])) # แก้ไขให้เลือกคนแรก
        select.callback = callback
        view.add_item(select)
        await interaction.response.send_message("โปรดเลือกสมาชิก:", view=view, ephemeral=True)

# --- 4. ตั้งค่าบอท ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="เมนู")
async def menu(ctx):
    embed = discord.Embed(title="🤖 ระบบจัดการสมาชิก", description="ยินดีต้อนรับครับ! เลือกทำรายการด้านล่างได้เลย", color=0x9B59B6)
    await ctx.send(embed=embed, view=MenuView())

bot.run(os.getenv('BOT_TOKEN'))
