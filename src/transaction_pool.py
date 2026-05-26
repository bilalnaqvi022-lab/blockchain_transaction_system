"""
Transaction Pool Module
-----------------------
Manages pending (unconfirmed) transactions waiting to be mined.
Course: Parallel and Distributed Computing
"""

import threading
from typing import List, Dict, Optional
from wallet import verify_transaction_signature


class TransactionPool:
    """
    Thread-safe mempool for unconfirmed transactions.

    Multiple nodes may submit transactions concurrently, so all
    mutations are guarded by a reentrant lock.
    """

    def __init__(self, max_size: int = 100):
        self.max_size    = max_size
        self._pool: List[Dict] = []
        self._lock       = threading.RLock()
        self._seen_tx_ids = set()   # Prevent duplicates

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def add_transaction(self, transaction: Dict) -> bool:
        """
        Add a transaction to the pool.

        Returns True on success, False if rejected (duplicate,
        invalid signature, or pool full).
        """
        with self._lock:
            tx_id = transaction.get("tx_id")

            # Reject duplicates
            if tx_id in self._seen_tx_ids:
                print(f"  [Pool] Duplicate TX {tx_id} rejected.")
                return False

            # Reject invalid signatures
            if not verify_transaction_signature(transaction):
                print(f"  [Pool] TX {tx_id} has invalid signature – rejected.")
                return False

            # Reject if pool is full
            if len(self._pool) >= self.max_size:
                print(f"  [Pool] Pool full – TX {tx_id} dropped.")
                return False

            self._pool.append(transaction)
            self._seen_tx_ids.add(tx_id)
            print(f"  [Pool] [OK] TX {tx_id} accepted  "
                  f"({transaction['sender'][:10]}... -> "
                  f"{transaction['recipient'][:10]}...  "
                  f"Amt: {transaction['amount']})")
            return True

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_pending_transactions(self, limit: int = 10) -> List[Dict]:
        """Return up to `limit` transactions without removing them."""
        with self._lock:
            return list(self._pool[:limit])

    def pop_transactions(self, count: int = 10) -> List[Dict]:
        """Remove and return up to `count` transactions for block inclusion."""
        with self._lock:
            batch = self._pool[:count]
            self._pool = self._pool[count:]
            return batch

    def remove_confirmed(self, confirmed_tx_ids: List[str]):
        """Remove transactions that have been confirmed in a mined block."""
        with self._lock:
            self._pool = [
                tx for tx in self._pool
                if tx.get("tx_id") not in confirmed_tx_ids
            ]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._pool)

    def is_empty(self) -> bool:
        return self.size == 0

    def display(self):
        with self._lock:
            print(f"\n  === Transaction Pool ({self.size} pending) ===")
            if not self._pool:
                print("   (empty)")
                return
            for tx in self._pool:
                print(f"   TX {tx['tx_id']}  |  "
                      f"{tx['sender'][:12]}... -> "
                      f"{tx['recipient'][:12]}...  "
                      f"| {tx['amount']} coins")

    def __len__(self):
        return self.size

    def __repr__(self):
        return f"TransactionPool(size={self.size}/{self.max_size})"
