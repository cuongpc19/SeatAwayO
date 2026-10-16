/* ---------------- the 3D renderer ----------------
   Built into the `3d` target only - see build.py. It is appended straight after
   engine.js, inside the same <script>, and replaces exactly these engine
   functions by redeclaration:

       fitCanvas   layout   P   draw   pickWorld   pickCell   pickSeatAt   stopAt

   In one script the LAST `function` declaration of a name is the one every
   caller gets, wherever the call is written, so engine.js itself is not edited
   and the 2D build that ships is untouched. build.py asserts each of the eight
   still exists in engine.js, so a rename there fails the build instead of
   quietly leaving a 2D function in a 3D page.

   Everything else - the rules, the walk and the hop onto the seat, the queue
   stepping up, the jump and the extra lane, the walkthroughs, the result card,
   the clock, the sound, the host SDK - is the shipped game, line for line. This
   file only decides what that game looks like.

   #board stays where it was and becomes a transparent layer over the 3D view.
   The shell paints its rings, washes and coach marks on it through P(), which
   now projects through the 3D camera, so none of that code changes either. The
   WebGL canvas goes underneath it.

   ⚠ Every name of its own lives inside G3. engine.js and game_shell.js already
   own ROOM, view, frame, tick, S and more, and a second `const` of any of them
   is a SyntaxError that takes the whole page down with no message at all. */

const G3 = (function () {
  /* World units. The engine works in cells of SX = 1.60; the 3D models were
     built against cells of 1.16. Everything that crosses between the two goes
     through K, so the engine's coordinates stay exactly the engine's. */
  const GAP = 1.16, CELLW = 0.86, K = GAP / SX;
  /** The one size a passenger is, standing, walking or sitting. ⚠ It used to
      grow by half on landing, which read as somebody inflating in their seat. */
  const PEEP = 1.15;
  const SEAT_Y = 0.16;                     // where a sitting passenger rests

  /* The ORIGINAL's view, and nothing of this file's own. META.yaw and
     META.pitch are the angles the seat atlas was baked at and the 2D draw
     projects with (rotM in engine.js): yaw 0 - straight on, no swing - and a
     pitch of 1.33 rad, which puts the camera 76 degrees up and a little behind
     the seats. Read here rather than copied, so the two cannot drift apart.

     ⚠ Parallel projection, like the 2D draw: a row at the back of the room is
     the same size as a row at the front. A perspective camera at this height
     swells the near rows, which is a different board to look at.

     ?elev=N still tries a height, for comparing on a real screen. */
  const ELEV_ASKED = (e => (e >= 15 && e <= 85 ? e : 0))(
    parseFloat(new URLSearchParams(location.search).get("elev")));
  const ELEV = ELEV_ASKED ? ELEV_ASKED * Math.PI / 180 : META.pitch;
  const YAW = META.yaw || 0;
  const CAM_DIST = 30;                     // parallel projection: only clears the room

  const TONE = [
    { lt: 0xbdc5d4, md: 0x969ca8, dk: 0x575a61 },   // 0  grey   - bolted down
    { lt: 0xff4e5b, md: 0xe83e48, dk: 0x87242a },   // 1  red
    { lt: 0x2cc3ff, md: 0x239be1, dk: 0x145a82 },   // 2  sky
    { lt: 0xfff73a, md: 0xfac42e, dk: 0x91721b },   // 3  yellow
    { lt: 0x5df974, md: 0x4ac65c, dk: 0x2b7335 },   // 4  green
    { lt: 0xffa435, md: 0xfa822a, dk: 0x914b18 },   // 5  orange
    { lt: 0xcc74ff, md: 0xa25cea, dk: 0x5e3588 },   // 6  purple
    { lt: 0x3ab8ff, md: 0x2e92f2, dk: 0x1b558c },   // 7  blue
    { lt: 0xff8dde, md: 0xf470b0, dk: 0x8e4166 },   // 8  pink
    { lt: 0xd4ff5d, md: 0xa8d94a, dk: 0x617e2b },   // 9  lime
    { lt: 0x2fd4c3, md: 0x25a89b, dk: 0x15615a },   // 10 teal
    { lt: 0xde975d, md: 0xb0784a, dk: 0x66462b },   // 11 brown
  ];
  const HUE = {
    plinth: 0x557c78, slab: 0xc5bba5, tileA: 0xede9dc, tileB: 0xdedfd0,
    wall: 0xabc6bc, cap: 0xfff2d9, frame: 0x326e68, glass: 0xa5d9dc,
    rail: 0xcaa66b, step: 0xd8cbb3, sill: 0xe8b94e, table: 0xb99770, lock: 0xd9b64a,
    crate: 0x8a6a48, crateTop: 0xa98a63, strap: 0x5c4732,
  };
  const SKY = 0xa3cbb9;                  // clear colour and fog: the far edge of the ground
  const ROT = [0, -Math.PI / 2, Math.PI, Math.PI / 2];   // a seat's dir, as a turn
  const FACE = { u: 0, d: Math.PI, l: Math.PI / 2, r: -Math.PI / 2 };

  let renderer = null, scene, camera, rootG, roomG, seatG, peepG;
  let built = "", fitKey = "", queued = false, ASPECT = 1;
  const seatMesh = new Map();          // seat id -> group
  const riders = new Map();            // "id:k" -> mesh
  const walkers = new WeakMap();       // engine anim object -> { mesh, hop, dist, x, z }
  let walkerMeshes = new Set();
  let qMeshes = [];                    // [door][place] -> mesh

  /* ---- coordinates ---------------------------------------------------- */
  // engine world (x, z) -> 3D, and back
  const to3 = v => v * K;
  const wx = (g, c) => (c - (g.W - 1) / 2) * GAP;
  const wz = (g, r) => (r - (g.H - 1) / 2) * GAP;

  /* ---- scene ---------------------------------------------------------- */
  function init() {
    if (renderer) return true;
    if (typeof THREE === "undefined") return false;
    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    renderer.setClearColor(SKY, 1);
    if (THREE.ColorManagement) THREE.ColorManagement.enabled = true;
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.06;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    // Underneath #board, in the same box: the CSS gives every canvas inset 0.
    renderer.domElement.setAttribute("aria-hidden", "true");
    /* ⚠ The sky's own colour before the first frame exists. The first render
       compiles every shader the room uses, and until it lands the canvas is
       empty - which, under the hard-level stamp that opens a board, read as a
       white page with words on it. */
    renderer.domElement.style.background = "#" + SKY.toString(16).padStart(6, "0");
    cv.parentNode.insertBefore(renderer.domElement, cv);
    scene = new THREE.Scene();
    // Pushed well past the room: under a parallel camera every part of the room
    // sits at much the same distance, and fog would grey the board evenly.
    scene.fog = new THREE.Fog(SKY, 60, 120);
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 200);
    scene.add(new THREE.HemisphereLight(0xe9f9ff, 0x71836c, 0.85));
    scene.add(new THREE.AmbientLight(0xffffff, 0.14));
    const key = new THREE.DirectionalLight(0xfff0d6, 1.22);
    key.position.set(4, 16, 5);              // from over the camera's shoulder
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.radius = 3;
    key.shadow.bias = -0.0006; key.shadow.normalBias = 0.022;
    const d = 20;
    key.shadow.camera.left = -d; key.shadow.camera.right = d;
    key.shadow.camera.top = d; key.shadow.camera.bottom = -d;
    key.shadow.camera.near = 1; key.shadow.camera.far = 56;
    scene.add(key);
    // ⚠ .position.set(), never Object.assign: position is a read-only accessor.
    const fill = new THREE.DirectionalLight(0x9fc0ff, 0.22);
    fill.position.set(-8, 6, 5); scene.add(fill);
    const rim = new THREE.DirectionalLight(0xbcd6ff, 0.34);
    rim.position.set(-4, 3.5, -9); scene.add(rim);
    backdrop();
    rootG = new THREE.Group(); scene.add(rootG);
    /* Not mirrored. From behind the seats, as the original stands, +x is the
       right of the screen, so the door is on the right and the spare lane on
       the left - where every sentence the game says about sides puts them. */
    return true;
  }

  function gradTex(stops) {
    const c = document.createElement("canvas"); c.width = 8; c.height = 256;
    const x = c.getContext("2d"), g = x.createLinearGradient(0, 0, 0, 256);
    for (const st of stops) g.addColorStop(st[0], st[1]);
    x.fillStyle = g; x.fillRect(0, 0, 8, 256);
    const t = new THREE.CanvasTexture(c);
    t.encoding = THREE.sRGBEncoding;       // ⚠ or colour management bleaches it
    return t;
  }
  function poolTex() {
    const n = 512, c = document.createElement("canvas"); c.width = c.height = n;
    const x = c.getContext("2d");
    const g = x.createRadialGradient(n / 2, n / 2, 0, n / 2, n / 2, n / 2);
    g.addColorStop(0, "#d5eadf"); g.addColorStop(0.36, "#bdddcd");
    g.addColorStop(0.68, "#a5cfba"); g.addColorStop(1, "#91c1aa");
    x.fillStyle = g; x.fillRect(0, 0, n, n);
    const t = new THREE.CanvasTexture(c); t.encoding = THREE.sRGBEncoding; return t;
  }
  /* The ground around the room and the sky over it: mint, picked off three
     renders (A) when the old cream-to-sage read as faded - after the young
     grass (C) was tried in the game and found too bright to sit in front of,
     and A itself then softened: 60% of its saturation, a touch lighter. ⚠ Neither is
     tone-mapped. ACES greys and darkens whatever it is handed, which is right
     for a lit room and wrong for a backdrop whose colour was chosen by eye -
     it was half of why the old one looked washed out. */
  function backdrop() {
    scene.add(new THREE.Mesh(new THREE.SphereGeometry(90, 32, 20),
      new THREE.MeshBasicMaterial({
        map: gradTex([[0, "#f3f9f5"], [0.42, "#cee5da"], [0.76, "#acd2c2"], [1, "#96c3b0"]]),
        side: THREE.BackSide, fog: false, depthWrite: false, toneMapped: false })));
    const ground = new THREE.Mesh(new THREE.CircleGeometry(40, 56),
      new THREE.MeshBasicMaterial({ map: poolTex(), fog: true, toneMapped: false }));
    ground.rotation.x = -Math.PI / 2; ground.position.y = -1.06;
    scene.add(ground);
  }

  /* ---- rounded geometry, cached by size -------------------------------- */
  const GEO = new Map();
  function rbox(w, h, d, r) {
    const k = w.toFixed(3) + "_" + h.toFixed(3) + "_" + d.toFixed(3) + "_" + r.toFixed(3);
    let g = GEO.get(k); if (g) return g;
    r = Math.max(0.004, Math.min(r, w / 2 - 0.002, h / 2 - 0.002, d / 2 - 0.002));
    const sh = new THREE.Shape();
    const x0 = -w / 2 + r, y0 = -h / 2 + r, x1 = w / 2 - r, y1 = h / 2 - r;
    sh.moveTo(x0, -h / 2); sh.lineTo(x1, -h / 2);
    sh.absarc(x1, y0, r, -Math.PI / 2, 0);
    sh.lineTo(w / 2, y1); sh.absarc(x1, y1, r, 0, Math.PI / 2);
    sh.lineTo(x0, h / 2); sh.absarc(x0, y1, r, Math.PI / 2, Math.PI);
    sh.lineTo(-w / 2, y0); sh.absarc(x0, y0, r, Math.PI, Math.PI * 1.5);
    const depth = Math.max(0.002, d - 2 * r);
    g = new THREE.ExtrudeGeometry(sh, { depth, bevelEnabled: true, bevelThickness: r,
      bevelSize: r, bevelSegments: 2, curveSegments: 3, steps: 1 });
    g.translate(0, 0, -depth / 2); g.computeVertexNormals();
    GEO.set(k, g); return g;
  }
  const MAT = new Map();
  function mat(hex, opt) {
    const k = hex + "|" + JSON.stringify(opt || {});
    if (!MAT.has(k)) MAT.set(k, new THREE.MeshStandardMaterial(
      Object.assign({ color: hex, roughness: 0.76, metalness: 0.0 }, opt || {})));
    return MAT.get(k);
  }
  function solid(w, h, d, r, m, shadow) {
    const o = new THREE.Mesh(rbox(w, h, d, r), m);
    if (shadow !== false) { o.castShadow = true; o.receiveShadow = true; }
    return o;
  }
  const tube = (rad, len, m) => new THREE.Mesh(new THREE.CylinderGeometry(rad, rad, len, 12), m);

  /* ---- the room -------------------------------------------------------
     Built for the original's camera, behind the seats: the near end wall (+z)
     is cut low so nothing stands between the camera and the back row; the end
     the seats face (-z, row 0) gets the full height and the windows; the
     garden is out beyond it, at the top of the screen. */
  function buildRoom(g) {
    if (roomG) rootG.remove(roomG);
    roomG = new THREE.Group(); rootG.add(roomG);
    const W = g.W, H = g.H, RX = W * GAP, RZ = H * GAP, HW = RX / 2, HH = RZ / 2;
    const two = g.doors && g.doors.length > 1;

    const plinth = solid(RX + 1.8, 0.5, RZ + 1.5, 0.20, mat(HUE.plinth), false);
    plinth.receiveShadow = true; plinth.userData.deco = true;
    plinth.position.set(0, -0.72, 0); roomG.add(plinth);
    const slab = solid(RX + 0.8, 0.44, RZ + 0.8, 0.15, mat(HUE.slab), false);
    slab.receiveShadow = true; slab.position.y = -0.26; roomG.add(slab);

    for (let r = 0; r < H; r++) for (let c = 0; c < W; c++) {
      // tiles under the hole cells too: the brick wall stands on them
      const t = solid(1.0, 0.09, 1.0, 0.05, mat(((c + r) & 1) ? HUE.tileA : HUE.tileB), false);
      t.receiveShadow = true;
      t.position.set(wx(g, c), 0, wz(g, r));
      roomG.add(t);
    }

    /* The board's own walls: its hole cells, which the 2D game raises into a
       partition (see holeRects in engine.js). This room first left them as a
       gap in the tiles - bare slab, near the floor's colour, so level 25's wall
       down the middle was not there at all - and then as a cream block filling
       the cell, which from this camera is all top and read as more floor.

       Now a brick wall, picked off four renders: thinner than the cell, so it
       stands ON the floor with tiles either side, and its top course two
       staggered rows of terracotta bricks - the one view this camera has of
       it, and a pattern nobody reads as anything but a wall. Merged rectangles
       as the 2D game draws them, so a column of holes is one wall. */
    const BRICK_T = 0.56, BRICK_H = 0.9;
    for (const [c0, r0, c1, r1] of holeRects(g)) {
      const vert = (r1 - r0) >= (c1 - c0);
      const L = (vert ? r1 - r0 + 1 : c1 - c0 + 1) * GAP - 0.1;
      const X = (wx(g, c0) + wx(g, c1)) / 2, Z = (wz(g, r0) + wz(g, r1)) / 2;
      const core = solid(vert ? BRICK_T : L, BRICK_H - 0.12, vert ? L : BRICK_T, 0.04, mat(0xa9573a));
      core.position.set(X, (BRICK_H - 0.12) / 2 - 0.07, Z); roomG.add(core);
      const n = Math.max(2, Math.round(L / 0.42)), bl = L / n;
      for (let row = 0; row < 2; row++) for (let i = 0; i < n + row; i++) {
        const a0 = Math.max(-L / 2 + (i - row * 0.5) * bl, -L / 2), a1 = Math.min(a0 + bl, L / 2);
        if (a1 - a0 < 0.08) continue;              // the half-brick sliver a stagger leaves at an end
        const along = (a0 + a1) / 2, across = (row ? 1 : -1) * BRICK_T / 4;
        const brick = solid(vert ? BRICK_T / 2 - 0.035 : a1 - a0 - 0.035, 0.14,
                            vert ? a1 - a0 - 0.035 : BRICK_T / 2 - 0.035, 0.03,
                            mat((i + row) % 3 ? 0xc8714f : 0xb8603f));
        brick.position.set(X + (vert ? across : along), BRICK_H - 0.12, Z + (vert ? along : across));
        roomG.add(brick);
      }
    }

    const WALLH = 1.34, TH = 0.22;
    function wall(len, vertical, x, z, glass, height) {
      const hh = height || WALLH;
      const m = solid(vertical ? TH : len, hh, vertical ? len : TH, 0.06, mat(HUE.wall));
      m.position.set(x, hh / 2 - 0.07, z); roomG.add(m);
      const cap = solid(vertical ? TH + 0.07 : len + 0.07, 0.10, vertical ? len + 0.07 : TH + 0.07,
                        0.045, mat(HUE.cap));
      cap.position.set(x, hh - 0.07, z); roomG.add(cap);
      if (!glass) return;
      const gm = mat(HUE.glass, { emissive: 0x8dc9cc, emissiveIntensity: 0.12, roughness: 0.22 });
      for (const at of glass) {
        const win = solid(vertical ? 0.05 : 0.58, 0.38, vertical ? 0.58 : 0.05, 0.03, gm, false);
        const off = TH / 2 + 0.012;
        win.position.set(vertical ? x + (x < 0 ? off : -off) : at, hh * 0.60,
                         vertical ? at : z + (z < 0 ? off : -off));
        roomG.add(win);
      }
    }
    const colsAt = [];
    for (let c = 0; c < W; c++) if (c % 2 === 0) colsAt.push(wx(g, c));
    wall(RX + 0.8, false, 0, -HH - 0.25, colsAt);             // the end the seats face, windows
    wall(RX + 0.8, false, 0, HH + 0.25, null, 0.62);          // the near end, low
    for (let k = 0; k < 2; k++) {                             // the long walls, door gaps open
      const x = k ? -HW - 0.25 : HW + 0.25;
      const gap = k === 0 ? g.doors[0][1] : (two ? g.doors[1][1] : -1);
      for (let r = 0; r < H; r++) {
        if (r === gap) continue;
        wall(GAP, true, x, wz(g, r), (!k && r % 2 === 0) ? [wz(g, r)] : null, WALLH);
      }
    }
    /* ⚠ No handrail. One ran down the left wall at shoulder height, and read as
       one from the old diagonal camera; from the original's camera, 76 degrees
       up, it projected straight down across the left-hand column of seats - a
       gold line through the board that is not part of the board. */
    for (let k = 0; k < g.doors.length; k++) doorway(g, k, HW);
    for (const f of (g.fixtures || [])) roomG.add(fixture(g, f));
    garden(RX, RZ);
  }

  /** Scenery beyond the room, never on a puzzle cell - and behind it. */
  function garden(sx, sz) {
    const deco = new THREE.Group(); deco.userData.deco = true; roomG.add(deco);
    const z0 = -sz / 2;                      // -z: the far end, beyond row 0
    const terrace = solid(sx + 3, 0.12, 2.1, 0.12, mat(0xd4c9ae), false);
    terrace.position.set(0, -0.85, z0 - 1.65); terrace.receiveShadow = true; deco.add(terrace);
    const leaves = mat(0x689c7b, { roughness: 0.85 }), tips = mat(0x94b88b);
    for (const sign of [-1, 1]) {
      const x = sign * (sx / 2 + 0.7), z = z0 - 1.0;
      const planter = solid(0.82, 0.58, 0.82, 0.14, mat(0xc08e73));
      planter.position.set(x, -0.5, z); deco.add(planter);
      const trunk = tube(0.075, 0.8, mat(0x997957)); trunk.position.set(x, 0, z); deco.add(trunk);
      for (let i = 0; i < 3; i++) {
        const crown = new THREE.Mesh(new THREE.SphereGeometry(0.48 - i * 0.07, 12, 8), i === 2 ? tips : leaves);
        crown.scale.set(1, 0.9, 0.9); crown.position.set(x + (i === 1 ? 0.17 : 0), 0.40 + i * 0.26, z);
        crown.castShadow = true; deco.add(crown);
      }
    }
  }

  /** A doorway, its step, and the platform the engine's queue stands on.
      ⚠ The platform is laid where stopAt() and queueDir() say the line is -
      those decide where people stand, so the floor under them has to agree. */
  function doorway(g, k, HW) {
    const side = k ? -1 : 1, dz = wz(g, g.doors[k][1]), x = side * (HW + 0.25), hh = 1.34;
    for (const s of [-1, 1]) {
      const post = solid(0.20, hh + 0.16, 0.16, 0.05, mat(HUE.frame));
      post.position.set(x, (hh + 0.16) / 2 - 0.07, dz + s * GAP * 0.54); roomG.add(post);
    }
    const lintel = solid(0.20, 0.16, GAP * 1.18, 0.05, mat(HUE.frame));
    lintel.position.set(x, hh + 0.01, dz); roomG.add(lintel);
    const step = solid(0.94, 0.09, 0.94, 0.05, mat(HUE.tileA), false);
    step.receiveShadow = true;
    step.position.set(wx(g, g.doors[k][0]), 0.005, dz); roomG.add(step);
    const strip = solid(0.12, 0.06, GAP * 0.96, 0.02,
                        mat(HUE.sill, { emissive: HUE.sill, emissiveIntensity: 0.25 }), false);
    strip.position.set(side * (HW - 0.06), 0.075, dz); roomG.add(strip);

    const [lx, lz] = stopAt(g, k), dir = queueDir(g, k), pitch = to3(QUEUE_PITCH);
    const n = Math.min(7, queueOf(g, k).length);
    const len = 1.1 + Math.max(0, n - 1) * pitch;
    const lane = to3(lx);
    // from the doorway out to the lane, then along it
    const reach = Math.abs(lane - x) + 0.6;
    const walk = solid(reach, 0.30, 1.05, 0.12, mat(HUE.step), false);
    walk.receiveShadow = true; walk.userData.deco = true;
    walk.position.set((lane + x) / 2, -0.19, dz); roomG.add(walk);
    const plat = solid(1.35, 0.30, len, 0.12, mat(HUE.step), false);
    plat.receiveShadow = true; plat.userData.deco = true;
    plat.position.set(lane, -0.19, to3(lz) + dir * (len - 1.1) / 2); roomG.add(plat);
  }

  /** An obstacle bolted to its cell: a small table with bottles on it. */
  function fixture(g, f) {
    const grp = new THREE.Group();
    const top = solid(0.82, 0.09, 0.60, 0.04, mat(HUE.table));
    top.position.y = 0.42; grp.add(top);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      const leg = solid(0.08, 0.38, 0.08, 0.03, mat(0x6a7280));
      leg.position.set(sx * 0.32, 0.19, sz * 0.22); grp.add(leg);
    }
    const bottles = [[-0.20, 0x7fbf9a], [0.02, 0xd8dde4], [0.22, 0x7fbf9a]];
    for (let i = 0; i < bottles.length; i++) {
      const b = tube(0.055, 0.20, mat(bottles[i][1], { roughness: 0.3 }));
      b.position.set(bottles[i][0], 0.57, (i % 2 ? 0.07 : -0.06)); b.castShadow = true; grp.add(b);
    }
    grp.position.set(wx(g, f[0]), 0, wz(g, f[1]));
    return grp;
  }

  /* ---- the seat --------------------------------------------------------
     Built facing row 0 (local -z forward), turned by its dir. */
  function buildSeat(b) {
    const grp = new THREE.Group();
    const tag = m => { m.userData.seatId = b.id; grp.add(m); return m; };
    if (isBlock(b)) {
      /* ⚠ Colour 12 is not a colour: it is a crate, a movable obstacle nobody
         can sit in. Drawn as a seat it came out navy - a seat that could never
         be filled, on boards whose places match their queue exactly. */
      for (let k = 0; k < b.len; k++) {
        const off = (k - (b.len - 1) / 2) * GAP;
        const box = solid(0.78, 0.62, 0.78, 0.05, mat(HUE.crate));
        box.position.set(off, 0.31, 0); tag(box);
        const lid = solid(0.82, 0.06, 0.82, 0.03, mat(HUE.crateTop));
        lid.position.set(off, 0.64, 0); tag(lid);
        for (const s of [-1, 1]) {
          const strap = solid(0.08, 0.64, 0.80, 0.02, mat(HUE.strap));
          strap.position.set(off + s * 0.22, 0.32, 0); tag(strap);
        }
      }
      grp.userData.seatId = b.id;
      return grp;
    }
    const t = TONE[b.colour] || TONE[0];
    const L = b.len, w = (L - 1) * GAP + CELLW;
    tag(solid(w * 0.80, 0.11, 0.60, 0.04, mat(t.dk))).position.set(0, 0.065, 0.02);
    tag(solid(w, 0.20, 0.84, 0.085, mat(t.md))).position.set(0, 0.225, -0.01);
    tag(solid(w * 0.88, 0.10, 0.70, 0.05, mat(t.lt))).position.set(0, 0.335, -0.035);
    tag(solid(w, 0.58, 0.20, 0.085, mat(t.md))).position.set(0, 0.51, 0.32);
    tag(solid(w * 0.86, 0.40, 0.11, 0.05, mat(t.lt))).position.set(0, 0.51, 0.225);
    tag(solid(w * 0.95, 0.10, 0.25, 0.045, mat(t.dk))).position.set(0, 0.82, 0.32);
    for (let k = 1; k < b.cap; k++) {
      tag(solid(0.055, 0.17, 0.76, 0.022, mat(t.dk))).position.set((k - b.cap / 2) * (w / b.cap), 0.305, -0.02);
    }
    for (const sx of [-1, 1]) tag(solid(0.11, 0.13, 0.64, 0.05, mat(t.dk))).position.set(sx * (w / 2 + 0.015), 0.385, 0.015);
    if (b.colour === 0) {                      // grey: bolted to the floor, and it shows
      const plate = tag(solid(w + 0.08, 0.05, 0.94, 0.03, mat(0x626b79), false));
      plate.position.set(0, 0.025, 0);
      for (const sx of [-1, 1]) for (const sz of [-1, 1])
        tag(tube(0.05, 0.07, mat(0x99a3b2, { roughness: 0.38 }))).position.set(sx * (w / 2 - 0.10), 0.065, sz * 0.38);
    }
    // the padlock, on the back where the shipped game puts it
    const lockG = new THREE.Group();
    lockG.add(solid(0.20, 0.20, 0.10, 0.05, mat(HUE.lock, { roughness: 0.4 })));
    const sh = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.022, 8, 16, Math.PI),
                              mat(0xcfd6e0, { roughness: 0.35 }));
    sh.position.y = 0.10; lockG.add(sh);
    lockG.position.set(0, 0.58, 0.45);
    lockG.userData.seatId = b.id;
    grp.add(lockG); grp.userData.lock = lockG;
    grp.userData.seatId = b.id;
    return grp;
  }

  /* ---- the passenger ---------------------------------------------------- */
  function peepGeo(kind) {
    const key = "peep_" + kind;
    if (!GEO.has(key)) {
      const sizes = { head: 0.183, eye: 0.021, shine: 0.006, nose: 0.026, hand: 0.051 };
      let geo;
      if (kind === "body") geo = new THREE.CapsuleGeometry(0.17, 0.15, 4, 12);
      else if (kind === "hair") geo = new THREE.SphereGeometry(0.19, 16, 8, 0, Math.PI * 2, 0, 1.2);
      else if (kind === "arm") geo = new THREE.CapsuleGeometry(0.05, 0.12, 3, 8);
      else if (kind === "leg") geo = new THREE.CapsuleGeometry(0.052, 0.055, 3, 8);
      else geo = new THREE.SphereGeometry(sizes[kind], 12, 8);
      GEO.set(key, geo);
    }
    return GEO.get(key);
  }
  function buildPeep(ci) {
    const grp = new THREE.Group();
    const t = TONE[ci] || TONE[0];
    // ⚠ The DEEP tone: a passenger sits in a seat of their own colour, and a body
    // in the cushion's shade vanishes into it.
    const body = new THREE.Mesh(peepGeo("body"), mat(t.dk, { roughness: 0.48 }));
    body.position.y = 0.43; body.castShadow = true; grp.add(body);
    const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.152, 0.176, 0.07, 16), mat(t.lt));
    collar.position.y = 0.555; grp.add(collar);
    const skin = [0xf0cbaa, 0xc48e69, 0xe1ac83][ci % 3];
    const head = new THREE.Mesh(peepGeo("head"), mat(skin, { roughness: 0.58 }));
    head.position.y = 0.72; head.castShadow = true; grp.add(head);
    const hair = new THREE.Mesh(peepGeo("hair"), mat([0x49392f, 0x725238, 0x30343b][ci % 3]));
    hair.position.y = 0.735; grp.add(hair);
    for (const side of [-1, 1]) {
      const eye = new THREE.Mesh(peepGeo("eye"), mat(0x263334));
      eye.position.set(side * 0.059, 0.726, -0.166); grp.add(eye);
      const shine = new THREE.Mesh(peepGeo("shine"), mat(0xffffff));
      shine.position.set(side * 0.059 - 0.004, 0.733, -0.181); grp.add(shine);
    }
    const nose = new THREE.Mesh(peepGeo("nose"), mat(skin));
    nose.position.set(0, 0.686, -0.176); grp.add(nose);
    const arms = [], legs = [], knees = [];
    for (const sx of [-1, 1]) {
      const pivot = new THREE.Group(); pivot.position.set(sx * 0.19, 0.52, 0);
      const a = new THREE.Mesh(peepGeo("arm"), mat(t.dk)); a.position.y = -0.11; a.castShadow = true;
      pivot.add(a);
      const hand = new THREE.Mesh(peepGeo("hand"), mat(skin)); hand.position.y = -0.22; pivot.add(hand);
      grp.add(pivot); arms.push(pivot);
    }
    for (const side of [-1, 1]) {
      const hip = new THREE.Group(); hip.position.set(side * 0.095, 0.30, 0);
      const thigh = new THREE.Mesh(peepGeo("leg"), mat(t.dk)); thigh.position.y = -0.065; hip.add(thigh);
      const knee = new THREE.Group(); knee.position.y = -0.13;
      const shin = new THREE.Mesh(peepGeo("leg"), mat(t.dk)); shin.position.y = -0.055; knee.add(shin);
      const shoe = solid(0.135, 0.075, 0.21, 0.035, mat(0xfaf1dc));
      shoe.position.set(0, -0.12, -0.045); knee.add(shoe);
      hip.add(knee); grp.add(hip); legs.push(hip); knees.push(knee);
    }
    const bag = solid(0.21, 0.24, 0.12, 0.05, mat(t.md));
    bag.position.set(0, 0.43, 0.195); grp.add(bag);
    grp.userData = { ci, arms, legs, knees, bag };
    grp.scale.setScalar(PEEP);
    return grp;
  }
  /** One pose function for every state; ⚠ it never touches the scale. */
  function pose(mesh, phase, seated, tucked) {
    const u = mesh.userData;
    u.bag.visible = !seated;
    for (let i = 0; i < 2; i++) {
      const stride = Math.sin(phase + i * Math.PI);
      u.legs[i].rotation.x = seated ? Math.PI / 2 : tucked ? 0.9 : stride * 0.62;
      u.knees[i].rotation.x = seated ? -Math.PI / 2 : tucked ? -1.2 : -Math.max(0, -stride) * 0.72;
      u.arms[i].rotation.x = seated ? 0.20 : tucked ? -1.1 : -stride * 0.48;
      u.arms[i].rotation.z = (i === 0 ? 1 : -1) * (tucked ? 0.35 : 0.08);
    }
    mesh.rotation.z = seated || tucked ? 0 : Math.sin(phase) * 0.035;
  }

  /* ---- keeping the scene in step with the engine ------------------------ */
  function rebuild(g) {
    buildRoom(g);
    if (seatG) rootG.remove(seatG);
    if (peepG) rootG.remove(peepG);
    seatG = new THREE.Group(); rootG.add(seatG);
    peepG = new THREE.Group(); rootG.add(peepG);
    seatMesh.clear(); riders.clear(); walkerMeshes = new Set(); qMeshes = [];
    for (const b of g.seats) { const m = buildSeat(b); seatG.add(m); seatMesh.set(b.id, m); }
    fitKey = "";
    // Compile now, while the board is being put up, rather than inside the
    // first frame somebody is looking at. A no-op for programs already built.
    renderer.compile(scene, camera);
  }

  function syncSeats(g) {
    const held = HELD && HELD.moved ? HELD.seat : null;
    const live = new Set();
    for (const b of g.seats) {
      const m = seatMesh.get(b.id); if (!m) continue;
      let [sx, sz] = seatCentre(b);
      let y = 0;
      if (b === held) { sx += HELD.dx; sz += HELD.dz; y = 0.22; }
      else if (g.sel === b) y = 0.12;
      m.position.set(to3(sx), y, to3(sz));
      m.rotation.y = ROT[b.dir];
      if (m.userData.lock) m.userData.lock.visible = !!b.chain;
      // the people sitting in it, and the wave that runs across them on a win
      b.occ.forEach((ci, k) => {
        if (ci == null) return;
        const key = b.id + ":" + k;
        let p = riders.get(key);
        if (!p || p.userData.ci !== ci) {
          if (p) peepG.remove(p);
          p = buildPeep(ci); p.userData.seatId = b.id;
          peepG.add(p); riders.set(key, p); pose(p, 0, true);
        }
        live.add(key);
        let [px, pz] = placeAt(b, k);
        const [c, r] = placeCell(b, k);
        if (b === held) { px += HELD.dx; pz += HELD.dz; }
        const f = ROT[b.dir];
        p.position.set(to3(px) - Math.sin(f) * 0.08, SEAT_Y + y + to3(cheerLift(c, r)) * 1.4,
                       to3(pz) - Math.cos(f) * 0.08);
        p.rotation.y = f;
      });
    }
    for (const [key, p] of riders) if (!live.has(key)) { peepG.remove(p); riders.delete(key); }
  }

  function syncWalkers(g) {
    const seen = new Set();
    for (const a of g.anim) {
      let w = walkers.get(a);
      if (!w) {
        w = { mesh: buildPeep(a.ci), hop: false, dist: 0, x: a.x, z: a.z };
        peepG.add(w.mesh); walkers.set(a, w); walkerMeshes.add(w.mesh);
      }
      seen.add(w.mesh);
      w.dist += Math.hypot(a.x - w.x, a.z - w.z); w.x = a.x; w.z = a.z;
      /* The hop onto the seat is the only time a walker leaves the ground by
         more than the walking bob (.10), so a peak over that marks it - and it
         never goes back to walking. The landing half then rises to seat height,
         so the hand-over to the seated figure happens at the same height. */
      const y0 = a.y || 0;
      if (y0 > 0.15) w.hop = true;
      const landing = w.hop && a.phase === 3;
      w.mesh.position.set(to3(a.x), 0.02 + to3(y0) * 1.5 + (landing ? SEAT_Y * (1 - y0 / 0.42) : 0), to3(a.z));
      w.mesh.rotation.y = FACE[a.facing] != null ? FACE[a.facing] : 0;
      pose(w.mesh, w.dist / STRIDE * Math.PI, false, w.hop);
    }
    for (const m of walkerMeshes) if (!seen.has(m)) { peepG.remove(m); walkerMeshes.delete(m); }
  }

  /** The line at each door, placed exactly as the 2D draw() placed it: the
      places still to walk, the drift that makes a narrow board's line a crowd,
      and the glance off down the platform. */
  function syncQueues(g) {
    const now = performance.now();
    const doors = g.doors ? g.doors.length : 1;
    for (let dk = 0; dk < doors; dk++) {
      const q = queueOf(g, dk);
      const [lx0, lz] = stopAt(g, dk), dir = queueDir(g, dk);
      const row = qMeshes[dk] || (qMeshes[dk] = []);
      for (let i = 0; i < 7; i++) {
        let m = row[i];
        if (i >= q.length) { if (m) m.visible = false; continue; }
        if (!m || m.userData.ci !== q[i]) {
          if (m) peepG.remove(m);
          m = row[i] = buildPeep(q[i]); peepG.add(m);
        }
        m.visible = true;
        const st = g.qsteps && g.qsteps[dk] && g.qsteps[dk][i];
        const back = st ? placesBack(st, now) : 0;
        const walking = back > 1e-3 && now >= st.t0;
        const f = Math.max(0, Math.min(1, back));
        const dA = queueDrift(g, dk, i), dB = queueDrift(g, dk, i + 1);
        const x = lx0 + dA[0] * (1 - f) + dB[0] * f;
        const z = lz + (i + back) * QUEUE_PITCH * dir + dA[1] * (1 - f) + dB[1] * f;
        m.position.set(to3(x), 0.02, to3(z));
        // facing the door they are waiting for; a glance turns them down the platform
        const gl = walking ? null : glanceAt(g, dk, i, now);
        const toDoor = dir > 0 ? 0 : Math.PI;
        m.rotation.y = gl ? toDoor + (gl === "l" ? 0.9 : -0.9) : toDoor;
        pose(m, walking ? (st.from - back) * QUEUE_PITCH / STRIDE * Math.PI : 0, false, false);
      }
    }
  }

  /* ---- the camera -------------------------------------------------------
     As close as it can stand while every corner of the room - and the head of
     each line - stays inside the frame and clear of the HUD. The HUD only eats
     height, and how much is measured off the top bar and the booster row. */
  const BOX = new THREE.Box3();
  function limits() {
    const r = cv.getBoundingClientRect(), W = r.width || 1, H = r.height || 1, EDGE = 6;
    const bar = document.querySelector("#play .topbar"), bst = document.getElementById("boosters");
    let top = 0, bot = 0;
    if (bar) { const b = bar.getBoundingClientRect(); top = Math.max(0, b.bottom - r.top); }
    if (bst) { const b = bst.getBoundingClientRect(); bot = Math.max(0, r.bottom - b.top); }
    return { x: 1 - EDGE * 2 / W, hi: 1 - (top + EDGE) * 2 / H, lo: -1 + (bot + EDGE) * 2 / H };
  }
  const ROOMBOX = new THREE.Box3();
  function fit(g) {
    BOX.makeEmpty();
    for (const ch of roomG.children) if (!ch.userData.deco) BOX.expandByObject(ch);
    ROOMBOX.copy(BOX);
    // the head of each line, so a short board does not throw it off the side
    // ⚠ Through rootG: these are room coordinates, and the room is mirrored.
    for (let dk = 0; dk < (g.doors ? g.doors.length : 1); dk++) {
      const [lx, lz] = stopAt(g, dk);
      BOX.expandByPoint(rootG.localToWorld(new THREE.Vector3(to3(lx) + 0.3, 1.0, to3(lz))));
      BOX.expandByPoint(rootG.localToWorld(new THREE.Vector3(to3(lx) - 0.3, 0, to3(lz))));
    }
    const cx = (BOX.max.x + BOX.min.x) / 2, cz = (BOX.max.z + BOX.min.z) / 2;
    // Behind the seats (+z) and up at the atlas's pitch, turned by its yaw.
    camera.position.set(cx + CAM_DIST * Math.cos(ELEV) * Math.sin(YAW),
                        CAM_DIST * Math.sin(ELEV),
                        cz + CAM_DIST * Math.cos(ELEV) * Math.cos(YAW));
    camera.lookAt(cx, 0, cz);
    camera.updateMatrixWorld(true);
    /* Solved, not searched. A parallel projection is linear, so the frame that
       holds the room as large as the free band allows - between the top bar and
       the booster row - comes straight out of the box's extent in camera space:
       the half-height h that fits both axes, and an offset that centres the
       room in the BAND rather than in the screen. The HUD is heavier at the
       bottom, and centring on the screen would leave the top of the band empty. */
    const L = limits(), inv = camera.matrixWorldInverse, P0 = new THREE.Vector3();
    const span = box => {
      let a0 = Infinity, a1 = -Infinity, b0 = Infinity, b1 = -Infinity;
      for (let i = 0; i < 8; i++) {
        P0.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z)
          .applyMatrix4(inv);
        a0 = Math.min(a0, P0.x); a1 = Math.max(a1, P0.x); b0 = Math.min(b0, P0.y); b1 = Math.max(b1, P0.y);
      }
      return [a0, a1, b0, b1];
    };
    const [x0, x1, y0, y1] = span(BOX);                  // the room AND the head of each line
    const [r0, r1] = span(ROOMBOX);                      // the room on its own
    const h = Math.max((x1 - x0) / 2 / (ASPECT * L.x), (y1 - y0) / (L.hi - L.lo), 0.5);
    /* ⚠ Across, the ROOM goes in the middle of the screen, not the room and its
       queue together. The booster row is centred on the screen, as it is in the
       2D game, and the line stands off to one side of the room - so centring the
       pair pushed the room 66px left of the boosters on a wide screen and it read
       as lopsided. The room is moved towards the middle only as far as the frame
       allows at this same size, so nothing shrinks to pay for it: where height is
       the limit there is slack across and the room centres exactly; on an upright
       phone, where width is the limit, it stays where it was. */
    const slack = h * ASPECT * L.x;
    const ox = Math.min(Math.max((r0 + r1) / 2, x1 - slack), x0 + slack);
    const oy = (y0 + y1) / 2 - h * (L.hi + L.lo) / 2;
    camera.left = ox - h * ASPECT; camera.right = ox + h * ASPECT;
    camera.top = oy + h; camera.bottom = oy - h;
    camera.updateProjectionMatrix();
  }

  function size() {
    const r = cv.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.max(240, Math.round(r.width)), h = Math.max(240, Math.round(r.height));
    renderer.setPixelRatio(dpr);
    renderer.setSize(w, h, false);
    ASPECT = w / h;                       // a parallel camera keeps it in its frustum
    return w + "x" + h;
  }

  /* ---- one render a frame, however many times the engine asks ----------
     The engine calls draw() from every animation it runs - the walk, the
     queue, the finale - often several times in one frame. The scene is
     brought up to date and drawn once, on the next frame. */
  function render() {
    queued = false;
    const g = S; if (!g || !init()) return;
    const key = g.token + ":" + g.W + "x" + g.H;
    if (key !== built) { rebuild(g); built = key; }
    const sk = size() + ":" + key;
    if (sk !== fitKey) { fit(g); fitKey = sk; }
    syncSeats(g); syncWalkers(g); syncQueues(g);
    renderer.render(scene, camera);
    /* ⚠ LAY again, now the camera has been fitted. draw() worked it out before
       this frame's fit, so on a fresh board its scale was read off a camera
       still parked at the origin - and every ring the shell paints is sized by
       it. */
    LAY = layout();
    // the shell's own marks, on the layer above
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (g.sel) for (const [c, r] of cellsOf(g.sel)) {
      ctx.save(); ctx.globalAlpha = .30; quad(tileQuad(c, r, .016), "#ffe9a8"); ctx.restore();
    }
    onOverlay(g);
  }
  function request() { if (!queued) { queued = true; requestAnimationFrame(render); } }

  /* ---- projection and picking ------------------------------------------- */
  const V = () => new THREE.Vector3();
  function project(x, y, z) {
    if (!renderer || !S) return [0, 0, 0];
    const v = V().set(to3(x), to3(y), to3(z));
    rootG.localToWorld(v);
    const d = v.distanceTo(camera.position);
    v.project(camera);
    return [(v.x * .5 + .5) * cv.width, (-v.y * .5 + .5) * cv.height, -d];
  }
  const ray = new THREE.Raycaster(), NDC = new THREE.Vector2();
  const FLOOR = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  function aim(cx, cy) {
    const r = cv.getBoundingClientRect();
    NDC.set((cx - r.left) / r.width * 2 - 1, -((cy - r.top) / r.height * 2 - 1));
    ray.setFromCamera(NDC, camera);
  }
  function floor(cx, cy) {
    if (!renderer) return null;
    aim(cx, cy);
    const hit = V();
    if (!ray.ray.intersectPlane(FLOOR, hit)) return null;
    rootG.worldToLocal(hit);
    return [hit.x / K, hit.z / K];
  }
  function seatHit(cx, cy) {
    if (!renderer || !seatG) return null;
    aim(cx, cy);
    const hits = ray.intersectObjects([seatG, peepG], true);
    for (const h of hits) {
      for (let o = h.object; o; o = o.parent) {
        if (o.userData && o.userData.seatId != null) return S.seats[o.userData.seatId] || null;
      }
    }
    return null;
  }

  return { init, size, render, request, project, floor, seatHit,
           scale() {
             // pixels per engine unit at the middle of the room, for the overlay's ring sizes
             if (!renderer || !S) return 1;
             const a = project(0, 0, 0), b = project(SX, 0, 0);
             return Math.max(1e-3, Math.hypot(b[0] - a[0], b[1] - a[1]) / SX);
           } };
})();

/* ======================= the eight engine functions ===================== */

/** Where a door's line waits. Both lines stand LANE_NEAR off their wall here.
    engine.js pulls the far one in to LANE_FAR, which is what keeps the 2D board
    its size - but in this room it laid the far platform over the plinth, a
    third of a cell onto the frame, on every board with a second door (level 26
    first), while the near one stood clear of it. One distance, so the two
    platforms mirror. The queue, the platform under it, the walk in and the
    camera's box all read this, so they move together. */
function stopAt(g, k) {
  const [dc, dr] = doorCell(g, k);
  return [cellW(dc) + (dc === 0 ? -SX : SX) * LANE_NEAR, cellZ(dr)];
}

/** The overlay canvas keeps its own resolution; the 3D view sizes itself. */
function fitCanvas(g) {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const w = Math.max(320, Math.round(cv.clientWidth * dpr));
  const h = Math.max(320, Math.round(cv.clientHeight * dpr));
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
}

/** The same shape the 2D layout returned. x0/z0 are what cellW and cellZ read,
    and they put the middle of the board at the origin exactly as before; s is
    pixels per world unit, which the shell's rings are sized by. */
function layout() {
  const g = S;
  const x0 = -(g.W - 1) / 2 * SX, z0 = -(g.H - 1) / 2 * SZ;
  if (!G3.init()) return { s: 1, ox: 0, oy: 0, x0, z0 };
  const o = G3.project(0, 0, 0);
  return { s: G3.scale(), ox: o[0], oy: o[1], x0, z0 };
}

function P(x, y, z) { return G3.project(x, y, z); }

function draw() {
  if (!S) return;
  fitCanvas(S);
  LAY = layout();
  // ⚠ Advanced here, synchronously: finale()'s loop reads FIN.f straight after
  // calling draw() to decide whether to go on, so it cannot wait for the frame.
  if (FIN) FIN.f = Math.min(1, (performance.now() - FIN.t0) / FIN.ms);
  S.nextSeat = (nextUp(S) || {}).spot || null;
  G3.request();
  scheduleGlance(S);
}

/** Where the pointer is on the floor, in engine world units. */
function pickWorld(clientX, clientY) { return G3.floor(clientX, clientY); }

function pickCell(clientX, clientY) {
  const w = G3.floor(clientX, clientY);
  if (!w || !LAY) return null;
  const col = Math.round((w[0] - LAY.x0) / SX), row = Math.round((w[1] - LAY.z0) / SZ);
  if (col < 0 || col >= S.W || row < 0 || row >= S.H) return null;
  return [col, row];
}

/** The seat under the pointer: its model or anybody sitting in it, nearest
    first, and the floor cell under the pointer when the ray misses both. */
function pickSeatAt(clientX, clientY) {
  const hit = G3.seatHit(clientX, clientY);
  if (hit) return hit;
  const cell = pickCell(clientX, clientY);
  return cell ? seatAt(S, cell[0], cell[1]) : null;
}
