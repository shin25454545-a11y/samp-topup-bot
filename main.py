import discord
from discord.ext import commands
import os
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ตั้งค่ายศกับราคา - แก้ role_id ให้ตรงกับเซิร์ฟท่าน
ROLES_DATA = {
    "VIP Gold": {"price": 300, "role_id": 1499228473095356597},
    "VIP Silver": {"price": 150, "role_id": 1499228661335724072},
    "VIP Bronze": {"price": 50, "role_id": 1499228752234942566}
}

def load_credits():
    credits = {}
    if os.path.exists("credits.txt"):
        with open("credits.txt", "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    user_id, amount = line.strip().split(":")
                    credits[user_id] = int(amount)
    return credits

def save_credits(credits):
    with open("credits.txt", "w", encoding="utf-8") as f:
        for user_id, amount in credits.items():
            f.write(f"{user_id}:{amount}\n")

def log_purchase(user, item_name, price):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    with open("purchase_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{now} | {user} | ซื้อ {item_name} ราคา {price}฿\n")

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for item_name, data in ROLES_DATA.items():
            button = discord.ui.Button(
                label=f"{item_name} {data['price']}฿",
                style=discord.ButtonStyle.blurple,
                custom_id=item_name
            )
            button.callback = self.handle_buy
            self.add_item(button)

    async def handle_buy(self, interaction: discord.Interaction):
        item_name = interaction.data['custom_id']
        price = ROLES_DATA[item_name]['price']
        role_id = ROLES_DATA[item_name]['role_id']

        credits = load_credits()
        user_id = str(interaction.user.id)
        user_credit = credits.get(user_id, 0)

        if user_credit < price:
            await interaction.response.send_message(f"❌ เครดิตไม่พอ! ท่านมี {user_credit}฿ แต่ {item_name} ราคา {price}฿", ephemeral=True)
            return

        credits[user_id] = user_credit - price
        save_credits(credits)

        role = interaction.guild.get_role(role_id)
        if role:
            await interaction.user.add_roles(role)
            log_purchase(interaction.user, item_name, price)
            await interaction.response.send_message(f"✅ ซื้อยศ {item_name} สำเร็จ! เครดิตคงเหลือ {credits[user_id]}฿", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ไม่พบยศในเซิร์ฟเวอร์ ติดต่อแอดมิน", ephemeral=True)

@bot.command()
async def เมนู(ctx):
    embed = discord.Embed(
        title="🏪 ร้าน VIP ของท่าน",
        description="กดปุ่มด้านล่างเพื่อซื้อยศเลย เครดิตจะถูกหักอัตโนมัติ",
        color=0xffd700
    )
    for item_name, data in ROLES_DATA.items():
        embed.add_field(name=item_name, value=f"ราคา `{data['price']}฿`", inline=False)
    embed.set_footer(text="พิมพ์!เติม เพื่อเติมเงิน |!เงิน เพื่อเช็คเครดิต")
    await ctx.send(embed=embed, view=ShopView())

@bot.command()
async def เติม(ctx, member: discord.Member, amount: int):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คำสั่งนี้สำหรับแอดมินเท่านั้น")
        return
    credits = load_credits()
    user_id = str(member.id)
    credits[user_id] = credits.get(user_id, 0) + amount
    save_credits(credits)
    await ctx.send(f"✅ เติมเงินให้ {member.mention} จำนวน {amount}฿ สำเร็จ! ยอดคงเหลือ {credits[user_id]}฿")

@bot.command()
async def เงิน(ctx):
    credits = load_credits()
    user_id = str(ctx.author.id)
    amount = credits.get(user_id, 0)
    await ctx.send(f"💰 {ctx.author.mention} ท่านมีเครดิต {amount}฿")

@bot.command()
async def ประวัติ(ctx):
    if not os.path.exists("purchase_log.txt"):
        await ctx.send("❌ ยังไม่มีประวัติการซื้อ")
        return
    with open("purchase_log.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()[-10:]
    if not lines:
        await ctx.send("❌ ยังไม่มีประวัติการซื้อ")
        return
    embed = discord.Embed(title="📜 ประวัติการซื้อล่าสุด 10 รายการ", color=0x00ff00)
    log_text = "".join([f"`{line.strip()}`\n" for line in reversed(lines)])
    embed.description = log_text
    await ctx.send(embed=embed)

@bot.command()
async def ยอดขาย(ctx):
    total = 0
    count = 0
    if os.path.exists("purchase_log.txt"):
        with open("purchase_log.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "฿" in line:
                    try:
                        price = int(line.split("ราคา ")[1].split("฿")[0])
                        total += price
                        count += 1
                    except: pass
    embed = discord.Embed(title="💰 สรุปยอดขายร้าน", color=0xffd700)
    embed.add_field(name="ยอดขายรวม", value=f"`{total:,}฿`", inline=True)
    embed.add_field(name="จำนวนที่ขายได้", value=f"`{count} ยศ`", inline=True)
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"บอท {bot.user} ออนไลน์แล้ว!")
    bot.add_view(ShopView())

# รันบอทโดยดึง Token จาก Environment Variables
if __name__ == "__main__":
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("❌ ไม่เจอ TOKEN ใน Environment Variables")
    else:
        bot.run(TOKEN)
