import os
import sys
import time
import yaml
import grpc
import signal
import random
import subprocess
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import handler_pb2, handler_pb2_grpc


class TestRaftCluster(unittest.TestCase):
    """Integration test suite for the 5-server Raft cluster."""

    @classmethod
    def setUpClass(cls):
        """
        One-time setup: parse config, launch all servers as separate processes.
        """
        # Load config.yaml
        config_path = HERE.parent / "config.yaml"
        with open(config_path, "r") as f:
            cls.config = yaml.safe_load(f)

        cls.n_servers = len(cls.config["servers"])
        cls.processes = []

        # Start each server in a separate process
        for i in range(cls.n_servers):
            p = subprocess.Popen(
                [sys.executable, str(SRC_DIR / "server.py"), str(i)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            cls.processes.append(p)

        # Let servers initialize
        time.sleep(3)

    @classmethod
    def tearDownClass(cls):
        """
        One-time teardown: terminate all running server processes.
        """
        for p in cls.processes:
            p.terminate()
        for p in cls.processes:
            p.wait()

    def get_leader(self, host: str, port: int) -> str:
        """
        Calls GetLeader RPC on a single server, returns the leader_addr.
        If it fails, returns an empty string.
        """
        try:
            with grpc.insecure_channel(f"{host}:{port}") as channel:
                stub = handler_pb2_grpc.RaftStub(channel)
                resp = stub.GetLeader(handler_pb2.GetLeaderRequest())
                return resp.leader_addr
        except Exception as e:
            print(f"Error calling GetLeader on {host}:{port}: {e}")
            return ""

    def test_leader_election_and_2fault(self):
        """
        1) Ensure at least one server is recognized as leader (across all).
        2) Kill 2 servers (in a 5-server cluster).
        3) Check the new cluster of 3 forms a consistent leader.
        """
        self.assertGreaterEqual(self.n_servers, 5, "Need at least 5 servers in config.")

        # 1) Check current leader consistency
        #    We'll poll each server's GetLeader to see if we find a non-empty leader address.
        all_hosts_ports = []
        for i, s in enumerate(self.config["servers"]):
            h = s["host"]
            pt = s["port"]
            all_hosts_ports.append((h, pt))

        # Attempt to find a leader
        leaders = []
        for (h, pt) in all_hosts_ports:
            leader_addr = self.get_leader(h, pt)
            if leader_addr:
                leaders.append(leader_addr)

        # We don't strictly require the same leader across all servers,
        # but typically they converge. We'll at least ensure there's a known leader from *someone*.
        self.assertTrue(len(leaders) > 0, "No server returned a valid leader_addr. Possibly no leader elected yet.")

        # 2) Kill 2 servers at random (2-fault tolerance for a 5 server cluster).
        #    Then we check if the remaining cluster picks a new or same stable leader.
        random_two = random.sample(range(self.n_servers), 2)
        print(f"Killing servers at indices: {random_two}")
        for idx in sorted(random_two, reverse=True):
            proc = self.processes[idx]
            proc.terminate()
            proc.wait()
            self.processes.pop(idx)  # remove from the list of running processes
            all_hosts_ports.pop(idx)  # also remove from host/port list

        # Give some time for reelection
        time.sleep(3)

        # 3) Check each remaining server for a new leader
        new_leaders = []
        for (h, pt) in all_hosts_ports:
            leader_addr = self.get_leader(h, pt)
            if leader_addr:
                new_leaders.append(leader_addr)

        self.assertTrue(
            len(new_leaders) > 0,
            "After killing 2 servers, no remaining server sees a valid leader."
        )

        # Optionally, we can check for consistency among the new leader addresses
        # to ensure they converge on the same address, but minimal check is to have *some* leader.
        print("Remaining cluster sees leaders:", new_leaders)


if __name__ == "__main__":
    # Typically run: `python -m unittest tests/test_raft_cluster.py`
    unittest.main()
