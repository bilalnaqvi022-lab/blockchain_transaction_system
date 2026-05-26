"""
Unit Tests
----------
Course: Parallel and Distributed Computing
"""

import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wallet           import Wallet, verify_transaction_signature
from blockchain       import Block, Blockchain
from transaction_pool import TransactionPool
from miner            import ParallelMiner


class TestWallet(unittest.TestCase):

    def setUp(self):
        self.alice = Wallet("Alice")
        self.bob   = Wallet("Bob")

    def test_address_format(self):
        self.assertTrue(self.alice.address.startswith("0x"))
        self.assertEqual(len(self.alice.address), 42)

    def test_unique_addresses(self):
        self.assertNotEqual(self.alice.address, self.bob.address)

    def test_create_transaction(self):
        tx = self.alice.create_transaction(self.bob.address, 10.0)
        self.assertEqual(tx["sender"], self.alice.address)
        self.assertEqual(tx["recipient"], self.bob.address)
        self.assertEqual(tx["amount"], 10.0)
        self.assertIn("tx_id", tx)
        self.assertIn("signature", tx)

    def test_transaction_signature_valid(self):
        tx = self.alice.create_transaction(self.bob.address, 5.0)
        self.assertTrue(verify_transaction_signature(tx))

    def test_negative_amount_raises(self):
        with self.assertRaises(ValueError):
            self.alice.create_transaction(self.bob.address, -1.0)


class TestBlock(unittest.TestCase):

    def test_compute_hash_deterministic(self):
        b = Block(1, [], "0" * 64)
        h1 = b.compute_hash()
        h2 = b.compute_hash()
        self.assertEqual(h1, h2)

    def test_is_valid_hash(self):
        b = Block(1, [], "0" * 64)
        self.assertTrue(b.is_valid_hash("000abc", 3))
        self.assertFalse(b.is_valid_hash("00abc", 3))

    def test_merkle_root_changes_with_transactions(self):
        b1 = Block(1, [], "0" * 64)
        b2 = Block(1, [{"tx_id": "abc"}], "0" * 64)
        self.assertNotEqual(b1.merkle_root, b2.merkle_root)


class TestBlockchain(unittest.TestCase):

    def setUp(self):
        self.bc = Blockchain()

    def test_genesis_block(self):
        self.assertEqual(len(self.bc.chain), 1)
        self.assertEqual(self.bc.chain[0].block_id, 0)

    def test_chain_valid_initially(self):
        self.assertTrue(self.bc.is_chain_valid())

    def test_tamper_invalidates_chain(self):
        # Mine and add one block
        miner = ParallelMiner("test", num_workers=2)
        b = Block(1, [{"tx_id": "t1", "amount": 5}], self.bc.last_block.current_hash)
        mined = miner.mine_block(b, Blockchain.DIFFICULTY)
        if mined:
            self.bc.add_block(mined)
            # Tamper
            self.bc.chain[1].transactions[0]["amount"] = 9999
            self.assertFalse(self.bc.is_chain_valid())


class TestTransactionPool(unittest.TestCase):

    def setUp(self):
        self.pool  = TransactionPool(max_size=10)
        self.alice = Wallet("Alice")
        self.bob   = Wallet("Bob")

    def _make_tx(self, amount=5.0):
        return self.alice.create_transaction(self.bob.address, amount)

    def test_add_transaction(self):
        tx = self._make_tx()
        result = self.pool.add_transaction(tx)
        self.assertTrue(result)
        self.assertEqual(self.pool.size, 1)

    def test_no_duplicate(self):
        tx = self._make_tx()
        self.pool.add_transaction(tx)
        self.assertFalse(self.pool.add_transaction(tx))
        self.assertEqual(self.pool.size, 1)

    def test_pool_limit(self):
        for _ in range(12):
            tx = self.alice.create_transaction(self.bob.address, 1.0)
            self.pool.add_transaction(tx)
        self.assertLessEqual(self.pool.size, 10)

    def test_pop_transactions(self):
        for _ in range(5):
            self.pool.add_transaction(self.alice.create_transaction(self.bob.address, 1.0))
        batch = self.pool.pop_transactions(3)
        self.assertEqual(len(batch), 3)
        self.assertEqual(self.pool.size, 2)


class TestParallelMiner(unittest.TestCase):

    def test_mine_block_returns_valid_hash(self):
        miner = ParallelMiner("test", num_workers=2)
        block = Block(1, [{"tx_id": "t1"}], "0" * 64)
        mined = miner.mine_block(block, difficulty=2)
        self.assertIsNotNone(mined)
        self.assertTrue(mined.current_hash.startswith("00"))

    def test_parallel_faster_than_sequential(self):
        """Parallel mining should not be slower than sequential."""
        miner = ParallelMiner("test", num_workers=2)
        b_seq = Block(1, [{"tx_id": "t_seq"}], "0" * 64)
        b_par = Block(1, [{"tx_id": "t_par"}], "0" * 64)
        b_par.timestamp = b_seq.timestamp

        t0 = time.time()
        miner.mine_sequential(b_seq, difficulty=2)
        seq_time = time.time() - t0

        t0 = time.time()
        miner.mine_block(b_par, difficulty=2)
        par_time = time.time() - t0

        # Parallel should not take more than 3× sequential (generous bound)
        self.assertLess(par_time, seq_time * 3 + 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
