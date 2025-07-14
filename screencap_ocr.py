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
    ret, img = cv2.threshold(np.array(img), 125, 255, cv2.THRESH_BINARY)
    # enhancer = ImageEnhance.Contrast(img)
    # img = enhancer.enhance(2.0)
    return img


# === Fuzzy Matching ===


def get_best_matches_with_path(detected_text):
    """
    Finds the best fuzzy matches for the detected text and returns detailed match information.
    Filters matches manually based on a score cutoff.
    """
    normalized = detected_text.upper().strip().replace(" ", "-")
    results = process.extract(normalized, lookup_map.keys())  # Removed score_cutoff

    # Manually filter results based on score cutoff
    score_cutoff = 70
    filtered_results = [result for result in results if result[1] >= score_cutoff]

    matches = []
    for result in filtered_results:
        match, score = result
        values = lookup_map[match]
        category, subcat = code_to_path[match]
        matches.append({
            "code": match,
            "category": category,
            "subcategory": subcat,
            "options": values,
            "score": score,
        })

    return matches if matches else None


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
    """
    Continuously scans the defined regions, performs OCR, and updates the UI with results.
    Dynamically resizes the window to fit the text content, up to a maximum height.
    """
    last_results = {}  # Stores the last detected text for each region
    last_selected_matches = {}  # Stores the last selected match for each region
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
            detected = text or "[No text detected]"

            # Initialize selected_match
            selected_match = None

            # Check if the detected text has changed
            if last_results.get(name) != detected:
                last_results[name] = detected  # Update the last detected text
                matches = get_best_matches_with_path(detected)

                if matches:
                    if len(matches) == 1:
                        # Automatically select the single match
                        selected_match = matches[0]
                    else:
                        # Check if all matches are identical
                        first_match = matches[0]
                        if all(match["code"] == first_match["code"] and match["score"] == first_match["score"] for match in matches):
                            # Prompt the user to select a match if all matches are identical
                            selected_match = select_match(matches)
                        else:
                            # Automatically select the best match
                            selected_match = matches[0]  # Select the match with the highest score
                    last_selected_matches[name] = selected_match if selected_match else None
                else:
                    last_selected_matches[name] = None
            else:
                # Use the last selected match if the text hasn't changed
                selected_match = last_selected_matches.get(name)

            result = selected_match if selected_match else None
            output = f"{name}: {detected}\n{format_result(result)}"
            outputs.append(output)

        # Update the label with the OCR results
        label.config(text="\n\n".join(outputs))
        label.update_idletasks()  # Force the label to update its layout

        # Dynamically resize the window based on the label's content height
        content_height = label.winfo_height()  # Fetch updated height after layout update
        window_width = root.winfo_width()

        max_height = 1000  # Maximum height limit
        min_height = 400   # Minimum height limit
        new_height = max(min(content_height + 60, max_height), min_height)

        root.geometry(f"{window_width}x{new_height}")
        time.sleep(1)


# === Overlay Window Setup ===
root = tk.Tk()
root.geometry("1200x300+50+50")
root.configure(bg="black")
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
    activeforeground="yellow",
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
    activeforeground="red",
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
    wraplength=1150,
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

# === Match Selection Dialog ===


def select_match(matches):
    """
    Displays a dialog for the user to select a match from multiple fuzzy matches.
    """
    if not matches:
        return None

    def on_select(selected_index):
        nonlocal selected_match
        selected_match = matches[selected_index]
        dialog.destroy()

    # Increase the width of the dialog window
    dialog = tk.Toplevel(root)
    dialog.title("Select Match")
    dialog.geometry("1000x300")  # Adjusted width to 1000
    dialog.configure(bg="black")

    selected_match = None

    for i, match in enumerate(matches):
        text = f"[{match['category']} > {match['subcategory']} > {match['code']}] (Score: {match['score']})"
        button = tk.Button(
            dialog,
            text=text,
            command=lambda idx=i: on_select(idx),
            bg="black",
            fg="white",
            font=("Consolas", 10),
            bd=0,
            highlightthickness=0,
            activebackground="black",
            activeforeground="yellow",
            wraplength=950,  # Adjusted wraplength to fit wider text
        )
        button.pack(fill="x", padx=10, pady=5)

    dialog.transient(root)
    dialog.grab_set()
    root.wait_window(dialog)

    return selected_match


# === Start scanning in a thread ===

time.sleep(1)

threading.Thread(
    target=scan_loop,
    args=(
        label,
        regions,
    ),
    daemon=True,
).start()

root.mainloop()
