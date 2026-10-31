"""Image: Content Credentials (C2PA), generator metadata, UnivFD full-image AI detector, GenD on any face.

UnivFD (Ojha et al., CVPR 2023, MIT): CLIP ViT-L/14 image features + the authors' trained linear head
(models/univfd_fc.pth, from WisconsinAIVision/UniversalFakeDetect). Generalises across GAN and diffusion
generators better than detectors trained on one generator.
"""
import functools
import json
import os
import re

import numpy as np

from detectors import video

AI_TOOLS = re.compile(r"stable diffusion|midjourney|dall.?e|firefly|comfyui|automatic1111|flux|leonardo|ideogram|imagen", re.I)


def c2pa_manifest(path):
    try:
        import c2pa
    except ImportError:
        return None
    for read in (lambda: c2pa.Reader.from_file(str(path)).json(), lambda: c2pa.Reader(str(path)).json()):
        try:
            return json.loads(read())
        except Exception:
            continue
    return None


def provenance_signal(path):
    from PIL import Image
    ev = []
    m = c2pa_manifest(path)
    if m:
        dump = json.dumps(m)
        if "trainedAlgorithmicMedia" in dump or "compositeWithTrainedAlgorithmicMedia" in dump:
            return {"signal": "image_synthetic", "label": "Content Credentials", "score": 0.95,
                    "why": "the image's Content Credentials declare it AI-generated",
                    "evidence": [{"type": "metadata", "text": "C2PA digitalSourceType: trainedAlgorithmicMedia"}]}
        return {"signal": "image_synthetic", "label": "Content Credentials", "score": 0.2,
                "why": "the image carries valid Content Credentials from a capture device or editor",
                "evidence": [{"type": "metadata", "text": "C2PA manifest present"}]}
    img = Image.open(path)
    for key in ("parameters", "prompt", "workflow"):  # A1111 / ComfyUI write these PNG text chunks
        if key in img.info:
            ev.append({"type": "metadata", "text": f"PNG '{key}' chunk from an image generator"})
    exif = img.getexif()
    software, make, model = exif.get(305, ""), exif.get(271, ""), exif.get(272, "")
    if AI_TOOLS.search(str(software)):
        ev.append({"type": "metadata", "text": f"EXIF Software: {software}"})
    if ev:
        return {"signal": "image_synthetic", "label": "Generator metadata", "score": 0.95, "why": "metadata names an AI image generator", "evidence": ev}
    if make or model:
        return {"signal": "image_synthetic", "label": "Camera metadata", "score": 0.35, "why": f"EXIF says taken on {make} {model}".strip(),
                "evidence": [{"type": "metadata", "text": f"{make} {model}"}]}
    return {"signal": "image_synthetic", "label": "No provenance", "score": 0.55, "why": "no camera metadata or Content Credentials (weak signal)",
            "evidence": [{"type": "metadata", "text": "metadata stripped or absent"}]}


UNIVFD_FC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "univfd_fc.pth")
CLIP_MEAN, CLIP_STD = np.array([0.48145466, 0.4578275, 0.40821073]), np.array([0.26862954, 0.26130258, 0.27577711])


@functools.cache
def univfd():
    import torch
    from transformers import CLIPVisionModelWithProjection
    from detectors.audio import device
    # vision tower only (the text half is never used), fp16 on GPU: ~0.6 GB instead of ~1.7 GB
    dtype = torch.float16 if device() == "cuda" else torch.float32
    clip = CLIPVisionModelWithProjection.from_pretrained("openai/clip-vit-large-patch14", torch_dtype=dtype).to(device()).eval()
    fc = torch.nn.Linear(768, 1)
    fc.load_state_dict(torch.load(UNIVFD_FC, map_location="cpu"))
    return clip, fc.to(device()).eval()


def five_crops(img, size=224):
    """UnivFD scores a 224 px centre crop of the original; we average centre + four corners for big photos."""
    w, h = img.size
    if min(w, h) < size:
        img = img.resize((max(size, round(w * size / min(w, h))), max(size, round(h * size / min(w, h)))))
        w, h = img.size
    boxes = [((w - size) // 2, (h - size) // 2), (0, 0), (w - size, 0), (0, h - size), (w - size, h - size)]
    return [img.crop((x, y, x + size, y + size)) for x, y in boxes]


def univfd_prob(path):
    import torch
    from PIL import Image
    from detectors.audio import device
    clip, fc = univfd()
    crops = five_crops(Image.open(path).convert("RGB"))
    x = np.stack([((np.asarray(c, np.float32) / 255 - CLIP_MEAN) / CLIP_STD).transpose(2, 0, 1) for c in crops])
    with torch.no_grad():
        feats = clip(pixel_values=torch.from_numpy(x).to(device(), clip.dtype)).image_embeds.float()
        return float(torch.sigmoid(fc(feats)).mean())


def analyze(path):
    res = {"signals": [], "errors": [], "face_emb": None}
    try:
        res["signals"].append(provenance_signal(path))
    except Exception as e:
        res["errors"].append(f"could not read image metadata: {e}")
    try:
        p = round(univfd_prob(path), 3)
        res["signals"].append({"signal": "image_univfd", "label": "AI-generated image (UnivFD)", "score": p,
                               "why": f"the picture {'looks' if p >= .5 else 'does not look'} AI-generated (p {p:.2f})",
                               "evidence": [{"type": "metric", "text": f"UnivFD p(fake) {p:.2f}, mean of 5 crops"}]})
    except Exception as e:
        res["errors"].append(f"UnivFD image model unavailable: {e}")
    sig, emb, err = video.image_face(path)
    if sig:
        res["signals"].append(sig)
    res["face_emb"] = emb
    if err:
        res["errors"].append(err)
    return res
