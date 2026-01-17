from node import Node
from discovery import Discovery
from ring import Ring
from election import Election
import time

print("=" * 60)
print("VOLLSTÄNDIGER SYSTEM-TEST")
print("Distributed Shopping List - Peer-to-Peer System")
print("=" * 60)

# 3 Nodes erstellen
print("\n[1/6] Erstelle 3 Nodes...")
node1 = Node()
node2 = Node()
node3 = Node()

# Discovery starten
print("\n[2/6] Starte Discovery Services...")
disc1 = Discovery(node1)
disc2 = Discovery(node2)
disc3 = Discovery(node3)

disc1.start()
time.sleep(0.3)
disc2.start()
time.sleep(0.3)
disc3.start()

print("Warte 2 Sekunden auf Peer Discovery...")
time.sleep(2)

print(f"\nNode 1 kennt {len(disc1.get_peers())} Peers")
print(f"Node 2 kennt {len(disc2.get_peers())} Peers")
print(f"Node 3 kennt {len(disc3.get_peers())} Peers")

# Ring erstellen
print("\n[3/6] Erstelle Ring Topology...")
ring1 = Ring(node1, disc1)
ring2 = Ring(node2, disc2)
ring3 = Ring(node3, disc3)

ring1.update_ring()
ring2.update_ring()
ring3.update_ring()

# Election vorbereiten
print("\n[4/6] Initialisiere Leader Election...")
elec1 = Election(node1, ring1)
elec2 = Election(node2, ring2)
elec3 = Election(node3, ring3)

elec1.start()
elec2.start()
elec3.start()

time.sleep(0.5)

# Leader Election durchführen
print("\n[5/6] Führe Leader Election durch (Chang-Roberts)...")
elec1.start_election()
time.sleep(2)

# Zeige Leader
leader_node = None
leader_name = ""
if node1.is_leader:
    leader_node = node1
    leader_name = "Node 1"
elif node2.is_leader:
    leader_node = node2
    leader_name = "Node 2"
elif node3.is_leader:
    leader_node = node3
    leader_name = "Node 3"

print(f"\nLEADER: {leader_name} ({leader_node.id[:8]})")

# Coordinator starten
print("\n[6/6] Starte Coordinator für Synchronisation...")
node1.set_coordinator(elec1)
node2.set_coordinator(elec2)
node3.set_coordinator(elec3)

node1.start_coordinator()
node2.start_coordinator()
node3.start_coordinator()

time.sleep(0.5)

# DEMO: Shopping-Liste befüllen
print("\n" + "=" * 60)
print("DEMO: Synchronisierte Shopping-Liste")
print("=" * 60)

print("\n[AKTION] Node 1 fügt 'Milch' hinzu...")
node1.send_to_leader("add", "Milch")
time.sleep(0.3)

print("[AKTION] Node 2 fügt 'Brot' hinzu...")
node2.send_to_leader("add", "Brot")
time.sleep(0.3)

print("[AKTION] Node 3 fügt 'Eier' hinzu...")
node3.send_to_leader("add", "Eier")
time.sleep(0.3)

print("\n[STATUS] Shopping-Listen nach Hinzufügen:")
print(f"Node 1: {node1.shopping_list.get_items()}")
print(f"Node 2: {node2.shopping_list.get_items()}")
print(f"Node 3: {node3.shopping_list.get_items()}")

print("\n[AKTION] Node 1 entfernt 'Brot'...")
node1.send_to_leader("remove", "Brot")
time.sleep(0.3)

print("\n[STATUS] Shopping-Listen nach Entfernen:")
print(f"Node 1: {node1.shopping_list.get_items()}")
print(f"Node 2: {node2.shopping_list.get_items()}")
print(f"Node 3: {node3.shopping_list.get_items()}")

# Verifikation
print("\n" + "=" * 60)
print("VERIFIKATION")
print("=" * 60)

lists_equal = (
    node1.shopping_list.get_items() == 
    node2.shopping_list.get_items() == 
    node3.shopping_list.get_items()
)

if lists_equal:
    print("\nERFOLG: Alle Nodes haben die identische Shopping-Liste!")
    print("Das System funktioniert korrekt.")
else:
    print("\nFEHLER: Listen sind nicht synchron!")

# Zeige finale Listen
print("\nFinale Shopping-Liste:")
for i, item in enumerate(node1.shopping_list.get_items(), 1):
    print(f"  {i}. {item}")

# Aufräumen
print("\n" + "=" * 60)
print("Stoppe alle Services...")
node1.stop_coordinator()
node2.stop_coordinator()
node3.stop_coordinator()
elec1.stop()
elec2.stop()
elec3.stop()
disc1.stop()
disc2.stop()
disc3.stop()

print("\nTest abgeschlossen.")
print("=" * 60)