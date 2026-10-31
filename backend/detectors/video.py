"""Video and face: face-swap detection (GenD, WACV 2026) + face embedding (InsightFace ArcFace).

Run `python ../eval/check_gend.py` once after setup to confirm GenD's fake-class index.
"""
import functools
import os

import numpy as np

from detectors.audio import device

GEND_MODEL = os.getenv("GEND_MODEL", "yermandy/GenD_CLIP_L_14")
FAKE_INDEX = int(os.getenv("GEND_FAKE_INDEX", "1"))  # ponytail: index 1 = fake; eval/check_gend.py verifies it
N_FRAMES = int(os.getenv("VIDEO_FRAMES", "32"))       # set 8 on CPU-only laptops


@functools.cache
def face_app():
    from insightface.app import FaceAnalysis
    cuda = device() == "cuda"  # also imports torch first, so onnxruntime-gpu reuses torch's CUDA/cuDNN DLLs on Windows
    gpu = [("CUDAExecutionProvider", {"cudnn_conv_algo_search": "HEURISTIC", "arena_extend_strategy": "kSameAsRequested"})]
    # only box + ArcFace embedding are used; skipping landmark and gender/age models is ~3x faster
    app = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"],
                       providers=(gpu if cuda else []) + ["CPUExecutionProvider"])
    app.prepare(ctx_id=0 if cuda else -1, det_size=(640, 640))
    return app


@functools.cache
def gend():
    from vendor.modeling_gend import GenD
    m = GenD.from_pretrained(GEND_MODEL).to(device()).eval()
    return m.half() if device() == "cuda" else m  # fp16 halves VRAM; 6 GB cards spill to system RAM otherwise


def largest_face(frame_bgr):
    faces = face_app().get(frame_bgr)
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])) if faces else None


def crop_face(frame_bgr, bbox, scale=1.3, size=224):
    """Square crop around the face enlarged 1.3x, as in GenD's preprocessing.
    ponytail: no landmark alignment; add it if real faces score high on your eval set."""
    import cv2
    from PIL import Image
    x1, y1, x2, y2 = bbox
    cx, cy, half = (x1 + x2) / 2, (y1 + y2) / 2, max(x2 - x1, y2 - y1) * scale / 2
    h, w = frame_bgr.shape[:2]
    a, b = int(max(0, cx - half)), int(max(0, cy - half))
    c, d = int(min(w, cx + half)), int(min(h, cy + half))
    face = cv2.resize(frame_bgr[b:d, a:c], (size, size))
    return Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))


def fake_probs(crops):
    import torch
    m = gend()
    out = []
    for i in range(0, len(crops), 16):
        x = torch.stack([m.feature_extractor.preprocess(c) for c in crops[i:i + 16]]).to(device(), m.dtype)
        with torch.no_grad():
            out += m(x).float().softmax(-1)[:, FAKE_INDEX].cpu().tolist()
    return out


def sample_frames(path, n=N_FRAMES):
    import cv2
    cap = cv2.VideoCapture(str(path))
    total, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), cap.get(cv2.CAP_PROP_FPS) or 25
    frames = []
    for idx in np.linspace(0, max(total - 1, 0), num=min(n, max(total, 1))).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append((round(idx / fps, 2), frame))
    cap.release()
    return frames


def _mean_unit(embs):
    v = np.mean(embs, axis=0)
    return (v / (np.linalg.norm(v) + 1e-9)).tolist()


def thumb(pil_img, size=112):
    import base64
    import io
    buf = io.BytesIO()
    pil_img.resize((size, size)).save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def analyze(path, wav=None):
    res = {"signals": [], "errors": [], "frames": [], "face_emb": None}
    try:
        crops, times, embs = [], [], []
        for t, frame in sample_frames(path):
            f = largest_face(frame)
            if f is not None:
                crops.append(crop_face(frame, f.bbox))
                times.append(t)
                embs.append(f.normed_embedding)
        if not crops:
            res["errors"].append("no face found in the video")
            return res
        probs = fake_probs(crops)
        res["frames"] = [{"t": t, "p_fake": round(p, 3)} for t, p in zip(times, probs)]
        k = max(1, len(probs) // 3)
        score = round(float(np.mean(sorted(probs, reverse=True)[:k])), 3)
        order = sorted(range(len(probs)), key=lambda i: -probs[i])[:3]
        res["signals"].append({
            "signal": "face_video", "label": "Face manipulation (GenD)", "score": score,
            "why": f"face looks manipulated in {sum(p >= .5 for p in probs)} of {len(probs)} sampled frames",
            "evidence": [{"type": "frame", "t": times[i], "img": thumb(crops[i]),
                          "text": f"frame at {times[i]}s, p(fake) {probs[i]:.2f}"} for i in order]})
        res["face_emb"] = _mean_unit(embs)
    except Exception as e:
        res["errors"].append(f"video model unavailable: {e}")
        res["signals"].append({"signal": "face_video", "label": "Face manipulation (GenD)", "score": None, "why": "model unavailable", "evidence": []})
    if wav is not None:
        try:
            sig = lip_sync(path, wav)
            if sig:
                res["signals"].append(sig)
        except Exception as e:
            res["errors"].append(f"lip-sync check failed: {e}")
    return res


LIPSYNC_SECONDS, LIPSYNC_FPS, SR = 8, 10, 16000


def best_lag_corr(a, b, max_lag=5):
    """Highest Pearson r between a and b shifted by -max_lag..+max_lag samples. Returns (r, lag)."""
    best = (-1.0, 0)
    for lag in range(-max_lag, max_lag + 1):
        x, y = (a[lag:], b[:len(b) - lag]) if lag >= 0 else (a[:lag], b[-lag:])
        if len(x) > 5 and x.std() > 0 and y.std() > 0:
            best = max(best, (float(np.corrcoef(x, y)[0, 1]), lag))
    return best


def lip_sync(path, wav):
    """Heuristic stand-in for SyncNet: does mouth-region motion rise and fall with speech energy?
    Real talking heads correlate; dubbed or lip-synced fakes drift or don't correlate.
    ponytail: motion energy of the lower-face crop, no landmarks; swap in SyncNet if time allows."""
    import cv2
    cap = cv2.VideoCapture(str(path))
    fps, total = cap.get(cv2.CAP_PROP_FPS) or 25, int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur = total / fps
    if dur < 3:
        return None
    start = max(0.0, dur / 2 - LIPSYNC_SECONDS / 2)
    step = max(1, round(fps / LIPSYNC_FPS))
    first, last = int(start * fps), min(total, int((start + LIPSYNC_SECONDS) * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    motion, times, prev, box = [], [], None, None
    for i in range(first, last):
        ok, frame = cap.read()
        if not ok:
            break
        if (i - first) % step:
            continue
        if box is None or (i - first) % (step * 10) == 0:  # re-detect the face once a second
            f = largest_face(frame)
            if f is None:
                continue
            x1, y1, x2, y2 = f.bbox.astype(int)
            box = (x1 + (x2 - x1) // 5, y1 + int((y2 - y1) * 0.62), x2 - (x2 - x1) // 5, y2)
        a, b, c, d = box
        crop = frame[max(b, 0):d, max(a, 0):c]
        if crop.size == 0:
            continue
        g = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (64, 32)).astype(np.float32)
        if prev is not None:
            motion.append(float(np.abs(g - prev).mean()))
            times.append(i / fps)
        prev = g
    cap.release()
    if len(motion) < 20:
        return None
    half = SR // (2 * LIPSYNC_FPS)
    env = np.array([np.sqrt(np.mean(wav[max(0, int(t * SR) - half):int(t * SR) + half] ** 2) + 1e-12) for t in times])
    if env.mean() < 0.005:
        return None  # nobody speaking in this stretch
    r, lag = best_lag_corr(np.array(motion), env)
    s = round(1 / (1 + np.exp((r - 0.25) * 10)), 3)
    ms = int(lag * 1000 / LIPSYNC_FPS)
    return {"signal": "lip_sync", "label": "Lip-sync (heuristic)", "score": float(s),
            "why": f"mouth movement {'does not follow' if s >= .5 else 'follows'} the voice (r {r:.2f}, offset {ms} ms)",
            "evidence": [{"type": "metric", "text": f"best correlation {r:.2f} at {ms} ms offset over {len(motion)} frames"}]}


def image_face(path):
    """Same as analyze() but for a single photo. Returns (signal or None, face_emb or None, error or None)."""
    import cv2
    try:
        img = cv2.imread(str(path))
        f = largest_face(img) if img is not None else None
        if f is None:
            return None, None, None
        p = round(fake_probs([crop_face(img, f.bbox)])[0], 3)
        sig = {"signal": "face_video", "label": "Face manipulation in image (GenD)", "score": p,
               "why": f"face in the image looks {'manipulated' if p >= .5 else 'natural'} (p {p:.2f})",
               "evidence": [{"type": "metric", "text": f"p(fake) {p:.2f}"}]}
        return sig, f.normed_embedding.tolist(), None
    except Exception as e:
        return None, None, f"face model unavailable: {e}"
