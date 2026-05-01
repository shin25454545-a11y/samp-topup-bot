import nextcord
from nextcord.ext import commands
import json
import os

# 1.  Token  Railway  
TOKEN = os.getenv("DISCORD_TOKEN")
PROMPTPAY_ID = "0886560336"  # 
DATA_FILE = "topup_data.json"
QR_IMAGE_URL = f"https://promptpay.io/{PROMPTPAY_ID}.png"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        topup_data = json.load(f)
else:
    topup_data = {}

intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(topup_data, f, ensure_ascii=False, indent=4)

class TopupMenu(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label=" ", style=nextcord.ButtonStyle.green)
    async def check_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        user_id = str(interaction.user.id)
         = topup_data.get(user_id, 0)
        await interaction.response.send_message(f"  {interaction.user.mention}  {:,} ", ephemeral=True)

    @nextcord.ui.button(label="  QR ", style=nextcord.ButtonStyle.blurple)
    async def qrcode_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(
            title="  QR ",
            description=f"1.  QR Code \n2.  `{PROMPTPAY_ID}`\n3. ** 10 **\n4.   @ ",
            color=0x3498db
        )
        embed.set_image(url=QR_IMAGE_URL)
        embed.set_footer(text=" SAMP CITY")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"BOT ONLINE: {bot.user}")
    bot.add_view(TopupMenu())

@bot.command()
async def (ctx):
    embed = nextcord.Embed(title="  SAMP CITY", description="", color=0x00ff00)
    await ctx.send(embed=embed, view=TopupMenu())

@commands.has_permissions(administrator=True)
@bot.command(name="")
async def topup_admin(ctx, : int, : nextcord.Member):
    if  < 10:
        await ctx.send(f" {ctx.author.mention}  10 ")
        return
    user_id = str(.id)
    topup_data[user_id] = topup_data.get(user_id, 0) + 
    save_data()
    await ctx.send(f"  {ctx.author.mention}  {.mention} {:,} \n : {topup_data[user_id]:,} ")

@topup_admin.error
async def topup_admin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(" ")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("  : `!  @`")

bot.run(TOKEN)