import os
import discord
from discord.ext import commands
from discord import app_commands
import yfinance as yf
import pandas as pd
import mplfinance as mpf
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# 🎨 Embed color (light purple/pink)
EMBED_COLOR = 0xE6A6FF

# -----------------------------
# HELPER
# -----------------------------
def get_data(symbol, interval="1h", period="1mo"):
    data = yf.download(symbol, interval=interval, period=period)
    if data.empty:
        return None

    # Clean data (fix mplfinance crash)
    data = data[["Open", "High", "Low", "Close", "Volume"]]
    data = data.apply(pd.to_numeric, errors='coerce')
    data.dropna(inplace=True)

    return data if not data.empty else None

# -----------------------------
# READY
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# -----------------------------
# /help
# -----------------------------
@bot.tree.command(name="help", description="Show all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📊 Trading Bot Help",
        description="""
/price symbol  
/chart symbol interval  
/indicators symbol interval  
/signal symbol  
/forex pair  
/commodity oil|gold  
/options symbol  

📈 Intervals: 1m, 5m, 15m, 1h, 1d
""",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

# -----------------------------
# /price
# -----------------------------
@bot.tree.command(name="price", description="Get price")
async def price(interaction: discord.Interaction, symbol: str):
    data = yf.Ticker(symbol).history(period="1d")

    if data.empty:
        return await interaction.response.send_message(
            embed=discord.Embed(
                description="❌ Invalid symbol",
                color=EMBED_COLOR
            )
        )

    price = data["Close"].iloc[-1]

    embed = discord.Embed(
        title=f"📊 {symbol.upper()} Price",
        description=f"**${price:.2f}**",
        color=EMBED_COLOR
    )

    await interaction.response.send_message(embed=embed)

# -----------------------------
# /chart
# -----------------------------
@bot.tree.command(name="chart", description="Candlestick chart")
async def chart(interaction: discord.Interaction, symbol: str, interval: str = "1h"):
    await interaction.response.defer()

    valid_intervals = ["1m", "5m", "15m", "1h", "1d"]
    if interval not in valid_intervals:
        return await interaction.followup.send(
            embed=discord.Embed(
                description="❌ Invalid interval",
                color=EMBED_COLOR
            )
        )

    data = get_data(symbol, interval)

    if data is None:
        return await interaction.followup.send(
            embed=discord.Embed(
                description="❌ No data found",
                color=EMBED_COLOR
            )
        )

    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        facecolor="black",
        gridcolor="gray"
    )

    file = f"{symbol}_{interval}.png"

    mpf.plot(
        data,
        type="candle",
        style=style,
        volume=True,
        title=f"{symbol.upper()} {interval}",
        savefig=file
    )

    embed = discord.Embed(
        title=f"📈 {symbol.upper()} Chart ({interval})",
        color=EMBED_COLOR
    )

    await interaction.followup.send(embed=embed, file=discord.File(file))

# -----------------------------
# /indicators
# -----------------------------
@bot.tree.command(name="indicators", description="RSI, MACD, SMA")
async def indicators(interaction: discord.Interaction, symbol: str, interval: str = "1h"):
    data = get_data(symbol, interval, "3mo")

    if data is None:
        return await interaction.response.send_message(
            embed=discord.Embed(description="❌ No data", color=EMBED_COLOR)
        )

    close = data["Close"]

    rsi = RSIIndicator(close).rsi().iloc[-1]
    macd = MACD(close).macd().iloc[-1]
    sma = SMAIndicator(close, window=20).sma_indicator().iloc[-1]

    embed = discord.Embed(
        title=f"📊 {symbol.upper()} Indicators",
        color=EMBED_COLOR
    )
    embed.add_field(name="RSI", value=f"{rsi:.2f}")
    embed.add_field(name="MACD", value=f"{macd:.2f}")
    embed.add_field(name="SMA (20)", value=f"{sma:.2f}")

    await interaction.response.send_message(embed=embed)

# -----------------------------
# /signal
# -----------------------------
@bot.tree.command(name="signal", description="Buy/Sell signal")
async def signal(interaction: discord.Interaction, symbol: str):
    data = get_data(symbol, period="3mo")

    if data is None:
        return await interaction.response.send_message(
            embed=discord.Embed(description="❌ No data", color=EMBED_COLOR)
        )

    rsi = RSIIndicator(data["Close"]).rsi().iloc[-1]

    if rsi < 30:
        signal_text = "🟢 BUY ZONE"
    elif rsi > 70:
        signal_text = "🔴 SELL ZONE"
    else:
        signal_text = "🟡 NEUTRAL"

    embed = discord.Embed(
        title=f"{symbol.upper()} Signal",
        description=f"{signal_text}\nRSI: {rsi:.2f}",
        color=EMBED_COLOR
    )

    await interaction.response.send_message(embed=embed)

# -----------------------------
# /forex
# -----------------------------
@bot.tree.command(name="forex", description="Forex price")
async def forex(interaction: discord.Interaction, pair: str):
    symbol = pair.upper() + "=X"
    data = yf.Ticker(symbol).history(period="1d")

    if data.empty:
        return await interaction.response.send_message(
            embed=discord.Embed(description="❌ Invalid pair", color=EMBED_COLOR)
        )

    price = data["Close"].iloc[-1]

    embed = discord.Embed(
        title=f"💱 {pair.upper()}",
        description=f"{price:.5f}",
        color=EMBED_COLOR
    )

    await interaction.response.send_message(embed=embed)

# -----------------------------
# /commodity
# -----------------------------
@bot.tree.command(name="commodity", description="Oil or Gold")
async def commodity(interaction: discord.Interaction, name: str):
    mapping = {"oil": "CL=F", "gold": "GC=F"}

    symbol = mapping.get(name.lower())
    if not symbol:
        return await interaction.response.send_message(
            embed=discord.Embed(description="Use oil or gold", color=EMBED_COLOR)
        )

    data = yf.Ticker(symbol).history(period="1d")
    price = data["Close"].iloc[-1]

    embed = discord.Embed(
        title=f"📦 {name.upper()}",
        description=f"${price:.2f}",
        color=EMBED_COLOR
    )

    await interaction.response.send_message(embed=embed)

# -----------------------------
# /options
# -----------------------------
@bot.tree.command(name="options", description="Options chain snapshot")
async def options(interaction: discord.Interaction, symbol: str):
    stock = yf.Ticker(symbol)

    try:
        exp = stock.options[0]
        chain = stock.option_chain(exp)

        calls = chain.calls.head(3)
        puts = chain.puts.head(3)

        embed = discord.Embed(
            title=f"📉 {symbol.upper()} Options ({exp})",
            color=EMBED_COLOR
        )

        calls_text = "\n".join([f"{r['strike']} | {r['lastPrice']} | vol {r['volume']}" for _, r in calls.iterrows()])
        puts_text = "\n".join([f"{r['strike']} | {r['lastPrice']} | vol {r['volume']}" for _, r in puts.iterrows()])

        embed.add_field(name="CALLS", value=calls_text or "None", inline=False)
        embed.add_field(name="PUTS", value=puts_text or "None", inline=False)

        await interaction.response.send_message(embed=embed)

    except:
        await interaction.response.send_message(
            embed=discord.Embed(description="❌ Options unavailable", color=EMBED_COLOR)
        )

# -----------------------------
bot.run(TOKEN)