import ctypes
import numpy as np
import time

solver = ctypes.CDLL('./solver.so')

# Define argument types
solver.solver_set_weights.argtypes = [
    ctypes.c_double, ctypes.c_double, ctypes.c_double,
    ctypes.c_double, ctypes.c_double, ctypes.c_double,
    ctypes.c_double, ctypes.c_double
]
solver.solver_play_game.argtypes = [
    ctypes.c_uint64, ctypes.c_int,
    ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
]

def run_bench(w_empty, w_mono, mono_pow, w_smooth, smooth_pow, w_merge, w_corner, w_bigrock):
    solver.solver_set_weights(w_empty, w_mono, mono_pow, w_smooth, smooth_pow, w_merge, w_corner, w_bigrock)
    
    scores = []
    moves_list = []
    max_tiles = []
    
    for i in range(4):
        seed = 12345 + i
        score = ctypes.c_longlong(0)
        moves = ctypes.c_int(0)
        maxtile = ctypes.c_int(0)
        
        t0 = time.time()
        solver.solver_play_game(seed, 5, ctypes.byref(score), ctypes.byref(moves), ctypes.byref(maxtile))
        t1 = time.time()
        
        scores.append(score.value)
        moves_list.append(moves.value)
        max_tiles.append(maxtile.value)
        print(f"Game {i+1}: score={score.value}, moves={moves.value}, max={maxtile.value} ({t1-t0:.1f}s)")
        
    print(f"Avg Score: {sum(scores)/len(scores)}")
    print(f"Max Score: {max(scores)}")

print("Testing with W_BIGROCK = -500000")
run_bench(20000.0, 200.0, 4.0, 30.0, 3.5, 4000.0, 2000000.0, -500000.0)

print("\nTesting with W_BIGROCK = -500000 and lower W_MONO")
run_bench(20000.0, 50.0, 4.0, 30.0, 3.5, 4000.0, 2000000.0, -500000.0)
