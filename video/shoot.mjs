// Ad-hoc: screenshot specific timestamps (seconds) → frames/shot_<t>.png
//   node shoot.mjs 60 70 88 100 110
import { chromium } from 'playwright';
import { readFile } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { SCENES, FPS, WIDTH, HEIGHT } from './script.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const times = process.argv.slice(2).map(Number);

const { durations, totalVideo } = JSON.parse(await readFile(join(HERE, 'audio/durations.json'), 'utf8'));
let cursor = 0;
const scenes = SCENES.map((s) => { const d = durations[s.id]; const o = { id: s.id, start: cursor, dur: d.total, capDur: d.voice, captions: s.captions }; cursor += d.total; return o; });
const cfg = { fps: FPS, width: WIDTH, height: HEIGHT, total: totalVideo, scenes };

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });
await page.addInitScript((c) => { window.__TIMELINE__ = c; }, cfg);
await page.goto(pathToFileURL(join(HERE, 'composition.html')).href, { waitUntil: 'networkidle' });
await page.waitForFunction('window.__ready === true');
const stage = page.locator('#stage');
for (const t of times) {
  await page.evaluate((tt) => window.__seek(tt), t);
  await stage.screenshot({ path: join(HERE, 'frames', `shot_${t}.png`) });
  console.log('shot', t + 's');
}
await browser.close();
