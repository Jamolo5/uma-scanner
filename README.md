# UMA Musume Scanner Overlay Tool

A lightweight **screen overlay application** designed to assist players of the game **UMA Musume** by scanning the game screen, recognizing text choices using OCR, and displaying detailed contextual information dynamically.

---

## Features

- **Screen Region Scanning:**  
  Capture a specific user-configurable region of the screen to detect in-game choice text.

- **OCR Text Recognition:**  
  Uses Tesseract OCR to accurately extract text from screen captures in real time.

- **Fuzzy Matching:**  
  Matches detected text against a nested database of known game choices using fuzzy string matching for robust recognition even with OCR inaccuracies.

- **Dynamic Overlay:**  
  Displays matched choice information as a transparent, always-on-top overlay window with options listed and categorized.

- **Configurable Region:**  
  Capture region is user-configurable via an external JSON file (`config.json`), enabling flexible setup based on screen resolution or window layout.

- **User-Friendly Interface:**  
  Includes a draggable overlay window with a fixed-position Close button for convenient control without obstructing gameplay.

---

## Installation & Requirements

- **Python 3.8+**  
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed and added to system PATH  
- Python packages:  
  ```bash
  pip install pytesseract pillow pyautogui fuzzywuzzy python-Levenshtein

## Setup

1. Configure the capture region:
    The application scans one region of the screen where UMA Musume's event details appear. This region is specified in config.json as follows:
    ```
    {
    "regions": [
        {
        "name": "Event details",
        "box": [X, Y, WIDTH, HEIGHT]
        }
    ]
    }
    ```

    Replace X, Y, WIDTH, and HEIGHT with the pixel coordinates and size of the capture box on your screen.

2. How to determine the correct region coordinates:

    Launch UMA Musume and open the event screen with choices visible.

    Use a screen ruler tool or Windows’ built-in Snipping Tool / Snip & Sketch to estimate the exact position and size of the event details box on your screen.

    Alternatively, use a Python snippet to capture mouse position:

    import pyautogui
    print(pyautogui.position())

    Run this script, then hover your mouse over the top-left corner of the event details area and note the coordinates (X, Y).
    Repeat for the bottom-right corner, then calculate width and height as (bottom_right_x - X) and (bottom_right_y - Y).

3. Update the `box` field in config.json with your measurements. For example:
    ```
    {
    "regions": [
        {
        "name": "Event details",
        "box": [100, 200, 400, 150]
        }
    ]
    }
    ```

4. Run the scanner:
    ```
    python screencap_ocr.py
    ```