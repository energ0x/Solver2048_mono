"""
Зчитування стану ігрової дошки 2048 з екрану Mac.

Захоплює скриншот через macOS screencapture (надійніше ніж pyautogui
для iPhone Mirroring), зчитує кольори пікселів у точках сітки,
перетворює їх у номінали плиток через ColorMapper.
"""

import subprocess
import tempfile
import os
import numpy as np
from PIL import Image
from color_mapper import ColorMapper


# Зсуви від центру клітинки для зчитування кольору.
# Уникаємо центру, де може бути білий текст числа.
# 8 точок — більше = надійніше визначення медіани.
SAMPLE_OFFSETS = [
    (-18, -18),  # Верхній лівий (далі)
    (18, -18),   # Верхній правий (далі)
    (-18, 18),   # Нижній лівий (далі)
    (18, 18),    # Нижній правий (далі)
    (-20, 0),    # Лівий
    (20, 0),     # Правий
    (0, -20),    # Верхній
    (0, 20),     # Нижній
]


def _take_screenshot() -> Image.Image:
    """
    Захоплення екрану через macOS screencapture.
    Набагато надійніше ніж pyautogui.screenshot() для iPhone Mirroring.
    """
    tmp_path = os.path.join(tempfile.gettempdir(), "solver2048_screen.png")
    # -x = без звуку, -C = без курсора, -t png = формат
    subprocess.run(
        ["screencapture", "-x", "-C", "-t", "png", tmp_path],
        check=True,
        capture_output=True
    )
    img = Image.open(tmp_path)
    return img


def _median_rgb(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    """Повертає медіану RGB з набору пікселів."""
    r = sorted(p[0] for p in pixels)
    g = sorted(p[1] for p in pixels)
    b = sorted(p[2] for p in pixels)
    mid = len(pixels) // 2
    return (r[mid], g[mid], b[mid])


def read_board(start_x: int, start_y: int, step: int,
               color_mapper: ColorMapper) -> np.ndarray | None:
    """
    Зчитує стан дошки з екрану.

    Args:
        start_x: X-координата центру верхньої лівої клітинки.
        start_y: Y-координата центру верхньої лівої клітинки.
        step: Відстань між центрами клітинок (однакова для X та Y).
        color_mapper: Об'єкт ColorMapper для визначення номіналів.

    Returns:
        numpy.ndarray 4x4 з номіналами плиток,
        або None якщо не вдалося розпізнати.
    """
    board = np.zeros((4, 4), dtype=int)

    try:
        screen = _take_screenshot()
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ Помилка захоплення екрану: {e}")
        return None

    # Retina дисплеї мають масштаб 2x — screencapture зберігає в реальних пікселях
    screen_w, screen_h = screen.size
    # Визначаємо масштаб: якщо зображення значно більше за типовий
    # розмір екрану, значить це Retina
    scale = 1
    try:
        # Отримуємо логічний розмір екрану
        result = subprocess.run(
            ["python3", "-c",
             "import AppKit; s = AppKit.NSScreen.mainScreen().frame().size; print(int(s.width), int(s.height))"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logical_w = int(result.stdout.strip().split()[0])
            if screen_w > logical_w * 1.5:
                scale = round(screen_w / logical_w)
    except Exception:
        # Якщо не вдалося визначити — спробуємо стандартний масштаб 2x для Retina
        if screen_w > 3000:
            scale = 2

    if scale > 1:
        print(f"  📱 Retina дисплей виявлено (масштаб {scale}x)")

    for r in range(4):
        for c in range(4):
            cx = start_x + c * step
            cy = start_y + r * step

            # Збираємо кольори з кількох точок навколо центру
            pixels = []
            for dx, dy in SAMPLE_OFFSETS:
                # Масштабуємо координати для Retina
                px = (cx + dx) * scale
                py = (cy + dy) * scale
                try:
                    rgb = screen.getpixel((px, py))
                    # Відкидаємо альфа-канал якщо є
                    pixels.append(rgb[:3])
                except (IndexError, Exception):
                    continue

            if not pixels:
                print(f"  ⚠ Не вдалося зчитати піксель для [{r}][{c}] ({cx}, {cy})")
                board[r][c] = 0
                continue

            # Медіана для стабільності
            median_color = _median_rgb(pixels)

            # Визначаємо номінал
            value = color_mapper.identify(median_color)

            if value is None:
                # Невідомий колір — запитуємо у користувача
                value = color_mapper.ask_user(median_color, r, c)

            board[r][c] = value

    return board


def print_board(board: np.ndarray):
    """Красивий вивід дошки в консоль."""
    print("\n┌──────┬──────┬──────┬──────┐")
    for r in range(4):
        row_str = "│"
        for c in range(4):
            val = board[r][c]
            if val == 0:
                row_str += "   ·  │"
            else:
                row_str += f"{val:>5} │"
        print(row_str)
        if r < 3:
            print("├──────┼──────┼──────┼──────┤")
    print("└──────┴──────┴──────┴──────┘")
