import asyncio
import os
import sys
import time
import subprocess
import signal
import httpx
from pathlib import Path

# Helper to run key manager process
class key_manager_process:
    def __init__(self, name, port, peers, env_mod=None):
        self.name = name
        self.port = port
        self.process = None
        self.env = os.environ.copy()
        self.env["PORT"] = str(port)
        self.env["LOCAL_PEER_ID"] = name
        # Fix peers format for env var (JSON string)
        import json
        self.env["PEERS"] = json.dumps(peers)
        self.env["PERSISTENCE_PATH"] = f"./data/{name}_keystore.enc"
        self.env["AUDIT_PATH"] = f"./data/{name}_audit.log"
        self.env["QKD_LINK_SECRET"] = "secret123" 
        
        # mTLS Config
        self.env["SSL_CA_FILE"] = "./data/pki/ca_cert.pem"
        self.env["SSL_CERT_FILE"] = f"./data/pki/km-{name}_cert.pem"
        self.env["SSL_KEY_FILE"] = f"./data/pki/km-{name}_key.pem"
        
        if env_mod:
            self.env.update(env_mod)

    async def start(self):
        cmd = [sys.executable, "d:/QuMail/key_manager/main.py"]
        print(f"[{self.name}] Starting on port {self.port}...")
        self.process = subprocess.Popen(
            cmd, 
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="d:/QuMail/key_manager"
        )
        # Wait for startup
        for _ in range(10):
            try:
                # We need to act as a valid client too to check health
                # Use Alice's cert for the health check client
                cert = ("./data/pki/km-alice_cert.pem", "./data/pki/km-alice_key.pem")
                ca = "./data/pki/ca_cert.pem"
                
                async with httpx.AsyncClient(verify=ca, cert=cert) as client:
                    resp = await client.get(f"https://127.0.0.1:{self.port}/health")
                    if resp.status_code == 200:
                        print(f"[{self.name}] UP! (Secure Connection Verified)")
                        return
            except Exception as e:
                # print(e)
                await asyncio.sleep(1)
        
        # If we get here, it failed to start
        stdout, stderr = self.process.communicate()
        print(f"[{self.name}] STDOUT:\n{stdout.decode()}")
        print(f"[{self.name}] STDERR:\n{stderr.decode()}")
        raise RuntimeError(f"[{self.name}] Failed to start")

    def stop(self):
        if self.process:
            print(f"[{self.name}] Stopping...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()

async def run_scenario():
    # Scenario: Alice (8100) and Bob (8101)
    # Alice pushes key to Bob
    
    alice = key_manager_process("alice", 8100, {"bob": "https://127.0.0.1:8101"})
    bob = key_manager_process("bob", 8101, {"alice": "https://127.0.0.1:8100"})
    
    try:
        await bob.start()
        await alice.start()
        
        # Use Alice's certs to talk to Alice (as if we were her local backend)
        # Note: In reality backend would have its own cert, but we reuse Alice's node cert here
        cert = ("./data/pki/km-alice_cert.pem", "./data/pki/km-alice_key.pem")
        ca = "./data/pki/ca_cert.pem"
        
        async with httpx.AsyncClient(verify=ca, cert=cert) as client:
            # 1. Verification: Check Health and Entropy
            print("\n--- 1. Checking Health and Entropy ---")
            resp = await client.get("https://127.0.0.1:8100/api/v1/entropy/stats")
            stats = resp.json()
            print(f"Alice Entropy Source: {stats.get('source', 'Unknown')}")
            print(f"Quantized: {stats.get('quantum_grade', False)}")
            
            # 2. Key Exchange Scenario
            print("\n--- 2. Testing Distributed Key Exchange ---")
            # Alice generates key for Bob
            req = {
                "peer_id": "bob", # Alice knows this peer
                "size": 32,
                "key_type": "aes_seed"
            }
            resp = await client.post("https://127.0.0.1:8100/api/v1/keys/request", json=req)
            if resp.status_code != 200:
                print(f"FAILED to request key: {resp.text}")
                return
                
            key_data = resp.json()
            key_id = key_data["key_id"]
            print(f"Alice generated key: {key_id}")
            
            # Wait a moment for async push
            await asyncio.sleep(1)
            
            print(f"Checking if Bob received key {key_id}...")
            # We connect to Bob using Bob's cert (pretending to be his backend) or Alice's (if we had a universal client cert)
            # For simplicity, we just use the same client context which has a valid cert trusted by Bob's CA
            resp = await client.delete(f"https://127.0.0.1:8101/api/v1/keys/{key_id}")
            
            if resp.status_code == 200:
                print("✅ SUCCESS! Bob received and deleted the key.")
            else:
                print(f"❌ FAILURE! Bob did not find the key. Status: {resp.status_code}")
                
            # 3. Persistence Check
            print("\n--- 3. Testing Persistence ---")
            # Create a PERSISTENT key on Alice
            resp = await client.post("https://127.0.0.1:8100/api/v1/keys/request", json={
                "peer_id": "bob", "size": 32
            })
            p_key_id = resp.json()["key_id"]
            print(f"Created persistent key {p_key_id} on Alice")
            
            # Restart Alice
            print("Restarting Alice...")
            alice.stop()
            await asyncio.sleep(2)
            await alice.start()
            
            # Check if key exists
            resp = await client.delete(f"https://127.0.0.1:8100/api/v1/keys/{p_key_id}")
            if resp.status_code == 200:
                print("✅ SUCCESS! Alice remembered the key after restart.")
            else:
                print("❌ FAILURE! Alice forgot the key.")

    finally:
        alice.stop()
        bob.stop()

if __name__ == "__main__":
    try:
        asyncio.run(run_scenario())
    except KeyboardInterrupt:
        pass
