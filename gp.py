class SimRacingBot:
    def __init__(self, command_prefix):
        self.command_prefix = command_prefix
        self.commands = {"ping": self.ping, "welcome": self.welcome}

    def on_ready(self):
        print(f"Bot is ready. Logged in as SimRacingBot")

    def ping(self, ctx):
        return "Pong!"

    def welcome(self, ctx):
        return "Welcome to the Sim Racing Server! Enjoy the race!"

    def process_command(self, command, ctx):
        if command in self.commands:
            response = self.commands[command](ctx)
            print(f"Response: {response}")
        else:
            print("Unknown command")


# Create an instance of the bot
bot = SimRacingBot(command_prefix="!")

# Simulate the bot being ready
bot.on_ready()

# Simulate processing commands
bot.process_command("ping", "User")
bot.process_command("welcome", "User")
