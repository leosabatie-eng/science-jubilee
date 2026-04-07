import json
import logging
import os
import time
from itertools import dropwhile, takewhile
from typing import Iterator, List, Tuple, Union

import numpy as np
import requests

from science_jubilee.labware.Labware import Labware, Location, Well
from science_jubilee.tools.Tool import (
    Tool,
    ToolConfigurationError,
    ToolStateError,
    requires_active_tool,
)


class HTTPSyringe(Tool):
    def __init__(self, index, name, url, ip_raspberry="10.0.9.55"):
        """
        HTTP Syringe est un client pur : parle à Jubilee (url) et à notre serveur Pi.
        """
        self.name = name
        self.index = index
        self.url = url
        # ⚠ Port 5001 pour éviter le conflit avec OctoPrint
        self.url_materiel = f"http://{ip_raspberry}:5001"  

        # --- Initialisation HTTP standard de Jubilee ---
        config_r = requests.post(url + "/get_config", json={"name": name})
        config = config_r.json()
        super().__init__(index, **config, url=url)

        # Vérifie le serveur Pi
        self._init_gpio()

        # Status initial
        status_r = requests.post(url + "/get_status", json={"name": name})
        status = status_r.json()
        self.syringe_loaded = status.get("syringe_loaded", False)
        self.remaining_volume = status.get("remaining_volume", 0.0)

    def _init_gpio(self):
        """
        Initialise l'accès au Pi si ce n'est pas déjà fait.
        """
        if hasattr(self, "gpio_disponible"):
            return

        try:
            requests.get(f"{self.url_materiel}/capteur", timeout=2)
            self.gpio_disponible = True
            print(f"[{self.name}] ✅ Connecté au serveur matériel du Raspberry Pi.")
        except requests.exceptions.RequestException:
            self.gpio_disponible = False
            print(f"[{self.name}] ❌ ERREUR : Impossible de joindre le Pi sur {self.url_materiel}.")

    def lire_capteur(self):
        """
        Interroge le Pi pour obtenir la valeur immédiate du capteur.
        """
        self._init_gpio()
        if not getattr(self, "gpio_disponible", False):
            return None, None
        try:
            req = requests.get(f"{self.url_materiel}/capteur", timeout=2)
            reponse = req.json()
            tension = reponse.get("tension", 0.0)
            brute = reponse.get("brute", 0)
            return tension, brute
        except Exception:
            return None, None

    @requires_active_tool
    def avancer_jusqu_au_seuil(self, seuil: float = 1.0, timeout_sec: int = 5):
        self._init_gpio()
        if not getattr(self, "gpio_disponible", False):
            raise ToolStateError("Le serveur Pi n'est pas joignable.")

        print(f"[{self.name}] Ordre au Pi : Moteur forward (Attente seuil >= {seuil}V)")
        requests.post(f"{self.url_materiel}/moteur", json={"action": "forward", "speed": 1.0})
        
        start_time = time.time()
        try:
            while True:
                try:
                    req = requests.get(f"{self.url_materiel}/capteur", timeout=1)
                    tension_actuelle = req.json().get("tension", 0.0)
                except Exception:
                    tension_actuelle = 0.0 

                if tension_actuelle >= seuil:
                    print(f"[{self.name}] Seuil atteint ({tension_actuelle:.2f}V).")
                    break
                    
                if (time.time() - start_time) > timeout_sec:
                    print(f"[{self.name}] Timeout atteint ({timeout_sec}s).")
                    break
                    
                time.sleep(0.1)
                
        finally:
            requests.post(f"{self.url_materiel}/moteur", json={"action": "stop"})
            print(f"[{self.name}] Moteur arrêté.")

    @requires_active_tool
    def remplir_seringue(self, temps_secondes: float):
        self._init_gpio()
        if not getattr(self, "gpio_disponible", False):
            raise ToolStateError("Le serveur Pi n'est pas joignable.")

        temps_vide = 4.0
        print(f"[{self.name}] Vidage en cours pour {temps_vide} sec...")
        requests.post(f"{self.url_materiel}/moteur", json={"action": "forward", "speed": 1.0})
        time.sleep(temps_vide)

        print(f"[{self.name}] Remplissage en cours pour {temps_secondes} sec...")
        requests.post(f"{self.url_materiel}/moteur", json={"action": "backward", "speed": 1.0})
        time.sleep(temps_secondes)

        requests.post(f"{self.url_materiel}/moteur", json={"action": "stop"})
        print(f"[{self.name}] Remplissage terminé.")

        if hasattr(self, 'capacity'):
            self.remaining_volume = self.capacity

    def cleanup_gpio(self):
        if getattr(self, "gpio_disponible", False):
            try:
                requests.post(f"{self.url_materiel}/moteur", json={"action": "stop"})
            except:
                pass

    @classmethod
    def from_config(cls, index, fp):
        with open(fp) as f:
            kwargs = json.load(f)
        return cls(index, **kwargs)

    def status(self):
        r = requests.post(self.url + "/get_status", json={"name": self.name})
        status = r.json()
        self.syringe_loaded = status["syringe_loaded"]
        self.remaining_volume = status["remaining_volume"]
        return status

    def load_syringe(self, volume, pulsewidth):
        requests.post(self.url + "/load_syringe", json={"volume": volume, "pulsewidth": pulsewidth, "name": self.name})
        self.status()

    @requires_active_tool
    def _aspirate(self, vol, s):
        r = requests.post(self.url + "/aspirate", json={"volume": vol, "name": self.name, "speed": s})
        self.remaining_volume = requests.post(self.url + "/get_status", json={"name": self.name}).json()["remaining_volume"]

    @requires_active_tool
    def _dispense(self, vol, s):
        r = requests.post(self.url + "/dispense", json={"volume": vol, "name": self.name, "speed": s})
        self.remaining_volume = requests.post(self.url + "/get_status", json={"name": self.name}).json()["remaining_volume"]

    @requires_active_tool
    def dispense(self, vol: float, location: Union[Well, Tuple, Location], s: int = 100):
        x, y, z = Labware._getxyz(location)
        if isinstance(location, Well):
            self.current_well = location
            if z == location.z:
                z += 10
        elif isinstance(location, Location):
            self.current_well = location._labware
        self._machine.safe_z_movement()
        self._machine.move_to(x=x, y=y, wait=True)
        self._machine.move_to(z=z, wait=True)
        self._dispense(vol, s)

    @requires_active_tool
    def aspirate(self, vol: float, location: Union[Well, Tuple, Location], s: int = 100):
        x, y, z = Labware._getxyz(location)
        if isinstance(location, Well):
            self.current_well = location
        elif isinstance(location, Location):
            self.current_well = location._labware
        self._machine.safe_z_movement()
        self._machine.move_to(x=x, y=y, wait=True)
        self._machine.move_to(z=z, wait=True)
        self._aspirate(vol, s)

    @requires_active_tool
    def mix(self, vol: float, n_mix: int, location: Union[Well, Tuple, Location], t_hold: int = 1, s_aspirate: int = 100, s_dispense: int = 100):
        x, y, z = Labware._getxyz(location)
        self._machine.safe_z_movement()
        self._machine.move_to(x=x, y=y, wait=True)
        self._aspirate(500, s_aspirate)
        self._machine.move_to(z=z, wait=True)
        for _ in range(n_mix):
            self._aspirate(vol, s_aspirate)
            time.sleep(t_hold)
            self._dispense(vol, s_dispense)
            time.sleep(t_hold)
        self._dispense(500, s_dispense)

    def set_pulsewidth(self, pulsewidth: int, s: int = 100):
        requests.post(self.url + "/set_pulsewidth", json={"pulsewidth": pulsewidth, "name": self.name, "speed": s})
        self.status()
