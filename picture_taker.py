import os
import time
from datetime import datetime
from picamera import PiCamera
from telegram import Bot
from PIL import Image
import requests

# Configuration
TELEGRAM_BOT_TOKEN = "<your-telegram-bot-token>"
TELEGRAM_CHAT_ID = "<your-chat-id>"
HOME_ASSISTANT_URL = "http://<home-assistant-url>:8123/api/services/light"
HOME_ASSISTANT_TOKEN = "<your-home-assistant-long-lived-access-token>"
LIGHT_ENTITY_ID = "light.your_light_entity_id"
PICTURE_INTERVAL = 600  # 10 minutes in seconds
BASE_DIRECTORY = "/home/pi/timelapse"

# Initialize camera
camera = PiCamera()
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Function to ensure directory exists
def ensure_directory(directory):
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

# Function to send GIF via Telegram
def send_gif_via_telegram(gif_path):
    with open(gif_path, "rb") as gif_file:
        bot.send_document(chat_id=TELEGRAM_CHAT_ID, document=gif_file)

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
        camera.capture(picture_path)
        print(f"Captured {picture_path}")

        # Turn off the light
        turn_off_light()

        # Check if it's midnight to create and send the GIF
        if current_time.hour == 0 and current_time.minute < 10:
            gif_path = os.path.join(BASE_DIRECTORY, current_time.strftime("%Y-%m-%d") + ".gif")
            create_gif(date_folder, gif_path)
            print(f"GIF created: {gif_path}")

            send_gif_via_telegram(gif_path)
            print("GIF sent via Telegram.")

        time.sleep(PICTURE_INTERVAL)

except KeyboardInterrupt:
    print("Script terminated by user.")
finally:
    camera.close()
    print("Camera closed.")
