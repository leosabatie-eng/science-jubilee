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
            if etat == "avant":
                output_file = f"avant.jpg"
            else :
                output_file = f"après.jpg"
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
    
    def preprocess(img):
    # Conversion en Lab (plus stable à la lumière)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)
    
        # Normalisation du canal L pour réduire l'effet des reflets
        L = cv2.equalizeHist(L)
    
        lab = cv2.merge([L, A, B])
        img_norm = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
        # Flou léger pour lisser les reflets résiduels
        img_blur = cv2.GaussianBlur(img_norm, (5, 5), 0)
        
        return img_blur
    
    
    def extract_center_square(img, radius=100):
        h, w = img.shape[:2]
        cx, cy = w // 2, h // 2
        return img[cy-radius:cy+radius, cx-radius:cx+radius]
        
    def detect_diff(test = "test"):
        img1 = cv2.imread("avant.jpg")
        img2 = cv2.imread("après.jpg")

        #On extrait la zone centrale de chaque image pour se concentrer sur la lentille
        #img1 = self.extract_center_square(img1)
        #img2 = self.extract_center_square(img2)
        
    
        img1 = Detection_erreur.preprocess(img1)
        img2 = Detection_erreur.preprocess(img2)
    
        # Différence absolue
        diff = cv2.absdiff(img2, img1)
    
        # Carte de différence en niveaux de gris
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    
        # Binarisation pour mettre en évidence les différences significatives
        _, diff_thresh = cv2.threshold(diff_gray, 25, 255, cv2.THRESH_BINARY)
    
    
        #on parcours l'image binaire et on compte les pixels blancs pour détecter les différences significatives
        total_white_pixels = np.sum(diff_thresh == 255)
        if total_white_pixels < 10:
            print(f"Erreur détectée : l'action doit être relancé la lentille n'est pas présente")
        else:
            print("Aucune erreur détectée")