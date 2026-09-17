import discord
from discord.ext import commands

# Define the token for the bot (replace this with an actual token in a production environment)
bot_token = "YOUR_BOT_TOKEN_HERE"

# Create an instance of the bot
bot = commands.Bot(command_prefix="!")


# Define the on_ready event to print a message when the bot is ready
@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")


# Define a simple command for testing
@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("Hello, this is the sim racing bot!")


# Run the bot
bot.run(bot_token)
