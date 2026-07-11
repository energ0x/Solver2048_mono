from expectimax import _HEUR, _WROW
print(f"Max HEUR row score: {max(_HEUR)}")
print(f"Min HEUR row score: {min(_HEUR)}")
print(f"Max WROW score: {max(max(r) for w in _WROW for r in w)}")
