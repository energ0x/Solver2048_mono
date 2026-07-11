"""
Діагностичний інструмент для налагодження калібрування та розпізнавання кольорів.

Зберігає скриншот з накладеною сіткою та виводить RGB кожної клітинки.
"""

import subprocess
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont


def _take_screenshot() -> Image.Image:
    """Захоплення екрану через macOS screencapture."""
    tmp_path = os.path.join(tempfile.gettempdir(), "solver2048_screen.png")
    subprocess.run(
        ["screencapture", "-x", "-C", "-t", "png", tmp_path],
        check=True, capture_output=True
    )
    return Image.open(tmp_path)


def _get_retina_scale(screen_w: int) -> int:
    """Визначити масштаб Retina."""
    try:
        result = subprocess.run(
            ["python3", "-c",
             "import AppKit; s = AppKit.NSScreen.mainScreen().frame().size; print(int(s.width), int(s.height))"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            logical_w = int(result.stdout.strip().split()[0])
            if screen_w > logical_w * 1.5:
                return round(screen_w / logical_w)
    except Exception:
        pass
    return 2 if screen_w > 3000 else 1


def run_debug(start_x: int, start_y: int, step: int):
    """
    Запускає діагностику:
    1. Робить скриншот
    2. Малює сітку з позначками зчитування
    3. Виводить RGB кожної клітинки
    4. Зберігає зображення для перегляду
    """
    print("\n🔍 ДІАГНОСТИКА КАЛІБРУВАННЯ")
    print("=" * 60)

    screen = _take_screenshot()
    screen_w, screen_h = screen.size
    scale = _get_retina_scale(screen_w)

    print(f"  Розмір скриншота: {screen_w}x{screen_h}")
    print(f"  Retina масштаб: {scale}x")
    print(f"  Калібрування: start=({start_x}, {start_y}), step={step}")
    print()

    # Зсуви для зчитування (ті ж що в board_reader)
    SAMPLE_OFFSETS = [(-15, -15), (15, -15), (-15, 15), (15, 15)]

    # Малюємо на копії скриншота
    debug_img = screen.copy()
    draw = ImageDraw.Draw(debug_img)

    print("  RGB значення для кожної клітинки:")
    print("  (4 точки навколо центру + медіана)")
    print()

    for r in range(4):
        row_info = []
        for c in range(4):
            cx = start_x + c * step
            cy = start_y + r * step

            # Центр клітинки (в пікселях скриншота)
            px_center = cx * scale
            py_center = cy * scale

            # Малюємо хрестик у центрі
            cross_size = 10 * scale
            draw.line([(px_center - cross_size, py_center),
                       (px_center + cross_size, py_center)],
                      fill="lime", width=2)
            draw.line([(px_center, py_center - cross_size),
                       (px_center, py_center + cross_size)],
                      fill="lime", width=2)

            # Малюємо рамку клітинки
            half_step = step * scale // 2
            draw.rectangle(
                [px_center - half_step, py_center - half_step,
                 px_center + half_step, py_center + half_step],
                outline="lime", width=2
            )

            # Зчитуємо кольори з 4 точок
            samples = []
            for dx, dy in SAMPLE_OFFSETS:
                px = (cx + dx) * scale
                py = (cy + dy) * scale

                # Малюємо точку зчитування
                dot_r = 4 * scale
                draw.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                             fill="red", outline="yellow", width=1)

                try:
                    rgb = screen.getpixel((px, py))[:3]
                    samples.append(rgb)
                except Exception:
                    samples.append(None)

            # Обчислюємо медіану
            valid = [s for s in samples if s is not None]
            if valid:
                r_vals = sorted(s[0] for s in valid)
                g_vals = sorted(s[1] for s in valid)
                b_vals = sorted(s[2] for s in valid)
                mid = len(valid) // 2
                median = (r_vals[mid], g_vals[mid], b_vals[mid])
            else:
                median = (0, 0, 0)

            # Підпис
            label = f"[{r}][{c}]"
            try:
                draw.text((px_center - 15 * scale, py_center - 25 * scale),
                          label, fill="lime")
            except Exception:
                pass

            row_info.append(f"[{r}][{c}]: median={median}")

        # Виводимо інфо рядка
        for info in row_info:
            print(f"    {info}")
        print()

    # Зберігаємо діагностичне зображення
    debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_grid.png")
    debug_img.save(debug_path)
    print(f"  📷 Діагностичне зображення збережено: {debug_path}")
    print(f"     Відкрийте його і перевірте чи зелені хрестики")
    print(f"     знаходяться в центрах клітинок сітки 2048.")
    print()

    # Також зчитуємо колір прямо в центрі (без зсуву) для порівняння
    print("  Кольори прямо в центрі клітинок (без зсуву):")
    for r in range(4):
        row_str = "    "
        for c in range(4):
            cx = (start_x + c * step) * scale
            cy = (start_y + r * step) * scale
            try:
                rgb = screen.getpixel((cx, cy))[:3]
                row_str += f"({rgb[0]:>3},{rgb[1]:>3},{rgb[2]:>3})  "
            except Exception:
                row_str += "(err)           "
        print(row_str)

    print()
    print("  Якщо всі кольори однакові — калібрування неправильне.")
    print("  Запустіть: python3 main.py --calibrate")
