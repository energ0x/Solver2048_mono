# 🎮 2048 Score-Maximizing Bot
### *Anti-2048 Strategy — Expectimax with Bitboards, Computer Vision & iPhone Mirroring*

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![C](https://img.shields.io/badge/C-C99%20%2F%20O3-A8B9CC?style=for-the-badge&logo=c&logoColor=white)
![macOS](https://img.shields.io/badge/Platform-macOS%20Tahoe%20%2F%20Golden%20Gate-000000?style=for-the-badge&logo=apple&logoColor=white)
![Algorithm](https://img.shields.io/badge/Algorithm-Bitboard%20Expectimax-FF6F00?style=for-the-badge)
![Strategy](https://img.shields.io/badge/Strategy-Anti--2048%20Score%20Farm-red?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Autonomous 2048 bot that plays via macOS iPhone Mirroring.**  
*Not just a bot that wins 2048 — a bot specifically engineered to **never form the 2048 tile** and instead farm points indefinitely by keeping two 1024 tiles alive as long as possible.*

[The Core Idea](#-the-core-idea-anti-2048-strategy) •
[Architecture](#-architecture) •
[Heuristics](#-heuristics--evaluation-function) •
[Technical Deep Dive](#-technical-deep-dive) •
[Vision Pipeline](#-computer-vision-pipeline) •
[Quick Start](#-quick-start)

</div>

---

## 🎯 The Core Idea: Anti-2048 Strategy

A normal 2048 solver has one goal: **build the 2048 tile as fast as possible**. That gives you around 20,000–35,000 points per game.

This bot flips the objective: **avoid forming the 2048 tile for as long as possible** while continuously merging smaller tiles to accumulate score. The result is 3× more moves and 2–3× more points.

```
Standard Solver (greedy):
  [1024][1024][ · ][ · ]  ──▶  [ · ][ · ][ · ][2048]  Game done. Score: ~25,000

This Bot (Anti-2048 farming):
  [1024][ 512][256][128]
  [  32][  16][  8][  4]   ──▶  keeps merging small tiles forever,
  [   4][   2][ · ][ · ]         holding 1024+1024 safely apart
  [   2][ · ][ · ][ · ]          Score: 58,000–85,000+
```

### Why is this harder than normal 2048?

1. **Permanent board congestion** — the two 1024 tiles never merge, so the bot plays with only 12–13 free cells instead of 16.
2. **Accidental merge avoidance** — every move must be evaluated to ensure the two 1024s never end up adjacent in a merge direction.
3. **Dead-end risk multiplies** — with fewer open cells, random tile spawns (90% chance of 2, 10% chance of 4) can create inescapable congestion much faster.
4. **Deep lookahead required** — preventing a catastrophic merge might require planning 10–14 moves ahead, not just 4–6.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph macOS Environment
        IPM[iPhone Mirroring — 2048 Game Window]
    end

    subgraph Perception Layer
        SC[macOS screencapture CLI] -->|Raw PNG| RD[Retina Scale Detector]
        RD --> SP[8-Point Spatial Sampler]
        SP --> MF[Median RGB Filter]
        MF --> CM[ColorMapper: Euclidean Clustering]
        CM -->|4×4 int matrix| BB[Bitboard Encoder]
    end

    subgraph C99 Decision Engine — solver.so via ctypes
        BB --> SM[solver_find_best_move]
        SM --> LUT[65,536-Entry Row Lookup Tables]
        SM --> EXP[Expectimax Search Tree]
        EXP <--> TT[16M-Entry Transposition Table]
        EXP --> EVAL[Heuristic Evaluator]
    end

    subgraph Action Layer
        SM -->|Direction 0=UP 1=DOWN 2=LEFT 3=RIGHT| CTRL[pyautogui Controller]
        CTRL -->|Synthetic Drag Gestures| IPM
    end

    IPM -.->|Visual Feedback| SC
```

### Key Files

```
.
├── main.py           # 🚀 Orchestration loop: capture → decide → swipe → repeat
├── solver.c          # ⚡ C99 Expectimax engine (bitboards + LUTs + TT)
├── solver.so         # 📦 Compiled shared library
├── expectimax.py     # 🧠 Python ctypes wrapper + pure Python fallback
├── board_reader.py   # 👁️ Screen capture, Retina scale, 8-point color sampler
├── color_mapper.py   # 🎨 Euclidean color→tile value recognition
├── calibration.py    # 📐 2-click interactive grid calibration
├── controller.py     # 🖱️ pyautogui drag swipe automation
├── game_logic.py     # 🎮 Pure Python 2048 logic (board simulation)
├── debug_tool.py     # 🔍 Visual diagnostic snapshot generator
├── benchmark.py      # 📊 Anti-2048 strategy benchmark (10-game suite)
├── bench.py          # ⏱️ C-engine stress test
├── colors.json       # 💾 Learned RGB → tile value database
└── calibration.json  # 💾 Grid coordinates & step size
```

---

## 🧠 Heuristics & Evaluation Function

The entire heuristic is designed around one principle: **keep tiles small and the board open**, while keeping the big tile anchored in a corner and its twin safely away.

### Row Score (precomputed for all 65,536 possible rows)

| Component | Formula | Purpose |
|---|---|---|
| **Empty cells** | `+900 × N_empty` | Absolute priority — free space is survival |
| **Monotonicity** | `-50 × (Δlog₂)⁴` for non-decreasing steps | Enforces snake/waterfall tile ordering |
| **Smoothness** | `-10 × Σ|log₂(a) - log₂(b)|` for neighbors | Keeps adjacent values compatible for future merges |
| **Adjacent 1024 penalty** | `-50,000` if two 1024s sit side-by-side | Prevents accidental merge via a stray swipe |

### Global Board Penalties

| Check | Penalty | Purpose |
|---|---|---|
| Max tile not in corner `(0,0)` | `-500,000` | Forces stable snake topology — highest tile always anchored |
| Any tile ≥ 2048 on board | `-∞` | **Hard ban**: this state is never allowed to win |

> **Why `-∞` wins over `-500,000`?** Because `-∞` propagates intact through chance nodes (IEEE 754: `-∞ / n = -∞`). A large negative finite number gets averaged with other branches and can look "acceptable". `-∞` cannot.

### Dynamic Search Depth

Depth scales with board congestion. The tighter the board, the further ahead we look:

| Empty Cells | Search Depth | Rationale |
|:---:|:---:|---|
| > 8 | 4 | Open board — quick decisions, many options |
| 4–8 | 6 | Building phase |
| 1–3 | 10 | Critical — one wrong merge can cascade |
| 0 | 14 | Last chance — exhaustive lookahead |

This is especially important for the Anti-2048 strategy where congestion with 1024+1024 is the **permanent state**, not a rare edge case.

---

## ⚙️ Technical Deep Dive

### 1. 64-Bit Bitboard Representation

The 4×4 grid is packed into a single `uint64_t`. Each cell stores `log₂(tile_value)` in 4 bits:

```
Cell value:   0   2   4   8   16  32  64  128  256  512  1024  2048
Stored as:    0   1   2   3    4   5   6    7    8    9    10    11
```

**Board layout in bits:**

```
Cell [row][col]:    [0][0]  [0][1]  [0][2]  [0][3]
Bit positions:      60-63   56-59   52-55   48-51   (row 0)
                    44-47   40-43   36-39   32-35   (row 1)
                    28-31   24-27   20-23   16-19   (row 2)
                    12-15    8-11    4-7     0-3    (row 3)
```

**Encoding formula (row-major, cell `[r][c]` at bit `(r*4 + c) * 4`):**

```c
bitboard |= (log2_value << ((r * 4 + c) * 4));
```

> ⚠️ **Critical implementation detail**: The Python wrapper (`expectimax.py`) must use this same encoding when passing boards to the C solver. An early bug used a reversed encoding (`(3-r)*16 + (3-c)*4`) that effectively rotated the board 180°, causing the solver to plan moves for a mirror image of the real board. This was the root cause of wrong-direction swipes.

### 2. O(1) Matrix Transposition (No Loops)

Vertical moves (Up/Down) are handled by transposing the 64-bit matrix, applying a horizontal move, then transposing back. The transpose is purely bitwise — no array allocation, no loops:

```c
static uint64_t transpose(uint64_t x) {
    uint64_t a1 = x & 0xF0F00F0FF0F00F0FULL;
    uint64_t a2 = x & 0x0000F0F00000F0F0ULL;
    uint64_t a3 = x & 0x0F0F00000F0F0000ULL;
    uint64_t a  = a1 | (a2 << 12) | (a3 >> 12);
    uint64_t b1 = a & 0xFF00FF0000FF00FFULL;
    uint64_t b2 = a & 0x00FF00FF00000000ULL;
    uint64_t b3 = a & 0x00000000FF00FF00ULL;
    return b1 | (b2 >> 24) | (b3 << 24);
}
```

### 3. Row Lookup Tables — 65,536 Entries Each

There are only 2¹⁶ = 65,536 possible 4-cell rows. At startup we precompute three tables for every possible row value:

| Table | Content |
|---|---|
| `row_left_table[65536]` | Result row after sliding & merging left |
| `row_right_table[65536]` | Result row after sliding & merging right |
| `row_eval_table[65536]` | Heuristic score: empty + monotonicity + smoothness + 1024 penalty |

Executing a full board move = **4 table lookups + bit shifts**:

```c
static uint64_t execute_move_left(uint64_t board) {
    uint64_t r = 0;
    for (int i = 0; i < 4; i++) {
        uint16_t row = (board >> (i * 16)) & 0xFFFF;
        r |= (row_left_table[row] << (i * 16));
    }
    return r;
}

// Vertical moves via transpose:
static uint64_t execute_move_up(uint64_t board) {
    uint64_t t = transpose(board);
    return transpose(execute_move_left(t));
}
```

### 4. Expectimax Tree with Chance Nodes

2048 is a non-deterministic game — after each player move, a random tile appears. Minimax doesn't apply. Expectimax models it correctly:

$$V(s) = \begin{cases} \text{Evaluate}(s) & \text{if } \text{depth} = 0 \text{ or terminal} \\ \max_{a} V(\text{move}(s, a)) & \text{player node} \\ \frac{1}{N} \sum_{i} \left(0.9 \cdot V(s \cup 2_i) + 0.1 \cdot V(s \cup 4_i)\right) & \text{chance node} \end{cases}$$

At each chance node we iterate over every empty cell and both spawn probabilities. Pruning: tile-4 branches are skipped at depth ≥ 5 when there are more than 2 empty cells (low-impact branches cut without accuracy loss).

### 5. 16-Million-Entry Transposition Table

```c
#define TT_SIZE (1 << 24)  // 16,777,216 entries

typedef struct {
    uint64_t key;    // full 64-bit board state
    float    value;  // cached evaluation
    int      depth;  // depth at which value was computed
    uint8_t  flag;   // entry valid?
} TTEntry;
```

Hash function: `(board ^ (board >> 32)) & TT_MASK`.  
Reduces redundant subtree evaluations by ~85% in congested mid/late game positions.

### 6. Direction Mapping — Fixed Consistently

All layers use a single agreed encoding:

| Integer | Direction | `controller.py` swipe | `solver.c` move |
|:---:|:---:|---|---|
| `0` | UP | drag up | `execute_move_up()` |
| `1` | DOWN | drag down | `execute_move_down()` |
| `2` | LEFT | drag left | `execute_move_left()` |
| `3` | RIGHT | drag right | `execute_move_right()` |

> This mapping was a persistent source of bugs — early versions had `0=LEFT, 2=RIGHT, 3=UP` in Python but `0=UP, 3=RIGHT` in C, causing the bot to swipe the physically wrong direction on every move.

### 7. Python ↔ C Interface (ctypes)

```python
import ctypes
_lib = ctypes.CDLL("solver.so")
_lib.solver_find_best_move.argtypes = [ctypes.c_uint64, ctypes.c_int]
_lib.solver_find_best_move.restype  = ctypes.c_int

# Board → bitboard using the same C encoding
def board_to_bitboard(board_np):
    bb = 0
    for r in range(4):
        for c in range(4):
            v = int(board_np[r, c])
            if v > 0:
                bb |= ((v.bit_length() - 1) << ((r * 4 + c) * 4))
    return bb

move = _lib.solver_find_best_move(bitboard, empty_cell_count)
```

---

## 👁️ Computer Vision Pipeline

The bot reads the game board entirely from a screenshot — no game API, no source code access.

```
[iPhone Mirroring Window]
        │
        ▼
[screencapture -x -C -t png]   ← macOS native, <10ms, silent
        │
        ▼
[Retina Scale Detection]        ← AppKit.NSScreen: 1x or 2x pixel ratio
        │
        ▼
[8-Point Spatial Sampler]       ← avoids center pixels (contain text/numbers)
  Per cell: sample at ±18px and ±20px offsets from center
        │
        ▼
[Component-wise Median Filter]  ← rejects glare, anti-aliasing noise, text
        │
        ▼
[ColorMapper: Euclidean Match]  ← dist² = (ΔR)²+(ΔG)²+(ΔB)² ≤ 400
        │
      match?──NO──▶ [Interactive prompt → save to colors.json]
        │
       YES
        │
        ▼
  [4×4 tile value matrix]
```

**Calibration** is done once: 2 mouse clicks on top-left and bottom-right cells. The grid step and all 16 cell centers are computed automatically.

**Color learning** is zero-shot: if a new tile color is seen (e.g., 2048 appears for the first time), the bot pauses and asks the user to type the tile value, then remembers it permanently in `colors.json`.

---

## 📊 Performance

### Engine Speed (Apple Silicon)

| Metric | C99 Engine (`solver.so`) | Python fallback (`expectimax.py`) | Speedup |
|---|:---:|:---:|:---:|
| Nodes/sec | **~12,400,000** | ~45,000 | **275×** |
| Move time @ depth 6 | **~0.4 ms** | ~110 ms | **275×** |
| Move time @ depth 10 | **~3.8 ms** | ~1,250 ms | **328×** |
| RAM | **< 400 MB** (16M TT) | > 1.2 GB | **3× less** |

### Strategy Comparison

| Strategy | Goal | Avg Moves | Avg Score | Max Tile |
|---|---|:---:|:---:|:---:|
| Standard solver | Build 2048 ASAP | ~1,100 | ~24,000 | 2048 |
| **This bot (Anti-2048)** | **Delay 2048, farm points** | **3,200+** | **58,000–85,000+** | **1024 + 1024** |

---

## 🛠️ Quick Start

### Prerequisites

- macOS Tahoe or Golden Gate
- Python 3.10+
- Clang or GCC (comes with Xcode Command Line Tools)
- `pipenv` (or plain `pip`)
- iPhone Mirroring with 2048 installed on iPhone

### 1. Install

```bash
git clone https://github.com/your-username/Solver2048.git
cd Solver2048

pipenv install
pipenv shell

# Compile C engine
cc -O3 -shared -fPIC -o solver.so solver.c -lm
```

### 2. macOS Permissions

In *System Settings → Privacy & Security*, grant your terminal app:
- **Screen Recording**
- **Accessibility**

### 3. Calibrate (once)

```bash
python main.py --calibrate
```

Hover over the **center of the top-left cell** → Enter.  
Hover over the **center of the bottom-right cell** → Enter.  
Saves to `calibration.json`.

### 4. Debug / Verify Alignment (optional)

```bash
python main.py --debug
```

Generates `debug_grid.png` with bounding boxes and sample points overlaid.

### 5. Run

```bash
python main.py
```

Switch focus to iPhone Mirroring within 3 seconds. The bot plays autonomously.

---

## ⚙️ CLI Flags

| Flag | Description | Default |
|---|---|:---:|
| `--calibrate` | Interactive 2-click grid calibration | — |
| `--debug` | Generate annotated `debug_grid.png` | — |
| `--show-colors` | Print all learned tile colors | — |
| `--reset-colors` | Clear `colors.json` to relearn colors | — |
| `--depth N` | Override base search depth | `3` |
| `--delay N` | Seconds between swipes | `0.3` |
| `--swipe-distance N` | Drag gesture length in pixels | `120` |

---

## 📜 License

MIT — see [LICENSE](LICENSE).

<div align="center">
  <sub>Built by Roman. Designed for score, not speed.</sub>
</div>
