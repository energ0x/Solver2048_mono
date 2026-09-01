"""Свіп ваг евристики для пошуку конфігурації з максимальним рахунком."""
import ctypes, os, time, sys

_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solver.so')
lib = ctypes.CDLL(_path)
lib.solver_init()
lib.solver_play_game.restype = None
lib.solver_play_game.argtypes = [ctypes.c_uint64, ctypes.c_int,
    ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_int),
    ctypes.POINTER(ctypes.c_int)]
lib.solver_set_weights.restype = None
lib.solver_set_weights.argtypes = [ctypes.c_double] * 8
lib.solver_set_chance_sample.restype = None
lib.solver_set_chance_sample.argtypes = [ctypes.c_int]

# default weights
DEF = dict(w_empty=100000.0, w_mono=47.0, mono_pow=4.0, w_smooth=30.0,
           smooth_pow=3.5, w_merge=700.0, w_corner=500000.0, w_bigrock=0.0)

def set_w(**kw):
    p = dict(DEF); p.update(kw)
    lib.solver_set_weights(*[ctypes.c_double(p[k]) for k in
        ('w_empty','w_mono','mono_pow','w_smooth','smooth_pow','w_merge','w_corner','w_bigrock')])

def play(seed, d):
    s=ctypes.c_longlong(0); m=ctypes.c_int(0); t=ctypes.c_int(0)
    lib.solver_play_game(ctypes.c_uint64(seed), ctypes.c_int(d),
        ctypes.byref(s), ctypes.byref(m), ctypes.byref(t))
    return s.value, m.value, t.value

def evalcfg(cfg, n, d):
    set_w(**cfg)
    sc=[]; mv=[]; hit=0
    for i in range(n):
        s,m,t = play(1+i*7919, d)
        sc.append(s); mv.append(m)
        if t>=2048: hit+=1
    avg=sum(sc)/n; mx=max(sc); amv=sum(mv)/n
    return avg, mx, amv, hit

def run(configs, n=10, d=4):
    print(f"n={n} games, depth={d}")
    best=None
    for name,cfg in configs:
        t0=time.time()
        avg,mx,amv,hit=evalcfg(cfg,n,d)
        el=time.time()-t0
        flag = " ⚠2048" if hit else ""
        print(f"  {name:<28} avg={avg:>7.0f} max={mx:>7} moves={amv:>5.0f} ({el:.0f}s){flag}")
        if best is None or avg>best[1]: best=(name,avg)
    print(f"  BEST: {best[0]} ({best[1]:.0f})")

if __name__=="__main__":
    BEST3 = dict(w_mono=200.0, w_smooth=30.0, w_corner=2000000.0, w_merge=4000.0, w_empty=20000.0)
    configs = [
        ("best3", dict(BEST3)),
        ("best3+empty5k", dict(BEST3, w_empty=5000.0)),
        ("best3+empty0", dict(BEST3, w_empty=0.0)),
        ("best3+empty100k", dict(BEST3, w_empty=100000.0)),
    ]
    run(configs, n=int(sys.argv[1]) if len(sys.argv)>1 else 10,
                 d=int(sys.argv[2]) if len(sys.argv)>2 else 4)
