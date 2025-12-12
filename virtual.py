import cv2
import mediapipe as mp
import time

# MediaPipe Initialization
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)

# Webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# States
keyboard_active = False
virtual_keys = {}
current_key = None
key_hold_start = None
esc_hold_start = None
esc_deactivate_start = None
base_point = None
buffer = []

# Constants
KEY_WIDTH = 60
KEY_HEIGHT = 60
KEY_SPACING_X = 75
KEY_SPACING_Y = 75
ESC_HOLD_TIME = 5
ESC_DEACTIVATE_TIME = 3
KEY_HOLD_TIME = 2

# Generate virtual keyboard
def generate_virtual_keyboard(base_x, base_y):
    global virtual_keys
    virtual_keys = {}

    rows = [
        ['ESC', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Backspace'],
        [      'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'             ],
        [      'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Enter'        ],
        [      'Z', 'X', 'C', 'V', 'B', 'N', 'M'                           ],
        ['    123   ', '           Space           '                      ]
    ]

    for row_index, row in enumerate(rows):
        row_y = base_y + row_index * KEY_SPACING_Y
        x_offset = 0

        if row_index == 1: x_offset = KEY_SPACING_X // 2
        if row_index == 2: x_offset = KEY_SPACING_X
        if row_index == 3: x_offset = int(1.5 * KEY_SPACING_X)
        if row_index == 4: x_offset = KEY_SPACING_X

        key_x = base_x + x_offset

        for key in row:
            key_clean = key.strip()
            key_width = KEY_WIDTH

            if 'Space' in key:
                key_width = KEY_WIDTH * 6
            elif '123' in key:
                key_width = KEY_WIDTH * 2
            elif 'Backspace' in key or 'Enter' in key:
                key_width = KEY_WIDTH * 2

            virtual_keys[key_clean] = (key_x + key_width // 2, row_y)
            key_x += key_width + (KEY_SPACING_X - KEY_WIDTH)

# Detect key under finger
def detect_key_under_finger(fx, fy):
    for key, (kx, ky) in virtual_keys.items():
        if key == 'Space':
            w = KEY_WIDTH * 6
        elif key == '123':
            w = KEY_WIDTH * 2
        elif key in ['Backspace', 'Enter']:
            w = KEY_WIDTH * 2
        else:
            w = KEY_WIDTH

        if abs(fx - kx) < w // 2 and abs(fy - ky) < KEY_HEIGHT // 2:
            return key
    return None

# Main Loop
while True:
    success, img = cap.read()
    img = cv2.flip(img, 1)
    h, w, _ = img.shape
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    if results.multi_hand_landmarks and results.multi_handedness:
        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            hand_label = results.multi_handedness[idx].classification[0].label
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            lm = hand_landmarks.landmark[8]
            cx, cy = int(lm.x * w), int(lm.y * h)

            if not keyboard_active and hand_label == "Left":
                if base_point and abs(cx - base_point[0]) < 15 and abs(cy - base_point[1]) < 15:
                    if esc_hold_start and time.time() - esc_hold_start >= ESC_HOLD_TIME:
                        keyboard_active = True
                        generate_virtual_keyboard(cx, cy)
                        print("[INFO] Virtual keyboard activated.")
                        esc_hold_start = None
                    elif esc_hold_start is None:
                        esc_hold_start = time.time()
                else:
                    esc_hold_start = None
                    base_point = (cx, cy)

                cv2.circle(img, (cx, cy), 25, (0, 255, 0), 2)
                cv2.putText(img, "Hold 5s to activate keyboard", (cx - 80, cy - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            elif keyboard_active:
                key = detect_key_under_finger(cx, cy)
                if key:
                    x, y = virtual_keys[key]

                    if key == 'Space':
                        width = KEY_WIDTH * 6
                    elif key == '123':
                        width = KEY_WIDTH * 2
                    elif key in ['Backspace', 'Enter']:
                        width = KEY_WIDTH * 2
                    else:
                        width = KEY_WIDTH

                    cv2.rectangle(img, (x - width // 2, y - 30), (x + width // 2, y + 30), (0, 255, 255), 2)

                    if key == 'ESC':
                        if esc_deactivate_start is None:
                            esc_deactivate_start = time.time()
                        elif time.time() - esc_deactivate_start >= ESC_DEACTIVATE_TIME:
                            keyboard_active = False
                            virtual_keys = {}
                            esc_deactivate_start = None
                            print("[INFO] Virtual keyboard deactivated.")
                            continue
                    else:
                        esc_deactivate_start = None

                    if current_key != key:
                        current_key = key
                        key_hold_start = time.time()
                    elif time.time() - key_hold_start >= KEY_HOLD_TIME:
                        print(f"[KEY PRESSED]: {key}")
                        if key == 'Enter':
                            print("Final sentence:", ''.join(buffer))
                            buffer = []
                        elif key == 'Space':
                            buffer.append(' ')
                        elif key == 'Backspace':
                            if buffer: buffer.pop()
                        else:
                            buffer.append(key)
                        current_key = None
                        key_hold_start = None
                else:
                    current_key = None
                    key_hold_start = None
                    esc_deactivate_start = None

    # Draw keyboard
    if keyboard_active:
        overlay = img.copy()
        for key, (x, y) in virtual_keys.items():
            if key == 'Space':
                width = KEY_WIDTH * 6
            elif key == '123':
                width = KEY_WIDTH * 2
            elif key in ['Backspace', 'Enter']:
                width = KEY_WIDTH * 2
            else:
                width = KEY_WIDTH

            color = (0, 255, 0) if key != current_key else (0, 255, 255)

            cv2.rectangle(overlay, (x - width // 2, y - 30), (x + width // 2, y + 30), (0, 200, 0), -1)
            cv2.rectangle(overlay, (x - width // 2, y - 30), (x + width // 2, y + 30), color, 2)

            size = cv2.getTextSize(key, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            tx, ty = x - size[0] // 2, y + size[1] // 2
            cv2.putText(overlay, key, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        alpha = 0.4
        img = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

    # Display typed text
    cv2.rectangle(img, (20, 20), (w - 20, 70), (0, 0, 0), -1)
    cv2.putText(img, 'Typed: ' + ''.join(buffer), (30, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

    cv2.imshow("Virtual Air Keyboard", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
