#!/usr/bin/env python3
import numpy as np

def tiled_ring_offsets(nring, r, pa):
    a, b, c, d = 0.0, 0.5 * np.sqrt(3.0), 0.5, 1.0
    dx = [+b, +a, -b, -b, +a, +b]
    dy = [-c, -d, -c, +c, +d, +c]
    xr = [0.0]
    yr = [0.0]
    for iring in np.arange(1, nring + 1):
        x = 0.0
        y = 1.0 * iring
        for iside in range(6):
            for ipart in range(iring):
                xr.append(x)
                yr.append(y)
                x += dx[iside]
                y += dy[iside]

    xr_a, yr_a = r * np.asarray(xr), r * np.asarray(yr)
    ca, sa = np.cos(pa), np.sin(pa)
    xt = xr_a * ca + sa * yr_a
    yt = -xr_a * sa + ca * yr_a
    return xt, yt

def ring_coordinates(pref, nring, r):
    x, y = tiled_ring_offsets(nring, r, 0)
    return pref.spherical_offsets_by(x, y)
