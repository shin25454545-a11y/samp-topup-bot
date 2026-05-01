import nextcord 
from nextcord.ext import commands 
import json 
import os 

TOKEN = os.getenv("DISCORD_TOKEN") 
PROMPTPAY_ID = "0886560336" 
DATA_FILE = "topup_data.json" 
QR_IMAGE_URL = f"https://promptpay.io/{PROMPTPAY_ID}.png" 

# โหลดข้อมูลเก่า
if os.path.exists(DATA_FILE): 
    with open(DATA_FILE, 'r', encoding='utf-8') as f: 
        topup_data = json.load(f) 
else: 
    topup_data = {} 

# ตั้งค่า Intents - สำคัญมาก
intents = nextcord.Intents.default() 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

def save_data(): 
    with open(DATA_FILE, 'w', encoding='utf-8') as f: 
        json.dump(topup_data, f, ensure_ascii=False, indent=4) 

# ปุ่มเติมเงิน - แบบ Persistent
class TopupMenu(nextcord.ui.View): 
    def __init__(self): 
        super().__init__(timeout=None) 
    
    @nextcord.ui.button(label="เติมเงิน", style=nextcord.ButtonStyle.green, custom_id="topup_button_persistent") 
    async def topup_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction): 
        await interaction.response.send_message(
            f"**สแกน QR เพื่อเติมเงิน**\n"
            f"PromptPay: `{PROMPTPAY_ID}`\n\n"
            f"**ลิงก์ QR:** {QR_IMAGE_URL}\n\n"
            f"โอนแล้วกรุณาแนบสลิปในห้องนี้",
            ephemeral=True
        )

@bot.event 
async def on_ready(): 
    print(f'BOT ONLINE: {bot.user}') 
    bot.add_view(TopupMenu()) # ทำให้ปุ่มกดได้หลังรีบอท

# คำสั่งเรียกเมนู
@bot.command(name="เมนู") 
@commands.has_permissions(administrator=True) 
async def menu_command(ctx): 
    embed = nextcord.Embed( 
        title="ระบบเติมเงินอัตโนมัติ", 
        description="กดปุ่ม 'เติมเงิน' ด้านล่างเพื่อรับ QR Code", 
        color=0x00ff00 
    ) 
    await ctx.send(embed=embed, view=TopupMenu()) 

bot.run(TOKEN)
