import cv2
import numpy as np
import serial
import time

# =========================================================
# 1. ARDUINO SERIAL CONNECTION
# =========================================================

ARDUINO_PORT = "COM3"   # Change if required
BAUD_RATE = 9600

try:
    arduino = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)  # Wait for Arduino reset
    print("Arduino connected on", ARDUINO_PORT)

except serial.SerialException as e:
    arduino = None
    print("Arduino connection failed:", e)
    print("PWM will only be displayed on screen.")

# =========================================================
# 2. CAMERA SETUP
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Webcam not detected.")

    if arduino is not None:
        arduino.write(b"0,0\n")
        arduino.close()

    exit()

# =========================================================
# 3. GREEN HSV RANGE
# =========================================================

lower_green = np.array([35, 60, 60])
upper_green = np.array([85, 255, 255])

MIN_AREA = 800

# =========================================================
# 4. PWM SETTINGS
# =========================================================

BASE_PWM = 180
MAX_PWM = 255
MIN_PWM = 0

KP = 0.4
CENTER_TOLERANCE = 25

# =========================================================
# 5. SERIAL SEND FUNCTION
# =========================================================

def send_pwm(left, right):

    left = int(np.clip(left, 0, 255))
    right = int(np.clip(right, 0, 255))

    if arduino is not None and arduino.is_open:

        command = f"{left},{right}\n"

        arduino.write(command.encode())

# =========================================================
# 6. MAIN LOOP
# =========================================================

try:

    while True:

        ret, frame = cap.read()

        if not ret:
            print("Camera frame error.")
            break

        # Mirror camera
        frame = cv2.flip(frame, 1)

        height, width = frame.shape[:2]

        center_x = width // 2
        center_y = height // 2

        # =================================================
        # HSV CONVERSION
        # =================================================

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, lower_green, upper_green)

        # =================================================
        # NOISE REMOVAL
        # =================================================

        kernel = np.ones((5, 5), np.uint8)

        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, kernel
        )

        mask = cv2.morphologyEx(
            mask, cv2.MORPH_CLOSE, kernel
        )

        # =================================================
        # CONTOUR DETECTION
        # =================================================

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # =================================================
        # FRAME CENTER LINE
        # =================================================

        cv2.line(
            frame,
            (center_x, 0),
            (center_x, height),
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            "FRAME CENTER",
            (center_x + 10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        # =================================================
        # DEFAULT VALUES
        # =================================================

        detected = False

        cx = 0
        cy = 0

        left_distance = 0
        right_distance = 0
        offset = 0

        direction = "STOP"

        left_pwm = 0
        right_pwm = 0

        # =================================================
        # FIND LARGEST GREEN CONTOUR
        # =================================================

        if contours:

            largest_contour = max(
                contours,
                key=cv2.contourArea
            )

            area = cv2.contourArea(largest_contour)

            if area > MIN_AREA:

                M = cv2.moments(largest_contour)

                if M["m00"] != 0:

                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    detected = True

                    # =====================================
                    # DISTANCES AND OFFSET
                    # =====================================

                    left_distance = cx
                    right_distance = width - cx

                    offset = cx - center_x

                    # =====================================
                    # DIRECTION AND PWM CALCULATION
                    # =====================================

                    if abs(offset) <= CENTER_TOLERANCE:

                        direction = "CENTER"

                        left_pwm = BASE_PWM
                        right_pwm = BASE_PWM

                    else:

                        correction = int(KP * abs(offset))

                        if offset < 0:

                            direction = "LEFT"

                            left_pwm = BASE_PWM - correction
                            right_pwm = BASE_PWM + correction

                        else:

                            direction = "RIGHT"

                            left_pwm = BASE_PWM + correction
                            right_pwm = BASE_PWM - correction

                    # =====================================
                    # PWM LIMITING
                    # =====================================

                    left_pwm = int(
                        np.clip(left_pwm, MIN_PWM, MAX_PWM)
                    )

                    right_pwm = int(
                        np.clip(right_pwm, MIN_PWM, MAX_PWM)
                    )

                    # =====================================
                    # DRAW CONTOUR
                    # =====================================

                    cv2.drawContours(
                        frame,
                        [largest_contour],
                        -1,
                        (0, 255, 0),
                        3
                    )

                    # =====================================
                    # CENTROID
                    # =====================================

                    cv2.circle(
                        frame,
                        (cx, cy),
                        8,
                        (0, 0, 255),
                        -1
                    )

                    cv2.putText(
                        frame,
                        "CENTROID",
                        (cx + 10, cy - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 255),
                        2
                    )

                    # =====================================
                    # CENTER TO CENTROID LINE
                    # =====================================

                    cv2.line(
                        frame,
                        (center_x, center_y),
                        (cx, cy),
                        (0, 255, 255),
                        3
                    )

                    # =====================================
                    # INFORMATION DISPLAY
                    # =====================================

                    cv2.putText(
                        frame,
                        f"Centroid: ({cx}, {cy})",
                        (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Left Distance: {left_distance}px",
                        (20, 95),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (255, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Right Distance: {right_distance}px",
                        (20, 130),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (255, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Offset: {offset}px",
                        (20, 165),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (0, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Direction: {direction}",
                        (20, 200),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.75,
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Left Motor PWM: {left_pwm}",
                        (20, 240),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (255, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Right Motor PWM: {right_pwm}",
                        (20, 275),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (255, 255, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        "SERIAL: SENDING TO ARDUINO",
                        (20, 310),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 165, 255),
                        2
                    )

        # =================================================
        # GREEN LANE NOT DETECTED
        # =================================================

        if not detected:

            left_pwm = 0
            right_pwm = 0
            direction = "STOP"

            cv2.putText(
                frame,
                "NO GREEN LANE DETECTED",
                (20, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                "Centroid: --",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "Left Distance: --",
                (20, 135),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "Right Distance: --",
                (20, 170),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "Offset: --",
                (20, 205),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "Direction: STOP",
                (20, 240),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                "Left Motor PWM: 0",
                (20, 280),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "Right Motor PWM: 0",
                (20, 315),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

        # =================================================
        # SEND PWM TO ARDUINO EVERY FRAME
        # =================================================

        send_pwm(left_pwm, right_pwm)

        # =================================================
        # DISPLAY WINDOWS
        # =================================================

        cv2.imshow("Camera View", frame)
        cv2.imshow("HSV Mask", mask)

        # ESC to exit
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

# =========================================================
# 7. CLEANUP
# =========================================================

finally:

    # Send STOP command before closing
    send_pwm(0, 0)

    time.sleep(0.1)

    cap.release()
    cv2.destroyAllWindows()

    if arduino is not None and arduino.is_open:
        arduino.close()

    print("Program stopped.")