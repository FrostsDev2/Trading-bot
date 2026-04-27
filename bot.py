# FIXED
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
COLOR = 0xE6A6FF


# -----------------------------
# SAFE DATA FETCH (IMPORTANT FIX)
# -----------------------------
def get_data(symbol, interval="1h", period="1mo"):
    try:
        df = yf.download(symbol, interval=interval, period=period)

        if df is None or df.empty:
            return None

        df = df.copy()

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()

        if df.empty:
            return None

        return df.astype(float)

    except:
        return None


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
        title="📊 Trading Bot Commands",
        color=COLOR,
        description="""
/price symbol
/chart symbol interval
/indicators symbol interval
/signal symbol
/forex pair
/commodity oil|gold
/options symbol

📈 Intervals: 1m, 5m, 15m, 1h, 1d
"""
    )
    await interaction.response.send_message(embed=embed)


# -----------------------------
# /price
# -----------------------------
@bot.tree.command(name="price", description="Get asset price")
async def price(interaction: discord.Interaction, symbol: str):
    data = yf.Ticker(symbol).history(period="1d")

    if data.empty:
        return await interaction.response.send_message(
            embed=discord.Embed(description="❌ Invalid symbol", color=COLOR)
        )

    price = data["Close"].iloc[-1]

    embed = discord.Embed(
        title=f"📊 {symbol.upper()}",
        description=f"**${price:.2f}**",
        color=COLOR
    )

    await interaction.response.send_message(embed=embed)


# -----------------------------
# /chart (FIXED CLEAN VERSION)
# -----------------------------
@bot.tree.command(name="chart", description="Candlestick chart")
async def chart(interaction: discord.Interaction, symbol: str, interval: str = "1h"):
    await interaction.response.defer()

    valid = ["1m", "5m", "15m", "1h", "1d"]
    if interval not in valid:
        return await interaction.followup.send(
            embed=discord.Embed(description="❌ Invalid interval", color=COLOR)
        )

    data = get_data(symbol, interval)

    if data is None:
        return await interaction.followup.send(
            embed=discord.Embed(description="❌ No valid data", color=COLOR)
        )

    # 🎨 Chart style (black TradingView-like)
    mc = mpf.make_marketcolors(
        up="lime",
        down="red",
        wick="white",
        volume="inherit"
    )

    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
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
        title=f"📈 {symbol.upper()} Chart",
        description=f"Interval: {interval}",
        color=COLOR
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
            embed=discord.Embed(description="❌ No data", color=COLOR)
        )

    close = data["Close"]

    rsi = RSIIndicator(close).rsi().iloc[-1]
    macd = MACD(close).macd().iloc[-1]
    sma = SMAIndicator(close, window=20).sma_indicator().iloc[-1]

    embed = discord.Embed(
        title=f"📊 {symbol.upper()} Indicators",
        color=COLOR
    )

    embed.add_field(name="RSI", value=f"{rsi:.2f}")
    embed.add_field(name="MACD", value=f"{macd:.2f}")
    embed.add_field(name="SMA(20)", value=f"{sma:.2f}")

    await interaction.response.send_message(embed=embed)


# -----------------------------
# /signal
# -----------------------------
@bot.tree.command(name="signal", description="Buy/Sell signal")
async def signal(interaction: discord.Interaction, symbol: str):
    data = get_data(symbol, "1h", "3mo")

    if data is None:
        return await interaction.response.send_message(
            embed=discord.Embed(description="❌ No data", color=COLOR)
        )

    rsi = RSIIndicator(data["Close"]).rsi().iloc[-1]

    if rsi < 30:
        msg = "🟢 BUY ZONE"
    elif rsi > 70:
        msg = "🔴 SELL ZONE"
    else:
        msg = "🟡 NEUTRAL"

    embed = discord.Embed(
        title=f"{symbol.upper()} Signal",
        description=f"{msg}\nRSI: {rsi:.2f}",
        color=COLOR
    )

    await interaction.response.send_message(embed=embed)


# -----------------------------
# /forex
# -----------------------------
@bot.tree.command(name="forex", description="Forex prices")
async def forex(interaction: discord.Interaction, pair: str):
    symbol = pair.upper() + "=X"
    data = yf.Ticker(symbol).history(period="1d")

    if data.empty:
        return await interaction.response.send_message(
            embed=discord.Embed(description="❌ Invalid pair", color=COLOR)
        )

    price = data["Close"].iloc[-1]

    embed = discord.Embed(
        title=f"💱 {pair.upper()}",
        description=f"{price:.5f}",
        color=COLOR
    )

    await interaction.response.send_message(embed=embed)


# -----------------------------
# /commodity (oil / gold)
# -----------------------------
@bot.tree.command(name="commodity", description="Oil or Gold")
async def commodity(interaction: discord.Interaction, name: str):
    mapping = {"oil": "CL=F", "gold": "GC=F"}

    symbol = mapping.get(name.lower())
    if not symbol:
        return await interaction.response.send_message(
            embed=discord.Embed(description="Use oil or gold", color=COLOR)
        )

    data = yf.Ticker(symbol).history(period="1d")

    if data.empty:
        return await interaction.response.send_message(
            embed=discord.Embed(description="❌ No data", color=COLOR)
        )

    price = data["Close"].iloc[-1]

    embed = discord.Embed(
        title=f"📦 {name.upper()}",
        description=f"${price:.2f}",
        color=COLOR
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
            color=COLOR
        )

        calls_text = "\n".join(
            f"{r['strike']} | {r['lastPrice']} | vol {r['volume']}"
            for _, r in calls.iterrows()
        )

        puts_text = "\n".join(
            f"{r['strike']} | {r['lastPrice']} | vol {r['volume']}"
            for _, r in puts.iterrows()
        )

        embed.add_field(name="CALLS", value=calls_text or "None", inline=False)
        embed.add_field(name="PUTS", value=puts_text or "None", inline=False)

        await interaction.response.send_message(embed=embed)

    except:
        await interaction.response.send_message(
            embed=discord.Embed(description="❌ Options unavailable", color=COLOR)
        )


# -----------------------------
bot.run(TOKEN)