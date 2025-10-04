import os
import shutil
from datetime import datetime
import time
import pathlib

# Path to desktop
desktop = os.path.join(pathlib.Path.Home(), "Desktop")
screenshots_folder = os.path.join(desktop, "Screenshots")

# Make sure Screenshots folder exists
os.makedirs(screenshots_folder, exist_ok=True)

def move_screenshots():
    for filename in os.listdir(desktop):
        if filename.startswith("Screenshot"):
            source = os.path.join(desktop, filename)

            # Create subfolders based on Month Year
            now = datetime.now()
            subfolder_name = now.strftime("%B, %Y")
            subfolder = os.path.join(screenshots_folder, subfolder_name)
            os.makedirs(subfolder, exist_ok=True)

            # Move file
            destination = os.path.join(subfolder, filename)
            shutil.move(source, destination)
            print(f"Moved {filename} → {subfolder}")

def main():
    always_run = True
    while always_run:
        move_screenshots()
        time.sleep(5)

if __name__ == "__main__":
    main()
