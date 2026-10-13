# End Zone Board

Password-protected site. index.html is encrypted; keys.json holds a password-encrypted private key and a public key.
Rebuild: `python3 wrap.py board.html full.html && python3 lock.py seal keys.json full.html index.html` (no password needed).
