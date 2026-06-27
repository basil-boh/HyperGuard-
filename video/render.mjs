// Renders composition.html to PNG frames by seeking the GSAP master timeline
// in headless Chromium, then assembles the ElevenLabs voiceover + ambient bed
// and encodes the final MP4 with ffmpeg.
//
//   node render.mjs            # full render
//   node render.mjs --probe    # render just a few sample frames for a quick look
//
import { chromium } from 'playwright';
import { readFile, writeFile, mkdir, rm, readdir } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';
import { SCENES, FPS, WIDTH, HEIGHT } from './script.mjs';

const exec = promisify(execFile);
const HERE = dirname(fileURLToPath(import.meta.url));
const FRAMES = join(HERE, 'frames');
const AUDIO = join(HERE, 'audio');
const OUT = join(HERE, 'out');
const PROBE = process.argv.includes('--probe');

const pad = (n, w = 5) => String(n).padStart(w, '0');
const ff = (args) => exec('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...args]);

async function buildConfig() {
  const { durations, totalVideo } = JSON.parse(await readFile(join(AUDIO, 'durations.json'), 'utf8'));
  let cursor = 0;
  const scenes = SCENES.map((s) => {
    const d = durations[s.id];
    const scene = { id: s.id, start: cursor, dur: d.total, capDur: d.voice, captions: s.captions };
    cursor += d.total;
    return scene;
  });
  return { fps: FPS, width: WIDTH, height: HEIGHT, total: totalVideo, scenes };
}

async function renderFrames(cfg) {
  await rm(FRAMES, { recursive: true, force: true });
  await mkdir(FRAMES, { recursive: true });

  const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
  const page = await browser.newPage({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
  });
  await page.addInitScript((c) => { window.__TIMELINE__ = c; }, cfg);
  await page.goto(pathToFileURL(join(HERE, 'composition.html')).href, { waitUntil: 'networkidle' });
  await page.waitForFunction('window.__ready === true', { timeout: 30000 });

  const stage = page.locator('#stage');
  const total = await page.evaluate('window.__duration');
  const totalFrames = Math.round(total * cfg.fps);
  console.log(`rendering ${totalFrames} frames @ ${cfg.fps}fps (${total.toFixed(2)}s)`);

  const frameList = PROBE
    ? [0, 30, 70, 120, 200, 320, 460, 600, 760, 900, 1050, 1200, totalFrames - 5].filter((f) => f < totalFrames)
    : Array.from({ length: totalFrames }, (_, i) => i);

  let done = 0;
  for (const f of frameList) {
    await page.evaluate((t) => window.__seek(t), f / cfg.fps);
    await stage.screenshot({ path: join(FRAMES, `${pad(PROBE ? done : f)}.png`), animations: 'disabled' });
    done++;
    if (done % 60 === 0 || done === frameList.length) {
      process.stdout.write(`\r  ${done}/${frameList.length} frames`);
    }
  }
  process.stdout.write('\n');
  await browser.close();
  return totalFrames;
}

async function buildAudio(cfg) {
  // Per scene: voice clip padded with silence to the scene's full duration, then concat.
  const segs = [];
  for (const s of cfg.scenes) {
    const inMp3 = join(AUDIO, `${s.id}.mp3`);
    const outWav = join(AUDIO, `_seg_${s.id}.wav`);
    await ff(['-i', inMp3, '-af', `apad,atrim=0:${s.dur}`, '-ar', '44100', '-ac', '2', outWav]);
    segs.push(outWav);
  }
  const listFile = join(AUDIO, '_concat.txt');
  await writeFile(listFile, segs.map((s) => `file '${s}'`).join('\n'));
  const voiceTrack = join(AUDIO, '_voice.wav');
  await ff(['-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', voiceTrack]);

  // Subtle ambient bed: two soft low sines, lowpassed, slow tremolo, very low volume, faded.
  const bed = join(AUDIO, '_bed.wav');
  const T = cfg.total;
  await ff([
    '-f', 'lavfi', '-i', `sine=frequency=110:duration=${T}`,
    '-f', 'lavfi', '-i', `sine=frequency=164.81:duration=${T}`,
    '-filter_complex',
    `[0][1]amix=inputs=2:normalize=0,lowpass=f=300,tremolo=f=0.12:d=0.6,` +
    `volume=-28dB,afade=t=in:d=2.5,afade=t=out:st=${(T - 2.5).toFixed(2)}:d=2.5[b]`,
    '-map', '[b]', bed,
  ]);

  const mix = join(AUDIO, '_mix.wav');
  await ff([
    '-i', voiceTrack, '-i', bed,
    '-filter_complex', '[0:a][1:a]amix=inputs=2:normalize=0:duration=first,dynaudnorm=p=0.6:m=12[a]',
    '-map', '[a]', mix,
  ]);
  return mix;
}

async function encode(cfg, audio) {
  await mkdir(OUT, { recursive: true });
  const outFile = join(OUT, 'HyperGuard.mp4');
  await ff([
    '-framerate', String(cfg.fps),
    '-i', join(FRAMES, '%05d.png'),
    '-i', audio,
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'slow',
    '-x264-params', 'keyint=60:min-keyint=30',
    '-c:a', 'aac', '-b:a', '192k',
    '-shortest', '-movflags', '+faststart',
    outFile,
  ]);
  return outFile;
}

async function main() {
  const cfg = await buildConfig();
  await writeFile(join(HERE, 'timeline.json'), JSON.stringify(cfg, null, 2));
  if (!process.argv.includes('--no-frames')) {
    await renderFrames(cfg);
  } else {
    const have = (await readdir(FRAMES)).filter((f) => f.endsWith('.png')).length;
    console.log(`reusing ${have} existing frames`);
  }
  if (PROBE) { console.log('probe frames in video/frames/'); return; }
  console.log('building audio …');
  const audio = await buildAudio(cfg);
  console.log('encoding mp4 …');
  const out = await encode(cfg, audio);
  const { stdout } = await exec('ffprobe', ['-v', 'error', '-show_entries',
    'format=duration:stream=width,height,codec_name', '-of', 'default=noprint_wrappers=1', out]);
  console.log('\n✓ ' + out + '\n' + stdout);
}

main().catch((e) => { console.error(e); process.exit(1); });
