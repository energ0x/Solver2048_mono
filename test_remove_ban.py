with open("solver.c", "r") as f:
    text = f.read()

text = text.replace("if (creates_2048(moved)) continue;", "")
text = text.replace("if (get_max_log(b) >= 11) break;", "")

with open("solver.c", "w") as f:
    f.write(text)

with open("expectimax.py", "r") as f:
    text_py = f.read()
import re
text_py = re.sub(r'    # В ЖОДНОМУ РАЗІ НЕ ДОСЯГАТИ 2048!.*?\n    mx = _get_max_log\(b\)\n    if mx >= 11:\n        return -1e18', '    mx = _get_max_log(b)', text_py, flags=re.DOTALL)
with open("expectimax.py", "w") as f:
    f.write(text_py)

import subprocess
subprocess.run(["cc", "-O3", "-shared", "-fPIC", "-o", "solver.so", "solver.c", "-lm"], check=True)
