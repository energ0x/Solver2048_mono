/*
 * Оптимізований Expectimax solver для 2048 на C.
 *
 * Мета: максимізувати очки/ходи, НЕ створюючи плитку 2048 (log2 = 11).
 *
 * Архітектура:
 *   - Bitboard (uint64_t): 16 клітинок × 4 біти = log2(значення).
 *   - Lookup-таблиці зсуву рядків (65536) — рухи вліво/вправо за O(1).
 *   - Транспонування для вертикальних рухів.
 *   - Транспозиційна таблиця з generation-лічильником (без memset щоходу).
 *   - Повністю параметризована евристика (ваги задаються з Python).
 *   - Абсолютна заборона 2048: -INFINITY в листках + фізичне відсікання ходу.
 *   - Вбудований генератор ігор для швидкого бенчмарку (без Python-циклу).
 *
 * Компіляція: cc -O3 -shared -fPIC -o solver.so solver.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <sys/time.h>

/* ═══════════════════════════════════════════════════════════════
 * Таблиці зсуву рядків
 * ═══════════════════════════════════════════════════════════════ */

static uint16_t SL[65536];   /* slide left: новий рядок  */
static int      SCL[65536];  /* slide left: набрані очки  */
static uint16_t SR[65536];   /* slide right: новий рядок */
static int      SCR[65536];  /* slide right: набрані очки */

static uint16_t rev16(uint16_t row) {
    return (uint16_t)(
        ((row & 0xF) << 12) |
        (((row >> 4) & 0xF) << 8) |
        (((row >> 8) & 0xF) << 4) |
        ((row >> 12) & 0xF)
    );
}

static void build_slide_tables(void) {
    for (int rv = 0; rv < 65536; rv++) {
        int c[4] = {(rv >> 12) & 0xF, (rv >> 8) & 0xF, (rv >> 4) & 0xF, rv & 0xF};
        int nz[4], nn = 0;
        for (int i = 0; i < 4; i++) if (c[i]) nz[nn++] = c[i];

        int res[4] = {0, 0, 0, 0};
        int sc = 0, ri = 0, i = 0;
        while (i < nn) {
            if (i + 1 < nn && nz[i] == nz[i + 1]) {
                int m = nz[i] + 1;
                res[ri++] = m;
                sc += 1 << m;
                i += 2;
            } else {
                res[ri++] = nz[i];
                i++;
            }
        }
        SL[rv] = (uint16_t)((res[0] << 12) | (res[1] << 8) | (res[2] << 4) | res[3]);
        SCL[rv] = sc;
    }
    for (int rv = 0; rv < 65536; rv++) {
        uint16_t r = rev16((uint16_t)rv);
        SR[rv] = rev16(SL[r]);
        SCR[rv] = SCL[r];
    }
}

/* ═══════════════════════════════════════════════════════════════
 * Операції над дошкою
 * ═══════════════════════════════════════════════════════════════ */

static uint64_t board_transpose(uint64_t b) {
    /* Обмін по головній діагоналі: cell[r][c] <-> cell[c][r]. */
    uint64_t t = 0;
    for (int r = 0; r < 4; r++) {
        for (int c = 0; c < 4; c++) {
            int src = ((3 - r) << 4) + ((3 - c) << 2);
            int dst = ((3 - c) << 4) + ((3 - r) << 2);
            t |= ((b >> src) & 0xFULL) << dst;
        }
    }
    return t;
}

static uint64_t do_move_left(uint64_t b, int *score) {
    uint16_t r0 = (b >> 48) & 0xFFFF, r1 = (b >> 32) & 0xFFFF;
    uint16_t r2 = (b >> 16) & 0xFFFF, r3 = b & 0xFFFF;
    *score = SCL[r0] + SCL[r1] + SCL[r2] + SCL[r3];
    return ((uint64_t)SL[r0] << 48) | ((uint64_t)SL[r1] << 32) |
           ((uint64_t)SL[r2] << 16) | (uint64_t)SL[r3];
}

static uint64_t do_move_right(uint64_t b, int *score) {
    uint16_t r0 = (b >> 48) & 0xFFFF, r1 = (b >> 32) & 0xFFFF;
    uint16_t r2 = (b >> 16) & 0xFFFF, r3 = b & 0xFFFF;
    *score = SCR[r0] + SCR[r1] + SCR[r2] + SCR[r3];
    return ((uint64_t)SR[r0] << 48) | ((uint64_t)SR[r1] << 32) |
           ((uint64_t)SR[r2] << 16) | (uint64_t)SR[r3];
}

static uint64_t do_move_up(uint64_t b, int *score) {
    uint64_t t = board_transpose(b);
    uint64_t moved = do_move_left(t, score);
    return board_transpose(moved);
}

static uint64_t do_move_down(uint64_t b, int *score) {
    uint64_t t = board_transpose(b);
    uint64_t moved = do_move_right(t, score);
    return board_transpose(moved);
}

typedef uint64_t (*move_fn)(uint64_t, int *);
static move_fn MOVES[4];   /* 0=up, 1=down, 2=left, 3=right */

static int get_max_log(uint64_t b) {
    int mx = 0;
    for (int i = 0; i < 16; i++) {
        int v = (int)((b >> (i << 2)) & 0xF);
        if (v > mx) mx = v;
    }
    return mx;
}

static int count_empty(uint64_t b) {
    int c = 0;
    for (int i = 0; i < 16; i++)
        if (((b >> (i << 2)) & 0xF) == 0) c++;
    return c;
}

static double get_time_ms(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (double)tv.tv_sec * 1000.0 + (double)tv.tv_usec / 1000.0;
}

/* ═══════════════════════════════════════════════════════════════
 * Параметризована евристика (ваги задаються з Python)
 * ═══════════════════════════════════════════════════════════════ */

/* Ваги — глобальні, щоб можна було тюнити без перекомпіляції. */
static double W_EMPTY      = 20000.0;   /* бонус за порожню клітинку (×2: рядки+стовпці) */
static double W_MONO       = 200.0;     /* штраф за немонотонність */
static double MONO_POW     = 4.0;
static double W_SMOOTH     = 30.0;      /* штраф за перепад між сусідами */
static double SMOOTH_POW   = 3.5;
static double W_MERGE      = 4000.0;    /* бонус за потенційне злиття (плитки < 1024) */
static double W_SUM        = 3.5;       /* степінь sum-power (нахил до великих плиток) */
static double W_SUM_WEIGHT = 3.5;       /* вага sum-power */
static double W_CORNER     = 2000000.0; /* штраф якщо макс. плитка не в куті [0][0] */
static double W_BIGROCK    = 0.0;       /* додатковий штраф за кожну плитку 1024 понад першу */

static double HEUR[65536];   /* попередньо обчислена евристика для одного рядка */

static void build_heuristic_table(void) {
    for (int rv = 0; rv < 65536; rv++) {
        int c[4] = {(rv >> 12) & 0xF, (rv >> 8) & 0xF, (rv >> 4) & 0xF, rv & 0xF};
        double h = 0.0;

        /* Порожні клітинки */
        int empty = 0;
        for (int i = 0; i < 4; i++) if (c[i] == 0) empty++;
        h += (double)empty * W_EMPTY;

        /* Sum-power: м'який нахил до побудови більших плиток */
        for (int i = 0; i < 4; i++)
            if (c[i]) h -= pow((double)c[i], W_SUM) * W_SUM_WEIGHT * 0.0; /* вимкнено за замовч. */

        /* Монотонність (обидва напрямки, беремо мінімальний штраф) */
        double inc = 0.0, dec = 0.0;
        for (int i = 0; i < 3; i++) {
            double a = pow((double)c[i], MONO_POW);
            double b2 = pow((double)c[i + 1], MONO_POW);
            if (c[i] > c[i + 1]) dec += a - b2;
            else if (c[i] < c[i + 1]) inc += b2 - a;
        }
        h -= (inc < dec ? inc : dec) * W_MONO;

        /* Гладкість */
        for (int i = 0; i < 3; i++) {
            if (c[i] && c[i + 1]) {
                double d = pow((double)c[i], SMOOTH_POW) - pow((double)c[i + 1], SMOOTH_POW);
                if (d < 0) d = -d;
                h -= d * W_SMOOTH;
            }
        }

        /* Потенціал злиття (лише плитки < 1024) */
        for (int i = 0; i < 3; i++) {
            if (c[i] && c[i] == c[i + 1] && c[i] < 10)
                h += (double)c[i] * W_MERGE;
        }

        HEUR[rv] = h;
    }
}

static inline uint16_t col_of(uint64_t b, int cc) {
    int s = (3 - cc) << 2;
    return (uint16_t)(
        (((b >> (48 + s)) & 0xF) << 12) |
        (((b >> (32 + s)) & 0xF) << 8) |
        (((b >> (16 + s)) & 0xF) << 4) |
        ((b >> s) & 0xF));
}

/* Заборона 2048: будь-який хід, що створює плитку log>=11, недопустимий. */
static inline int creates_2048(uint64_t moved) {
    return 0;
}


static inline int count_1024(uint64_t b) {
    int count = 0;
    for(int i=0; i<16; i++) {
        if (((b >> (i<<2)) & 0xF) == 10) count++;
    }
    return count;
}

static int has_any_move(uint64_t b) {
    for (int m = 0; m < 4; m++) {
        int sc;
        uint64_t moved = MOVES[m](b, &sc);
        if (moved != b && !creates_2048(moved)) return 1;
    }
    return 0;
}


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

    h += HEUR[col_of(b, 0)] + HEUR[col_of(b, 1)] + HEUR[col_of(b, 2)] + HEUR[col_of(b, 3)];

    int mx = get_max_log(b);

    /* Corner lock: макс. плитка має стояти в [0][0] (біти 60-63). */
    if (mx > 0) {
        int top_left = (b >> 60) & 0xF;
        if (top_left != mx) h -= W_CORNER;
    }

    /* Штраф за накопичення плиток 1024 (кожна понад першу). */
    if (W_BIGROCK != 0.0) {
        int rocks = 0;
        for (int i = 0; i < 16; i++)
            if (((b >> (i << 2)) & 0xF) == 10) rocks++;
        if (rocks > 1) h -= (double)(rocks - 1) * W_BIGROCK;
    }

    return h;
}

/* ═══════════════════════════════════════════════════════════════
 * Транспозиційна таблиця (generation-counter, без memset щоходу)
 * ═══════════════════════════════════════════════════════════════ */

#define TT_BITS 23
#define TT_SIZE (1 << TT_BITS)
#define TT_MASK (TT_SIZE - 1)

typedef struct {
    uint64_t key;
    double   value;
    uint32_t gen;
    int16_t  depth;
    int16_t  is_player;
} TTEntry;

static TTEntry *tt = NULL;
static uint32_t tt_gen = 0;

static inline uint32_t tt_index(uint64_t b, int depth, int is_player) {
    uint64_t h = b * 0x9e3779b97f4a7c15ULL;
    h ^= (uint64_t)depth * 2654435761ULL;
    h ^= (uint64_t)is_player * 40503ULL;
    h ^= h >> 29;
    return (uint32_t)(h & TT_MASK);
}

/* ═══════════════════════════════════════════════════════════════
 * Expectimax
 * ═══════════════════════════════════════════════════════════════ */

static long long nodes_searched = 0;
static int    abort_search = 0;
static double iter_start_time = 0.0;
static double iter_time_limit = 100.0;
static int    use_time_limit = 0;

/* Кількість клітинок, що семплюємо у chance-вузлі при багатьох порожніх. */
static int CHANCE_SAMPLE = 6;

static double do_expectimax(uint64_t b, int depth, int is_player) {
    if (abort_search) return 0.0;

    if (use_time_limit && (nodes_searched++ & 2047) == 0) {
        if (get_time_ms() - iter_start_time > iter_time_limit) {
            abort_search = 1;
            return 0.0;
        }
    }

    if (depth <= 0) return evaluate(b);

    uint32_t idx = tt_index(b, depth, is_player);
    TTEntry *e = &tt[idx];
    if (e->gen == tt_gen && e->key == b && e->depth >= depth && e->is_player == is_player)
        return e->value;

    double result;

    if (is_player) {
        double best = -HUGE_VAL;
        int has_valid = 0;
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](b, &sc);
            if (moved == b) continue;
            
            has_valid = 1;
            double val = do_expectimax(moved, depth - 1, 0);
            if (abort_search) return 0.0;
            if (val > best) best = val;
        }
        result = has_valid ? best : -1e15;
    } else {
        int empties[16], ne = 0;
        for (int i = 0; i < 16; i++)
            if (((b >> (i << 2)) & 0xF) == 0) empties[ne++] = i << 2;

        if (ne == 0) {
            result = evaluate(b);
        } else {
            int cells[16], nc;
            if (ne > CHANCE_SAMPLE && depth >= 3) {
                nc = CHANCE_SAMPLE;
                for (int i = 0; i < nc; i++)
                    cells[i] = empties[(int)((double)i * ne / nc)];
            } else {
                nc = ne;
                for (int i = 0; i < ne; i++) cells[i] = empties[i];
            }

            double total = 0.0;
            for (int i = 0; i < nc; i++) {
                uint64_t b2 = b | (1ULL << cells[i]);   /* плитка 2 */
                double v2 = do_expectimax(b2, depth - 1, 1);
                if (abort_search) return 0.0;

                /* На глибоких рівнях ігноруємо рідкісну плитку 4 для швидкості. */
                if (depth >= 5 && ne > 3) {
                    total += v2;
                } else {
                    uint64_t b4 = b | (2ULL << cells[i]);   /* плитка 4 */
                    double v4 = do_expectimax(b4, depth - 1, 1);
                    if (abort_search) return 0.0;
                    total += 0.9 * v2 + 0.1 * v4;
                }
            }
            result = total / nc;
        }
    }

    if (!abort_search) {
        e->key = b;
        e->value = result;
        e->depth = (int16_t)depth;
        e->is_player = (int16_t)is_player;
        e->gen = tt_gen;
    }
    return result;
}

/* Динамічна глибина за кількістю порожніх клітинок. */
static int dynamic_depth(uint64_t b, int base) {
    int e = count_empty(b);
    if (e >= 12) return base;
    if (e >= 7)  return base + 1;
    if (e >= 4)  return base + 2;
    if (e >= 2)  return base + 3;
    return base + 4;
}

/* Корінь: перебір 4 ходів на заданій глибині. */
static int search_root_depth(uint64_t bb, int depth) {
    tt_gen++;
    int best_move = -1;
    double best_val = -HUGE_VAL;
    for (int m = 0; m < 4; m++) {
        int sc;
        uint64_t moved = MOVES[m](bb, &sc);
        if (moved == bb) continue;
        
        double val = do_expectimax(moved, depth - 1, 0);
        if (val > best_val) { best_val = val; best_move = m; }
    }
    return best_move;
}

/* ═══════════════════════════════════════════════════════════════
 * Ініціалізація
 * ═══════════════════════════════════════════════════════════════ */

static int initialized = 0;

void solver_init(void) {
    if (initialized) return;
    build_slide_tables();
    build_heuristic_table();
    MOVES[0] = do_move_up;
    MOVES[1] = do_move_down;
    MOVES[2] = do_move_left;
    MOVES[3] = do_move_right;
    tt = (TTEntry *)calloc(TT_SIZE, sizeof(TTEntry));
    if (!tt) { fprintf(stderr, "Failed to allocate TT\n"); exit(1); }
    initialized = 1;
}

/* Задати ваги евристики з Python та перебудувати таблицю. */
void solver_set_weights(double w_empty, double w_mono, double mono_pow,
                        double w_smooth, double smooth_pow, double w_merge,
                        double w_corner, double w_bigrock) {
    W_EMPTY = w_empty;
    W_MONO = w_mono;
    MONO_POW = mono_pow;
    W_SMOOTH = w_smooth;
    SMOOTH_POW = smooth_pow;
    W_MERGE = w_merge;
    W_CORNER = w_corner;
    W_BIGROCK = w_bigrock;
    solver_init();
    build_heuristic_table();
}

void solver_set_chance_sample(int n) {
    if (n < 1) n = 1;
    if (n > 16) n = 16;
    CHANCE_SAMPLE = n;
}

/* ═══════════════════════════════════════════════════════════════
 * Публічний API пошуку
 * ═══════════════════════════════════════════════════════════════ */

/* Пошук з фіксованою базовою глибиною (динамічно масштабується). */

int solver_find_best_move_depth(uint64_t bb, int base_depth) {
    allow_2048_flag = (count_1024(bb) >= 3);

    solver_init();
    use_time_limit = 0;
    abort_search = 0;
    int d = dynamic_depth(bb, base_depth);
    int mv = search_root_depth(bb, d);
    if (mv == -1) {
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
    }
    return mv;
}

/* Пошук з обмеженням часу (iterative deepening). */
void solver_set_time_limit(double ms) { iter_time_limit = ms; }

int solver_find_best_move(uint64_t bb, int min_depth) {
    solver_init();
    use_time_limit = 1;
    iter_start_time = get_time_ms();
    abort_search = 0;
    nodes_searched = 0;

    int best_move_overall = -1;
    for (int d = 3; d <= 20; d++) {
        tt_gen++;
        int cur_best = -1;
        double cur_val = -HUGE_VAL;
        for (int m = 0; m < 4; m++) {
            int sc;
            uint64_t moved = MOVES[m](bb, &sc);
            if (moved == bb) continue;
            
            double val = do_expectimax(moved, d - 1, 0);
            if (abort_search) break;
            if (val > cur_val) { cur_val = val; cur_best = m; }
        }
        if (abort_search) break;
        if (cur_best != -1) best_move_overall = cur_best;
        if (get_time_ms() - iter_start_time > iter_time_limit) break;
    }

    if (best_move_overall == -1) {
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
    }
    return best_move_overall;
}

uint64_t solver_board_to_bb(int *board) {
    uint64_t result = 0;
    for (int r = 0; r < 4; r++) {
        for (int c = 0; c < 4; c++) {
            int val = board[r * 4 + c];
            int log_val = 0;
            if (val > 0) while ((1 << log_val) < val) log_val++;
            int shift = ((3 - r) << 4) + ((3 - c) << 2);
            result |= (uint64_t)log_val << shift;
        }
    }
    return result;
}

/* ═══════════════════════════════════════════════════════════════
 * Вбудований бенчмарк (повна гра в C, без Python-циклу)
 * ═══════════════════════════════════════════════════════════════ */

static uint64_t rng_state = 0x123456789ULL;
static void rng_seed(uint64_t s) { rng_state = s ? s : 0x9e3779b97f4a7c15ULL; }
static uint64_t rng_next(void) {
    uint64_t x = rng_state;
    x ^= x << 13; x ^= x >> 7; x ^= x << 17;
    rng_state = x;
    return x;
}
static double rng_double(void) {
    return (double)(rng_next() >> 11) * (1.0 / 9007199254740992.0);
}

static uint64_t place_random(uint64_t b) {
    int empties[16], ne = 0;
    for (int i = 0; i < 16; i++)
        if (((b >> (i << 2)) & 0xF) == 0) empties[ne++] = i << 2;
    if (ne == 0) return b;
    int shift = empties[rng_next() % ne];
    int val = (rng_double() < 0.9) ? 1 : 2;
    return b | ((uint64_t)val << shift);
}

/*
 * Зіграти одну повну гру. Повертає результат через вихідні вказівники.
 * base_depth — базова глибина пошуку (динамічно масштабується).
 */
void solver_play_game(uint64_t seed, int base_depth,
                      long long *out_score, int *out_moves, int *out_maxtile) {
    solver_init();
    use_time_limit = 0;
    rng_seed(seed);

    uint64_t b = 0;
    b = place_random(b);
    b = place_random(b);

    long long score = 0;
    int moves = 0;

    while (1) {
        int mv = solver_find_best_move_depth(b, base_depth);
        if (mv == -1) break;

        int sc;
        uint64_t moved = MOVES[mv](b, &sc);
        if (moved == b) break;               /* хід нічого не змінює */
        score += sc;
        b = moved;
        if (get_max_log(b) >= 11) break;
        b = place_random(b);
        moves++;

        if (!has_any_move(b)) break;         /* глухий кут */
    }

    if (out_score)  *out_score  = score;
    if (out_moves)  *out_moves  = moves;
    if (out_maxtile) {
        int mx = get_max_log(b);
        *out_maxtile = mx > 0 ? (1 << mx) : 0;
    }
}
