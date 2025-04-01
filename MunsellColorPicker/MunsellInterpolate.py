import math
from .MunsellFloats import *
from .Utils import *

def munsell_entry_exists(hue, value, chroma):
    try:
        triple = Munsell[int(hue)][int(value)][int(chroma)]
        return color_charted(triple)
    except (IndexError, ValueError):
        return False

def munsell_interpolate(i, j, k):
    
    if not munsell_entry_exists(i,j,k):
        return [0,0,0]
        
    i0 = int(math.floor(i))
    j0 = int(math.floor(j))
    k0 = int(math.floor(k))
    i1 = (i0 + 1) % 40
    j1 = j0 + 1
    k1 = k0 + 1
    a1 = i - i0
    b1 = j - j0
    c1 = k - k0
    a0 = 1 - a1
    b0 = 1 - b1
    c0 = 1 - c1
    ans = [0.0, 0.0, 0.0]
    for t in range(3):
        ans[t] = (
            mul(a0 * b0 * c0, Munsell[i0][j0][k0][t]) +
            mul(a1 * b0 * c0, Munsell[i1][j0][k0][t]) +
            mul(a0 * b1 * c0, Munsell[i0][j1][k0][t]) +
            mul(a1 * b1 * c0, Munsell[i1][j1][k0][t]) +
            mul(a0 * b0 * c1, Munsell[i0][j0][k1][t]) +
            mul(a1 * b0 * c1, Munsell[i1][j0][k1][t]) +
            mul(a0 * b1 * c1, Munsell[i0][j1][k1][t]) +
            mul(a1 * b1 * c1, Munsell[i1][j1][k1][t])
        )
    return [int(max(0, min(255, round(v * 255)))) for v in ans]
