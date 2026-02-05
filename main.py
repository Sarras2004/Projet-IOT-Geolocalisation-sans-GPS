from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
import base64
import math
import os
from datetime import datetime

app = FastAPI()

# --- CONFIGURATION ---
DB_FILE = "wifi_map.db"  # Ton fichier SQLite
TABLE_NAME = "access_points"

# Configuration pour que le HTML puisse parler au Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stockage de l'itinéraire (Liste de points)
# Format : [ {"lat": 48.8, "lon": 2.3, "time": "14:00:01"}, ... ]
position_history = []

# --- FONCTIONS UTILES ---

def get_ap_coords(mac_address):
    """ Cherche les coordonnées d'une MAC dans wifi_map.db """
    if not os.path.exists(DB_FILE):
        print(f"[ERREUR] Base de données introuvable : {DB_FILE}")
        return None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # On met en majuscule pour être sûr de trouver
        cursor.execute(f"SELECT lat, lon, ssid FROM {TABLE_NAME} WHERE mac = ?", (mac_address.upper(),))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"lat": result[0], "lon": result[1], "ssid": result[2]}
        return None
    except Exception as e:
        print(f"[ERREUR SQL] {e}")
        return None

def calculate_triangulation(routers_list):
    """ 
    Calcule la position par moyenne pondérée (Barycentre).
    Plus le signal (RSSI) est fort, plus le routeur 'attire' la position.
    """
    if not routers_list:
        return None

    lat_sum = 0
    lon_sum = 0
    total_weight = 0
    
    print("\n--- Calcul de Triangulation ---")

    for r in routers_list:
        # Formule de poids : on favorise exponentiellement les signaux forts
        # RSSI -50 (fort) => Poids élevé
        # RSSI -90 (faible) => Poids faible
        weight = math.pow(10, (float(r['rssi']) + 100) / 20)
        
        lat_sum += r['lat'] * weight
        lon_sum += r['lon'] * weight
        total_weight += weight
        
        print(f" [AP] {r['ssid']} ({r['mac']}) | RSSI: {r['rssi']} | Poids: {weight:.2f}")

    if total_weight > 0:
        final_lat = lat_sum / total_weight
        final_lon = lon_sum / total_weight
        return {"lat": final_lat, "lon": final_lon}
    else:
        return None

# --- ROUTES API ---

@app.post("/webhook")
async def receive_ttn_data(request: Request):
    global position_history
    try:
        body = await request.json()
        
        # Vérification que le message contient des données
        if "uplink_message" not in body or "frm_payload" not in body['uplink_message']:
            return {"status": "ignored", "reason": "No payload"}

        # 1. Décodage du Base64 (Format Brut TTN)
        raw_payload = body['uplink_message']['frm_payload']
        payload_bytes = base64.b64decode(raw_payload)
        
        found_routers = []
        
        # 2. Lecture par blocs de 7 octets (6 octets MAC + 1 octet RSSI)
        # Ex: [MAC1][MAC2][MAC3][MAC4][MAC5][MAC6][RSSI]
        for i in range(0, len(payload_bytes), 7):
            if i + 6 >= len(payload_bytes): break
            
            # Extraction MAC
            mac_bytes = payload_bytes[i:i+6]
            mac_str = ":".join("{:02X}".format(b) for b in mac_bytes)
            
            # Extraction RSSI (convertir l'octet non signé en entier signé)
            rssi_byte = payload_bytes[i+6]
            rssi = rssi_byte - 256 if rssi_byte > 127 else rssi_byte
            
            # 3. Recherche dans la DB
            info = get_ap_coords(mac_str)
            if info:
                found_routers.append({
                    "mac": mac_str,
                    "rssi": rssi,
                    "lat": info['lat'],
                    "lon": info['lon'],
                    "ssid": info['ssid']
                })

        # 4. Calcul de la position finale
        if found_routers:
            pos = calculate_triangulation(found_routers)
            
            # Ajout du timestamp
            pos["time"] = datetime.now().strftime("%H:%M:%S")
            
            # Enregistrement dans l'historique
            position_history.append(pos)
            
            print(f" >>> NOUVELLE POSITION CALCULÉE : {pos['lat']}, {pos['lon']}")
            return {"status": "success", "lat": pos['lat'], "lon": pos['lon']}
        else:
            print(" >>> AUCUN ROUTEUR CONNU DÉTECTÉ DANS CE MESSAGE.")
            return {"status": "no_match"}

    except Exception as e:
        print(f"[ERREUR CRITIQUE] {e}")
        return {"status": "error"}

@app.get("/history")
async def get_history():
    """ Renvoie tout le trajet au format JSON pour la carte """
    return position_history

@app.post("/reset")
async def reset_history():
    """ Efface le trajet """
    global position_history
    position_history = []
    print(" >>> Historique effacé !")
    return {"status": "cleared"}

if __name__ == "__main__":
    # Lancement du serveur
    uvicorn.run(app, host="0.0.0.0", port=8000)