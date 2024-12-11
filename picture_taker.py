import os
import time
from datetime import datetime
from picamera2 import Picamera2
from telegram import Bot
from PIL import Image
import requests

# Configuration
TELEGRAM_BOT_TOKEN = "<your-telegram-bot-token>"
SUBSCRIBERS_FILE = "subscribers.txt"
HOME_ASSISTANT_URL = "http://<home-assistant-url>:8123/api/services/light"
HOME_ASSISTANT_TOKEN = "<your-home-assistant-long-lived-access-token>"
LIGHT_ENTITY_ID = "light.your_light_entity_id"
PICTURE_INTERVAL = 600  # 10 minutes in seconds
BASE_DIRECTORY = "/home/pi/timelapse"

# Initialize camera
camera = Picamera2()
camera.configure(camera.create_still_configuration())
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Function to ensure directory exists
def ensure_directory(directory):
    print("DEBUG: " + str(directory))
    if not os.path.exists(directory):
        os.makedirs(directory)

# Function to create a GIF
def create_gif(image_folder, gif_path):
    images = []
    for file_name in sorted(os.listdir(image_folder)):
        if file_name.endswith(".jpg"):
            image_path = os.path.join(image_folder, file_name)
            images.append(Image.open(image_path))
    if images:
        images[0].save(gif_path, save_all=True, append_images=images[1:], duration=200, loop=0)

# Function to send GIF via Telegram to all subscribers
def send_gif_to_subscribers(gif_path):
    with open(gif_path, "rb") as gif_file:
        with open(SUBSCRIBERS_FILE, "r") as file:
            subscribers = file.readlines()
        for subscriber in subscribers:
            subscriber = subscriber.strip()
            if subscriber:
                try:
                    bot.send_document(chat_id=subscriber, document=gif_file)
                    print(f"GIF sent to {subscriber}.")
                except Exception as e:
                    print(f"Failed to send GIF to {subscriber}: {e}")

# Function to add a subscriber
def add_subscriber(chat_id):
    if not os.path.exists(SUBSCRIBERS_FILE):
        open(SUBSCRIBERS_FILE, "w").close()
    with open(SUBSCRIBERS_FILE, "r") as file:
        subscribers = file.readlines()
    if str(chat_id) + "\n" not in subscribers:
        with open(SUBSCRIBERS_FILE, "a") as file:
            file.write(str(chat_id) + "\n")
        print(f"Added subscriber: {chat_id}")
    else:
        print(f"Subscriber {chat_id} already exists.")

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

try:
    while True:
        current_time = datetime.now()
        date_folder = os.path.join(BASE_DIRECTORY, current_time.strftime("%Y-%m-%d"))
        ensure_directory(date_folder)

        # Turn on the light
        turn_on_light()

        # Take a picture
        picture_name = current_time.strftime("%H-%M-%S") + ".jpg"
        picture_path = os.path.join(date_folder, picture_name)
        camera.start()
        camera.capture_file(picture_path)
        camera.stop()
        print(f"Captured {picture_path}")

        # Turn off the light
        turn_off_light()

        # Check if it's midnight to create and send the GIF
        if current_time.hour == 0 and current_time.minute < 10:
            gif_path = os.path.join(BASE_DIRECTORY, current_time.strftime("%Y-%m-%d") + ".gif")
            create_gif(date_folder, gif_path)
            print(f"GIF created: {gif_path}")

            send_gif_to_subscribers(gif_path)
            print("GIF sent to all subscribers.")

        time.sleep(PICTURE_INTERVAL)

except KeyboardInterrupt:
    print("Script terminated by user.")
finally:
    print("Camera cleanup complete.")
