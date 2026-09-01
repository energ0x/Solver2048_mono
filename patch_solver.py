with open("solver.c", "r") as f:
    text = f.read()

# Make sure creates_2048 is defined
if "static inline int creates_2048" not in text:
    print("Error: creates_2048 not found")
    exit(1)

# In search_root_depth, keep the 2048 ban
# In solver_find_best_move_depth, fallback to 2048 if doomed
text = text.replace("""    if (mv == -1) {
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb && !creates_2048(moved)) return m;
        }
        return 0;
    }""",
"""    if (mv == -1) {
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb && !creates_2048(moved)) return m;
        }
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb) return m;
        }
        return 0;
    }""")

text = text.replace("""    if (best_move_overall == -1) {
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb && !creates_2048(moved)) return m;
        }
        return 0;
    }""",
"""    if (best_move_overall == -1) {
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb && !creates_2048(moved)) return m;
        }
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb) return m;
        }
        return 0;
    }""")

# Make sure benchmark stops at 2048 to simulate Monobank
text = text.replace("        b = place_random(b);\n        moves++;",
"""        if (get_max_log(b) >= 11) break;
        b = place_random(b);
        moves++;""")

with open("solver.c", "w") as f:
    f.write(text)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver.so", "solver.c", "-lm"], check=True)
