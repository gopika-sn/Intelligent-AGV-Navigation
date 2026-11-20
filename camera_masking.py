
import cv2
import numpy as np

# Open camera
cap = cv2.VideoCapture(0)

while True:

    # Read camera frame
    ret, frame = cap.read()

    if not ret:
        print("Camera not detected")
        break

    # Create mask
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)

    # Select rectangular region
    mask[100:400, 100:400] = 255

    # Apply masking
    result = cv2.bitwise_and(frame, frame, mask=mask)

    # Display frames
    cv2.imshow("Original Camera Frame", frame)
    cv2.imshow("Masked Camera Frame", result)

    # Press q to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release camera
cap.release()
cv2.destroyAllWindows()
