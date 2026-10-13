"""Password lock for the End Zone Board static site.

Design: the site password unlocks an RSA private key (stored encrypted in keys.json, safe to publish).
Each rebuild encrypts the board with a fresh AES key wrapped by the RSA *public* key, so rebuilds never
need the password. Browsers: password -> PBKDF2 -> AES-GCM decrypt private key -> unwrap page key -> page.

  python3 lock.py setup <keys.json>              # once; reads the password from SITE_PASSWORD
  python3 lock.py seal <keys.json> <board.html> <index.html>
"""
import base64, json, os, sys
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

b64 = lambda b: base64.b64encode(b).decode()
ITER = 310000


def setup(path):
    pw = os.environ["SITE_PASSWORD"].encode()
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pkcs8 = priv.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    spki = priv.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    salt, iv = os.urandom(16), os.urandom(12)
    k = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(pw)
    ct = AESGCM(k).encrypt(iv, pkcs8, None)
    json.dump(dict(v=1, iter=ITER, salt=b64(salt), iv=b64(iv), priv=b64(ct), pub=b64(spki)), open(path, "w"))
    print("keys written", path)


def seal(path, board, out):
    keys = json.load(open(path))
    pub = serialization.load_der_public_key(base64.b64decode(keys["pub"]))
    page_key, iv = AESGCM.generate_key(256), os.urandom(12)
    ct = AESGCM(page_key).encrypt(iv, open(board, "rb").read(), None)
    wrapped = pub.encrypt(page_key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    payload = dict(keys=keys, wk=b64(wrapped), iv=b64(iv), ct=b64(ct))
    shell = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "shell.html")).read()
    open(out, "w").write(shell.replace("/*PAYLOAD*/null", json.dumps(payload)))
    print("sealed", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    {"setup": lambda: setup(sys.argv[2]), "seal": lambda: seal(*sys.argv[2:5])}[sys.argv[1]]()
