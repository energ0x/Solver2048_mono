"""
Швидкий бенчмарк C-солвера (повна гра всередині C).

Використання:
    python bench.py [n_games] [base_depth]
"""
import ctypes
import os
import sys
import time

_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solver.so')
lib = ctypes.CDLL(_path)
lib.solver_init()

lib.solver_play_game.restype = None
lib.solver_play_game.argtypes = [
    ctypes.c_uint64, ctypes.c_int,
    ctypes.POINTER(ctypes.c_longlong),
    ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int),
]
lib.solver_set_weights.restype = None
lib.solver_set_weights.argtypes = [ctypes.c_double] * 8
lib.solver_set_chance_sample.restype = None
lib.solver_set_chance_sample.argtypes = [ctypes.c_int]


def set_weights(w_empty, w_mono, mono_pow, w_smooth, smooth_pow,
                w_merge, w_corner, w_bigrock):
    lib.solver_set_weights(
        ctypes.c_double(w_empty), ctypes.c_double(w_mono),
        ctypes.c_double(mono_pow), ctypes.c_double(w_smooth),
        ctypes.c_double(smooth_pow), ctypes.c_double(w_merge),
        ctypes.c_double(w_corner), ctypes.c_double(w_bigrock))


def play(seed, base_depth):
    score = ctypes.c_longlong(0)
    moves = ctypes.c_int(0)
    maxtile = ctypes.c_int(0)
    lib.solver_play_game(ctypes.c_uint64(seed), ctypes.c_int(base_depth),
                         ctypes.byref(score), ctypes.byref(moves),
                         ctypes.byref(maxtile))
    return score.value, moves.value, maxtile.value


def benchmark(n_games=8, base_depth=4, label="", start_seed=1):
    results = []
    t0 = time.time()
    for i in range(n_games):
        seed = start_seed + i * 7919
        ts = time.time()
        score, moves, maxtile = play(seed, base_depth)
        el = time.time() - ts
        results.append((score, moves, maxtile))
        print(f"  гра {i+1}: очки={score:>7}  ходи={moves:>5}  макс={maxtile:>5}  ({el:.1f}с)")
    total = time.time() - t0
    avg_score = sum(r[0] for r in results) / len(results)
    avg_moves = sum(r[1] for r in results) / len(results)
    max_score = max(r[0] for r in results)
    hit2048 = sum(1 for r in results if r[2] >= 2048)
    print(f"  {'─'*50}")
    print(f"  [{label}] сер.очки={avg_score:.0f}  макс.очки={max_score}  "
          f"сер.ходи={avg_moves:.0f}  2048={hit2048}  час={total:.1f}с")
    return avg_score, max_score, avg_moves, hit2048


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    print(f"Бенчмарк: {n} ігор, base_depth={d}")
    benchmark(n, d, label=f"depth{d}")
