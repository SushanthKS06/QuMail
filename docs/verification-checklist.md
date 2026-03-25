# QuMail Verification Checklist

Step-by-step procedures to verify that QuMail's E2E encryption works correctly.

---

## 1. Automated Proof Script

```bash
cd d:\QuMail\backend
set QUMAIL_DEV_MODE=1
python ..\scripts\prove_e2e_encryption.py
```

**Expected**: All 7 proofs show ✅ PASS. Final line: "ALL PROOFS PASSED".

---

## 2. Automated Test Suites

```bash
cd d:\QuMail\backend
set QUMAIL_DEV_MODE=1

# All tests
python -m pytest tests/ -v

# Integrity hash tests only
python -m pytest tests/test_integrity.py -v

# Tampering detection tests only
python -m pytest tests/test_tampering.py -v

# E2E proof tests only
python -m pytest tests/test_e2e_proof.py -v
```

**Expected**: All tests pass (green).

---

## 3. Gmail "Show Original" Verification

1. Send an encrypted email via QuMail (Level 2 or 3)
2. Open Gmail web UI → find the received message
3. Click the three-dot menu → "Show Original"
4. **Verify**:
   - MIME body contains Base64-encoded JSON with `ciphertext`, `nonce`, `tag` fields
   - The original message text does **NOT** appear anywhere
   - Subject line shows `[QuMail Secure] New Encrypted Message`, not the real subject
   - `X-QuMail-Security-Level` header is present

---

## 4. Ciphertext Tampering Test (Manual)

```python
from crypto_engine.aes_gcm import aes_encrypt, aes_decrypt, generate_aes_key

key = generate_aes_key()
ct, nonce, tag = aes_encrypt(b"Secret message", key)

# Tamper with ciphertext
tampered = bytearray(ct)
tampered[0] ^= 0x01

try:
    aes_decrypt(bytes(tampered), key, nonce, tag)
    print("FAIL: Tampering not detected!")
except Exception:
    print("PASS: Tampering detected — decryption rejected")
```

---

## 5. Hash Comparison Test (Manual)

```python
from crypto_engine.aes_gcm import aes_encrypt, aes_decrypt, generate_aes_key
from crypto_engine.integrity import compute_hash

msg = b"Verify this message"
original_hash = compute_hash(msg)

key = generate_aes_key()
ct, nonce, tag = aes_encrypt(msg, key)
decrypted = aes_decrypt(ct, key, nonce, tag)
decrypted_hash = compute_hash(decrypted)

assert original_hash == decrypted_hash, "FAIL: Hashes don't match!"
print(f"PASS: original={original_hash[:16]}... == decrypted={decrypted_hash[:16]}...")
```

---

## 6. Audit Log Verification

With the backend running:

```bash
# GET /api/v1/security/audit-log
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/security/audit-log
```

**Verify**:
- Events include `ENCRYPT_START`, `ENCRYPT_COMPLETE`, `DECRYPT_START`, `DECRYPT_COMPLETE`
- `key_id` values are truncated (max 8 chars + `...`)
- No plaintext or full keys appear in any event
- `hash_prefix` shows only first 12 characters

---

## 7. API Encryption Proof Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/security/verify-encryption \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"plaintext": "Test message", "security_level": 2}'
```

**Expected response**:
```json
{
  "plaintext_hash": "abc123...",
  "ciphertext_sample": "eyJ2ZX...",
  "decrypted_hash": "abc123...",
  "hashes_match": true,
  "ciphertext_differs_from_plaintext": true,
  "integrity_verified": true,
  "proof_summary": "✅ Ciphertext differs... | ✅ SHA-256 hashes match... | ✅ Integrity verified"
}
```

---

## Summary Checklist

| # | Check | Method | Expected |
|---|-------|--------|----------|
| 1 | Proof script passes | `prove_e2e_encryption.py` | All ✅ |
| 2 | Test suites pass | `pytest tests/ -v` | All green |
| 3 | Gmail shows ciphertext only | "Show Original" | No plaintext visible |
| 4 | Tampering detected | Bit-flip test | `InvalidTag` exception |
| 5 | Hashes match after roundtrip | Hash comparison | `original == decrypted` |
| 6 | Audit log is clean | API endpoint | No secrets leaked |
| 7 | Verification API works | POST endpoint | All fields `true` |
