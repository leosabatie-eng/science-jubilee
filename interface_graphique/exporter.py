"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : export_utils.py (ou nom de ton fichier)
Auteur      : [SABATIÉ Léo YAHIAOUI Rayan  / Projet industriel ROB4]
Date        : 10 Avril 2026
Description : Module de gestion des exports pour l'interface graphique.
              Gère la génération des fichiers de configuration (JSON), 
              des plans de découpe (DXF), et des parcours d'outils (G-code) 
              pour la configuration physique du plateau de la machine Jubilee.
=========================================================================================
"""

import json
import ezdxf
import math
import os
from constants import *


def export_led_pattern(light_data, filename="pattern_lumiere.json"):
    """
    Exporte les 24 valeurs des LEDs vers un fichier JSON destiné à être lu par l'ESP32.
    
    Args:
        light_data (dict): Dictionnaire contenant l'état des LEDs.
        filename (str): Nom du fichier de destination.
    """
    pattern = {str(k): v for k, v in light_data.items()}
    data = {"pattern": pattern}
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    print(f"✅ Pattern LED exporté -> {filename}")


def export_layout(placed_objects, slot_assignments, canvas, canvas_plateau, filename="experience.json"):
    """
    Exporte la configuration du plateau (positions des labwares et outils) en format JSON.
    Garantit que le fichier est sauvegardé dans le répertoire 'deck_definition' du projet.
    
    Args:
        placed_objects (list): Objets labwares placés sur le canvas.
        slot_assignments (dict): Assignation des outils aux emplacements.
        canvas (tk.Canvas): Le canvas de l'interface graphique.
        canvas_plateau (int): L'ID du plateau sur le canvas.
        filename (str): Le nom du fichier d'export.
    """
    # 1. Résolution dynamique des chemins pour garantir la portabilité
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    target_dir = os.path.join(project_root, "src", "science_jubilee", "decks", "deck_definition")

    # 2. Sécurisation de l'arborescence
    os.makedirs(target_dir, exist_ok=True)
    full_path = os.path.join(target_dir, filename)

    # 3. Récupération des dimensions et calcul des échelles (Pixels -> Millimètres)
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    plateau_w_px = x1_px - x0_px
    plateau_h_px = y1_px - y0_px
    scale_x = PLATEAU_W_MM / plateau_w_px
    scale_y = PLATEAU_H_MM / plateau_h_px

    # Structure de base du fichier de configuration Jubilee
    data = {
        "name": "Experience1", 
        "type": "SLAS", 
        "deck_offset": [0.0, 0.0],
        "slots": {}, 
        "tool_slots": {}
    }

    # Formatage des positions des labwares
    for idx, obj in enumerate(placed_objects):
        x1, y1, x2, y2 = canvas.coords(obj.id)
        
        # Conversion des coordonnées en millimètres
        y_mm = (x1 - x0_px) * scale_x
        x_mm = (y1 - y0_px) * scale_y
        w_mm = (x2 - x1) * scale_x
        h_mm = (y2 - y1) * scale_y

        data["slots"][str(idx)] = {
            "coordinates": [round(x_mm, 2), round(y_mm, 2)],
            "shape": "rectangle", 
            "width": round(w_mm, 2), 
            "length": round(h_mm, 2),
            "has_labware": True, 
            "labware": LABWARE[obj.name]["json"] if obj.name in LABWARE else None
        }

    # Formatage de l'assignation des outils
    for slot_id, tool in slot_assignments.items():
        if tool != "None": 
            data["tool_slots"][str(slot_id-1)] = tool  # Indexation à 0 pour le noyau Jubilee

    # 4. Écriture des données sur le disque
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Export JSON réussi dans : {full_path}")


def export_to_dxf(json_file="experience.json"):
    """
    Génère les plans de découpe vectoriels (DXF) à partir de la configuration JSON.
    Crée un plan complet et deux demi-plans optimisés pour la zone de travail d'une découpeuse laser.
    
    Args:
        json_file (str): Le fichier JSON source contenant les coordonnées.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    target_dir = os.path.join(project_root, "src", "science_jubilee", "decks", "deck_definition")

    json_path = os.path.join(target_dir, json_file)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture JSON: {e}")
        return

    milieu_x = PLATEAU_W_MM / 2
    jeu = 0.25  # Tolérance d'emboîtement (mm)

    # Définition des segments de découpe avec intégration des offsets de contour
    parties = [
        {
            "name": "plan_entier.dxf", 
            "x_min_zone": -OFFSET_CONTOUR, 
            "x_max_zone": PLATEAU_W_MM + 2*OFFSET_CONTOUR, 
            "offset_x": -OFFSET_CONTOUR
        },
        {
            "name": "plan_left.dxf",  
            "x_min_zone": -OFFSET_CONTOUR, 
            "x_max_zone": milieu_x, 
            "offset_x": -OFFSET_CONTOUR
        },
        {
            "name": "plan_right.dxf", 
            "x_min_zone": milieu_x, 
            "x_max_zone": PLATEAU_W_MM + 2*OFFSET_CONTOUR, 
            "offset_x": milieu_x
        }
    ]

    # Initialisation du document DXF principal (R2010 pour la compatibilité)
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 4  # Définition des unités en millimètres
    msp = doc.modelspace()

    # --- Fonctions de tracé utilitaires ---
    def draw_rectangle(x1, y1, x2, y2, layer="default"):
        msp.add_lwpolyline(
            [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
            close=True,
            dxfattribs={"layer": layer}
        )

    def trous_de_fixation(x1, y1, x2, y2):
        r = DIAMETRE_TROU / 2
        trous_positions = [
            (-OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y),                                # Bas Gauche
            (-OFFSET_TROU_LEFT_X, PLATEAU_H_MM - OFFSET_TROU_LEFT_Y),                 # Bas Droite
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y),                # Haut Gauche
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, PLATEAU_H_MM - OFFSET_TROU_RIGHT_Y)  # Haut Droite
        ]
        for x, y in trous_positions:
            msp.add_circle(center=(x, y), radius=r, dxfattribs={"layer": "fixation_holes"})

    # --- Tracé du plan complet ---
    x1, y1 = 0, 0
    x2, y2 = PLATEAU_W_MM, PLATEAU_H_MM

    draw_rectangle(x1, y1-2*OFFSET_CONTOUR, x2, y2+2*OFFSET_CONTOUR, layer="plateau")
    trous_de_fixation(x1, y1, x2, y2)

    slots = data.get("slots", {})
    for slot in slots.values():
        if not slot.get("has_labware", False):
            continue

        cx, cy = slot["coordinates"]
        w, h = slot.get("width", 0), slot.get("length", 0)

        # Conversion: coordonnées du centre -> coordonnées des coins
        lx1, ly1 = cx - w / 2, cy - h / 2
        lx2, ly2 = cx + w / 2, cy + h / 2
        draw_rectangle(lx1, ly1, lx2, ly2, layer="labware")

    
    # --- Tracé des sous-plans pour découpe laser ---
    for p in parties:
        doc = ezdxf.new(dxfversion="R2010")
        doc.header["$INSUNITS"] = 4 
        msp = doc.modelspace()
        
        off = p["offset_x"]

        def draw_rect(x1, y1, x2, y2, layer="default"):
            # Application de l'offset dynamique sur l'axe X
            pts = [(x1 - off, y1), (x2 - off, y1), (x2 - off, y2), (x1 - off, y2)]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

        # Contour du plateau tronqué
        draw_rect(p["x_min_zone"], 0, p["x_max_zone"], PLATEAU_H_MM, layer="plateau")

        # Trous de fixation filtrés selon la zone
        r = DIAMETRE_TROU / 2
        trous_positions = [
            (-OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y),
            (-OFFSET_TROU_LEFT_X, PLATEAU_H_MM - OFFSET_TROU_LEFT_Y),
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y),
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, PLATEAU_H_MM - OFFSET_TROU_RIGHT_Y)
        ]
        for tx, ty in trous_positions:
            if p["x_min_zone"] <= tx <= p["x_max_zone"]:
                msp.add_circle(center=(tx - off, ty), radius=r, dxfattribs={"layer": "fixation_holes"})

        # Labwares avec clipping horizontal si chevauchement
        for slot in slots.values():
            if not slot.get("has_labware", False): continue
            
            cx, cy = slot["coordinates"]
            w, h = slot.get("width", 0), slot.get("length", 0)
            
            lx1, lx2 = cx - jeu, cx + w + jeu
            ly1, ly2 = cy - jeu, cy + h + jeu

            # Vérification du chevauchement avec la zone active
            if lx2 > p["x_min_zone"] and lx1 < p["x_max_zone"]:
                draw_x1 = max(lx1, p["x_min_zone"])
                draw_x2 = min(lx2, p["x_max_zone"])
                draw_rect(draw_x1, ly1, draw_x2, ly2, layer="labware")

        doc.saveas(p["name"])
        print(f"✅ Export {p['name']} terminé.")


def json_to_gcode(json_file, gcode_file, z_up=30.0, z_down=20.0, feedrate=4000):
    """
    Traduit les positions géométriques d'un fichier JSON en commandes G-code 
    pour permettre à la machine Jubilee de dessiner le plan physique avec un stylo.
    
    Args:
        json_file (str): Fichier de configuration source.
        gcode_file (str): Fichier G-code de destination.
        z_up (float): Hauteur de dégagement de l'outil (Z).
        z_down (float): Hauteur de travail (Z).
        feedrate (int): Vitesse de déplacement (F).
    """
    # Résolution des chemins relatifs au projet
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    target_dir = os.path.join(project_root, "src", "science_jubilee", "decks", "deck_definition")

    json_path = os.path.join(target_dir, json_file)
    gcode_path = os.path.join(target_dir, gcode_file)
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture JSON ({json_path}): {e}")
        return

    with open(gcode_path, 'w', encoding='utf-8') as g:
        # --- INITIALISATION DE LA MACHINE ---
        g.write("; G-code genere directement depuis JSON\n")
        g.write("G21 ; Unites en mm\n")
        g.write("G90 ; Positionnement absolu\n")
        g.write(f"G0 Z{z_up} F600 ; Lever le stylo\n\n")

        # Séquence de verrouillage de l'outil
        param = "P"
        g.write(f"G4 {param}{4000}\n")
        g.write("G91\n")   
        g.write("G1 U10 F6000 H0\n") 
        g.write("G1 U200 F6000 H1\n") 
        g.write("G90\n\n") 

        # --- DÉFINITION DES OFFSETS PHYSIQUES ---
        x_0_0 = -4     # Décalage origine physique X
        y_0_0 = -43.5  # Décalage origine physique Y
        offset_stylo = 2

        # --- 1. DESSIN DU CONTOUR EXTERIEUR ---
        points_contour = [
            (x_0_0 + offset_stylo, y_0_0 + offset_stylo), 
            (PLATEAU_W_MM + x_0_0 - offset_stylo, y_0_0 + offset_stylo), 
            (PLATEAU_W_MM + x_0_0 - offset_stylo, PLATEAU_H_MM + y_0_0 - offset_stylo), 
            (x_0_0 + offset_stylo, PLATEAU_H_MM + y_0_0 - offset_stylo), 
            (x_0_0 + offset_stylo, y_0_0 + offset_stylo)
        ]
        
        g.write("; --- Contour Plateau ---\n")
        g.write(f"G0 X{points_contour[0][0]} Y{points_contour[0][1]} F{feedrate}\n")
        g.write(f"G1 Z{z_down} F800\n")
        for x, y in points_contour[1:]:
            g.write(f"G1 X{x:.3f} Y{y:.3f}\n")
        g.write(f"G1 Z{z_up} F600\n\n")

        # --- 2. DESSIN DES TROUS DE FIXATION ---
        g.write("; --- Trous de Fixation ---\n")
        r_hole = DIAMETRE_TROU / 2
        trous_pos = [
            (OFFSET_TROU_LEFT_Y + x_0_0, -OFFSET_TROU_LEFT_X + y_0_0),
            (PLATEAU_H_MM - OFFSET_TROU_LEFT_Y + x_0_0, -OFFSET_TROU_LEFT_X + y_0_0),
            (PLATEAU_W_MM - OFFSET_TROU_RIGHT_Y + x_0_0, PLATEAU_H_MM + OFFSET_TROU_RIGHT_X + y_0_0),
            (OFFSET_TROU_RIGHT_Y + x_0_0, PLATEAU_H_MM + OFFSET_TROU_RIGHT_X + y_0_0)
        ]
        
        for tx, ty in trous_pos:
            g.write(f"G0 X{tx + r_hole:.3f} Y{ty:.3f} F{feedrate}\n")
            g.write(f"G1 Z{z_down} F800\n")
            # Approximation du cercle en 32 segments linéaires
            for i in range(1, 33):
                angle = math.radians(i * (360/32))
                px = tx + r_hole * math.cos(angle)
                py = ty + r_hole * math.sin(angle)
                g.write(f"G1 X{px:.3f} Y{py:.3f}\n")
            g.write(f"G1 Z{z_up} F600\n\n")

        # --- 3. DESSIN DES EMPLACEMENTS LABWARES ---
        g.write("; --- Labwares ---\n")
        slots = data.get("slots", {})
        
        for slot in slots.values():
            if not slot.get("has_labware", False): continue
            
            x1, y1 = slot["coordinates"]
            w, h = slot.get("width", 0), slot.get("length", 0)
            
            x2 = x1 + h
            y2 = y1 + w
            
            # Application des offsets physiques sur les 4 coins
            pts = [
                (x1+x_0_0, y1+y_0_0), 
                (x2+x_0_0, y1+y_0_0), 
                (x2+x_0_0, y2+y_0_0), 
                (x1+x_0_0, y2+y_0_0), 
                (x1+x_0_0, y1+y_0_0)
            ]
            
            g.write(f"G0 X{pts[0][0]:.3f} Y{pts[0][1]:.3f} F{feedrate}\n")
            g.write(f"G1 Z{z_down} F800\n")
            for px, py in pts[1:]:
                g.write(f"G1 X{px:.3f} Y{py:.3f}\n")
            g.write(f"G1 Z{z_up} F600\n\n")

    print(f"✅ G-code généré avec succès : {gcode_path}")