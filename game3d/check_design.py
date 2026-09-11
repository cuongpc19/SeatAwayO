"""Local visual smoke test; never sends telemetry or changes saved player data."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 960}, device_scale_factor=1)
    errors = []
    page.route('**/*firebasedatabase.app/**', lambda route: route.abort())
    page.route('**/*google-analytics.com/**', lambda route: route.abort())
    page.route('**/*googletagmanager.com/**', lambda route: route.abort())
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8094/game3d/index.html', wait_until='networkidle')
    page.wait_for_function('window.ready === true')
    assert page.title() == 'Seat Fit'
    for width, height, name in [(1440, 960, 'desktop'), (390, 844, 'phone'), (844, 390, 'landscape')]:
        page.set_viewport_size({'width': width, 'height': height})
        page.evaluate("S=null; show('home')")
        assert page.locator('#h-line').evaluate('(e) => e.getBoundingClientRect().bottom <= innerHeight'), 'Home cropped'
        page.screenshot(path=str(HERE / ('preview-home-' + name + '.png')))
        page.locator('#b-play').click()
        page.wait_for_timeout(800)
        page.evaluate("S.phase='review'")
        page.screenshot(path=str(HERE / ('preview-play-' + name + '.png')))
        assert page.evaluate('inFrame()'), 'Board outside safe frame: ' + name
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
        for level in [15, 21, 98, 353, 2085]:
            page.evaluate(f"startLevel({level}); S.phase='review'")
            page.wait_for_timeout(400)
            assert page.evaluate('inFrame()'), f'Level {level} cropped on {name}'
        page.screenshot(path=str(HERE / ('preview-late-' + name + '.png')))
    # Exercise both walking and seated joint poses independently of queue availability.
    result = page.evaluate('''() => {
      const person=buildPeep(2); posePassenger(person,Math.PI/2,false);
      const walking=person.userData.legs.map(x=>x.rotation.x);
      posePassenger(person,0,true);
      const seated=person.userData.legs.map(x=>x.rotation.x);
      const seatedScale=person.scale.toArray();
      person.userData.sat=performance.now()-1000; peepG.add(person); idle(16);
      const settledScale=person.scale.toArray();
      peepG.remove(person);
      return {walking,seated,seatedScale,settledScale,levels:LEVELS.length};
    }''')
    assert result['walking'][0] > 0 and result['walking'][1] < 0
    assert all(abs(x-1.5707963267948966)<0.001 for x in result['seated'])
    assert result['seatedScale'] == result['settledScale'] == [1.48, 1.16, 1.4]
    page.set_viewport_size({'width': 600, 'height': 900})
    page.evaluate('''() => {
      startLevel(3); S.phase='review';
      for(const b of S.seats) for(let k=0;k<b.cap;k++){
        const pc=placeCell(b,k), person=buildPeep(b.colour||2), angle=ROT[b.dir];
        posePassenger(person,0,true);
        person.position.set(wx(S,pc[0])-Math.sin(angle)*0.08,.16,wz(S,pc[1])-Math.cos(angle)*0.08);
        person.rotation.y=angle; peepG.add(person);
      }
      frame(S);
    }''')
    page.wait_for_timeout(400)
    page.screenshot(path=str(HERE / 'preview-seated-fit.png'))
    assert not errors, errors
    print(json.dumps({'status':'ok','poses':result,'errors':errors}))
    browser.close()
