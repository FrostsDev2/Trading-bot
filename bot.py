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

# -----------------------------
# HELPER
# -----------------------------
def get_data(symbol, interval="1h", period="1mo"):
    return yf.download(symbol, interval=interval, period=period)

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
@bot.tree.command(name="help", description="Show all trading commands")
async def help_cmd(interaction: discord.Interaction):
    msg = """
📊 **Trading Bot Commands**

/price symbol
/chart symbol interval
/indicators symbol interval
/signal symbol
/forex pair
/commodity oil|gold
/options symbol

📈 Intervals: 1m, 5m, 15m, 1h, 1d
"""
    await interaction.response.send_message(msg)

# -----------------------------
# /price
# -----------------------------
@bot.tree.command(name="price", description="Get current price")
@app_commands.describe(symbol="Stock/crypto ticker (e.g. AAPL, TSLA, BTC-USD)")
async def price(interaction: discord.Interaction, symbol: str):
    data = yf.Ticker(symbol).history(period="1d")
    if data.empty:
        return await interaction.response.send_message("Invalid symbol")

    price = data["Close"].iloc[-1]
    await interaction.response.send_message(f"📊 {symbol.upper()} = **${price:.2f}**")

# -----------------------------
# /chart (candlestick black theme)
# -----------------------------
@bot.tree.command(name="chart", description="Candlestick chart")
@app_commands.describe(symbol="Ticker", interval="Timeframe")
async def chart(interaction: discord.Interaction, symbol: str, interval: str = "1h"):
    await interaction.response.defer()

    data = get_data(symbol, interval=interval)

    if data.empty:
        return await interaction.followup.send("No data found")

    style = mpf.make_mpf_style(base_mpf_style="nightclouds", facecolor="black")

    file = f"{symbol}_{interval}.png"

    mpf.plot(
        data,
        type="candle",
        style=style,
        volume=True,
        title=f"{symbol.upper()} {interval}",
        savefig=file
    )

    await interaction.followup.send(file=discord.File(file))

# -----------------------------
# /indicators
# -----------------------------
@bot.tree.command(name="indicators", description="RSI, MACD, SMA")
async def indicators(interaction: discord.Interaction, symbol: str, interval: str = "1h"):
    data = get_data(symbol, interval=interval, period="3mo")

    if data.empty:
        return await interaction.response.send_message("No data")

    close = data["Close"]

    rsi = RSIIndicator(close).rsi().iloc[-1]
    macd = MACD(close).macd().iloc[-1]
    sma = SMAIndicator(close, window=20).sma_indicator().iloc[-1]

    await interaction.response.send_message(
        f"📊 **{symbol.upper()} Indicators**\n"
        f"RSI: {rsi:.2f}\n"
        f"MACD: {macd:.2f}\n"
        f"SMA20: {sma:.2f}"
    )

# -----------------------------
# /signal
# -----------------------------
@bot.tree.command(name="signal", description="Simple buy/sell signal")
async def signal(interaction: discord.Interaction, symbol: str):
    data = get_data(symbol, period="3mo")

    if data.empty:
        return await interaction.response.send_message("No data")

    rsi = RSIIndicator(data["Close"]).rsi().iloc[-1]

    if rsi < 30:
        msg = "🟢 BUY ZONE"
    elif rsi > 70:
        msg = "🔴 SELL ZONE"
    else:
        msg = "🟡 NEUTRAL"

    await interaction.response.send_message(f"{symbol.upper()} → {msg} (RSI {rsi:.2f})")

# -----------------------------
# /forex
# -----------------------------
@bot.tree.command(name="forex", description="Forex prices")
async def forex(interaction: discord.Interaction, pair: str):
    symbol = pair.upper() + "=X"
    data = yf.Ticker(symbol).history(period="1d")

    if data.empty:
        return await interaction.response.send_message("Invalid pair")

    price = data["Close"].iloc[-1]
    await interaction.response.send_message(f"💱 {pair.upper()} = {price:.5f}")

# -----------------------------
# /commodity
# -----------------------------
@bot.tree.command(name="commodity", description="Oil or Gold price")
async def commodity(interaction: discord.Interaction, name: str):
    mapping = {
        "oil": "CL=F",
        "gold": "GC=F"
    }

    symbol = mapping.get(name.lower())
    if not symbol:
        return await interaction.response.send_message("Use oil or gold")

    data = yf.Ticker(symbol).history(period="1d")
    price = data["Close"].iloc[-1]

    await interaction.response.send_message(f"📦 {name.upper()} = {price:.2f}")

# -----------------------------
# /options
# -----------------------------
@bot.tree.command(name="options", description="Basic options chain")
async def options(interaction: discord.Interaction, symbol: str):
    stock = yf.Ticker(symbol)

    try:
        exp = stock.options[0]
        chain = stock.option_chain(exp)

        calls = chain.calls.head(3)
        puts = chain.puts.head(3)

        msg = f"📉 **{symbol.upper()} Options ({exp})**\n\nCALLS:\n"

        for _, r in calls.iterrows():
            msg += f"{r['strike']} | {r['lastPrice']} | vol {r['volume']}\n"

        msg += "\nPUTS:\n"

        for _, r in puts.iterrows():
            msg += f"{r['strike']} | {r['lastPrice']} | vol {r['volume']}\n"

        await interaction.response.send_message(msg)

    except:
        await interaction.response.send_message("Options unavailable")

# -----------------------------
bot.run(TOKEN)
