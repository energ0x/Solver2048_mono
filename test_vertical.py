with open("solver.c", "r") as f:
    text = f.read()

# Make sure creates_2048 is banned
text = text.replace("static inline int creates_2048(uint64_t moved) {\n    return 0;\n}", "static inline int creates_2048(uint64_t moved) {\n    return get_max_log(moved) >= 11;\n}")

# Add vertical 1024 reward to evaluate!
text = text.replace("    /* Corner lock: макс. плитка має стояти в [0][0] (біти 60-63). */",
"""
    int count10 = 0;
    for(int i=0; i<16; i++) if (((b >> (i<<2)) & 0xF) == 10) count10++;
    if (count10 >= 2) {
        int v00 = (b >> 60) & 0xF;
        int v10 = (b >> 44) & 0xF;
        if (v00 == 10 && v10 == 10) h += 1000000.0;
    }

    /* Corner lock: макс. плитка має стояти в [0][0] (біти 60-63). */
""")

with open("solver_vertical.c", "w") as f:
    f.write(text)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver_vertical.so", "solver_vertical.c", "-lm"], check=True)

import ctypes
import time
solver = ctypes.CDLL('./solver_vertical.so')
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
