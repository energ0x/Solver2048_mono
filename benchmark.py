#!/usr/bin/env python3
"""
2048 AI Benchmark — Anti-2048 Strategy
Компіляція C-солвера:
    gcc -O3 -shared -fPIC -o solver.so solver.c -lm
"""

import ctypes
import os
import random
import time

SOLVER = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "solver.so"))

SOLVER.solver_find_best_move.argtypes = [ctypes.c_uint64, ctypes.c_int]
SOLVER.solver_find_best_move.restype = ctypes.c_int

SOLVER.solver_board_to_bitboard.argtypes = [ctypes.POINTER(ctypes.c_int)]
SOLVER.solver_board_to_bitboard.restype = ctypes.c_uint64

SOLVER.solver_bitboard_to_board.argtypes = [ctypes.c_uint64, ctypes.POINTER(ctypes.c_int)]
SOLVER.solver_execute_move.argtypes = [ctypes.c_uint64, ctypes.c_int]
SOLVER.solver_execute_move.restype = ctypes.c_uint64

MOVES = ["up", "down", "left", "right"]


class Game2048:
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)
        self.board = [0] * 16
        self.score = 0
        self.add_tile()
        self.add_tile()

    def add_tile(self):
        empty = [i for i, v in enumerate(self.board) if v == 0]
        if empty:
            self.board[random.choice(empty)] = 2 if random.random() < 0.9 else 4

    def _slide(self, line):
        """Повертає (новий_рядок, очки)"""
        non_zero = [x for x in line if x != 0]
        merged = []
        score = 0
        i = 0
        while i < len(non_zero):
            if i + 1 < len(non_zero) and non_zero[i] == non_zero[i + 1]:
                merged.append(non_zero[i] * 2)
                score += non_zero[i] * 2
                i += 2
            else:
                merged.append(non_zero[i])
                i += 1
        merged += [0] * (4 - len(merged))
        return merged, score

    def move(self, direction):
        """0=left, 1=down, 2=right, 3=up. Повертає True якщо дошка змінилась."""
        old = self.board[:]

        if direction == 2:          # left (2)
            for r in range(4):
                row = self.board[r * 4:(r + 1) * 4]
                new, sc = self._slide(row)
                self.board[r * 4:(r + 1) * 4] = new
                self.score += sc

        elif direction == 3:        # right (3)
            for r in range(4):
                row = self.board[r * 4:(r + 1) * 4][::-1]
                new, sc = self._slide(row)
                self.board[r * 4:(r + 1) * 4] = new[::-1]
                self.score += sc

        elif direction == 0:        # up (0)
            for c in range(4):
                col = [self.board[r * 4 + c] for r in range(4)]
                new, sc = self._slide(col)
                for r in range(4):
                    self.board[r * 4 + c] = new[r]
                self.score += sc

        elif direction == 1:        # down (1)
            for c in range(4):
                col = [self.board[r * 4 + c] for r in range(4)][::-1]
                new, sc = self._slide(col)
                for r in range(4):
                    self.board[r * 4 + c] = new[::-1][r]
                self.score += sc

        return self.board != old

    def empty_count(self):
        return sum(1 for x in self.board if x == 0)

    def has_2048(self):
        return any(x >= 2048 for x in self.board)

    def can_move(self):
        for d in range(4):
            g = Game2048()
            g.board = self.board[:]
            if g.move(d):
                return True
        return False

    def __str__(self):
        return "\n".join(
            " ".join(f"{v:4d}" if v else "   ." for v in self.board[r * 4:(r + 1) * 4])
            for r in range(4)
        )


def play_game(seed=None, verbose=False):
    game = Game2048(seed)
    moves = 0

    while game.can_move():
        if game.has_2048():
            if verbose:
                print(f"!!! 2048 досягнуто на ході {moves}, очки: {game.score}")
            break

        arr = (ctypes.c_int * 16)(*game.board)
        bitboard = SOLVER.solver_board_to_bitboard(arr)
        empty = game.empty_count()

        t0 = time.time()
        move = SOLVER.solver_find_best_move(bitboard, empty)
        t1 = time.time()

        if move < 0:
            if verbose:
                print(f"Немає ходів на {moves}")
            break

        changed = game.move(move)
        if changed:
            game.add_tile()
            moves += 1

        if verbose and moves % 100 == 0:
            print(f"Хід {moves:4d} | Очки {game.score:6d} | Макс {max(game.board):4d} | "
                  f"Пусто {game.empty_count():2d} | {MOVES[move]:5s} | Час {t1-t0:.3f}s")
            print(game)
            print()

    return game.score, moves, max(game.board)


if __name__ == "__main__":
    print("=" * 65)
    print("2048 AI Benchmark — Максимізація очок без досягнення 2048")
    print("=" * 65)

    scores, moves_list, max_tiles, times = [], [], [], []

    for i in range(10):
        seed = 42 + i
        t0 = time.time()
        score, moves, max_tile = play_game(seed=seed, verbose=(i == 0))
        t1 = time.time()

        scores.append(score)
        moves_list.append(moves)
        max_tiles.append(max_tile)
        times.append(t1 - t0)

        print(f"Гра {i+1:2d}: Очки={score:6d}, Ходи={moves:4d}, "
              f"Макс={max_tile:4d}, Час={t1-t0:.2f}s")

    print("=" * 65)
    print(f"Середні очки: {sum(scores)/len(scores):.0f}")
    print(f"Середні ходи: {sum(moves_list)/len(moves_list):.0f}")
    print(f"Макс очки:    {max(scores)}")
    print(f"Макс ходи:    {max(moves_list)}")
    print(f"Загальний час:{sum(times):.1f}s")
