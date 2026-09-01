with open("solver.c", "r") as f:
    text = f.read()

# Add global flag
text = text.replace("void solver_init() {", "int allow_2048_flag = 0;\nvoid solver_init() {")

# Add count_1024 utility
utils = """
static inline int count_1024(uint64_t b) {
    int count = 0;
    for(int i=0; i<16; i++) {
        if (((b >> (i<<2)) & 0xF) == 10) count++;
    }
    return count;
}
"""
text = text.replace("static int has_any_move(uint64_t b) {", utils + "\nstatic int has_any_move(uint64_t b) {")

# Add evaluate logic
eval_logic = """
static double evaluate(uint64_t b) {
    if (!allow_2048_flag && get_max_log(b) >= 11) return -1e15;
    if (!has_any_move(b)) return -1e15;

    uint16_t r0 = (b >> 48) & 0xFFFF, r1 = (b >> 32) & 0xFFFF;
    uint16_t r2 = (b >> 16) & 0xFFFF, r3 = b & 0xFFFF;

    double h = HEUR[r0] + HEUR[r1] + HEUR[r2] + HEUR[r3];

    int c0 = (r0 >> 12) & 0xF;
    int c1 = (r0 >> 8) & 0xF;
    int c2 = (r0 >> 4) & 0xF;
    int c3 = r0 & 0xF;

    // Sandwich Reward
    if (c0 == 10 && c1 > 0 && c1 < 10 && c2 == 10) h += 500000.0;
    if (c0 == 10 && c1 > 0 && c1 < 10 && c2 > 0 && c2 < 10 && c3 == 10) h += 500000.0;
"""
import re
text = re.sub(r'static double evaluate\(uint64_t b\) \{.*?double h = HEUR\[r0\].*?;', eval_logic, text, flags=re.DOTALL)

# Add allow_2048_flag setup in solver_find_best_move_depth
find_logic = """
int solver_find_best_move_depth(uint64_t bb, int base_depth) {
    allow_2048_flag = (count_1024(bb) >= 3);
"""
text = text.replace("int solver_find_best_move_depth(uint64_t bb, int base_depth) {", find_logic)

# Make benchmark stop at 2048
text = text.replace("score += sc;\n        b = moved;\n        b = place_random(b);", "score += sc;\n        b = moved;\n        if (get_max_log(b) >= 11) break;\n        b = place_random(b);")

with open("solver_sandwich.c", "w") as f:
    f.write(text)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver_sandwich.so", "solver_sandwich.c", "-lm"], check=True)

import ctypes
import time
solver = ctypes.CDLL('./solver_sandwich.so')
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
