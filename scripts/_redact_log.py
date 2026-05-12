"""One-shot log redactor for JWT-like strings. Disposable."""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("usage: python _redact_log.py <path>")
    sys.exit(2)

p = Path(sys.argv[1])
if not p.is_file():
    print(f"FATAL: {p} is not a file")
    sys.exit(3)

content = None
used_encoding = None
for enc in ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin-1"):
    try:
        content = p.read_text(encoding=enc)
        used_encoding = enc
        break
    except UnicodeDecodeError:
        continue
if content is None:
    print("FATAL: could not decode file with any common encoding")
    sys.exit(4)
print(f"  decoded as: {used_encoding}")
before = len(content)

# Supabase JWTs start with eyJ (header base64 for {"alg":...) and continue as
# base64url chars plus dots. Be broad to catch all variants.
pattern = re.compile(r"eyJ[A-Za-z0-9_\-\.]{10,}")
matches = pattern.findall(content)
redacted = pattern.sub("<REDACTED-JWT>", content)

p.write_text(redacted, encoding=used_encoding)
after = len(redacted)

# Verify
verify = p.read_text(encoding=used_encoding)
remaining = pattern.findall(verify)

print(f"File: {p}")
print(f"  before size: {before} chars")
print(f"  after  size: {after} chars")
print(f"  JWT matches found:   {len(matches)}")
print(f"  JWT matches remaining: {len(remaining)}")
print(f"  eyJ literal count remaining: {verify.count('eyJ')}")
if remaining:
    print("  FAIL: redaction incomplete")
    sys.exit(1)
else:
    print("  PASS: no JWT-like strings remain")
