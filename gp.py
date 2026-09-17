# import discord
# from discord.ext import commands
from smolagents import CodeAgent, DuckDuckGoSearchTool, InferenceClientModel

# Define the token for the bot (replace this with an actual token in a production environment)
bot_token = "YOUR_BOT_TOKEN_HERE"

# Create an instance of the bot
# bot = commands.Bot(command_prefix="!")

# Initialize a model (using Hugging Face Inference API)
model = InferenceClientModel("Qwen/Qwen2.5-72B-Instruct")

agent = CodeAgent(tools=[], model=model)

# # Define the on_ready event to print a message when the bot is ready
# @bot.event
# async def on_ready():
#     print(f"Bot is ready. Logged in as {bot.user}")


# # Define a simple command for testing
# @bot.command(name="hello")
# async def hello(ctx):
#     await ctx.send("Hello, this is the sim racing bot!")


# # Run the bot
# bot.run(bot_token)
#


sample_spec = """Friday Night Lights SEP/4th
Spec 01:
Toyota Mark II Tourer (1997)
Toyota Mark V Chaser (1997)
Leave all settings default, except for power, making 450HP. How you reach that power figure (and how you customize the body) is up to you. Sports Medium Tires!

Spec 02:
Ford F-150 SVT Raptor (2011)
swapped! Windsor-351-Maverick (250,000 Cr.)
Toyota Tundra TRD Pro (2019)
swapped! Demon-Challenger (200,000 Cr.)
There are specific tunes for these trucks, what I am calling Production Supertrucks. You have your choice of "the full experience" (🌶️🌶️🌶️) or a more controllable option (🌶️🌶️)— which I recommend for those who aren't very confident on controller. You will need to engine swap these vehicles to make the power required; they are on Sports Soft tires. Trust in the tunes, I spent time on this!
Image guide forthcoming"
"""

query = input()
# Run the agent with a task
result = agent.run(
    "Answer ONLY using the spec below. If the answer is not explicitly stated in the spec, say so — do not guess or infer. "
    "Spec:\n" + sample_spec + "\n\nQuestion: " + query
)
print(result)
