import cv2
import mediapipe.python.solutions.hands as mp_hands
import mediapipe.python.solutions.drawing_utils as mp_draw
import time
import asyncio
import platform

# MediaPipe Initialization
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.8, min_tracking_confidence=0.7)

# Webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam. Please check your camera connection or permissions.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# States
keyboard_active = True
virtual_keys = {}
current_key = None
key_hold_start = None
buffer = []
last_key_press = 0
DEBOUNCE_TIME = 0.2  # seconds

# Constants
KEY_WIDTH = 50
KEY_HEIGHT = 50
KEY_SPACING_X = 60
KEY_SPACING_Y = 60
KEY_HOLD_TIME = 0.5  # Reduced hold time for better responsiveness
BASE_X, BASE_Y = 200, 350

# Generate virtual keyboard layout with standard QWERTY arrangement
def generate_virtual_keyboard(base_x, base_y):
    global virtual_keys
    virtual_keys = {}

    rows = [
        ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace'],
        ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\'],
        ['Caps', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', '\'', 'Enter'],
        ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'Shift'],
        ['Ctrl', 'Alt', 'Space', 'Alt', 'Ctrl']
    ]

    for row_index, row in enumerate(rows):
        row_y = base_y + row_index * KEY_SPACING_Y
        x_offset = 0

        if row_index == 1: x_offset = KEY_SPACING_X // 2
        if row_index == 2: x_offset = KEY_SPACING_X
        if row_index == 3: x_offset = int(1.5 * KEY_SPACING_X)
        if row_index == 4: x_offset = int(2 * KEY_SPACING_X)

        key_x = base_x + x_offset

        for key in row:
            key_clean = key.strip()
            key_width = KEY_WIDTH

            if key in ['Backspace', 'Enter']: key_width = KEY_WIDTH * 2
            elif key == 'Tab': key_width = KEY_WIDTH * 1.5
            elif key == 'Caps': key_width = KEY_WIDTH * 1.5
            elif key == 'Shift': key_width = KEY_WIDTH * 2.5
            elif key == 'Space': key_width = KEY_WIDTH * 6
            elif key in ['Ctrl', 'Alt']: key_width = KEY_WIDTH * 1.2

            virtual_keys[key_clean] = (key_x + key_width // 2, row_y, key_width)
            key_x += key_width + (KEY_SPACING_X - KEY_WIDTH)

# Detect key under finger with improved precision
def detect_key_under_finger(fx, fy):
    for key, (kx, ky, kw) in virtual_keys.items():
        if abs(fx - kx) < kw // 2 and abs(fy - ky) < KEY_HEIGHT // 2:
            return key
    return None

# Initialize keyboard layout
generate_virtual_keyboard(BASE_X, BASE_Y)

# Main Loop
async def main():
    current_key = None  # Initialize current_key locally
    last_key_press = 0  # Initialize last_key_press locally
    while True:
        success, img = cap.read()
        if not success:
            print("Error: Failed to capture video frame. Check webcam connection.")
            break
        img = cv2.flip(img, 1)
        h, w, _ = img.shape
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        cx, cy = None, None

        if results.multi_hand_landmarks and results.multi_handedness:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                hand_label = results.multi_handedness[idx].classification[0].label
                mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                lm = hand_landmarks.landmark[8]  # Index finger tip
                cx, cy = int(lm.x * w), int(lm.y * h)

                if hand_label == "Right":
                    cv2.circle(img, (cx, cy), 10, (0, 0, 255), -1)

                if keyboard_active:
                    key