import sys
import logging
sys.path.append('d:\\QuMail\\backend')

logging.basicConfig(level=logging.INFO)

from crypto_engine.quantum_sim import ChaCha20CSPRNG, EntropyPool

pool = EntropyPool()
rng = ChaCha20CSPRNG(pool)

print("Testing generate that triggers reseed...")
# The reseed threshold is 64*1024 (65536) bytes. 
# We'll generate 70000 bytes at once to trigger reseed inside generate()
rng.generate(70000)

print("Success! No deadlock!")
