"""Decode LevelCfModel ScriptableObjects out of the Unity bundle.

Binary layout (field names taken from IL2CPP global-metadata.dat, strides
brute-forced and verified to consume all 1303 assets byte-exactly):

    MonoBehaviour header ... m_Name
    int    timeLimit
    int    difficultLevel
    float  camSize
    float  camWinSize
    int    mapSizeW
    int    mapSizeH
    List<MapPosCfModel>     listMapPos      2 ints  (index, enabled)
    List<SeatObjectCfModel> listSeatObject  6 ints  (index, posX, posY, sizeW, direct, colour)
    List<UserObjectCfModel> listUserObject  4 ints  (index, size, colour, hidden)
    List<int>               listGateRow     1 int each
    List<PosLinkCfModel>    listPosLink     jagged  (index, n, links[n])

colour 0 on a seat == grey seat (accepts any colour); user colours are 1..8.
"""
import struct


def parse_level(raw):
    n = len(raw) // 4
    I = struct.unpack_from("<%di" % n, raw, 0)
    i = (32 + ((I[7] + 3) & ~3)) // 4
    d = {
        "timeLimit": I[i],
        "difficultLevel": I[i + 1],
        "camSize": struct.unpack_from("<f", raw, (i + 2) * 4)[0],
        "camWinSize": struct.unpack_from("<f", raw, (i + 3) * 4)[0],
        "mapSizeW": I[i + 4],
        "mapSizeH": I[i + 5],
    }
    p = i + 6
    c = I[p]; p += 1
    d["mapPos"] = [tuple(I[p + 2 * k: p + 2 * k + 2]) for k in range(c)]; p += 2 * c
    c = I[p]; p += 1
    d["seats"] = [tuple(I[p + 6 * k: p + 6 * k + 6]) for k in range(c)]; p += 6 * c
    c = I[p]; p += 1
    d["users"] = [tuple(I[p + 4 * k: p + 4 * k + 4]) for k in range(c)]; p += 4 * c
    c = I[p]; p += 1
    d["gateRow"] = list(I[p:p + c]); p += c
    c = I[p]; p += 1
    links = []
    for _ in range(c):
        idx, m = I[p], I[p + 1]; p += 2
        links.append((idx, list(I[p:p + m]))); p += m
    d["posLink"] = links
    if p != n:
        raise ValueError("parse consumed %d of %d ints" % (p, n))
    return d


def metrics(d):
    """Design-facing numbers for one level."""
    seats, users = d["seats"], d["users"]
    slots = sum(s[3] for s in seats)
    grey = sum(s[3] for s in seats if s[5] == 0)
    colours = sorted({u[2] for u in users})
    seat_colours = sorted({s[5] for s in seats if s[5] != 0})
    holes = sum(1 for m in d["mapPos"] if m[1] == 0)
    cells = d["mapSizeW"] * d["mapSizeH"]
    return {
        "W": d["mapSizeW"], "H": d["mapSizeH"], "cells": cells,
        "playable": cells - holes, "holes": holes,
        "timeLimit": d["timeLimit"], "difficultLevel": d["difficultLevel"],
        "camSize": round(d["camSize"], 2), "camWinSize": round(d["camWinSize"], 2),
        "benches": len(seats), "slots": slots, "guests": len(users),
        "greySlots": grey, "colours": len(colours), "seatColours": len(seat_colours),
        "wideBenches": sum(1 for s in seats if s[3] >= 2),
        "maxBenchSize": max((s[3] for s in seats), default=0),
        "rotatedBenches": sum(1 for s in seats if s[4] != 0),
        "bigGuests": sum(1 for u in users if u[1] >= 2),
        "hiddenGuests": sum(1 for u in users if u[3] == 1),
        "hasGate": int(any(g != -1 for g in d["gateRow"])),
        "density": round(slots / max(cells - holes, 1), 3),
        "guestsPerColour": round(len(users) / max(len(colours), 1), 2),
    }
