// Generates per-scene voiceover with ElevenLabs, then probes each clip's
// duration with ffprobe and writes audio/durations.json.
//
//   node narrate.mjs
//
// Reads ELEVENLABS_API_KEY from ../.env (falls back to process.env).

import { writeFile, readFile, mkdir } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { SCENES, VOICE_ID } from './script.mjs';

const exec = promisify(execFile);
const HERE = dirname(fileURLToPath(import.meta.url));
const AUDIO = join(HERE, 'audio');

async function loadKey() {
  if (process.env.ELEVENLABS_API_KEY) return process.env.ELEVENLABS_API_KEY;
  const env = await readFile(join(HERE, '..', '.env'), 'utf8');
  const m = env.match(/^ELEVENLABS_API_KEY=(.+)$/m);
  if (!m) throw new Error('ELEVENLABS_API_KEY not found in ../.env');
  return m[1].trim();
}

async function ttsScene(key, scene) {
  const url = `https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}?output_format=mp3_44100_128`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'xi-api-key': key, 'content-type': 'application/json' },
    body: JSON.stringify({
      text: scene.narration,
      model_id: 'eleven_multilingual_v2',
      voice_settings: {
        stability: 0.35,
        similarity_boost: 0.8,
        style: 0.25,
        use_speaker_boost: true,
      },
    }),
  });
  if (!res.ok) {
    throw new Error(`TTS ${scene.id} failed: ${res.status} ${await res.text()}`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  const out = join(AUDIO, `${scene.id}.mp3`);
  await writeFile(out, buf);
  return out;
}

async function probeDuration(file) {
  const { stdout } = await exec('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1', file,
  ]);
  return parseFloat(stdout.trim());
}

async function main() {
  await mkdir(AUDIO, { recursive: true });
  const key = await loadKey();
  const durations = {};
  for (const scene of SCENES) {
    process.stdout.write(`· ${scene.id} … `);
    const file = await ttsScene(key, scene);
    const dur = await probeDuration(file);
    durations[scene.id] = { voice: dur, tail: scene.tail, total: dur + scene.tail };
    console.log(`${dur.toFixed(2)}s voice (+${scene.tail}s tail)`);
  }
  const totalVideo = Object.values(durations).reduce((a, d) => a + d.total, 0);
  await writeFile(join(AUDIO, 'durations.json'), JSON.stringify({ durations, totalVideo }, null, 2));
  console.log(`\n✓ total video duration: ${totalVideo.toFixed(2)}s`);
}

main().catch((e) => { console.error(e); process.exit(1); });
