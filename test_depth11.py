import ctypes
import time
solver = ctypes.CDLL('./solver.so')
solver.solver_play_game.argtypes = [
    ctypes.c_uint64, ctypes.c_int,
    ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
]

score = ctypes.c_longlong(0)
moves = ctypes.c_int(0)
maxtile = ctypes.c_int(0)
t0 = time.time()
solver.solver_play_game(777, 11, ctypes.byref(score), ctypes.byref(moves), ctypes.byref(maxtile))
t1 = time.time()
print(f"Depth 11: score={score.value}, moves={moves.value}, max={maxtile.value} ({t1-t0:.1f}s)")
