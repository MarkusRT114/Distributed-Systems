from node import Node
from discovery import Discovery
from ring import Ring
from election import Election
import time

print("=" * 60)
print("TEST: Automatische Re-Election nach Leader-Crash")
print("=" * 60)

# 3 Nodes erstellen
node1 = Node()
node2 = Node()
node3 = Node()

disc1 = Discovery(node1)
disc2 = Discovery(node2)
disc3 = Discovery(node3)

disc1.start()
time.sleep(0.3)
disc2.start()
time.sleep(0.3)
disc3.start()

print("\n[INFO] Warte auf Peer Discovery...")
time.sleep(3)

# Ring erstellen
ring1 = Ring(node1, disc1)
ring2 = Ring(node2, disc2)
ring3 = Ring(node3, disc3)

ring1.update_ring()
ring2.update_ring()
ring3.update_ring()

# Election
elec1 = Election(node1, ring1)
elec2 = Election(node2, ring2)
elec3 = Election(node3, ring3)

elec1.start()
elec2.start()
elec3.start()

time.sleep(1)

# Leader Election
print("\n[INFO] Starte initiale Leader Election...")
elec1.start_election()
time.sleep(4)

# Finde Leader
if node1.is_leader:
    leader = node1
    leader_name = "Node 1"
    leader_disc = disc1
    leader_elec = elec1
    leader_ring = ring1
elif node2.is_leader:
    leader = node2
    leader_name = "Node 2"
    leader_disc = disc2
    leader_elec = elec2
    leader_ring = ring2
else:
    leader = node3
    leader_name = "Node 3"
    leader_disc = disc3
    leader_elec = elec3
    leader_ring = ring3

print(f"\n[INFO] Initialer Leader: {leader_name} ({leader.id[:8]})")

# Simuliere Leader-Crash
print("\n" + "=" * 60)
print("SIMULIERE LEADER-CRASH")
print("=" * 60)
print(f"\n[ACTION] Stoppe {leader_name}...")

leader_disc.stop()
leader_elec.stop()

print("\n[INFO] Warte 35 Sekunden auf Timeout-Detection und Re-Election...")
print("(Timeout ist 30 Sek + 5 Sek für Election)")

# Countdown
for i in range(35, 0, -5):
    print(f"  ... noch {i} Sekunden")
    time.sleep(5)

print("\n[INFO] Prüfe Leader-Status...")

remaining_nodes = []
remaining_rings = []
remaining_discs = []

if node1 != leader:
    remaining_nodes.append(("Node 1", node1))
    remaining_rings.append(ring1)
    remaining_discs.append(disc1)
if node2 != leader:
    remaining_nodes.append(("Node 2", node2))
    remaining_rings.append(ring2)
    remaining_discs.append(disc2)
if node3 != leader:
    remaining_nodes.append(("Node 3", node3))
    remaining_rings.append(ring3)
    remaining_discs.append(disc3)

print("\n" + "=" * 60)
print("ERGEBNIS:")
print("=" * 60)

for name, node in remaining_nodes:
    status = "LEADER" if node.is_leader else "Follower"
    peers = len([d for d in [disc1, disc2, disc3] if d.running])
    print(f"{name} ({node.id[:8]}): {status}")

# Prüfe ob ein neuer Leader gewählt wurde
new_leader_found = any(node.is_leader for _, node in remaining_nodes)

if new_leader_found:
    print("\nERFOLG: Automatische Re-Election funktioniert!")
    print("Ein neuer Leader wurde automatisch gewählt.")
else:
    print("\nKeine automatische Re-Election")
    print("Mögliche Gründe:")
    print("- Timeout zu kurz (aktuell 30 Sek)")
    print("- Election dauert zu lang")
    print("- TCP Ports blockiert")

# Cleanup
print("\n[INFO] Stoppe Services...")
for i, (name, node) in enumerate(remaining_nodes):
    ring = remaining_rings[i]
    disc = remaining_discs[i]
    
    if hasattr(ring, 'election') and ring.election:
        ring.election.stop()
    
    disc.stop()

print("\nTest abgeschlossen.")