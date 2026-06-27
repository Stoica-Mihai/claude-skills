# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy>=1.24", "opencv-python-headless>=4.9"]
# ///
"""Generate before/after screenshot fixtures for compare-screenshots evals."""
import os
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (245, 245, 245)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def canvas(w=800, h=500):
    return np.full((h, w, 3), BG, np.uint8)


def navbar(img, color=(180, 90, 40)):
    cv2.rectangle(img, (0, 0), (img.shape[1], 60), color, -1)
    cv2.putText(img, "Acme App", (20, 40), FONT, 1.0, (255, 255, 255), 2)


def button(img, x, y, label, color):
    cv2.rectangle(img, (x, y), (x + 200, y + 60), color, -1)
    cv2.putText(img, label, (x + 30, y + 40), FONT, 0.9, (255, 255, 255), 2)


def save(name, a, b):
    cv2.imwrite(os.path.join(HERE, f"{name}_before.png"), a)
    cv2.imwrite(os.path.join(HERE, f"{name}_after.png"), b)


def cosmetic():
    a = canvas(); navbar(a)
    cv2.putText(a, "Dashboard", (20, 130), FONT, 1.2, (30, 30, 30), 3)
    button(a, 20, 200, "Save", (200, 120, 40))
    b = a.copy()
    cv2.rectangle(b, (20, 200), (220, 260), BG, -1)
    button(b, 20, 200, "Save", (60, 170, 90))  # button blue -> green
    save("ui_cosmetic", a, b)


def text_change():
    a = canvas(); navbar(a)
    cv2.putText(a, "Welcome back, Alice", (20, 160), FONT, 1.0, (30, 30, 30), 2)
    cv2.putText(a, "You have 3 new messages", (20, 230), FONT, 0.8, (80, 80, 80), 2)
    b = a.copy()
    cv2.rectangle(b, (20, 200), (700, 250), BG, -1)
    cv2.putText(b, "You have 7 new messages", (20, 230), FONT, 0.8, (80, 80, 80), 2)  # 3 -> 7
    save("ui_text", a, b)


def layout_shift():
    a = canvas(); navbar(a)
    cv2.putText(a, "Profile", (20, 130), FONT, 1.2, (30, 30, 30), 3)
    button(a, 20, 180, "Edit", (200, 120, 40))
    b = canvas(); navbar(b)
    cv2.putText(b, "Profile", (20, 130), FONT, 1.2, (30, 30, 30), 3)
    cv2.putText(b, "Account verified", (20, 175), FONT, 0.7, (60, 160, 60), 2)  # new banner pushes button down
    button(b, 20, 220, "Edit", (200, 120, 40))
    save("ui_layout", a, b)


def identical():
    a = canvas(); navbar(a)
    cv2.putText(a, "Settings", (20, 130), FONT, 1.2, (30, 30, 30), 3)
    button(a, 20, 200, "Apply", (200, 120, 40))
    save("ui_identical", a, a.copy())


def different_screens():
    a = canvas(); navbar(a)
    cv2.putText(a, "Login", (20, 200), FONT, 1.5, (30, 30, 30), 3)
    button(a, 20, 280, "Sign in", (200, 120, 40))
    b = canvas(800, 500)
    b[:] = (250, 240, 230)
    for i in range(0, 800, 40):
        cv2.line(b, (i, 0), (i, 500), (200, 180, 160), 2)
    cv2.putText(b, "404 Not Found", (200, 260), FONT, 1.8, (40, 40, 200), 4)
    save("different_screens", a, b)


def diff_sizes():
    a = canvas(800, 500); navbar(a)
    cv2.putText(a, "Report", (20, 160), FONT, 1.2, (30, 30, 30), 3)
    button(a, 20, 220, "Export", (200, 120, 40))
    b = a.copy()
    cv2.rectangle(b, (20, 220), (220, 280), BG, -1)
    button(b, 20, 220, "Download", (200, 120, 40))  # label change
    b = cv2.resize(b, (1200, 750))  # different resolution
    save("diff_sizes", a, b)


if __name__ == "__main__":
    cosmetic(); text_change(); layout_shift(); identical(); different_screens(); diff_sizes()
    print("fixtures written to", HERE)
    for f in sorted(os.listdir(HERE)):
        if f.endswith(".png"):
            print(" ", f)
