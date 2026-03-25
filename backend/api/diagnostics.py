import base64
import json
import logging
import time
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()


class TestResult(BaseModel):
    test_name: str
    security_level: int
    success: bool
    duration_ms: float
    message: str
    details: Optional[dict] = None


class DiagnosticsResponse(BaseModel):
    overall_success: bool
    tests: List[TestResult]
    run_at: str
    total_duration_ms: float


async def _test_otp_encryption() -> TestResult:
    start = time.perf_counter()
    try:
        from crypto_engine.otp import otp_encrypt, otp_decrypt
        
        plaintext = b"QuMail OTP Test Message - Quantum Secure!"
        key = bytes([i % 256 for i in range(len(plaintext))])
        
        ciphertext = otp_encrypt(plaintext, key)
        
        if ciphertext == plaintext:
            raise ValueError("Encryption produced identical output - NOT encrypted!")
        
        decrypted = otp_decrypt(ciphertext, key)
        
        if decrypted != plaintext:
            raise ValueError(f"Decryption mismatch: expected {plaintext}, got {decrypted}")
        
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            test_name="One-Time Pad (OTP)",
            security_level=1,
            success=True,
            duration_ms=round(duration, 2),
            message="OTP encryption/decryption successful",
            details={
                "plaintext_size": len(plaintext),
                "key_size": len(key),
                "ciphertext_size": len(ciphertext),
            }
        )
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        logger.exception("OTP test failed: %s", e)
        return TestResult(
            test_name="One-Time Pad (OTP)",
            security_level=1,
            success=False,
            duration_ms=round(duration, 2),
            message=f"OTP test failed: {str(e)}",
        )


async def _test_aes_encryption() -> TestResult:
    start = time.perf_counter()
    try:
        from crypto_engine.aes_gcm import aes_encrypt, aes_decrypt
        
        plaintext = b"QuMail AES-256-GCM Test Message - Quantum Aided Security!"
        key = bytes([i % 256 for i in range(32)])
        
        # aes_encrypt returns (ciphertext, nonce, tag)
        ciphertext, nonce, tag = aes_encrypt(plaintext, key)
        
        if ciphertext == plaintext:
            raise ValueError("Encryption produced identical output - NOT encrypted!")
        
        decrypted = aes_decrypt(ciphertext, key, nonce, tag)
        
        if decrypted != plaintext:
            raise ValueError(f"Decryption mismatch")
        
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            test_name="AES-256-GCM",
            security_level=2,
            success=True,
            duration_ms=round(duration, 2),
            message="AES-256-GCM encryption/decryption successful",
            details={
                "plaintext_size": len(plaintext),
                "key_size": len(key),
                "nonce_size": len(nonce),
                "tag_size": len(tag),
            }
        )
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        logger.exception("AES test failed: %s", e)
        return TestResult(
            test_name="AES-256-GCM",
            security_level=2,
            success=False,
            duration_ms=round(duration, 2),
            message=f"AES test failed: {str(e)}",
        )


async def _test_pqc_encryption() -> TestResult:
    start = time.perf_counter()
    try:
        from crypto_engine.pqc import generate_kyber_keypair, kyber_encapsulate, kyber_decapsulate
        from crypto_engine.aes_gcm import aes_encrypt, aes_decrypt
        
        # Generate keypair
        public_key, secret_key = generate_kyber_keypair()
        
        # Encapsulate to get shared secret
        encapsulated_key, shared_secret = kyber_encapsulate(public_key)
        
        # Use shared secret to encrypt some data via AES
        plaintext = b"QuMail PQC Test - Post-Quantum Cryptography!"
        ciphertext, nonce, tag = aes_encrypt(plaintext, shared_secret)
        
        # Decapsulate to recover shared secret
        recovered_secret = kyber_decapsulate(encapsulated_key, secret_key)
        
        # Decrypt with recovered secret
        decrypted = aes_decrypt(ciphertext, recovered_secret, nonce, tag)
        
        if decrypted != plaintext:
            raise ValueError("PQC decryption mismatch")
        
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            test_name="Post-Quantum Crypto (Kyber)",
            security_level=3,
            success=True,
            duration_ms=round(duration, 2),
            message="PQC key encapsulation successful (simulated mode)",
            details={
                "public_key_size": len(public_key),
                "encapsulated_key_size": len(encapsulated_key),
                "shared_secret_size": len(shared_secret),
            }
        )
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        logger.exception("PQC test failed: %s", e)
        return TestResult(
            test_name="Post-Quantum Crypto (Kyber)",
            security_level=3,
            success=False,
            duration_ms=round(duration, 2),
            message=f"PQC test failed: {str(e)}",
        )


async def _test_attachment_encryption() -> TestResult:
    start = time.perf_counter()
    try:
        from crypto_engine.aes_gcm import aes_encrypt, aes_decrypt
        
        attachment_content = b"This is a test file attachment content for QuMail security diagnostics. " * 10
        key = bytes([i % 256 for i in range(32)])
        
        # aes_encrypt returns (ciphertext, nonce, tag)
        ciphertext, nonce, tag = aes_encrypt(attachment_content, key)
        
        if ciphertext == attachment_content:
            raise ValueError("Attachment encryption produced identical output!")
        
        decrypted = aes_decrypt(ciphertext, key, nonce, tag)
        
        if decrypted != attachment_content:
            raise ValueError("Attachment decryption mismatch")
        
        duration = (time.perf_counter() - start) * 1000
        return TestResult(
            test_name="Attachment Encryption",
            security_level=2,
            success=True,
            duration_ms=round(duration, 2),
            message="Attachment encryption/decryption successful",
            details={
                "original_size": len(attachment_content),
                "encrypted_size": len(ciphertext),
            }
        )
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        logger.exception("Attachment encryption test failed: %s", e)
        return TestResult(
            test_name="Attachment Encryption",
            security_level=2,
            success=False,
            duration_ms=round(duration, 2),
            message=f"Attachment test failed: {str(e)}",
        )


@router.post("/run", response_model=DiagnosticsResponse)
async def run_diagnostics():
    from datetime import datetime
    
    start_total = time.perf_counter()
    
    tests = [
        await _test_otp_encryption(),
        await _test_aes_encryption(),
        await _test_pqc_encryption(),
        await _test_attachment_encryption(),
    ]
    
    total_duration = (time.perf_counter() - start_total) * 1000
    overall_success = all(t.success for t in tests)
    
    logger.info(
        "Security diagnostics completed: %s (%.2fms)",
        "PASS" if overall_success else "FAIL",
        total_duration
    )
    
    return DiagnosticsResponse(
        overall_success=overall_success,
        tests=tests,
        run_at=datetime.utcnow().isoformat(),
        total_duration_ms=round(total_duration, 2),
    )


@router.get("/run/stream")
async def run_diagnostics_stream():
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    import asyncio
    
    async def generate_events():
        start_total = time.perf_counter()
        tests_completed = []
        
        test_functions = [
            ("otp", _test_otp_encryption),
            ("aes", _test_aes_encryption),
            ("pqc", _test_pqc_encryption),
            ("attachment", _test_attachment_encryption),
        ]
        
        for test_id, test_func in test_functions:
            result = await test_func()
            tests_completed.append(result)
            
            event_data = {
                "type": "test_result",
                "test_id": test_id,
                "result": result.model_dump()
            }
            yield f"data: {json.dumps(event_data)}\n\n"
            
            await asyncio.sleep(0.1)
        
        total_duration = (time.perf_counter() - start_total) * 1000
        overall_success = all(t.success for t in tests_completed)
        
        final_event = {
            "type": "complete",
            "overall_success": overall_success,
            "total_duration_ms": round(total_duration, 2),
            "run_at": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(final_event)}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
