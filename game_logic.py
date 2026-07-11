"""
Чиста симуляція гри 2048 (без UI).

Функції для зсуву, злиття, перевірки стану дошки.
Напрямки: 0=вгору, 1=вниз, 2=вліво, 3=вправо.
"""

import numpy as np


def slide_left(row: np.ndarray) -> tuple[np.ndarray, int]:
    """Зсув та злиття одного рядка вліво. Повертає (новий рядок, набрані очки)."""
    # Прибираємо нулі
    arr = row[row != 0]
    score = 0
    result = []
    skip = False

    for i in range(len(arr)):
        if skip:
            skip = False
            continue
        if i + 1 < len(arr) and arr[i] == arr[i + 1]:
            merged = arr[i] * 2
            result.append(merged)
            score += merged
            skip = True
        else:
            result.append(arr[i])

    # Доповнюємо нулями до 4
    result += [0] * (4 - len(result))
    return np.array(result, dtype=int), score


def move_board(board: np.ndarray, direction: int) -> tuple[np.ndarray, int]:
    """
    Виконання ходу на дошці.

    Напрямки: 0=вгору, 1=вниз, 2=вліво, 3=вправо.
    Повертає (нова дошка, набрані очки).
    """
    new_board = np.copy(board)
    total_score = 0

    # Обертаємо так, щоб завжди зсувати вліво
    if direction == 0:    # Вгору → обертаємо на 90° за годинниковою
        new_board = np.rot90(new_board, 1)
    elif direction == 1:  # Вниз → обертаємо на 90° проти годинникової
        new_board = np.rot90(new_board, -1)
    elif direction == 3:  # Вправо → обертаємо на 180°
        new_board = np.rot90(new_board, 2)
    # direction == 2 (вліво) — обертання не потрібне

    for i in range(4):
        new_board[i], s = slide_left(new_board[i])
        total_score += s

    # Повертаємо обертання назад
    if direction == 0:
        new_board = np.rot90(new_board, -1)
    elif direction == 1:
        new_board = np.rot90(new_board, 1)
    elif direction == 3:
        new_board = np.rot90(new_board, 2)

    return new_board, total_score


def is_game_over(board: np.ndarray) -> bool:
    """Перевіряє чи залишились можливі ходи."""
    # Є порожні клітинки — гра продовжується
    if np.any(board == 0):
        return False

    # Перевіряємо чи є сусідні однакові плитки
    for r in range(4):
        for c in range(4):
            if c + 1 < 4 and board[r][c] == board[r][c + 1]:
                return False
            if r + 1 < 4 and board[r][c] == board[r + 1][c]:
                return False

    return True


def get_empty_cells(board: np.ndarray) -> list[tuple[int, int]]:
    """Повертає список координат порожніх клітинок."""
    return list(zip(*np.where(board == 0)))


def board_changed(board: np.ndarray, new_board: np.ndarray) -> bool:
    """Перевіряє чи змінилася дошка після ходу."""
    return not np.array_equal(board, new_board)
