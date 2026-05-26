"""
Parallel Mining Engine
-----------------------
Implements Proof-of-Work using Python threading.
Each worker thread independently searches a nonce range,
and the first to find a valid hash signals all others to stop.

Demonstrates PARALLEL COMPUTING: multiple concurrent hash
attempts coordinated via shared-memory synchronisation primitives.
Course: Parallel and Distributed Computing
"""

import hashlib
import json
import time
import threading
import multiprocessing
from typing import Optional, Dict, List

from blockchain import Block


# -----------------------------------------------------------------------
# Worker function (runs in a thread)
# -----------------------------------------------------------------------

def _mining_worker(
    worker_id:     int,
    block_data:    dict,
    start_nonce:   int,
    end_nonce:     int,
    difficulty:    int,
    result_holder: list,         # result_holder[0] set by winner
    stop_event:    threading.Event,
    lock:          threading.Lock,
):
    """
    Search nonces in [start_nonce, end_nonce) for a hash that satisfies
    the Proof-of-Work difficulty constraint.
    """
    prefix = "0" * difficulty

    for nonce in range(start_nonce, end_nonce):
        if stop_event.is_set():
            return

        data         = dict(block_data)
        data["nonce"] = nonce
        hash_val     = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

        if hash_val.startswith(prefix):
            with lock:
                if not stop_event.is_set():   # Only the first winner counts
                    stop_event.set()
                    result_holder[0] = {
                        "worker_id": worker_id,
                        "nonce":     nonce,
                        "hash":      hash_val,
                    }
            return


# -----------------------------------------------------------------------
# Mining Engine
# -----------------------------------------------------------------------

class ParallelMiner:
    """
    Parallel Proof-of-Work miner using threads.

    Splits the nonce space across ``num_workers`` threads.
    Each thread hashes independently; the first valid hash wins
    and all others are cancelled via a shared ``threading.Event``.
    """

    NONCE_RANGE_PER_WORKER = 200_000   # Each thread searches 200 k nonces

    def __init__(self, node_id: str, num_workers: Optional[int] = None):
        self.node_id     = node_id
        self.num_workers = num_workers or max(2, multiprocessing.cpu_count())
        print(f"  [Miner:{self.node_id}] Initialized with "
              f"{self.num_workers} parallel workers")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mine_block(self, block: Block, difficulty: int) -> Optional[Block]:
        """
        Mine ``block`` using parallel threads.
        Returns the block with nonce & hash set, or None on failure.
        """
        print(f"\n  [Miner:{self.node_id}] Starting parallel mining  "
              f"(difficulty={difficulty}, workers={self.num_workers})")

        t0     = time.time()
        result = self._parallel_search(block, difficulty)

        if result is None:
            print(f"  [Miner:{self.node_id}] No valid nonce found in search space.")
            return None

        elapsed            = time.time() - t0
        block.nonce        = result["nonce"]
        block.current_hash = result["hash"]
        block.mined_by     = self.node_id

        print(f"  [Miner:{self.node_id}] Block mined by Worker-{result['worker_id']}  "
              f"| Nonce={result['nonce']:,}  "
              f"| Hash={result['hash'][:20]}...  "
              f"| Time={elapsed:.4f}s")
        return block

    # ------------------------------------------------------------------
    # Internal parallel search
    # ------------------------------------------------------------------

    def _parallel_search(self, block: Block, difficulty: int) -> Optional[Dict]:
        """Launch worker threads and collect the winning result."""

        block_header = {
            "block_id":      block.block_id,
            "timestamp":     block.timestamp,
            "merkle_root":   block.merkle_root,
            "previous_hash": block.previous_hash,
            "nonce":         0,
        }

        result_holder = [None]
        stop_event    = threading.Event()
        lock          = threading.Lock()

        threads: List[threading.Thread] = []
        for i in range(self.num_workers):
            start = i * self.NONCE_RANGE_PER_WORKER
            end   = start + self.NONCE_RANGE_PER_WORKER
            t = threading.Thread(
                target=_mining_worker,
                args=(
                    i,
                    dict(block_header),
                    start,
                    end,
                    difficulty,
                    result_holder,
                    stop_event,
                    lock,
                ),
                daemon=True,
            )
            threads.append(t)
            print(f"    Worker-{i} started  (nonce range: {start:,} – {end:,})")

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return result_holder[0]

    # ------------------------------------------------------------------
    # Sequential fallback  (benchmark comparison)
    # ------------------------------------------------------------------

    def mine_sequential(self, block: Block, difficulty: int) -> Optional[Block]:
        """Single-threaded mining – used for performance comparison."""
        prefix      = "0" * difficulty
        t0          = time.time()
        total_range = self.num_workers * self.NONCE_RANGE_PER_WORKER

        block_header = {
            "block_id":      block.block_id,
            "timestamp":     block.timestamp,
            "merkle_root":   block.merkle_root,
            "previous_hash": block.previous_hash,
            "nonce":         0,
        }

        for nonce in range(total_range):
            block_header["nonce"] = nonce
            hash_val = hashlib.sha256(
                json.dumps(block_header, sort_keys=True).encode()
            ).hexdigest()
            if hash_val.startswith(prefix):
                block.nonce        = nonce
                block.current_hash = hash_val
                elapsed = time.time() - t0
                print(f"  [Sequential] Nonce={nonce:,}  "
                      f"Hash={hash_val[:20]}...  Time={elapsed:.4f}s")
                return block

        return None
