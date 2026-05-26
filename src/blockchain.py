"""
Block & Blockchain Module
--------------------------
Core data structures: Block and Blockchain ledger.
Course: Parallel and Distributed Computing
"""

import hashlib
import json
import time
from typing import List, Optional, Dict


class Block:
    """Represents a single block in the blockchain."""

    def __init__(
        self,
        block_id: int,
        transactions: List[Dict],
        previous_hash: str,
        mined_by: str = "Unknown",
    ):
        self.block_id       = block_id
        self.timestamp      = time.time()
        self.transactions   = transactions
        self.previous_hash  = previous_hash
        self.mined_by       = mined_by
        self.nonce          = 0
        self.merkle_root    = self._compute_merkle_root()
        self.current_hash   = ""  # Set after mining

    # ------------------------------------------------------------------
    # Hashing helpers
    # ------------------------------------------------------------------

    def _compute_merkle_root(self) -> str:
        """
        Merkle root over the full content of every transaction.
        ANY field change (amount, sender, recipient) invalidates the root.
        """
        if not self.transactions:
            return hashlib.sha256(b"empty").hexdigest()
        tx_hashes = [
            hashlib.sha256(json.dumps(tx, sort_keys=True).encode()).hexdigest()
            for tx in self.transactions
        ]
        return hashlib.sha256("".join(tx_hashes).encode()).hexdigest()

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this block's contents."""
        block_data = {
            "block_id":     self.block_id,
            "timestamp":    self.timestamp,
            "merkle_root":  self.merkle_root,
            "previous_hash": self.previous_hash,
            "nonce":        self.nonce,
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def is_valid_hash(self, hash_value: str, difficulty: int) -> bool:
        """Check whether the hash satisfies the Proof-of-Work difficulty."""
        return hash_value.startswith("0" * difficulty)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "block_id":      self.block_id,
            "timestamp":     self.timestamp,
            "mined_by":      self.mined_by,
            "transactions":  self.transactions,
            "previous_hash": self.previous_hash,
            "merkle_root":   self.merkle_root,
            "nonce":         self.nonce,
            "current_hash":  self.current_hash,
        }

    def display(self):
        sep = "-" * 55
        print(f"\n{sep}")
        print(f"  Block #{self.block_id}  |  Mined by: {self.mined_by}")
        print(sep)
        print(f"  Timestamp    : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))}")
        print(f"  Nonce        : {self.nonce}")
        print(f"  Prev Hash    : {self.previous_hash[:32]}...")
        print(f"  Current Hash : {self.current_hash[:32]}...")
        print(f"  Merkle Root  : {self.merkle_root[:32]}...")
        print(f"  Transactions : {len(self.transactions)}")
        for tx in self.transactions:
            sender = tx.get("sender", "GENESIS")[:12]
            recip  = tx.get("recipient", "N/A")[:12]
            amt    = tx.get("amount", 0)
            print(f"    -> {sender}... -> {recip}... : {amt}")
        print(sep)

    def __repr__(self):
        return f"Block(id={self.block_id}, hash={self.current_hash[:12]}...)"


# ======================================================================

class Blockchain:
    """
    Immutable distributed ledger.

    Maintains a chain of Blocks and enforces:
      - Proof-of-Work difficulty
      - Chain integrity (hash linkage)
      - Double-spend detection
    """

    DIFFICULTY  = 3         # Leading zeros required in valid hash
    REWARD      = 10.0      # Coins awarded to the miner

    def __init__(self):
        self.chain: List[Block] = []
        self.spent_tx_ids = set()   # Track spent transaction IDs
        self._create_genesis_block()

    # ------------------------------------------------------------------
    # Genesis
    # ------------------------------------------------------------------

    # Fixed genesis timestamp so ALL nodes produce the identical genesis hash
    GENESIS_TIMESTAMP = 1_700_000_000.0

    def _create_genesis_block(self):
        genesis = Block(
            block_id=0,
            transactions=[{"tx_id": "genesis", "sender": "SYSTEM",
                           "recipient": "NETWORK", "amount": 0}],
            previous_hash="0" * 64,
            mined_by="SYSTEM",
        )
        genesis.timestamp    = self.GENESIS_TIMESTAMP   # deterministic
        genesis.merkle_root  = genesis._compute_merkle_root()
        genesis.current_hash = genesis.compute_hash()
        self.chain.append(genesis)

    # ------------------------------------------------------------------
    # Chain management
    # ------------------------------------------------------------------

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, block: Block) -> bool:
        """Add a pre-mined block after verifying its linkage and hash."""
        if block.previous_hash != self.last_block.current_hash:
            print(f"  [Blockchain] Block #{block.block_id} rejected: bad previous hash.")
            return False
        if not block.is_valid_hash(block.current_hash, self.DIFFICULTY):
            print(f"  [Blockchain] Block #{block.block_id} rejected: hash difficulty not met.")
            return False
        self.chain.append(block)
        # Mark transactions as spent
        for tx in block.transactions:
            self.spent_tx_ids.add(tx.get("tx_id"))
        return True

    def is_transaction_spent(self, tx_id: str) -> bool:
        return tx_id in self.spent_tx_ids

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_chain_valid(self) -> bool:
        """Validate the entire chain for integrity."""
        for i in range(1, len(self.chain)):
            current  = self.chain[i]
            previous = self.chain[i - 1]

            # 1. Hash linkage
            if current.previous_hash != previous.current_hash:
                return False
            # 2. Stored hash matches recomputed hash
            if current.current_hash != current.compute_hash():
                return False
            # 3. Proof-of-Work difficulty satisfied
            if not current.is_valid_hash(current.current_hash, self.DIFFICULTY):
                return False
            # 4. Merkle root matches actual transaction data (tamper check)
            recomputed_merkle = current._compute_merkle_root()
            if current.merkle_root != recomputed_merkle:
                return False
        return True

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display_chain(self):
        print("\n" + "=" * 55)
        print(f"  BLOCKCHAIN LEDGER  ({len(self.chain)} blocks)")
        print("=" * 55)
        for block in self.chain:
            block.display()
        valid = self.is_chain_valid()
        print(f"\n  Chain Integrity: {'[OK] VALID' if valid else '[!!] COMPROMISED'}")
        print("=" * 55)

    def get_stats(self) -> Dict:
        total_tx = sum(len(b.transactions) for b in self.chain)
        return {
            "total_blocks":       len(self.chain),
            "total_transactions": total_tx,
            "chain_valid":        self.is_chain_valid(),
            "difficulty":         self.DIFFICULTY,
        }
