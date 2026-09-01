import ctypes
import time
solver = ctypes.CDLL('./solver.so')
solver.solver_play_game.argtypes = [
    ctypes.c_uint64, ctypes.c_int,
    ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
]

print("Running pure test, breaking ONLY on exactly 2048.")
# Note: we need to compile solver.c with a strict break on 2048 to see the "Monobank" score.
