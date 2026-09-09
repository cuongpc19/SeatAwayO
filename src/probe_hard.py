import struct, sys, re, collections
import UnityPy
env = UnityPy.load(sys.argv[1])
def name_of(raw):
    if len(raw) < 32: return None
    n = struct.unpack_from("<i", raw, 28)[0]
    if not (0 < n < 96) or 32 + n > len(raw): return None
    try: return raw[32:32+n].decode("ascii")
    except UnicodeDecodeError: return None
named = []
tables = []
for o in env.objects:
    if o.type.name != "MonoBehaviour": continue
    raw = bytes(o.get_raw_data()); n = len(raw)//4
    nm = name_of(raw)
    if nm and re.search(r"hard|zor|difficult|diff", nm, re.I):
        named.append((nm, n))
    if n < 200: continue
    I = struct.unpack_from("<%di" % n, raw, 0)
    # a level column 1,2,3... paired with a column that is only 0/1/2
    for base in range(0, 30):
        c = I[base]
        if not (200 < c < 3000): continue
        for stride in (2, 3, 4):
            if base + 1 + c*stride > n: continue
            col0 = [I[base+1+stride*k] for k in range(min(c, 8))]
            if col0 != list(range(col0[0], col0[0]+len(col0))): continue
            for off in range(1, stride):
                col = [I[base+1+stride*k+off] for k in range(c)]
                if set(col) <= {0,1,2} and len(set(col)) > 1:
                    tables.append((nm, c, stride, off, collections.Counter(col)))
            break
print("MonoBehaviours named hard/difficult:", named or "none")
print()
print("tables pairing a level number with a 0/1/2 column:")
for t in tables: print("   name=%r count=%d stride=%d field=%d  %s" % t)
if not tables: print("   none")
