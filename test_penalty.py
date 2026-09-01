with open("solver.c", "r") as f:
    text = f.read()

# Remove the hard ban from creates_2048 check
text = text.replace("if (creates_2048(moved)) continue;", "")

# In evaluate, change the penalty for 2048
text = text.replace("if (get_max_log(b) >= 11) return -HUGE_VAL;", "if (get_max_log(b) >= 11) return -1000000.0;")

with open("solver_penalty.c", "w") as f:
    f.write(text)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver_penalty.so", "solver_penalty.c", "-lm"], check=True)

import ctypes
import time
solver = ctypes.CDLL('./solver_penalty.so')
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
