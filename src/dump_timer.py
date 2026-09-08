import struct, sys, json
import UnityPy
env = UnityPy.load(sys.argv[1])
def name_of(raw):
    if len(raw) < 32: return None
    n = struct.unpack_from("<i", raw, 28)[0]
    if not (0 < n < 96) or 32 + n > len(raw): return None
    try: return raw[32:32+n].decode("ascii")
    except UnicodeDecodeError: return None
for o in env.objects:
    if o.type.name != "MonoBehaviour": continue
    raw = bytes(o.get_raw_data())
    nm = name_of(raw)
    if nm != "TimerData": continue
    n = len(raw)//4
    I = struct.unpack_from("<%di" % n, raw, 0)
    print("TimerData raw ints:", n)
    print("first 40:", I[:40])
    # find where the count 1350 sits, then read triples after it
    for base in range(0, 24):
        if I[base] == 1350:
            print("count 1350 at int index", base)
            trip = [(I[base+1+3*k], I[base+2+3*k], I[base+3+3*k]) for k in range(1350)]
            print("first 12 triples:", trip[:12])
            print("last  6 triples:", trip[-6:])
            bad = [t for t in trip if t[1] != t[0]-1]
            print("triples where mid != level-1:", len(bad), bad[:6])
            json.dump(trip, open("lv/timerdata.json","w"))
            print("wrote lv/timerdata.json")
            break
    break
