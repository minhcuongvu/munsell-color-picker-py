import math

def mul(factor, maybe_number):
    if factor == 0 or maybe_number is None or math.isnan(maybe_number):
        return 0.0
    return factor * maybe_number

def color_charted(triple):
    return all(isinstance(value, (int, float)) and not math.isnan(value) for value in triple)

def srgb_coords(triple):
    ans = [round(c * 255) for c in triple]
    return [0, 0, 0] if any(c < 0 or c > 255 for c in ans) else ans

def color_valid(triple):
    srgb = srgb_coords(triple)
    return all(0 <= value <= 255 for value in srgb)

def chroma_map(k):
    return k / 26.0

def lightness_map(j):
    if j < 5:
        return j * 0.02
    else:
        return (j - 4) / 10.0
