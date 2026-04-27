import os
import discord
from discord.ext import commands
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from ta.momentum import RSIIndicator

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# 📊 STOCK PRICE COMMAND
# -----------------------------
@bot.command()
async def price(ctx, ticker: str):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1d")

    if data.empty:
        await ctx.send("Invalid ticker.")
        return

    price = data["Close"].iloc[-1]
    await ctx.send(f"📊 {ticker.upper()} price: **${price:.2f}**")

# -----------------------------
# 📈 RSI INDICATOR
# -----------------------------
@bot.command()
async def rsi(ctx, ticker: str):
    stock = yf.Ticker(ticker)
    data = stock.history(period="3mo", interval="1d")

    if data.empty:
        await ctx.send("Invalid ticker.")
        return

    rsi = RSIIndicator(close=data["Close"]).rsi()
    latest = rsi.iloc[-1]

    await ctx.send(f"📈 {ticker.upper()} RSI: **{latest:.2f}**")

# -----------------------------
# 📉 SIMPLE CHART
# -----------------------------
@bot.command()
async def chart(ctx, ticker: str):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1mo", interval="1h")

    if data.empty:
        await ctx.send("Invalid ticker.")
        return

    plt.figure()
    plt.plot(data.index, data["Close"])
    plt.title(f"{ticker.upper()} Chart")
    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = f"{ticker}_chart.png"
    plt.savefig(filename)
    plt.close()

    await ctx.send(file=discord.File(filename))

# -----------------------------
# 🧠 SIMPLE SIGNAL (BASIC LOGIC)
# -----------------------------
@bot.command()
async def signal(ctx, ticker: str):
    stock = yf.Ticker(ticker)
    data = stock.history(period="3mo")

    if data.empty:
        await ctx.send("Invalid ticker.")
        return

    rsi = RSIIndicator(close=data["Close"]).rsi().iloc[-1]

    if rsi < 30:
        signal = "🟢 OVERSOLD (possible buy zone)"
    elif rsi > 70:
        signal = "🔴 OVERBOUGHT (possible sell zone)"
    else:
        signal = "🟡 NEUTRAL"

    await ctx.send(f"{ticker.upper()} signal: {signal} (RSI {rsi:.2f})")

# -----------------------------
# 🤖 READY
# -----------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)
