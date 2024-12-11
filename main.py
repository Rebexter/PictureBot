#!/usr/bin/env python
# pylint: disable=unused-argument
import logging
from logging.handlers import RotatingFileHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import JobQueue
from datetime import datetime
import os, json

# File to save the subscribed users list
SUBSCRIBERS_FILE = "subscribed_users.json"


def setup_logging(log_file='app.log', max_file_size=1 * 1024 * 1024, backup_count=5, log_level=logging.WARNING):
    # Create a RotatingFileHandler
    handler = RotatingFileHandler(
        filename=log_file,         # Base log file name
        mode='a',                  # Append mode
        maxBytes=max_file_size,    # Max size of each log file in bytes
        backupCount=backup_count   # Number of backup files to keep
    )
    # Configure the logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set the formatter for the handler
    handler.setFormatter(formatter)
    # Get the root logger
    logger = logging.getLogger()
    # Set the logging level
    logger.setLevel(log_level)
    # Add the handler to the root logger
    logger.addHandler(handler)


# Example usage
setup_logging()

logger = logging.getLogger()


class BotController:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.subscribed_users = set()
        #self.token = token
        self.message_manager = MessageManager()
        self.old_message, self.new_message = None, None
        current_time = datetime.now()
        self.current_folder = os.path.join(self.picture_path, current_time.strftime("%Y-%m-%d"))

    def load_subscribed_users(self):
        """Load the subscribed users from disk if the file exists."""
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r') as f:
                self.subscribed_users = set(json.load(f))
            print(f"Loaded {len(self.subscribed_users)} subscribed users.")
        else:
            print("No subscribed users file found, starting fresh.")

    def save_subscribed_users(self):
        """Save the subscribed users to disk only if there are changes."""
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r') as f:
                saved_users = set(json.load(f))
        else:
            saved_users = set()

        if saved_users != self.subscribed_users:
            with open(SUBSCRIBERS_FILE, 'w') as f:
                json.dump(list(self.subscribed_users), f)
            print(f"Saved {len(self.subscribed_users)} subscribed users.")
        else:
            print("No changes detected, skipping save.")

    # Function to ensure directory exists
    def ensure_directory(self):
        if not os.path.exists(self.current_folder):
            os.makedirs(self.current_folder)

    # Function to create a GIF
    def create_gif(image_folder, gif_path):
        images = []
        for file_name in sorted(os.listdir(image_folder)):
            if file_name.endswith(".jpg"):
                image_path = os.path.join(image_folder, file_name)
                images.append(Image.open(image_path))
        if images:
            images[0].save(gif_path, save_all=True, append_images=images[1:], duration=200, loop=0)

    # Function to turn on the light via Home Assistant
    def turn_on_light():
        headers = {
            "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
            "Content-Type": "application/json",
        }
        data = {
            "entity_id": LIGHT_ENTITY_ID
        }
        response = requests.post(f"{HOME_ASSISTANT_URL}/turn_on", headers=headers, json=data)
        if response.status_code == 200:
            print("Light turned on successfully.")
        else:
            print(f"Failed to turn on light: {response.status_code}, {response.text}")

    # Function to turn off the light via Home Assistant
    def turn_off_light():
        headers = {
            "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}",
            "Content-Type": "application/json",
        }
        data = {
            "entity_id": LIGHT_ENTITY_ID
        }
        response = requests.post(f"{HOME_ASSISTANT_URL}/turn_off", headers=headers, json=data)
        if response.status_code == 200:
            print("Light turned off successfully.")
        else:
            print(f"Failed to turn off light: {response.status_code}, {response.text}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        if chat_id not in self.subscribed_users:
            self.subscribed_users.add(chat_id)
            self.save_subscribed_users()
            await update.message.reply_text('You are now subscribed to periodic updates!\n'
                                            'You can view all available commands by typing /help.\n'
                                            'You can stop the updates at any time by typing /stopBot.')
            await update.message.reply_text(self.old_message)
            logging.warning("A new user has subscribed. Total subscribed users: %s",
                            len(self.subscribed_users))
        else:
            await update.message.reply_text('You are already subscribed!')

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        if chat_id in self.subscribed_users:
            self.subscribed_users.remove(chat_id)
            self.save_subscribed_users()
            await update.message.reply_text('You have been unsubscribed from periodic updates.')
            logging.warning("A user has unsubscribed. Total subscribed users: %s",
                            len(self.subscribed_users))
        else:
            await update.message.reply_text('You are not subscribed.')

    async def send_current_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(self.old_message)

    async def send_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Available commands:\n'
                                        '/start - subscribe to periodic updates\n'
                                        '/stopBot - unsubscribe from periodic updates\n'
                                        '/currentStatus - view the current status message\n'
                                        '/help - view this help message')

    async def background_task(self, context):
        print("Background task is called")
        current_time = datetime.now()
        self.current_folder = os.path.join(self.picture_path, current_time.strftime("%Y-%m-%d"))
        print(self.current_folder)
        # old shit
        message_content = context.job.data

        try:
            results =  "result" # fetch_starship_data()
        except Exception as e:
            print(f'Exception: {e}')
            logging.error("Failed to fetch data. Exception: %s", e)
        else:
            message_content[1] = self.message_manager.assemble_message(results)
            if message_content[0] != message_content[1]:
                print("New data available")
                message_content[0] = message_content[1]
                for chat_id in self.subscribed_users:
                    await context.bot.send_message(chat_id=chat_id, text=message_content[1])
                save_message_to_disk(message_content[0])
                logging.warning(f"New data available: {message_content[0]}")
            else:
                print("No new data available")
                logging.warning("No new data available")

    async def save_users_periodically(self, context):
        self.save_subscribed_users()

    def run(self):
        self.load_subscribed_users()
        self.old_message, self.new_message = load_message_from_disk()

        application = Application.builder().token(self.token).build()

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("stopBot", self.stop))
        application.add_handler(CommandHandler("currentStatus", self.send_current_message))
        application.add_handler(CommandHandler("help", self.send_help))

        job_queue = application.job_queue
        job_queue.run_repeating(self.background_task, interval=3600, first=300, data=[self.old_message, self.new_message])
        # job_queue.run_repeating(self.save_users_periodically, interval=30, first=20)

        application.run_polling()


class MessageManager:
    def assemble_message(self, results):
        # mission_name, current_net, current_status_name = (
        #     results['upcoming']['launches'][0]['mission']['name'],
        #     results['upcoming']['launches'][0]['net'],
        #     results['upcoming']['launches'][0]['status']['name'],
        # )
        #current_net_berlin_time, current_utc_time = get_berlin_time_from_utc(current_net)
        message = "test message"
        return message

def save_message_to_disk(message):
    with open('message.txt', 'w') as f:
        f.write(message)

def load_message_from_disk():
    old_message, new_message = None, None
    if os.path.exists('message.txt'):
        with open('message.txt', 'r') as f:
            old_message = f.read()
            new_message = old_message
    return old_message, new_message




def load_config():
    with open('config.json', 'r') as f:
        config = json.load(f)
    return config


def main():
    config = load_config()
    bot_token = config.get('token')
    bot_controller = BotController(config)
    bot_controller.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
