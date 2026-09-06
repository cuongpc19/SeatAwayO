import UnityPy, json, re
SRC = (r"C:/Users/admin/AppData/Local/Temp/claude/C--Users-admin/"
       r"3beaed4b-e1cd-4d23-aa1b-7645b344a31c/scratchpad/seataway/assets/bin/Data/data.unity3d")
env = UnityPy.load(SRC)
for obj in env.objects:
    if obj.type.name != "TextAsset":
        continue
    d = obj.read()
    if str(getattr(d, "m_Name", "")) != "RemoteConfig":
        continue
    raw = d.m_Script if hasattr(d, "m_Script") else d.script
    if isinstance(raw, str): raw = raw.encode("utf-8", "surrogateescape")
    open("remote_config.json", "wb").write(raw)
    print("RemoteConfig: %d bytes" % len(raw))
    try:
        cfg = json.loads(raw.decode("utf-8", "replace"))
        keys = sorted(cfg) if isinstance(cfg, dict) else []
        print("top-level keys:", len(keys))
        for k in keys:
            if re.search(r"skin|level|unlock|theme|cinema", k, re.I):
                v = cfg[k]
                s = json.dumps(v)
                print("   %-34s %s" % (k, s[:110]))
    except Exception as e:
        print("not json:", e)
        print(raw[:400])
    break
