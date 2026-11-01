import json
import hashlib

m = json.load(open('output_full/manifest.json'))
files = m['files']

print("Checksum verification:")
for f in files:
    filepath = 'output_full/' + f['name']
    actual = hashlib.sha256(open(filepath, 'rb').read()).hexdigest()
    result = 'MATCH' if actual == f['sha256'] else 'MISMATCH'
    print(f"{f['name']}: {result}")

all_match = all(
    hashlib.sha256(open('output_full/' + f['name'], 'rb').read()).hexdigest() == f['sha256']
    for f in files
)
print(f"\nAll checksums match: {all_match}")
