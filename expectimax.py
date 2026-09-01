"""
Оптимізований Expectimax solver для 2048.

Ключові оптимізації:
- Bitboard (64-біт int) представлення дошки
- Lookup-таблиці для зсуву рядків (65536 записів)
- Транспозиційна таблиця з кешуванням оцінок
- Динамічна глибина (3–7 залежно від порожніх клітинок)
- Відсікання (pruning) малоймовірних гілок (tile-4 на глибоких рівнях)
- Оцінка дошки через per-row lookup таблиці
"""

import numpy as np

# ═══════════════════════════════════════════════════════════════
# КОДУВАННЯ ДОШКИ (Bitboard)
# ═══════════════════════════════════════════════════════════════
#
# Кожна клітинка: 4 біти = log2(значення), 0 = порожня
# Рядок: 16 біт, cell[0] в бітах 12-15 (ліва), cell[3] в бітах 0-3
# Дошка: 64 біти, row[0] в бітах 48-63 (верх), row[3] в бітах 0-15
#
# Приклад: плитка 2048 = log2(2048) = 11 = 0b1011

# ═══════════════════════════════════════════════════════════════
# LOOKUP ТАБЛИЦІ ДЛЯ ЗСУВУ РЯДКІВ
# ═══════════════════════════════════════════════════════════════

_SL = [0] * 65536   # slide left: новий рядок
_SCL = [0] * 65536  # slide left: очки
_SR = [0] * 65536   # slide right: новий рядок
_SCR = [0] * 65536  # slide right: очки


def _rev16(row):
    """Реверс 16-бітного рядка (4 ніблів)."""
    return (((row) & 0xF) << 12 |
            ((row >> 4) & 0xF) << 8 |
            ((row >> 8) & 0xF) << 4 |
            ((row >> 12) & 0xF))


def _build_slide_tables():
    for rv in range(65536):
        c = [(rv >> 12) & 0xF, (rv >> 8) & 0xF, (rv >> 4) & 0xF, rv & 0xF]
        nz = [x for x in c if x]
        res, sc, i = [], 0, 0
        while i < len(nz):
            if i + 1 < len(nz) and nz[i] == nz[i + 1]:
                m = nz[i] + 1
                res.append(m)
                sc += 1 << m
                i += 2
            else:
                res.append(nz[i])
                i += 1
        res += [0] * (4 - len(res))
        _SL[rv] = res[0] << 12 | res[1] << 8 | res[2] << 4 | res[3]
        _SCL[rv] = sc

    for rv in range(65536):
        r = _rev16(rv)
        _SR[rv] = _rev16(_SL[r])
        _SCR[rv] = _SCL[r]


_build_slide_tables()

# ═══════════════════════════════════════════════════════════════
# LOOKUP ТАБЛИЦЯ ДЛЯ ЕВРИСТИЧНОЇ ОЦІНКИ (per-row)
# ═══════════════════════════════════════════════════════════════

_HEUR = [0.0] * 65536


def _build_heuristic_table():
    for rv in range(65536):
        c0 = (rv >> 12) & 0xF
        c1 = (rv >> 8) & 0xF
        c2 = (rv >> 4) & 0xF
        c3 = rv & 0xF
        cells = [c0, c1, c2, c3]

        score = 0.0

        # Порожні клітинки
        empty = sum(1 for x in cells if x == 0)
        score += empty * 270.0

        # Монотонність (як в Nneonneo - зведення в ступінь для штрафу)
        inc = dec = 0
        for i in range(3):
            if cells[i] > cells[i + 1]:
                dec += (cells[i] ** 4.0) - (cells[i + 1] ** 4.0)
            elif cells[i] < cells[i + 1]:
                inc += (cells[i + 1] ** 4.0) - (cells[i] ** 4.0)
        score -= min(inc, dec) * 47.0

        # Гладкість — штраф за різницю сусідів
        for i in range(3):
            if cells[i] != 0 and cells[i + 1] != 0:
                score -= abs((cells[i] ** 3.5) - (cells[i + 1] ** 3.5)) * 11.0

        # Потенціал злиття
        for i in range(3):
            if cells[i] != 0 and cells[i] == cells[i + 1]:
                score += (cells[i] ** 1.0) * 700.0

        _HEUR[rv] = score


_build_heuristic_table()

# ═══════════════════════════════════════════════════════════════
# ОПЕРАЦІЇ НАД ДОШКОЮ (bitboard)
# ═══════════════════════════════════════════════════════════════

def _move_left(b):
    s = 0
    r0 = (b >> 48) & 0xFFFF
    r1 = (b >> 32) & 0xFFFF
    r2 = (b >> 16) & 0xFFFF
    r3 = b & 0xFFFF
    n = (_SL[r0] << 48 | _SL[r1] << 32 | _SL[r2] << 16 | _SL[r3])
    s = _SCL[r0] + _SCL[r1] + _SCL[r2] + _SCL[r3]
    return n, s


def _move_right(b):
    r0 = (b >> 48) & 0xFFFF
    r1 = (b >> 32) & 0xFFFF
    r2 = (b >> 16) & 0xFFFF
    r3 = b & 0xFFFF
    n = (_SR[r0] << 48 | _SR[r1] << 32 | _SR[r2] << 16 | _SR[r3])
    s = _SCR[r0] + _SCR[r1] + _SCR[r2] + _SCR[r3]
    return n, s


def _move_up(b):
    n = 0
    sc = 0
    for c in range(4):
        s = (3 - c) << 2
        col = (((b >> (48 + s)) & 0xF) << 12 |
               ((b >> (32 + s)) & 0xF) << 8 |
               ((b >> (16 + s)) & 0xF) << 4 |
               ((b >> s) & 0xF))
        ncol = _SL[col]
        sc += _SCL[col]
        n |= (((ncol >> 12) & 0xF) << (48 + s) |
              ((ncol >> 8) & 0xF) << (32 + s) |
              ((ncol >> 4) & 0xF) << (16 + s) |
              (ncol & 0xF) << s)
    return n, sc


def _move_down(b):
    n = 0
    sc = 0
    for c in range(4):
        s = (3 - c) << 2
        col = (((b >> (48 + s)) & 0xF) << 12 |
               ((b >> (32 + s)) & 0xF) << 8 |
               ((b >> (16 + s)) & 0xF) << 4 |
               ((b >> s) & 0xF))
        ncol = _SR[col]
        sc += _SCR[col]
        n |= (((ncol >> 12) & 0xF) << (48 + s) |
              ((ncol >> 8) & 0xF) << (32 + s) |
              ((ncol >> 4) & 0xF) << (16 + s) |
              (ncol & 0xF) << s)
    return n, sc


# Набір рухів (Порядок має відповідати controller.py: 0=UP, 1=DOWN, 2=LEFT, 3=RIGHT)
_MOVES = [
    _move_up,
    _move_down,
    _move_left,
    _move_right
]


# ═══════════════════════════════════════════════════════════════
# УТИЛІТАРНІ ФУНКЦІЇ
# ═══════════════════════════════════════════════════════════════

def _count_empty(b):
    """Кількість порожніх клітинок."""
    c = 0
    tmp = b
    for _ in range(16):
        if (tmp & 0xF) == 0:
            c += 1
        tmp >>= 4
    return c


def _get_empties(b):
    """Список бітових зсувів порожніх клітинок."""
    result = []
    for i in range(16):
        shift = i << 2
        if (b >> shift) & 0xF == 0:
            result.append(shift)
    return result


def _get_max_log(b):
    """Максимальне log2 значення на дошці."""
    mx = 0
    tmp = b
    for _ in range(16):
        v = tmp & 0xF
        if v > mx:
            mx = v
        tmp >>= 4
    return mx


def _np_to_bb(board_np):
    """Конвертація numpy 4x4 → bitboard (64-bit int)."""
    result = 0
    for r in range(4):
        for c in range(4):
            val = int(board_np[r][c])
            if val > 0:
                log_val = val.bit_length() - 1  # швидкий log2 для степенів 2
            else:
                log_val = 0
            shift = ((3 - r) << 4) + ((3 - c) << 2)
            result |= log_val << shift
    return result


# ═══════════════════════════════════════════════════════════════
# ФУНКЦІЯ ОЦІНКИ
# ═══════════════════════════════════════════════════════════════

def _evaluate(b):
    """Оцінка стану дошки. Більше = краще."""
    # Перевірка game over
    is_empty = False
    tmp = b
    for _ in range(16):
        if (tmp & 0xF) == 0:
            is_empty = True
            break
        tmp >>= 4

    if not is_empty:
        can_move = False
        for mf in _MOVES:
            if mf(b)[0] != b:
                can_move = True
                break
        if not can_move:
            return -1e18

    # Евристики з per-row lookup (рядки + стовпці)
    r0 = (b >> 48) & 0xFFFF
    r1 = (b >> 32) & 0xFFFF
    r2 = (b >> 16) & 0xFFFF
    r3 = b & 0xFFFF

    heur = _HEUR[r0] + _HEUR[r1] + _HEUR[r2] + _HEUR[r3]
    for c in range(4):
        s = (3 - c) << 2
        col = (((b >> (48 + s)) & 0xF) << 12 |
               ((b >> (32 + s)) & 0xF) << 8 |
               ((b >> (16 + s)) & 0xF) << 4 |
               ((b >> s) & 0xF))
        heur += _HEUR[col]

    return heur


# ═══════════════════════════════════════════════════════════════
# EXPECTIMAX З ТРАНСПОЗИЦІЙНОЮ ТАБЛИЦЕЮ
# ═══════════════════════════════════════════════════════════════

_TT = {}
_TT_MAX = 2_000_000


def _expectimax(b, depth, is_player):
    if depth <= 0:
        return _evaluate(b)

    # Транспозиційна таблиця
    key = (b, depth, is_player)
    cached = _TT.get(key)
    if cached is not None:
        return cached

    if is_player:
        best = -1e18
        for mf in _MOVES:
            moved, _ = mf(b)
            if moved == b:
                continue
            val = _expectimax(moved, depth - 1, False)
            if val > best:
                best = val
        result = best if best > -1e18 else _evaluate(b)

    else:
        # Chance node — випадкова плитка
        empties = _get_empties(b)
        if not empties:
            result = _evaluate(b)
        else:
            # Відсікання: обмежуємо кількість клітинок на глибоких рівнях
            cells = empties
            if len(empties) > 6 and depth >= 3:
                step = len(empties) / 6
                cells = [empties[int(i * step)] for i in range(6)]

            total = 0.0
            for shift in cells:
                # Плитка 2 (log2=1), ймовірність 0.9
                b2 = b | (1 << shift)
                v2 = _expectimax(b2, depth - 1, True)

                # Відсікання: на глибоких рівнях ігноруємо tile-4 для швидкості,
                # АЛЕ тільки якщо є достатньо порожніх клітинок (>2). 
                # Якщо клітинок мало, tile-4 може бути єдиним порятунком (10% шанс).
                if depth >= 5 and len(empties) > 2:
                    total += v2
                else:
                    b4 = b | (2 << shift)
                    v4 = _expectimax(b4, depth - 1, True)
                    total += 0.9 * v2 + 0.1 * v4

            result = total / len(cells)

    # Зберігаємо в TT (обмежений розмір)
    if len(_TT) < _TT_MAX:
        _TT[key] = result

    return result


# ═══════════════════════════════════════════════════════════════
# ПУБЛІЧНИЙ API
# ═══════════════════════════════════════════════════════════════

import os
import ctypes

_c_solver = None
try:
    so_path = os.path.join(os.path.dirname(__file__), "solver.so")
    if os.path.exists(so_path):
        _c_solver = ctypes.CDLL(so_path)
        _c_solver.solver_find_best_move.argtypes = [ctypes.c_uint64, ctypes.c_int]
        _c_solver.solver_find_best_move.restype = ctypes.c_int
except Exception as e:
    print(f"Попередження: не вдалося завантажити solver.so ({e}). Використовується повільна Python-версія.")

def find_best_move(board_np, depth=3):
    """
    Знаходить найкращий хід для numpy дошки 4x4.
    """
    if _c_solver:
        # Для C-солвера використовуємо правильне C-кодування: i * 4
        c_bb = 0
        for r in range(4):
            for c in range(4):
                val = int(board_np[r, c])
                if val > 0:
                    log_val = val.bit_length() - 1
                    c_bb |= (log_val << ((r * 4 + c) * 4))
        
        empty_cells = _count_empty(c_bb)
        return _c_solver.solver_find_best_move(c_bb, empty_cells)

    bb = _np_to_bb(board_np)

    # Fallback на Python
    global _TT
    _TT = {}
    
    empty = _count_empty(bb)
    if empty <= 2: d = max(depth, 7)
    elif empty <= 4: d = max(depth, 6)
    elif empty <= 7: d = max(depth, 5)
    elif empty <= 10: d = max(depth, 4)
    else: d = max(depth, 3)

    best_val = -1e18
    best_move = -1

    for i, mf in enumerate(_MOVES):
        moved, _ = mf(bb)
        if moved == bb: continue
        val = _expectimax(moved, d - 1, False)
        if val > best_val:
            best_val = val
            best_move = i

    return best_move
