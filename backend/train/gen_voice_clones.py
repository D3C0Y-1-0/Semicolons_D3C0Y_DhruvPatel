"""Zero-shot voice CLONES of real speakers, for evaluation only. Runs in its own venv (F5-TTS pins its own deps):
    train/data/big/f5env/Scripts/python.exe train/gen_voice_clones.py
Each LibriSpeech speaker (public CC BY 4.0 audiobook volunteers, the usual practice in spoofing research) is cloned
from ONE of their real clips and made to say three other lines: two of their own sentences and one scam line.
Writes train/data/big/voice/clones/*.wav and clones.json. Never used to imitate anyone outside this evaluation.
"""
import json
import os
import random
import subprocess
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "big" / "voice"
SCAM_LINES = ["This is urgent. Please transfer the payment to the new vendor account before the meeting ends.",
              "I'm stuck in a meeting and can't talk. Send me the code you just received, quickly.",
              "Keep this confidential. I need you to process the wire today, I will explain later."]


def wav_ref(path):
    """F5-TTS reads its reference through pydub; a plain 24 kHz WAV avoids needing ffprobe."""
    out = DATA / "clone_refs" / (Path(path).stem + ".wav")
    if not out.exists():
        out.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", "24000", str(out)], check=True)
    return str(out)


def main():
    # the venv has no ffmpeg of its own: use the copy of the app's bundled one in data/big/bin
    os.environ["PATH"] = str(DATA.parent / "bin") + os.pathsep + os.environ["PATH"]
    from f5_tts.api import F5TTS
    real = [r for r in json.loads((DATA / "real.json").read_text(encoding="utf-8")) if r["lang"] == "en"]
    by_spk = {}
    for r in real:
        by_spk.setdefault(r["speaker"], []).append(r)
    out_dir = DATA / "clones"
    out_dir.mkdir(exist_ok=True)
    meta = DATA / "clones.json"
    rows = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else []
    done = {r["path"] for r in rows}
    tts = F5TTS()
    rng = random.Random(5)
    for spk, clips in sorted(by_spk.items()):
        if len(clips) < 3:
            continue
        ref, others = clips[0], clips[1:]
        lines = [o["text"] for o in rng.sample(others, 2)] + [rng.choice(SCAM_LINES)]
        for j, line in enumerate(lines):
            p = out_dir / f"{spk}_{j}.wav"
            if str(p) not in done:
                tts.infer(ref_file=wav_ref(ref["path"]), ref_text=ref["text"], gen_text=line, file_wave=str(p), seed=7 + j)
                rows.append({"path": str(p), "speaker": spk, "ref": ref["path"], "text": line, "engine": "f5-tts"})
        meta.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        print(spk, "cloned", flush=True)
    print(len(rows), "clones")


if __name__ == "__main__":
    main()
