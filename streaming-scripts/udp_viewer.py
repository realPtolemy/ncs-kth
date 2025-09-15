import cv2
import numpy as np
from aestream import UDPInput

# Open both streams simultaneously using a context manager.
with UDPInput((640, 480), port=4001) as stream1, UDPInput((640, 480), port=4002) as stream2:
    while True:
        # Read the frames as torch tensors
        frame1 = stream1.read("torch")
        frame2 = stream2.read("torch")

        # Convert the tensors to NumPy arrays and cast them to uint8.
        frame1_to_show = (frame1 * 255).numpy().astype(np.uint8)
        frame2_to_show = (frame2 * 255).numpy().astype(np.uint8)

        # Rotate each frame 90 degrees clockwise.
        rotated_frame1 = cv2.rotate(frame1_to_show, cv2.ROTATE_90_CLOCKWISE)
        rotated_frame2 = cv2.rotate(frame2_to_show, cv2.ROTATE_90_CLOCKWISE)

        # Display the rotated frames in separate windows.
        cv2.imshow("Events Stream 1", rotated_frame1)
        cv2.imshow("Events Stream 2", rotated_frame2)

        # Press 'Esc' to quit
        if cv2.waitKey(1) & 0xFF == 27:
            break

cv2.destroyAllWindows()
