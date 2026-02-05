
## Description
Ce projet implémente un système de géolocalisation basse consommation conçu pour les environnements où le GPS est inefficace ou trop gourmand en énergie (intérieur, zones urbaines denses). Le système scanne les points d'accès WiFi environnants, transmet leurs identifiants via le réseau LoRaWAN, et calcule la position finale sur un serveur distant en utilisant une base de données de référence.

---

## Architecture du Système

### 1. Collecte des données (Hardware)
Le nœud capteur est basé sur un microcontrôleur ESP32 et un modem LoRa E5.

* **Fichier :** projetiot.ino
* **Scan WiFi :** L'appareil effectue un scan passif des réseaux environnants. 
* **Optimisation :** Pour respecter les contraintes de bande passante LoRaWAN, seuls les 3 signaux les plus forts sont conservés.

### 2. Transmission LoRaWAN
Les données sont envoyées vers le réseau The Things Network (TTN).

* **Identifiants :** Les clés de connexion (DevEUI, AppKey) sont configurées en début de fichier (lignes 10-12).
* **Format du Payload :** Les données sont formatées en hexadécimal pour minimiser la taille du message. Chaque point d'accès occupe 7 octets : 6 octets pour l'adresse MAC (BSSID) et 1 octet pour la puissance du signal (RSSI).
* **Envoi :** La commande AT+CMSGHEX est utilisée pour transmettre le paquet binaire.

### 3. Serveur de Traitement (Backend)
Le backend est développé avec FastAPI et traite les données reçues via un Webhook.

* **Fichier :** main.py
* **Réception :** Le point d'entrée /webhook réceptionne les données de TTN (ligne 74), décode le Base64 et découpe le payload par blocs de 7 octets (ligne 89).
* **Base de Données :** Le serveur interroge wifi_map.db pour convertir les adresses MAC en coordonnées géographiques réelles (ligne 104).
* **Algorithme :** La position est déterminée par une triangulation par barycentre pondéré (ligne 50).

### 4. Visualisation (Frontend)
Une interface web permet de suivre le déplacement en temps réel sur une carte.

* **Fichier :** map.html
* **Cartographie :** Utilisation de la bibliothèque Leaflet.js pour l'affichage des cartes OpenStreetMap (lignes 8-9).
* **Flux de données :** Le client JavaScript effectue une requête GET vers l'endpoint /history du serveur toutes les 2 secondes pour mettre à jour l'itinéraire (lignes 111 et 161).

---

## Structure des Fichiers

| Fichier | Description |
| :--- | :--- |
| projetiot.ino | Code source Arduino pour l'ESP32 et le module LoRa. |
| main.py | Serveur API FastAPI et logique de calcul de position. |
| map.html | Interface de visualisation cartographique (Leaflet). |
| wifi_map.db | Base de données SQLite contenant les positions des bornes WiFi. |
| IOT.pdf | Documentation technique et présentation du projet. |

