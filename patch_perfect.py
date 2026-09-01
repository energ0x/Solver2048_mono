with open("solver.c", "r") as f:
    text = f.read()

# Remove the sandwich heuristic
import re
text = re.sub(r'/\* Monobank 50k Sandwich Reward.*?HEUR\[rv\] = h;', 'HEUR[rv] = h;', text, flags=re.DOTALL)

with open("solver.c", "w") as f:
    f.write(text)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver.so", "solver.c", "-lm"], check=True)
