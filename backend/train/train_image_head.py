"""Adapts the UnivFD head (AI-generated image detector) to today's generators and to WhatsApp-style recompression.

Data (all built on this laptop, nothing gated):
  real: COCO val2017 photos (CC BY 4.0), downloaded from images.cocodataset.org
  fake: SD-Turbo (stabilityai/sd-turbo) images generated from the captions of OTHER COCO photos, so both classes
        show the same kind of scenes and the model can't learn "content" instead of "generated"
Both classes go through the same random resize and JPEG re-encode (quality 60-95), so file format and size
carry no signal; a separate test copy at JPEG 50 stands in for a WhatsApp forward.

Model: CLIP ViT-L/14 stays frozen (as in UnivFD); only the 768->1 linear head is refit, starting from the authors'
weights and pulled back towards them (L2), so it adapts without forgetting the GANs and diffusion models it knew.
Split: 70/30 by photo/prompt; the report compares the original head and the tuned head on the same held-out set.

Run from backend/:  python train/train_image_head.py [--n 1000]
Writes models/univfd_fc_tuned.pth (used by detectors/image.py when present) and eval/image_head_report.md.
ponytail: one generator (SD-Turbo) for training; add Flux / Midjourney samples to the fake set when available.
"""
import argparse
import io
import json
import random
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

import os
os.environ["USE_TUNED_HEADS"] = "0"  # always start from (and compare against) the original heads

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))
DATA = HERE / "data" / "big" / "image"
OUT = BACKEND / "models" / "univfd_fc_tuned.pth"
REPORT = BACKEND.parent / "eval" / "image_head_report.md"
COCO_IMG = "http://images.cocodataset.org/zips/val2017.zip"
COCO_ANN = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fetch(url, dest):
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log("downloading", url)
    tmp = dest.with_suffix(".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)
    return dest


def prepare_real(n):
    """n COCO photos for the real class, plus captions of n different photos to prompt the generator with."""
    ann = fetch(COCO_ANN, DATA / "annotations_trainval2017.zip")
    caps = {}
    with zipfile.ZipFile(ann) as z:
        for c in json.loads(z.read("annotations/captions_val2017.json"))["annotations"]:
            caps.setdefault(c["image_id"], c["caption"].strip())
    ids = sorted(caps)
    random.Random(7).shuffle(ids)
    real_ids, prompt_ids = ids[:n], ids[n:2 * n]
    real_dir = DATA / "real"
    if len(list(real_dir.glob("*.jpg"))) < n:
        z = zipfile.ZipFile(fetch(COCO_IMG, DATA / "val2017.zip"))
        real_dir.mkdir(parents=True, exist_ok=True)
        for i in real_ids:
            (real_dir / f"{i:012d}.jpg").write_bytes(z.read(f"val2017/{i:012d}.jpg"))
    return [real_dir / f"{i:012d}.jpg" for i in real_ids], [caps[i] for i in prompt_ids]


def generate_fake(prompts):
    import torch
    from diffusers import AutoPipelineForText2Image
    fake_dir = DATA / "fake_sdturbo"
    fake_dir.mkdir(parents=True, exist_ok=True)
    todo = [(k, p) for k, p in enumerate(prompts) if not (fake_dir / f"{k:05d}.png").exists()]
    if todo:
        pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=torch.float16, variant="fp16")
        # the running backend may hold most of the 6 GB GPU: stream weights layer by layer instead
        pipe.enable_sequential_cpu_offload()
        pipe.set_progress_bar_config(disable=True)
        g = torch.Generator("cpu").manual_seed(7)
        for j, (k, p) in enumerate(todo):
            pipe(p, num_inference_steps=1, guidance_scale=0.0, generator=g).images[0].save(fake_dir / f"{k:05d}.png")
            if j % 50 == 0:
                log(f"generated {j}/{len(todo)}")
        del pipe
        torch.cuda.empty_cache()
    return [fake_dir / f"{k:05d}.png" for k in range(len(prompts))]


def degrade(img, rng, quality=None):
    """Same treatment for both classes: random short side 384-640 px, JPEG re-encode."""
    from PIL import Image
    s = rng.randint(384, 640)
    w, h = img.size
    img = img.resize((max(224, round(w * s / min(w, h))), max(224, round(h * s / min(w, h)))), Image.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality or rng.randint(60, 95))
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def features(paths, quality=None, seed=0):
    import torch
    from PIL import Image
    from detectors.image import CLIP_MEAN, CLIP_STD, univfd
    from detectors.audio import device
    clip, _ = univfd()
    rng, out = random.Random(seed), []
    for i in range(0, len(paths), 32):
        crops = []
        for p in paths[i:i + 32]:
            img = degrade(Image.open(p).convert("RGB"), rng, quality)
            w, h = img.size
            crops.append(img.crop(((w - 224) // 2, (h - 224) // 2, (w + 224) // 2, (h + 224) // 2)))
        x = np.stack([((np.asarray(c, np.float32) / 255 - CLIP_MEAN) / CLIP_STD).transpose(2, 0, 1) for c in crops])
        with torch.no_grad():
            out.append(clip(pixel_values=torch.from_numpy(x).to(device(), clip.dtype)).image_embeds.float().cpu().numpy())
    return np.concatenate(out)


def fit_head(X, y, w0, b0, l2=1.0, steps=300):
    """Logistic regression on frozen features, initialised at and regularised towards the original head."""
    import torch
    X, y = torch.tensor(X), torch.tensor(y, dtype=torch.float32)
    w0, b0 = torch.tensor(w0), torch.tensor(b0)
    w, b = w0.clone().requires_grad_(), b0.clone().requires_grad_()
    opt = torch.optim.LBFGS([w, b], max_iter=steps, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(X @ w + b, y) + l2 * ((w - w0) ** 2).sum() / len(y)
        loss.backward()
        return loss
    opt.step(closure)
    return w.detach().numpy(), b.detach().numpy()


def metrics(y, p):
    from sklearn.metrics import roc_auc_score, roc_curve
    fpr, tpr, _ = roc_curve(y, p)
    eer = fpr[np.nanargmin(np.abs(fpr - (1 - tpr)))]
    yhat = p >= 0.5
    return {"AUROC": roc_auc_score(y, p), "EER": eer, "acc@0.5": float((yhat == y).mean()),
            "recall": float(yhat[y == 1].mean()), "FPR": float(yhat[y == 0].mean())}


def main():
    import torch
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000, help="images per class")
    n = ap.parse_args().n
    real, prompts = prepare_real(n)
    log(f"{len(real)} real photos ready; generating {len(prompts)} SD-Turbo images")
    fake = generate_fake(prompts)
    log("extracting CLIP features")
    paths, y = real + fake, np.array([0] * len(real) + [1] * len(fake))
    idx = np.random.default_rng(7).permutation(len(paths))
    cut = int(0.7 * len(paths))
    tr, te = idx[:cut], idx[cut:]
    Xtr = features([paths[i] for i in tr], seed=1)
    Xte = features([paths[i] for i in te], seed=2)
    Xwa = features([paths[i] for i in te], quality=50, seed=3)  # WhatsApp-like forward

    from detectors.image import UNIVFD_FC
    sd = torch.load(UNIVFD_FC, map_location="cpu")
    w0, b0 = sd["weight"].reshape(-1).numpy(), sd["bias"].numpy()
    best = None
    for l2 in (10.0, 1.0, 0.1):  # pick the strength on a slice of the TRAIN set, never on the test set
        k = int(0.8 * len(tr))
        w, b = fit_head(Xtr[:k], y[tr][:k], w0, b0, l2)
        auc = metrics(y[tr][k:], 1 / (1 + np.exp(-(Xtr[k:] @ w + b))))["AUROC"]
        log(f"l2={l2}: validation AUROC {auc:.3f}")
        best = max(best or (-1, l2), (auc, l2))
    w, b = fit_head(Xtr, y[tr], w0, b0, best[1])
    sig = lambda X, w, b: 1 / (1 + np.exp(-(X @ w + b)))
    res = {f"{name}, {cond}": metrics(y[te], sig(X, ww, bb))
           for cond, X in (("JPEG 60-95", Xte), ("JPEG 50, WhatsApp-like", Xwa))
           for name, ww, bb in (("original UnivFD head", w0, b0), ("tuned head", w, b))}
    OUT.parent.mkdir(exist_ok=True)
    torch.save({"weight": torch.tensor(w).reshape(1, -1), "bias": torch.tensor(b).reshape(1)}, OUT)

    lines = ["# AI-generated image detector (UnivFD head): adaptation report", "",
             f"Real: {len(real)} COCO val2017 photos. Fake: {len(fake)} SD-Turbo images prompted with captions of other COCO photos. "
             f"Both classes resized and JPEG re-encoded the same way. Train {len(tr)}, held-out test {len(te)} (70/30 by image). "
             f"CLIP ViT-L/14 frozen; head refit from the authors' weights with L2 = {best[1]} towards them (chosen on a train slice).", "",
             "| Model, test condition | AUROC | EER | Accuracy @0.5 | Recall (fakes caught) | False-positive rate |", "| --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {k} | {m['AUROC']:.3f} | {m['EER']:.3f} | {m['acc@0.5']:.3f} | {m['recall']:.3f} | {m['FPR']:.3f} |" for k, m in res.items()]
    lines += ["", "Limits: one generator in training (SD-Turbo) and COCO-style scenes; a new generator family can score lower. "
              "Test images come from the same generator as training (held-out prompts), so this measures adaptation, not "
              "generalisation to unseen generators. The original head's numbers on the same set are the honest baseline."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
