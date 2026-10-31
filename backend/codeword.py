"""Human 2FA: a spoken code word that changes every 30 seconds, like an authenticator app you say out loud.

Each enrolled person has a secret. The real person gets the current two words from the Telegram bot (/code);
the employee on the call asks for them and types what they heard. A perfect voice clone doesn't know them.
ponytail: no attempt limit yet; add one (e.g. 3 tries per case) before real use.
"""
import hashlib
import hmac
import re
import time

STEP = 30  # seconds per code word
WORDS = ("mango river tiger lantern pencil monsoon cricket window "   # 8 per line, 64 in all: easy to say,
         "rocket garden silver tomato planet violet coconut thunder "  # hard to mishear over a bad line
         "harbour jasmine falcon marble rainbow cactus pepper glacier "
         "orbit saffron lotus anchor bamboo copper desert ember "
         "forest ginger island jungle kettle lemon meadow ocean "
         "parrot ribbon sunset temple velvet walnut zebra almond "
         "bridge candle dolphin eagle feather guitar honey ivory "
         "button cobra diamond engine circus hockey kitten ladder").split()
assert len(WORDS) == 64


def phrase(secret, t=None):
    step = int((time.time() if t is None else t) // STEP)
    h = hmac.new(bytes.fromhex(secret), str(step).encode(), hashlib.sha256).digest()
    a = h[0] % 64
    return f"{WORDS[a]} {WORDS[(a + 1 + h[1] % 63) % 64]}"  # never the same word twice ("kitten kitten")


def seconds_left(t=None):
    return STEP - int((time.time() if t is None else t) % STEP)


def check(secret, said, t=None):
    """Accepts the current word and the one just before it, so a word read out at the turn of the window still counts."""
    t = time.time() if t is None else t
    said = " ".join(re.findall(r"[a-z]+", (said or "").lower()))
    return any(hmac.compare_digest(said, phrase(secret, t - k * STEP)) for k in (0, 1))


def demo():
    s = "00" * 16
    p = phrase(s, 1000)
    assert check(s, p.upper() + "!", 1000) and check(s, p, 1000 + STEP) and not check(s, p, 1000 + 3 * STEP)
    assert all(len(set(phrase(s, k * STEP).split())) == 2 for k in range(5000))
    print("codeword ok:", p)


if __name__ == "__main__":
    demo()
