import unittest
import subprocess
import time
import os
import sys
import signal
import random
import grpc
import yaml
from datetime import datetime
from pathlib import Path

# Add src to import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import handler_pb2
import handler_pb2_grpc

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
LOG_OUTPUT_PATH = Path(__file__).parent / "raft_test_log.txt"

def start_servers(num_servers=5):
    """Start each server in its own process with sys.argv[1] = i."""
    processes = []
    for i in range(num_servers):
        p = subprocess.Popen(["python", "server_grpc.py", str(i)])
        processes.append(p)
        time.sleep(0.5)  # small delay so they bind ports in order
    return processes

def get_leader(host: str, port: int):
    """Returns the leader_addr reported by a single server."""
    try:
        with grpc.insecure_channel(f"{host}:{port}") as channel:
            stub = handler_pb2_grpc.RaftStub(channel)
            resp = stub.GetLeader(handler_pb2.GetLeaderResponse())
            return resp.leader_addr
    except grpc.RpcError:
        return None

def log_leader_snapshot(clock_tick, leader_map, title):
    line = f"[{clock_tick:02d}s] " + ", ".join(f"{srv} → {ldr or 'None'}" for srv, ldr in leader_map.items())
    with open(LOG_OUTPUT_PATH, "a") as f:
        f.write(line + "\n")
    with open(LOG_OUTPUT_PATH, "a") as f:
        f.write(line + "\n")
    print(line)

def kill_processes(processes, indices):
    for idx in indices:
        p = processes[idx]
        p.kill()

def load_server_info():
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
    return [(s["host"], s["port"]) for s in config["servers"]]


def log_leader_table(leader_map, title=""):
    with open(LOG_OUTPUT_PATH, "a") as f:
        if title:
            f.write(f"\n=== {title} ===\n")
        f.write("Time: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        f.write("{:<10} | {}\n".format("Server", "Leader Seen"))
        f.write("-" * 30 + "\n")
        for server, leader in leader_map.items():
            f.write("{:<10} | {}\n".format(server, leader if leader else "N/A"))
        f.write("\n")


class TestRaftEdgeCases(unittest.TestCase):

    def tearDown(self):
        time.sleep(1)

    def test_1_server(self):
        processes = start_servers(num_servers=1)
        time.sleep(2)

        (host, port) = load_server_info()[0]
        leader = get_leader(host, port)

        self.assertIsNotNone(leader)
        log_leader_table({f"{host}:{port}": leader}, "Test 1 Server")
        # None leader dependent on n_servers
        if len(load_server_info()) == 1:
            self.assertEqual(leader, f"{host}:{port}")

        kill_processes(processes, range(1))

    def test_2_servers(self):
        processes = start_servers(2)
        time.sleep(3)

        servers = load_server_info()[:2]
        leader_map = {}
        for h, p in servers:
            leader_map[f"{h}:{p}"] = get_leader(h, p)

        log_leader_table(leader_map, "Test 2 Servers")
        if len(load_server_info()) < 4:
            self.assertTrue(any(leader_map.values()))  # at least one must return a leader

        kill_processes(processes, range(2))
        
    def test_5_servers(self):
        processes = start_servers(5)
        time.sleep(4)

        servers = load_server_info()
        leader_map = {}
        for h, p in servers:
            leader_map[f"{h}:{p}"] = get_leader(h, p)

        log_leader_table(leader_map, "Test 5 Servers")
        leaders = list(filter(None, leader_map.values()))
        self.assertTrue(len(set(leaders)) == 1)

        kill_processes(processes, range(5))

    def test_2_fault_tolerance(self):
        processes = start_servers(5)
        time.sleep(5)

        servers = load_server_info()[:5]

        initial_leader_map = {}
        for h, p in servers:
            initial_leader_map[f"{h}:{p}"] = get_leader(h, p)

        log_leader_table(initial_leader_map, "Before Fault Injection")

        # Kill 2 random servers
        dead_indices = random.sample(range(5), 2)
        kill_processes(processes, dead_indices)

        # Remove killed from server list
        survivors = [i for j, i in enumerate(servers) if j not in dead_indices]
        time.sleep(5)

        final_leader_map = {}
        for h, p in survivors:
            final_leader_map[f"{h}:{p}"] = get_leader(h, p)

        log_leader_table(final_leader_map, "After Killing 2 Servers")

        # Kill remaining
        alive_indices = [i for i in range(5) if i not in dead_indices]
        kill_processes(processes, alive_indices)

        leaders = list(filter(None, final_leader_map.values()))
        self.assertTrue(len(leaders) >= 1)

    def test_leader_tracking(duration=10, num_servers=5):
        """Tracks who each server thinks the leader is over N seconds."""
        servers = load_server_info()[:num_servers]
        duration = 10

        processes = start_servers(num_servers)

        print(f"Tracking leader election for {duration} seconds...\n")
        start_time = time.time()
        clock_tick = 0

        try:
            while time.time() - start_time < duration:
                leader_map = {}
                for host, port in servers:
                    key = f"{port}"
                    leader = get_leader(host, port)
                    leader_map[key] = leader.split(":")[-1] if leader else None
                log_leader_snapshot(clock_tick, leader_map, "Snapshot: Leader Election")
                time.sleep(1)
                clock_tick += 1
        finally:
            kill_processes(processes, range(num_servers))
            print("\nTracking complete. Log written to leader_tracking_log.txt")

    def test_leader_removal(self):
        """Start 5 servers, remove the current leader, verify a new leader is elected."""
        processes = start_servers(5)
        time.sleep(5)

        servers = load_server_info()
        leader_map = {f"{h}:{p}": get_leader(h, p) for h, p in servers}
        log_leader_table(leader_map, "Before Removing Leader")
        current_leaders = list(filter(None, leader_map.values()))
        self.assertTrue(len(set(current_leaders)) == 1)
        current_leader = current_leaders[0]

        # Find and kill the leader process
        leader_idx = None
        for i, (h, p) in enumerate(servers):
            if f"{h}:{p}" == current_leader:
                leader_idx = i
                break

        self.assertIsNotNone(leader_idx)
        kill_processes(processes, [leader_idx])
        time.sleep(5)

        # Check remaining servers for new leader
        remaining = [i for i in range(5) if i != leader_idx]
        new_leader_map = {}
        for i in remaining:
            h, p = servers[i]
            new_leader_map[f"{h}:{p}"] = get_leader(h, p)

        log_leader_table(new_leader_map, "After Removing Leader")

        leaders = list(filter(None, new_leader_map.values()))
        self.assertGreaterEqual(len(set(leaders)), 1)
        self.assertFalse(any(l == current_leader for l in leaders))

        kill_processes(processes, remaining)

    def test_snapshot_with_leader_kill(self):
        """Track leader perception across all servers and kill the leader mid-way."""
        num_servers = 5
        duration = 12
        kill_at_tick = 5

        servers = load_server_info()[:num_servers]
        processes = start_servers(num_servers)

        print(f"\nTracking leader evolution and killing leader at t={kill_at_tick}s\n")
        start_time = time.time()
        clock_tick = 0
        killed_leader = None
        leader_pid = None

        try:
            while time.time() - start_time < duration:
                leader_map = {}

                # Capture current leaders seen
                for host, port in servers:
                    key = f"{port}"
                    leader = get_leader(host, port)
                    leader_map[key] = leader.split(":")[-1] if leader else None

                log_leader_snapshot(clock_tick, leader_map, "Snapshot: Leader Killed")

                # Kill leader at specified tick
                if clock_tick == kill_at_tick and not killed_leader:
                    # Determine most common leader seen
                    leader_counts = {}
                    for leader in leader_map.values():
                        if leader:
                            leader_counts[leader] = leader_counts.get(leader, 0) + 1

                    if leader_counts:
                        current_leader_port = max(leader_counts, key=leader_counts.get)
                        for i, (h, p) in enumerate(servers):
                            if str(p) == current_leader_port:
                                print(f"[{clock_tick}s] Killing leader at port {p}")
                                os.kill(processes[i].pid, signal.SIGKILL)
                                killed_leader = f"{h}:{p}"
                                break

                time.sleep(1)
                clock_tick += 1
        finally:
            # Kill remaining processes
            for p in processes:
                if p.poll() is None:  # only if still alive
                    p.kill()

            print("\nSnapshot test complete. Log written to raft_test_log.txt")

if __name__ == "__main__":
    unittest.main(verbosity=2)
