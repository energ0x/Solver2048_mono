#!/usr/bin/env python3
"""
2048 Solver — автоматичний гравець у 2048 через iPhone Mirroring на Mac.

Захоплює екран, розпізнає стан дошки за кольорами плиток,
використовує алгоритм Expectimax для вибору оптимального ходу,
виконує свайпи через імітацію drag миші.

Використання:
    python main.py                  # Запуск з існуючим калібруванням
    python main.py --calibrate      # Перекалібрувати координати
    python main.py --reset-colors   # Скинути вивчені кольори
    python main.py --show-colors    # Показати відомі кольори
    python main.py --debug          # Діагностика: зберегти скриншот з сіткою
    python main.py --depth N        # Глибина пошуку (за замовч. 3)
    python main.py --delay N        # Затримка між ходами в секундах (за замовч. 0.3)
"""

import argparse
import sys
import time

import numpy as np

from calibration import load_calibration, interactive_calibrate, get_board_center
from color_mapper import ColorMapper
from board_reader import read_board, print_board
from expectimax import find_best_move
from controller import perform_swipe, DIRECTION_NAMES
from game_logic import is_game_over


def parse_args():
    parser = argparse.ArgumentParser(description="2048 Solver для iPhone Mirroring")
    parser.add_argument("--calibrate", action="store_true",
                        help="Перекалібрувати координати сітки")
    parser.add_argument("--reset-colors", action="store_true",
                        help="Скинути всі вивчені кольори")
    parser.add_argument("--show-colors", action="store_true",
                        help="Показати відомі кольори і вийти")
    parser.add_argument("--debug", action="store_true",
                        help="Діагностика: зберегти скриншот з сіткою")
    parser.add_argument("--depth", type=int, default=3,
                        help="Глибина пошуку Expectimax (за замовч. 3)")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Затримка між ходами в секундах (за замовч. 0.3)")
    parser.add_argument("--swipe-distance", type=int, default=120,
                        help="Відстань свайпу в пікселях (за замовч. 120)")
    return parser.parse_args()


def main():
    args = parse_args()

    print()
    print("╔══════════════════════════════════════╗")
    print("║       🎮 2048 SOLVER v1.0            ║")
    print("║   iPhone Mirroring + Expectimax      ║")
    print("╚══════════════════════════════════════╝")
    print()

    # --- Ініціалізація Color Mapper ---
    print("📎 Кольори плиток:")
    color_mapper = ColorMapper()

    if args.reset_colors:
        color_mapper.reset()
        print("  Кольори скинуто. Запустіть знову для навчання.")
        return

    if args.show_colors:
        color_mapper.show()
        return

    # --- Калібрування ---
    print("\n📐 Калібрування:")
    cal = None
    if not args.calibrate:
        cal = load_calibration()
        if cal:
            print(f"  Завантажено: початок=({cal['start_x']}, {cal['start_y']}), крок={cal['step']}px")
        else:
            print("  Збережене калібрування не знайдено.")

    if cal is None or args.calibrate:
        cal = interactive_calibrate()

    start_x = cal["start_x"]
    start_y = cal["start_y"]
    step = cal["step"]
    board_cx, board_cy = get_board_center(cal)

    # --- Діагностика ---
    if args.debug:
        from debug_tool import run_debug
        run_debug(start_x, start_y, step)
        return

    # --- Старт ---
    print(f"\n⚙ Налаштування:")
    print(f"  Глибина пошуку: {args.depth}")
    print(f"  Затримка: {args.delay}с")
    print(f"  Свайп: {args.swipe_distance}px")
    print(f"  Центр дошки: ({board_cx}, {board_cy})")

    print(f"\n🚀 Запуск через 3 секунди...")
    print(f"   Переведіть фокус на вікно iPhone Mirroring!")
    print(f"   (Ctrl+C для зупинки)")
    time.sleep(3)

    # --- Головний цикл ---
    move_count = 0
    total_score = 0
    fallback_moves = [3, 1, 2, 0]  # Вправо, вниз, вліво, вгору — порядок аварійних ходів

    try:
        while True:
            # 1. Зчитуємо стан дошки
            board = read_board(start_x, start_y, step, color_mapper)
            if board is None:
                print("  ⚠ Не вдалося зчитати дошку. Повтор...")
                time.sleep(1)
                continue

            # 2. Виводимо поточний стан
            move_count += 1
            max_tile = int(np.max(board))
            print(f"\n── Хід #{move_count}  |  Макс: {max_tile}  ──")
            print_board(board)

            # 3. Перевіряємо чи гра закінчена
            if is_game_over(board):
                print("\n💀 ГРА ЗАКІНЧЕНА!")
                print(f"   Зроблено ходів: {move_count}")
                print(f"   Максимальна плитка: {max_tile}")
                break

            # 4. Знаходимо найкращий хід
            t0 = time.time()
            best_move = find_best_move(board, depth=args.depth)
            elapsed = time.time() - t0

            if best_move == -1 or best_move not in [0, 1, 2, 3]:
                # Аварійний хід — пробуємо всі напрямки по черзі
                print(f"  ⚠ Солвер не знайшов хід, пробуємо аварійні...")
                moved = False
                for fb_move in fallback_moves:
                    from game_logic import move_board, board_changed
                    new_b, _ = move_board(board, fb_move)
                    if board_changed(board, new_b):
                        best_move = fb_move
                        moved = True
                        break
                if not moved:
                    print("\n💀 Немає можливих ходів! ГРА ЗАКІНЧЕНА!")
                    print(f"   Зроблено ходів: {move_count}")
                    print(f"   Максимальна плитка: {max_tile}")
                    break

            print(f"  ⚡ Solver: {DIRECTION_NAMES[best_move]}  ({elapsed:.2f}с)")

            # 5. Виконуємо свайп
            perform_swipe(
                direction=best_move,
                center_x=board_cx,
                center_y=board_cy,
                swipe_distance=args.swipe_distance,
                post_delay=args.delay
            )

    except KeyboardInterrupt:
        print(f"\n\n🛑 Зупинено користувачем.")
        print(f"   Зроблено ходів: {move_count}")
        max_tile = int(np.max(board)) if 'board' in dir() else 0
        print(f"   Максимальна плитка: {max_tile}")

    print("\nДякую за гру! 🎮")


if __name__ == "__main__":
    main()
