from paddleocr import PaddleOCR
import cv2
import pymupdf
import numpy as np


def preprocessing(img):
    
    if img is None:
        print(0)
        exit(0)
    gray_img= cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_img = cv2.medianBlur(gray_img, 3)
    canny= cv2.Canny(gray_img,50,255)

    #Contout enhancement
    clahe = cv2.createCLAHE( clipLimit=2.0, tileGridSize=(8, 8) )
    gray_img = clahe.apply(gray_img)

    # Find contours
    contours, _ = cv2.findContours(canny, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE )

    largest_contour= max(contours, key=cv2.contourArea)

    #Skewed bounding rect
    rect = cv2.minAreaRect(largest_contour)

    # Extract angle of skew
    angle = rect[2]

    if angle < -45:
        angle = 90 + angle

    # Rotate the original image
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    deskewed = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return deskewed


#Text Recognition
class TextRecog:
    
    def __init__(self, image=None, document=None):
        self.image=image
        self.document= document
        self.ocr= PaddleOCR()

    def get_image(self, image=None):  
        if image is None:
            image= self.image
        result = self.ocr.predict(self.image)
        all_text=[]
        for res in result:
            all_text.extend(res["rec_texts"])
        
        return " ".join(all_text)
    
    def check_pdf(self):
        total_page_area = 0.0
        total_text_area = 0.0

        doc = pymupdf.open(self.document)

        for page_num, page in enumerate(doc):
            total_page_area = total_page_area + abs(page.rect)
            text_area = 0.0
            for b in page.get_text_blocks():
                r = pymupdf.Rect(b[:4])  # rectangle where block text appears
                text_area = text_area + abs(r)
            total_text_area = total_text_area + text_area
        doc.close()
        percentage= total_text_area / total_page_area
        
        if (percentage <0.01):
            return 0
        
        return 1
    
    def get_document(self):
        if (self.check_pdf()==0):
            doc= pymupdf.open(self.document)
            doc_text=[]
            for page in doc:
                page_text=[]
                pix= page.get_pixmap()
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                else:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    
                final_image= preprocessing(img)
                text= self.get_image(final_image)
                text = " ".join(text.split())
                page_text.append(text)
                
                " ".join(page_text)
                "\n".join(doc_text, page_text)
            return doc_text
        
        else:
            pdf = pymupdf.open(self.document)
            doc_text=[]

            for page in pdf:
                text = page.get_text()
                text = " ".join(text.split())
                doc_text.append(text)                
            return "\n".join(doc_text)
            
def process_input(file_path):

    if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff")):

        image = cv2.imread(file_path)

        image = preprocessing(image)

        text_recog = TextRecog(image=image)

        return text_recog.get_image()


    elif file_path.lower().endswith(".pdf"):

        text_recog = TextRecog(document=file_path)

        return text_recog.get_document()


    else:

        return "Unsupported file type."





    
