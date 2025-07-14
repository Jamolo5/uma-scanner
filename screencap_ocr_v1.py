import json
import time
import cv2
import threading
import pyautogui
import pytesseract
import tkinter as tk
from fuzzywuzzy import process
import numpy as np
from PIL import Image, ImageOps, ImageEnhance

pytesseract.pytesseract.tesseract_cmd = (
    "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)

# === Load config ===

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

regions = config.get("regions", [])

# === Load 3-Level JSON ===

with open("results.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

lookup_map = {}
code_to_path = {}


def flatten_lookup(data):
    for category, subcats in data.items():
        for subcat, codes in subcats.items():
            for code, values in codes.items():
                code_upper = code.upper()
                lookup_map[code_upper] = values
                code_to_path[code_upper] = (category, subcat)


flatten_lookup(raw_data)

# === OCR Preprocessing ===


def preprocess_image(img):
    img = img.convert("L")  # grayscale
    img = ImageOps.autocontrast(img)
    ret,img = cv2.threshold(np.array(img), 125, 255, cv2.THRESH_BINARY)
    # enhancer = ImageEnhance.Contrast(img)
    # img = enhancer.enhance(2.0)
    return img


# === Fuzzy Matching ===


def get_best_match_with_path(detected_text):
    normalized = detected_text.upper().strip().replace(" ", "-")
    result = process.extractOne(normalized, lookup_map.keys(), score_cutoff=70)

    if result:
        match, score = result
        values = lookup_map[match]
        category, subcat = code_to_path[match]
        return {
            "code": match,
            "category": category,
            "subcategory": subcat,
            "options": values,
            "score": score,
        }
    else:
        return None


def format_result(result):
    if not result:
        return "No close match found"
    header = f"[{result['category']} > {result['subcategory']} > {result['code']}]\n\n"
    options = "\n".join(
        [f"Option {i + 1}: {val}" for i, val in enumerate(result["options"])]
    )
    return f"{header}\n{options}"


# === Scanning Loop ===


def scan_loop(label, regions):
    last_results = {}
    time.sleep(1)

    while True:
        outputs = []
        for region in regions:
            box = region["box"]
            name = region["name"]
            screenshot = pyautogui.screenshot(region=box)
            processed = preprocess_image(screenshot)
            custom_config = r"-c tessedit_char_whitelist=!♪()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
            text = (
                pytesseract.image_to_string(screenshot, config=custom_config)
                .strip()
                .upper()
            )

            if text:
                last_results[name] = text

            detected = last_results.get(name, "[No text detected]")
            result = get_best_match_with_path(detected)
            output = f"{name}: {detected}\n{format_result(result)}"
            outputs.append(output)

        label.config(text="\n\n".join(outputs))
        label.update_idletasks()  # Ensure size info is current
        content_height = label.winfo_height()
        window_width = root.winfo_width()

        # Optional: Set a max height to avoid runaway sizing
        max_height = 3000
        min_height = 300
        new_height = max(min(content_height + 60, max_height), min_height)  # +60 for padding and button

        root.geometry(f"{window_width}x{new_height}")
        time.sleep(1)


# === Overlay Window Setup ===
root = tk.Tk()
root.geometry("1200x300+50+50")
root.configure(bg='black')
root.attributes("-topmost", True)
root.attributes("-alpha", 0.85)
root.overrideredirect(True)

# === Main layout frame ===
frame = tk.Frame(root, bg="black")
frame.grid(row=0, column=0, sticky="nsew")

# === add overlay to scanned region
def create_overlay_box(region):
    x, y, w, h = region["box"]
    box = tk.Toplevel()
    box.overrideredirect(True)
    box.geometry(f"{w}x{h}+{x}+{y}")
    box.lift()
    box.attributes("-topmost", True)
    box.attributes("-alpha", 0.3)  # semi-transparent
    box.configure(bg="red")

    # Optional: Red border frame
    frame = tk.Frame(box, bg="red")
    frame.pack(expand=True, fill="both")

    return box

# Draw capture region
# region_boxes = []
# for region in regions:
#     box = create_overlay_box(region)
#     region_boxes.append(box)

# Let the frame expand with window
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# === Minimise button ===
toggle_state = {"is_small": False}

def toggle_size():
    toggle_state["is_small"] = not toggle_state["is_small"]
    is_small = toggle_state["is_small"]

    window_width = root.winfo_width()

    if is_small:
        # Small size - fixed height, maybe just show header or minimal info
        root.geometry(f"200x100")
    else:
        # Normal size - recalc height based on label content
        label.update_idletasks()
        root.geometry("1200x300")

# Toggle size button
toggle_button = tk.Button(
    frame,
    text="-",
    command=toggle_size,
    bg="black",
    fg="white",
    font=("Consolas", 10),
    bd=0,
    highlightthickness=0,
    activebackground="black",
    activeforeground="yellow"
)
toggle_button.grid(row=0, column=0, sticky="ne", padx=5, pady=5)


# === Close button ===
def close_app():
    root.destroy()

close_button = tk.Button(
    frame,
    text="✕",
    command=close_app,
    bg="black",
    fg="white",
    font=("Consolas", 12),
    bd=0,
    highlightthickness=0,
    activebackground="black",
    activeforeground="red"
)
close_button.grid(row=0, column=1, sticky="ne", padx=5, pady=5)

# === OCR Output Label ===
label = tk.Label(
    frame,
    text="Loading OCR...",
    fg="white",
    bg="black",
    font=("Consolas", 12),
    justify="left",
    anchor="nw",
    wraplength=1150
)
label.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

# Allow the label to grow vertically
# OCR label
label.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))

# Adjust grid config accordingly:
frame.grid_columnconfigure(0, weight=0)  # toggle button col
frame.grid_columnconfigure(1, weight=1)  # spacer (if needed)
frame.grid_columnconfigure(2, weight=0)  # close button col
frame.grid_rowconfigure(1, weight=1)

def start_move(event):
    widget = event.widget
    if isinstance(widget, tk.Button):
        return  # Don't drag if the click was on the button
    root.x = event.x
    root.y = event.y


def do_move(event):
    x = event.x_root - root.x
    y = event.y_root - root.y
    root.geometry(f"+{x}+{y}")

root.bind("<ButtonPress-1>", start_move)
root.bind("<B1-Motion>", do_move)

# === Start scanning in a thread ===

time.sleep(1)

threading.Thread(target=scan_loop, args=(label,regions,), daemon=True).start()

root.mainloop()
