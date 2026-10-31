"""Confirms GenD's fake-class index on the two sample face crops from the GenD README.
Run from the backend folder:  python ../eval/check_gend.py"""
import io
import sys
import urllib.request

sys.path.insert(0, ".")
from PIL import Image  # noqa: E402

from detectors import video  # noqa: E402

FAKE = "https://github.com/yermandy/deepfake-detection/blob/main/datasets/FF/DF/000_003/000.png?raw=true"
REAL = "https://github.com/yermandy/deepfake-detection/blob/main/datasets/FF/real/000/000.png?raw=true"
imgs = [Image.open(io.BytesIO(urllib.request.urlopen(u, timeout=30).read())).convert("RGB") for u in (FAKE, REAL)]
p_fake, p_real = video.fake_probs(imgs)
print(f"p(fake) using index {video.FAKE_INDEX}: fake sample {p_fake:.3f}, real sample {p_real:.3f}")
if p_fake > p_real:
    print("OK: GEND_FAKE_INDEX is correct.")
else:
    print(f"WRONG INDEX: set GEND_FAKE_INDEX={1 - video.FAKE_INDEX} in backend/.env")
