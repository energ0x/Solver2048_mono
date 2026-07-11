"""
Керування грою через імітацію свайпів на вікні iPhone Mirroring.

Використовує pyautogui.moveTo() + pyautogui.drag() для виконання
свайпів як drag-жестів миші.
"""

import pyautogui
import time

# Назви напрямків для логування
DIRECTION_NAMES = {0: "↑ ВГОРУ", 1: "↓ ВНИЗ", 2: "← ВЛІВО", 3: "→ ВПРАВО"}

# Вектори свайпів: (dx, dy)
SWIPE_VECTORS = {
    0: (0, -1),   # Вгору
    1: (0, 1),    # Вниз
    2: (-1, 0),   # Вліво
    3: (1, 0),    # Вправо
}


def perform_swipe(direction: int, center_x: int, center_y: int,
                  swipe_distance: int = 120, duration: float = 0.15,
                  post_delay: float = 0.3):
    """
    Виконує свайп через drag від центру дошки у вказаному напрямку.

    Args:
        direction: 0=вгору, 1=вниз, 2=вліво, 3=вправо.
        center_x: X-координата центру дошки.
        center_y: Y-координата центру дошки.
        swipe_distance: Відстань drag у пікселях.
        duration: Тривалість drag у секундах.
        post_delay: Затримка після свайпу (для анімації гри).
    """
    dx, dy = SWIPE_VECTORS[direction]

    # Переміщуємо курсор у центр дошки
    pyautogui.moveTo(center_x, center_y, duration=0.05)
    time.sleep(0.05)

    # Виконуємо drag з явно вказаним button='left'
    # (баг pyautogui 0.9.54 на macOS — не передає button автоматично)
    pyautogui.drag(
        dx * swipe_distance,
        dy * swipe_distance,
        duration=duration,
        button='left'
    )

    # Чекаємо завершення анімації гри
    time.sleep(post_delay)
