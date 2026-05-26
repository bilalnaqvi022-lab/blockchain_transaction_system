"""
Wallet Module
-------------
Handles key pair generation, wallet creation, and transaction signing.
Course: Parallel and Distributed Computing
"""

import hashlib
import json
import os
import time
from typing import Dict, Optional


class Wallet:
    """Represents a user's blockchain wallet with public/private keys."""

    def __init__(self, owner: str):
        self.owner = owner
        self.private_key = self._generate_private_key()
        self.public_key = self._derive_public_key(self.private_key)
        self.address = self._generate_address(self.public_key)
        self.balance = 0.0

    def _generate_private_key(self) -> str:
        """Generate a 256-bit private key using OS random bytes."""
        return hashlib.sha256(os.urandom(32)).hexdigest()

    def _derive_public_key(self, private_key: str) -> str:
        """Derive public key from private key (simplified simulation)."""
        return hashlib.sha256((private_key + "PUBLIC").encode()).hexdigest()

    def _generate_address(self, public_key: str) -> str:
        """Generate a wallet address from the public key (RIPEMD-160 style)."""
        step1 = hashlib.sha256(public_key.encode()).hexdigest()
        step2 = hashlib.sha256(step1.encode()).hexdigest()
        return "0x" + step2[:40]  # 40-character address (like Ethereum)

    def sign_transaction(self, transaction_data: dict) -> str:
        """Sign a transaction using the private key."""
        data_str = json.dumps(transaction_data, sort_keys=True)
        signature = hashlib.sha256(
            (self.private_key + data_str).encode()
        ).hexdigest()
        return signature

    def create_transaction(self, recipient_address: str, amount: float) -> Dict:
        """Create and sign a new transaction."""
        if amount <= 0:
            raise ValueError("Transaction amount must be positive.")

        transaction = {
            "sender":    self.address,
            "recipient": recipient_address,
            "amount":    amount,
            "timestamp": time.time(),
            "tx_id":     None,   # Will be filled after signing
        }

        # Sign transaction
        signature = self.sign_transaction(transaction)
        transaction["signature"] = signature

        # Generate unique transaction ID
        tx_id = hashlib.sha256(
            (str(transaction["timestamp"]) + self.address + recipient_address).encode()
        ).hexdigest()[:16]
        transaction["tx_id"] = tx_id

        return transaction

    def get_info(self) -> Dict:
        return {
            "owner":      self.owner,
            "address":    self.address,
            "public_key": self.public_key[:32] + "...",   # truncated for display
            "balance":    self.balance,
        }

    def __repr__(self):
        return f"Wallet(owner={self.owner}, address={self.address[:12]}...)"


def verify_transaction_signature(transaction: dict) -> bool:
    """Verify the signature of a transaction (without private key)."""
    sig = transaction.get("signature")
    if not sig:
        return False
    # In a real system we'd use asymmetric crypto; here we just check presence
    return len(sig) == 64
