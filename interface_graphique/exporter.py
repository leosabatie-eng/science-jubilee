import json
import ezdxf
from constants import *

def export_layout(placed_objects, slot_assignments, canvas, canvas_plateau, filename="test1.json"):
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    plateau_w_px = x1_px - x0_px
    plateau_h_px = y1_px - y0_px
    scale_x = PLATEAU_W_MM / plateau_w_px
    scale_y = PLATEAU_H_MM / plateau_h_px
    bl_x_px, bl_y_px = x0_px, y0_px + plateau_h_px

    data = {
        "name": "Experience1", "type": "SLAS", "deck_offset": [0.0, 0.0],
        "slots": {}, "tool_slots": {}
    }

    for idx, obj in enumerate(placed_objects):
        x1, y1, x2, y2 = canvas.coords(obj.id)
        y_mm = (x1 - x0_px) * scale_x
        x_mm = (y1 - y0_px) * scale_y
        
        # Calcul des dimensions
        w_mm = (x2 - x1) * scale_x
        h_mm = (y2 - y1) * scale_y
        

        data["slots"][str(idx)] = {
            "coordinates": [round(x_mm, 2), round(y_mm, 2)],
            "shape": "rectangle", "width": round(w_mm, 2), "length": round(h_mm, 2),
            "has_labware": True, "labware": LABWARE[obj.name]["json"] if obj.name in LABWARE else None
        }

    for slot_id, tool in slot_assignments.items():
        if tool != "None": data["tool_slots"][str(slot_id-1)] = tool        #-1 car les slot commence à 0

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Export JSON OK -> {filename}")


def export_to_dxf(json_file="test1.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur lecture JSON: {e}")
        return

    # Le milieu reste basé sur la largeur utile du plateau
    milieu_x = PLATEAU_W_MM / 2
    jeu = 0.5 
    jeu1 = 0.25

    # On définit les deux fichiers
    # x_min/max_zone incluent désormais l'OFFSET_CONTOUR pour ne pas couper le tracé du contour
    parties = [
        {
            "name": "plan_left.dxf",  
            "x_min_zone": -OFFSET_CONTOUR, 
            "x_max_zone": milieu_x, 
            "offset_x": -OFFSET_CONTOUR # On commence le fichier à l'extrémité gauche du contour
        },
        {
            "name": "plan_right.dxf", 
            "x_min_zone": milieu_x, 
            "x_max_zone": PLATEAU_W_MM + 2*OFFSET_CONTOUR, 
            "offset_x": milieu_x
        }
    ]
    cout=0#enlever
    for p in parties:
        doc = ezdxf.new(dxfversion="R2010")
        doc.header["$INSUNITS"] = 4 
        msp = doc.modelspace()
        
        off = p["offset_x"]

        def draw_rect(x1, y1, x2, y2, layer="default"):
            # Application de l'offset X pour que le point le plus à gauche de la zone soit à X=0 dans le DXF
            pts = [(x1 - off, y1), (x2 - off, y1), (x2 - off, y2), (x1 - off, y2)]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

        # 1) CONTOUR DU PLATEAU
        # Ici, l'offset est appliqué en X (élargissement latéral)
        # On dessine de x_min_zone à x_max_zone pour que la ligne de coupe soit propre
        draw_rect(p["x_min_zone"], 0, p["x_max_zone"], PLATEAU_H_MM, layer="plateau")

        # 2) TROUS DE FIXATION
        r = DIAMETRE_TROU / 2
        trous_positions = [
            (-OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y),                          # Bas Gauche
            (-OFFSET_TROU_LEFT_X, PLATEAU_H_MM - OFFSET_TROU_LEFT_Y),           # Bas Droite
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y),         # Haut Gauche
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, PLATEAU_H_MM - OFFSET_TROU_RIGHT_Y) # Haut Droite
        ]
        
        for tx, ty in trous_positions:
            # On vérifie si le centre du trou tombe dans la zone découpée
            if p["x_min_zone"] <= tx <= p["x_max_zone"]:
                msp.add_circle(center=(tx - off, ty), radius=r, dxfattribs={"layer": "fixation_holes"})

        # 3) LABWARES (À CHEVAL)
        slots = data.get("slots", {})
        
        for slot in slots.values():
            if not slot.get("has_labware", False): continue
            
            cx, cy = slot["coordinates"]
            w, h = slot.get("width", 0), slot.get("length", 0)
            
            # Coordonnées réelles avec jeu
            lx1, lx2 = cx - jeu, cx + w + jeu
            ly1, ly2 = cy - jeu, cy + h + jeu

            l2x1, l2x2 = cx -jeu1, cx +w+jeu1#enlever
            l2y1, l2y2 =100+ cy -jeu1, 100+cy +h +jeu1#{eznlever}

            
            # Si l'objet touche ou traverse la zone
            if lx2 > p["x_min_zone"] and lx1 < p["x_max_zone"]:
                # Clipping horizontal strict sur les limites de la zone
                draw_x1 = max(lx1, p["x_min_zone"])
                draw_x2 = min(lx2, p["x_max_zone"])
                
                draw_rect(draw_x1, ly1, draw_x2, ly2, layer="labware")
                #enlever le if
                if cout==0:
                    draw_x21 = max(l2x1, p["x_min_zone"])
                    draw_x22 = min(l2x2, p["x_max_zone"])
                    draw_rect(draw_x21, l2y1, draw_x22, l2y2, layer="labware")
                    cout=1

        doc.saveas(p["name"])
        print(f"Export {p['name']} terminé.")