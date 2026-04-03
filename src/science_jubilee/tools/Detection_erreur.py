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
        
        # =========================
        # DETECTION DU PUIT CENTRAL
        # =========================

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Amélioration du contraste local (très efficace ici)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)

        # Réduction du bruit tout en gardant les bords
        gray = cv2.bilateralFilter(gray, 9, 75, 75)

        # Détection de contours
        edges = cv2.Canny(gray, 50, 150)

        # HoughCircles pour détecter les cercles (puits),  paramètres adaptés pour une autre de caméra de Z = 90
        circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, dp=1, minDist=100, param1=50, param2=50, minRadius=30, maxRadius=200)

        #on identifie le cercle le plus au centre de l'image
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            img_center = (img.shape[1] // 2, img.shape[0] // 2)
            closest_circle = min(circles, key=lambda c: np.linalg.norm((c[0] - img_center[0], c[1] - img_center[1])))
            x, y, r = closest_circle
            cv2.circle(img, (x, y), r, (255, 0, 0), 2)
            cv2.circle(img, (x, y), 2, (255, 0, 0), 3)
        

        # =========================
        # MASQUE DE RECHERCHE - ZONE INTERIEURE DU PUIT CENTRAL
        # ========================= 
    
        mask = np.zeros_like(gray)
        if circles is not None:
            cv2.circle(mask, (x, y), r-5, 255, -1)  # masque légèrement plus petit que le cercle détecté
        masked_img = cv2.bitwise_and(img, img, mask=mask)
        
        # =========================
        # DETECTION DU VERT (ROBUSTE REFLETS)
        # =========================
        hsv = cv2.cvtColor(masked_img, cv2.COLOR_BGR2HSV)

        # seuil resserré (important avec reflets)
        lower_green = np.array([40, 80, 80])
        upper_green = np.array([85, 255, 255])

        green_mask = cv2.inRange(hsv, lower_green, upper_green)

        # nettoyage agressif pour éliminer les reflets et le bruit
        kernel = np.ones((7, 7), np.uint8)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)


        # =========================
        # DETECTION LENTILLE
        # =========================
        contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        lens_found = False

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 10:  # seuil de surface à ajuster selon ton image
                lens_found = True
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # =========================
        # RESULTAT
        # =========================
        
        cv2.waitKey(0)

        if lens_found:
            print("✅ Lentille détectée")
            return True
        else:
            print("❌ Pas de lentille dans ton image")
            return False
