# Dimensions et conversions
MM_TO_PIX = 3 
PLATEAU_W_MM = 305
PLATEAU_H_MM = 305
DIAMETRE_TROU = 3
OFFSET_TROU_BAS_X = 15.39
OFFSET_TROU_BAS_y = 5
OFFSET_TROU_HAUT_X = 5
OFFSET_TROU_HAUT_Y = 1.5
OFFSET_CONTOUR = 5

PLATEAU_W = PLATEAU_W_MM * MM_TO_PIX
PLATEAU_H = PLATEAU_H_MM * MM_TO_PIX

MARGIN_BETWEEN_OBJECTS = 5 
MARGIN_BORDER = 10 
MARGIN_BORDER_PX = MARGIN_BORDER * (PLATEAU_H / PLATEAU_H_MM)
MARGIN_BETWEEN_OBJECTS_PX = MARGIN_BETWEEN_OBJECTS * (PLATEAU_H / PLATEAU_H_MM)

TAGS_PROTEGES = {
    "__background__", "__grid__", "plateau_marge", "slot_text",
    "outil_1", "outil_2", "outil_3", "outil_4",
    "slot_text_1", "slot_text_2", "slot_text_3", "slot_text_4"
}

OUTIL_SLOTS = {
    1: {"x": 200, "y": 100},
    2: {"x": 200, "y": 300},
    3: {"x": 200, "y": 500},
    4: {"x": 200, "y": 700},
}

OUTILS_LISTE = ["None", "Pipette", "Inoculator", "Fluo", "Other"]

TOOLS = {
    "Plaque 24 puits": {"w_mm": 127.76, "h_mm": 85.48, "json": "greiner_24_wellplate_3300ul_orth.json"},
    "Réservoir eau": {"w_mm": 50, "h_mm": 30, "json": "pot_de_d'eau.json"},
    "Réservoir lentilles": {"w_mm": 30, "h_mm": 30, "json": "pot_de_lentille.json"}
}