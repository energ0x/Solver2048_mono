"""
Система навчання та маппінгу кольорів плиток 2048.

При зустрічі невідомого кольору запитує у користувача номінал плитки
і зберігає маппінг у colors.json для наступних запусків.
"""

import json
import os

# Поріг відстані для розпізнавання кольору (сума квадратів різниць RGB).
# Менше значення = суворіше розпізнавання (менше плутанини між схожими плитками).
# 400 ≈ різниця ~11 одиниць на канал. Наприклад, (200,150,100) vs (211,161,111).
COLOR_DISTANCE_THRESHOLD = 400

# Шлях до файлу з кольорами (поруч з скриптом)
COLORS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "colors.json")


class ColorMapper:
    """Маппінг RGB-кольорів на номінали плиток з інтерактивним навчанням."""

    def __init__(self, colors_file: str = COLORS_FILE):
        self.colors_file = colors_file
        self.color_map: dict[tuple[int, int, int], int] = {}
        self._load()

    def _load(self):
        """Завантажити збережений маппінг кольорів."""
        if os.path.exists(self.colors_file):
            try:
                with open(self.colors_file, "r") as f:
                    data = json.load(f)
                self.color_map = {}
                for key_str, value in data.items():
                    # Парсимо "(R, G, B)" назад у tuple
                    rgb = tuple(int(x.strip()) for x in key_str.strip("()").split(","))
                    self.color_map[rgb] = value
                print(f"  Завантажено {len(self.color_map)} кольорів з {self.colors_file}")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"  ⚠ Помилка читання {self.colors_file}: {e}")
                self.color_map = {}
        else:
            print(f"  Файл кольорів не знайдено, буде створено при навчанні.")

    def _save(self):
        """Зберегти маппінг кольорів у файл."""
        data = {}
        for rgb, value in self.color_map.items():
            data[str(rgb)] = value
        with open(self.colors_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _find_closest(self, rgb: tuple[int, int, int]) -> tuple[int | None, float]:
        """
        Знайти найближчий відомий колір.

        Returns:
            (номінал_плитки, відстань) або (None, inf) якщо нічого не знайдено.
        """
        if not self.color_map:
            return None, float('inf')

        min_dist = float('inf')
        best_val = None

        for known_rgb, val in self.color_map.items():
            dist = sum((a - b) ** 2 for a, b in zip(rgb, known_rgb))
            if dist < min_dist:
                min_dist = dist
                best_val = val

        if min_dist <= COLOR_DISTANCE_THRESHOLD:
            return best_val, min_dist

        return None, min_dist

    def identify(self, rgb: tuple[int, int, int]) -> int | None:
        """
        Визначити номінал плитки за кольором.

        Returns:
            Номінал плитки або None якщо колір невідомий.
        """
        val, _ = self._find_closest(rgb)
        return val

    def learn(self, rgb: tuple[int, int, int], value: int):
        """Додати новий колір у маппінг та зберегти."""
        self.color_map[rgb] = value
        self._save()
        print(f"  ✓ Збережено: RGB{rgb} → {value}")

    def ask_user(self, rgb: tuple[int, int, int], row: int, col: int) -> int:
        """
        Запитати у користувача номінал плитки для невідомого кольору.

        Args:
            rgb: RGB-значення піксела.
            row: Рядок клітинки (0-3).
            col: Стовпець клітинки (0-3).

        Returns:
            Номінал плитки (0 для порожньої).
        """
        print(f"\n{'='*50}")
        print(f"  🆕 Невідомий колір у клітинці [{row}][{col}]!")
        print(f"  RGB: ({rgb[0]}, {rgb[1]}, {rgb[2]})")
        print(f"  Введіть номінал плитки (0=порожня, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, ...):")

        while True:
            try:
                user_input = input("  > ").strip()
                value = int(user_input)
                if value == 0 or (value > 0 and (value & (value - 1)) == 0):
                    self.learn(rgb, value)
                    return value
                else:
                    print("  ⚠ Значення має бути 0 або степінь двійки (2, 4, 8, 16, ...)")
            except ValueError:
                print("  ⚠ Введіть число!")
            except KeyboardInterrupt:
                print("\n  Перервано користувачем.")
                raise

    def reset(self):
        """Скинути всі вивчені кольори."""
        self.color_map = {}
        if os.path.exists(self.colors_file):
            os.remove(self.colors_file)
        print("  Кольори скинуто.")

    def show(self):
        """Показати всі відомі кольори."""
        if not self.color_map:
            print("  Жодного кольору ще не вивчено.")
            return
        print(f"\n  Відомі кольори ({len(self.color_map)}):")
        for rgb, val in sorted(self.color_map.items(), key=lambda x: x[1]):
            label = "порожня" if val == 0 else str(val)
            print(f"    RGB{rgb} → {label}")
