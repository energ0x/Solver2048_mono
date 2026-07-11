"""
Калібрування координат ігрової сітки 4x4.

Інтерактивне визначення координат через введення позицій клітинок.
Зберігає калібрування у calibration.json.
"""

import json
import os
import time
import pyautogui

CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")


def load_calibration() -> dict | None:
    """Завантажити збережене калібрування."""
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r") as f:
                data = json.load(f)
            required = ["start_x", "start_y", "step"]
            if all(k in data for k in required):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def save_calibration(data: dict):
    """Зберегти калібрування."""
    with open(CALIBRATION_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ Калібрування збережено у {CALIBRATION_FILE}")


def interactive_calibrate() -> dict:
    """
    Інтерактивне калібрування.

    Користувач наводить курсор на центр лівої верхньої клітинки,
    потім на центр правої нижньої. Програма фіксує позиції.
    """
    print("\n" + "=" * 60)
    print("  📐 КАЛІБРУВАННЯ КООРДИНАТ СІТКИ")
    print("=" * 60)
    print()
    print("  Крок 1: Наведіть курсор миші на ЦЕНТР ВЕРХНЬОЇ ЛІВОЇ")
    print("          клітинки сітки 2048 і натисніть Enter.")
    print()
    input("  Натисніть Enter коли курсор у позиції... ")
    time.sleep(0.1)
    x1, y1 = pyautogui.position()
    print(f"  ✓ Верхня ліва: ({x1}, {y1})")

    print()
    print("  Крок 2: Наведіть курсор миші на ЦЕНТР НИЖНЬОЇ ПРАВОЇ")
    print("          клітинки сітки 2048 і натисніть Enter.")
    print()
    input("  Натисніть Enter коли курсор у позиції... ")
    time.sleep(0.1)
    x2, y2 = pyautogui.position()
    print(f"  ✓ Нижня права: ({x2}, {y2})")

    # Розрахунок кроку (сітка 4x4, тому 3 проміжки)
    step_x = (x2 - x1) / 3
    step_y = (y2 - y1) / 3
    step = int(round((step_x + step_y) / 2))  # Середнє (сітка квадратна)

    data = {
        "start_x": x1,
        "start_y": y1,
        "step": step,
    }

    print()
    print(f"  Результат калібрування:")
    print(f"    Початок: ({x1}, {y1})")
    print(f"    Крок: {step} px")
    print()

    # Показуємо де будуть центри всіх клітинок
    print("  Центри клітинок:")
    for r in range(4):
        row_str = "    "
        for c in range(4):
            cx = x1 + c * step
            cy = y1 + r * step
            row_str += f"({cx:>4},{cy:>4})  "
        print(row_str)
    print()

    confirm = input("  Зберегти калібрування? (y/n): ").strip().lower()
    if confirm in ("y", "", "д", "т", "yes"):
        save_calibration(data)
        return data
    else:
        print("  Калібрування скасовано. Спробуйте знову.")
        return interactive_calibrate()


def get_board_center(cal: dict) -> tuple[int, int]:
    """Повертає координати центру дошки."""
    cx = cal["start_x"] + cal["step"] * 1.5
    cy = cal["start_y"] + cal["step"] * 1.5
    return int(cx), int(cy)
