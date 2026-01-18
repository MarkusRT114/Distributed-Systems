from node import Node
from discovery import Discovery
from ring import Ring
from election import Election
import time
import sys

print("=" * 60)
print("INTERACTIVE DEMO - Distributed Shopping List")
print("=" * 60)

# Node erstellen
node = Node()
print(f"\n[INFO] Meine Node-ID: {node.id[:8]}")

# Discovery starten
disc = Discovery(node)
disc.start()

print("[INFO] Warte 3 Sekunden auf Peer Discovery...")
time.sleep(3)

# Ring erstellen
ring = Ring(node, disc)
ring.update_ring()

# Election
elec = Election(node, ring)
elec.start()

print("\n[INFO] Warte auf Election...")
time.sleep(2)

# Erste Election starten (nur wenn noch kein Leader)
if not node.current_leader_id:
    print("[INFO] Starte Election...")
    elec.start_election()
    time.sleep(3)

# Coordinator starten
node.set_coordinator(elec)
node.start_coordinator()

# Status anzeigen
def show_status():
    status = "LEADER" if node.is_leader else "Follower"
    peers = disc.get_peers()
    print(f"\n--- STATUS ---")
    print(f"Node: {node.id[:8]}")
    print(f"Port: {node.port}")
    print(f"Role: {status}")
    print(f"Peers: {len(peers)}")
    for peer_id, peer_info in peers.items():
        print(f"  - {peer_id[:8]} auf {peer_info['ip']}:{peer_info['port']}")
    print("--------------\n")

# Interaktive Schleife
print("\n" + "=" * 60)
print("BEFEHLE:")
print("  add <item>     - Item zur Liste hinzufuegen")
print("  remove <item>  - Item aus Liste entfernen")
print("  list           - Liste anzeigen")
print("  status         - Node-Status anzeigen")
print("  election       - Neue Election starten")
print("  quit           - Beenden")
print("=" * 60)

show_status()

while True:
    try:
        cmd = input("> ").strip()
        
        if not cmd:
            continue
        
        if cmd == "quit":
            print("\n[INFO] Beende Node...")
            disc.stop()
            elec.stop()
            node.stop_coordinator()
            break
        
        elif cmd == "list":
            items = node.shopping_list.get_items()
            if items:
                print("\nShopping-Liste:")
                for i, item in enumerate(items, 1):
                    print(f"  {i}. {item}")
            else:
                print("\nShopping-Liste ist leer")
        
        elif cmd == "status":
            show_status()
        
        elif cmd == "election":
            print("[INFO] Starte Election...")
            elec.start_election()
            time.sleep(2)
            show_status()
        
        elif cmd.startswith("add "):
            item = cmd[4:].strip()
            if item:
                node.send_to_leader("add", item)
                time.sleep(0.5)
                print(f"[OK] '{item}' hinzugefuegt")
            else:
                print("[ERROR] Bitte Item angeben: add <item>")
        
        elif cmd.startswith("remove "):
            item = cmd[7:].strip()
            if item:
                node.send_to_leader("remove", item)
                time.sleep(0.5)
                print(f"[OK] '{item}' entfernt")
            else:
                print("[ERROR] Bitte Item angeben: remove <item>")
        
        else:
            print("[ERROR] Unbekannter Befehl. Tippe 'list', 'add', 'remove', 'status', 'election' oder 'quit'")
    
    except KeyboardInterrupt:
        print("\n\n[INFO] Beende Node...")
        disc.stop()
        elec.stop()
        node.stop_coordinator()
        break
    except Exception as e:
        print(f"[ERROR] {e}")

print("\n[INFO] Node beendet.")