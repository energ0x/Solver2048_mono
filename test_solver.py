import re

with open("solver.c", "r") as f:
    text = f.read()

text = text.replace("if (!has_any_move(b)) return -1e15;           /* глухий кут */",
"""if (get_max_log(b) >= 11) return -HUGE_VAL;   /* абсолютна заборона */

    if (!has_any_move(b)) return -1e15;           /* глухий кут */""")

text = text.replace("""static int has_any_move(uint64_t b) {
    for (int m = 0; m < 4; m++) {
        int sc;
        uint64_t moved = MOVES[m](b, &sc);
        if (moved != b) return 1;
    }
    return 0;
}""",
"""static inline int creates_2048(uint64_t moved) {
    return get_max_log(moved) >= 11;
}

static int has_any_move(uint64_t b) {
    for (int m = 0; m < 4; m++) {
        int sc;
        uint64_t moved = MOVES[m](b, &sc);
        if (moved != b && !creates_2048(moved)) return 1;
    }
    return 0;
}""")

text = text.replace("""            if (moved == b) continue;
            has_valid = 1;""",
"""            if (moved == b) continue;
            if (creates_2048(moved)) continue;
            has_valid = 1;""")

text = text.replace("""        if (moved == bb) continue;
        double val = do_expectimax(moved, depth - 1, 0);""",
"""        if (moved == bb) continue;
        if (creates_2048(moved)) continue;
        double val = do_expectimax(moved, depth - 1, 0);""")

text = text.replace("""        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb) return m;
        }""",
"""        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved != bb && !creates_2048(moved)) return m;
        }""")

text = text.replace("""            if (moved == bb) continue;
            double val = do_expectimax(moved, d - 1, 0);""",
"""            if (moved == bb) continue;
            if (creates_2048(moved)) continue;
            double val = do_expectimax(moved, d - 1, 0);""")

text = text.replace("""        score += sc;
        b = moved;

        b = place_random(b);""",
"""        score += sc;
        b = moved;

        if (get_max_log(b) >= 11) break;

        b = place_random(b);""")

with open("solver.c", "w") as f:
    f.write(text)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver.so", "solver.c", "-lm"], check=True)
