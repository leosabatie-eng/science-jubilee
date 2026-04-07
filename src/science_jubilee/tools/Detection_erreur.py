import cv2
import numpy as np
import requests
from datetime import datetime
OCTOPI_IP = "10.0.9.55"  # Remplacez par l'adresse IP de votre OctoPi

class Detection_erreur:
    def capture_octopi_image(etat="" , url=f"http://{OCTOPI_IP}/webcam/?action=snapshot",output_file=None):
    # URL de l'OctoPi et nom de fichier de sortie
    
    # nom de fichier par défaut
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"apres.jpg"
        try:
            print("Connexion à OctoPi...")
            response = requests.get(url, timeout=5)
    
            if response.status_code == 200:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                    print(f"Image capturée et enregistrée : {output_file}")
            else:
                print(f"Erreur : statut HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion : {e}")


    
    def detect_lens():

        img = cv2.imread("apres.jpg")
        if img is None:
            raise ValueError("Image non chargée")
        
        #On conserve uniquement la zone centrale de l'image pour se concentrer sur le puits
        height, width = img.shape[:2]
        x_start = width * 2 // 5
        x_end = width * 3 // 5
        y_start = height * 2 // 5
        y_end = height * 4 // 5
        img = img[y_start:y_end, x_start:x_end]

        # =========================
        # Traitement de l'image pour améliorer la percetion du vert
        # =========================

        # Amélioration du contraste
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # =========================
        # DETECTION DU VERT (ROBUSTE REFLETS)
        # =========================
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # seuil de couleur vert pour détecter la lentille, ajusté pour être plus large
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([85, 255, 255])

        green_mask = cv2.inRange(hsv, lower_green, upper_green)

        # nettoyage agressif pour éliminer les reflets et le bruit
        kernel = np.ones((7, 7), np.uint8)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)

        #erosion et dilatation pour renforcer les contours
        green_mask = cv2.erode(green_mask, kernel, iterations=1)
        green_mask = cv2.dilate(green_mask, kernel, iterations=1)


        # =========================
        # DETECTION LENTILLE
        # =========================
        contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        lens_found = False

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 5:  # seuil de surface à ajuster selon ton image
                lens_found = True
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # =========================
        # RESULTAT
        # =========================


        if lens_found:
            print("✅ Lentille détectée, nombre de lentilles : ", len(contours))
            return True
        else:
            print("❌ Pas de lentille dans ton image")
            return False
    
