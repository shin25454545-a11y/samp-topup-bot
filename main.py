import discord
from discord.ext import commands
import os
import qrcode
import io
from promptpay import qrcode as pp_qr
import datetime

# ตั้งค่าหลัก
PROMPTPAY_ID = "0886560336"  # เบอร์พร้อมเพย์ท่าน
ADMIN_CHANNEL_ID = 1500036196703707308
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# เก็บออเดอร์ชั่วคราว
pending_orders = {}

class VIPShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🥉 Bronze 50฿", style=discord.ButtonStyle.secondary, custom_id="bronze")
    async def bronze_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_payment(interaction, "VIP Bronze", 50)

    @discord.ui.button(label="🥈 Silver 150฿", style=discord.ButtonStyle.secondary, custom_id="silver") 
    async def silver_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_payment(interaction, "VIP Silver", 150)

    @discord.ui.button(label="🥇 Gold 300฿", style=discord.ButtonStyle.secondary, custom_id="gold")
    async def gold_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_payment(interaction, "VIP Gold", 300)

    async def create_payment(self, interaction: discord.Interaction, product_name: str, price: int):
        # สร้าง QR PromptPay
        payload = pp_qr.generate_payload(PROMPTPAY_ID, amount=price)
        img = qrcode.make(payload)
        buffer = io.BytesIO()
        img.save(buffer, 'PNG')
        buffer.seek(0)
        
        # เก็บออเดอร์
        order_id = f"{interaction.user.id}_{int(datetime.datetime.now().timestamp())}"
        pending_orders[order_id] = {
            "user_id": interaction.user.id,
            "product": product_name,
            "price": price
        }
        
        # ปุ่มแจ้งโอน
        view = ConfirmPaymentView(order_id)
        file = discord.File(buffer, filename="qr.png")
        
        embed = discord.Embed(
            title=f"💸 ชำระเงิน {product_name}",
            description=f"**ยอดชำระ: {price}฿**\n\n1. สแกน QR เพื่อจ่ายเงิน\n2. กดปุ่ม `📢 แจ้งโอนเงินแล้ว` ด้านล่าง",
            color=0x00ff00
        )
        embed.set_image(url="attachment://qr.png")
        await interaction.response.send_message(embed=embed, file=file, view=view, ephemeral=True)

class ConfirmPaymentView(discord.ui.View):
    def __init__(self, order_id):
        super().__init__(timeout=600)
        self.order_id = order_id

    @discord.ui.button(label="📢 แจ้งโอนเงินแล้ว", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        order = pending_orders.get(self.order_id)
        if not order:
            await interaction.response.send_message("ออเดอร์หมดอายุแล้ว กรุณาทำรายการใหม่", ephemeral=True)
            return

        # ส่งไปห้องแอดมิน
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            user = interaction.user
            embed = discord.Embed(
                title="🔔 ออเดอร์ใหม่รอตรวจ",
                description=f"**ลูกค้า:** {user.mention} `{user.id}`\n**สินค้า:** {order['product']}\n**ยอด:** {order['price']}฿",
                color=0xffa500
            )
            view = ApproveView(self.order_id)
            await admin_channel.send(embed=embed, view=view)
            await interaction.response.edit_message(content="✅ แจ้งโอนเงินแล้ว รอแอดมินตรวจสอบ 1-5 นาที", embed=None, view=None, attachments=[])
        else:
            await interaction.response.send_message("ไม่พบห้องแอดมิน กรุณาติดต่อร้านค้า", ephemeral=True)

class ApproveView(discord.ui.View):
    def __init__(self, order_id):
        super().__init__(timeout=None)
        self.order_id = order_id

    @discord.ui.button(label="✅ อนุมัติ", style=discord.ButtonStyle.success, custom_id="approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        order = pending_orders.pop(self.order_id, None)
        if not order:
            await interaction.response.send_message("ออเดอร์นี้ถูกจัดการไปแล้ว", ephemeral=True)
            return

        guild = interaction.guild
        member = guild.get_member(order['user_id'])
        role = discord.utils.get(guild.roles, name=order['product'])
        
        if member and role:
            await member.add_roles(role)
            await interaction.response.edit_message(content=f"✅ อนุมัติ {order['product']} ให้ {member.mention} เรียบร้อย", embed=None, view=None)
            try:
                await member.send(f"🎉 ยินดีด้วย! คุณได้รับยศ {order['product']} แล้ว\nหมดอายุใน 30 วัน")
            except:
                pass
        else:
            await interaction.response.send_message("ไม่พบลูกค้าหรือยศในเซิร์ฟเวอร์", ephemeral=True)

@bot.event
async def on_ready():
    print(f'บอท {bot.user} ออนไลน์แล้ว!')
    bot.add_view(VIPShopView())
    
# คำสั่ง !เมนู ภาษาไทย
@bot.command(name="เมนู")
@commands.has_permissions(administrator=True)
async def menu_th(ctx):
    embed = discord.Embed(
        title="👑 PREMIUM MEMBERSHIP",
        description="**เลือกแพ็กเกจที่ต้องการด้านล่าง**\n\n**🥉 BRONZE** `50฿`\n`└ EXP x1.5 | ห้องพิเศษ`\n\n**🥈 SILVER** `150฿`\n`└ EXP x2.0 | ห้องพิเศษ | สีชื่อ`\n\n**🥇 GOLD** `300฿`\n`└ EXP x3.0 | ห้องพิเศษ | สีชื่อ | ยศทอง`",
        color=0x2b2d31
    )
    embed.set_image(url="https://i.imgur.com/u6i1b4G.png") # เปลี่ยนลิงก์รูปได้
    await ctx.send(embed=embed, view=VIPShopView())

# ซ่อน Error คำสั่งมั่ว
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

bot.run(TOKEN)
