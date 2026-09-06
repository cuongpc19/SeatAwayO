"""Cut game3_tpl.html into a shared engine and an editor shell.

The engine holds everything that IS the game - projection, rules, boarding,
drawing, input. It never touches the surrounding page except through three
hooks a shell fills in. The editor keeps its instrument panel; the real game
gets its own shell over the same engine, so a rule only ever exists once.
"""
import re, io

src = open("game3_tpl.html", encoding="utf-8").read()
head, rest = src.split("<script>\n", 1)
body, _tail = rest.split("\n</script>", 1)

# --- where the engine stops and the page chrome begins -------------------
CUT = body.index("/* ---------------- hud ---------------- */")
engine, shell = body[:CUT], body[CUT:]

# the data slots stay in the shell-specific build step, not the engine file
engine = engine.split("const NAMES =", 1)
DATA = engine[0]
engine = "const NAMES =" + engine[1]

# --- say()/finish() are page-specific; route them through hooks ----------
engine = engine.replace('''let sayUntil = 0;
function say(msg) {
  document.getElementById("hint").textContent = msg;
  sayUntil = performance.now() + 2600;      // hud() leaves the hint alone until then
}''', '''/* The three things only the surrounding page can answer. A shell assigns
   these; the engine never reaches into the DOM around the canvas itself. */
let onHud = () => {};
let onSay = () => {};
let onFinish = () => {};
function say(msg) { onSay(msg); }''')

engine = engine.replace('''function finish(won) {
  S.phase = won ? "win" : "lose";
  document.getElementById("ov-title").textContent = won ? "Level complete" : "Out of time";
  document.getElementById("ov-text").textContent = won
    ? "Everyone seated with " + fmt(S.left) + " left, in " + S.moves + " seat moves."
    : "The bus pulled away with " + S.queue.length + " still at the stop.";
  document.getElementById("ov-next").style.display = won ? "" : "none";
  document.getElementById("ov").classList.add("on");
}''', '''function finish(won) {
  S.phase = won ? "win" : "lose";
  onFinish(won);
}
function fmt(sec) { sec = Math.max(0, Math.ceil(sec));
  return Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0"); }''')

engine = re.sub(r'\bhud\(\)', 'onHud()', engine)

# --- the editor shell ----------------------------------------------------
shell = shell.replace("/* ---------------- hud ---------------- */\n", "")
shell = shell.replace('function fmt(sec) { sec = Math.max(0, Math.ceil(sec)); return Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0"); }\n', "")
shell = shell.replace("function hud() {", "onHud = function hud() {")
shell = re.sub(r'^\}\ndocument\.getElementById\("b-retry"\)', '};\ndocument.getElementById("b-retry")', shell, flags=re.M)

# the trace button had been spliced inside the guides handler by an earlier patch
shell = shell.replace('''document.getElementById("b-guides").onclick = ev => {
  GUIDES = !GUIDES;
document.getElementById("b-trace").onclick = e => {
  TRACING = !TRACING;
  e.target.textContent = "Trace " + (TRACING ? "on" : "off");
  document.getElementById("trace").hidden = !TRACING;
};
  ev.target.textContent = GUIDES ? "Guides on" : "Guides off";
  draw();
};''', '''document.getElementById("b-guides").onclick = ev => {
  GUIDES = !GUIDES;
  ev.target.textContent = GUIDES ? "Guides on" : "Guides off";
  draw();
};
document.getElementById("b-trace").onclick = e => {
  TRACING = !TRACING;
  e.target.textContent = "Trace " + (TRACING ? "on" : "off");
  document.getElementById("trace").hidden = !TRACING;
};''')

# the editor's own say(), and the end-of-level card it already had
shell = '''let sayUntil = 0;
onSay = msg => {
  document.getElementById("hint").textContent = msg;
  sayUntil = performance.now() + 2600;      // hud() leaves the hint alone until then
};
onFinish = won => {
  document.getElementById("ov-title").textContent = won ? "Level complete" : "Out of time";
  document.getElementById("ov-text").textContent = won
    ? "Everyone seated with " + fmt(S.left) + " left, in " + S.moves + " seat moves."
    : "The bus pulled away with " + S.queue.length + " still at the stop.";
  document.getElementById("ov-next").style.display = won ? "" : "none";
  document.getElementById("ov").classList.add("on");
};
''' + shell

open("engine.js", "w", encoding="utf-8").write(engine.strip() + "\n")
open("editor_shell.js", "w", encoding="utf-8").write(shell.strip() + "\n")
open("editor_head.html", "w", encoding="utf-8").write(head.rstrip() + "\n")
open("data_slots.js", "w", encoding="utf-8").write(DATA.strip() + "\n")
for f in ("engine.js", "editor_shell.js", "editor_head.html", "data_slots.js"):
    print("%-20s %6d bytes" % (f, len(open(f, encoding="utf-8").read())))
