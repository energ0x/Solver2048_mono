with open("solver.c", "r") as f:
    text = f.read()

text = text.replace("HEUR[rv] = h;",
"""
        // Reward adjacent 1024s
        for (int i=0; i<3; i++) {
            if (c[i] == 10 && c[i+1] == 10) h += 500000.0;
        }
        HEUR[rv] = h;
""")

with open("solver_adj.c", "w") as f:
    f.write(text)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver_adj.so", "solver_adj.c", "-lm"], check=True)

import ctypes
import time
solver = ctypes.CDLL('./solver_adj.so')
solver.solver_play_game.argtypes = [
    ctypes.c_uint64, ctypes.c_int,
    ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
]

scores = []
for i in range(4):
    seed = 12345 + i
    score = ctypes.c_longlong(0)
    moves = ctypes.c_int(0)
    maxtile = ctypes.c_int(0)
    t0 = time.time()
    solver.solver_play_game(seed, 5, ctypes.byref(score), ctypes.byref(moves), ctypes.byref(maxtile))
    t1 = time.time()
    scores.append(score.value)
    print(f"Game {i+1}: score={score.value}, moves={moves.value}, max={maxtile.value} ({t1-t0:.1f}s)")
print(f"Avg Score: {sum(scores)/len(scores)}")
