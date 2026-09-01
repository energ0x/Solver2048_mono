with open("solver.c", "r") as f:
    t = f.read()

t = t.replace("static inline int creates_2048(uint64_t moved) {\n    return get_max_log(moved) >= 11;\n}\n\nstatic inline int creates_2048(uint64_t moved)", "static inline int creates_2048(uint64_t moved)")

with open("solver.c", "w") as f:
    f.write(t)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver.so", "solver.c", "-lm"], check=True)
