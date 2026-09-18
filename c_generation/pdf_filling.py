import fitz
import json
import io
import base64
from numpy import float64, int64
import pandas as pd
import random
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

#просто открытие изображения
def get_image_from_path(path):
    return Image.open(path)

#декодирование изображений из base64
def decode_image(img_base64_data):
    if img_base64_data == "":
        return None
    if img_base64_data.startswith('data:image'):
        img_base64_data = img_base64_data.split(',')[1]
    image_data = base64.b64decode(img_base64_data)
    img_bytes = io.BytesIO(image_data)
    img_bytes.seek(0)
    return img_bytes

#для преобразования текста в изображения (для дат)
def text_to_img(text):
    # Используем стандартный шрифт или указанный
    font = ImageFont.truetype("courier_new.ttf", 12)
    
    # Определяем размер текста
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Создаём изображение с прозрачным фоном (PNG)
    img = Image.new("RGBA", (text_width + 10, text_height + 10), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.text((5, 5), text, font=font, fill="black")
    
    # Конвертируем в байты
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    return img_bytes

#работа непосредственно с pdf
class Form:
    def __init__(self, name):
        self.rows = {}
        self.name = name
    #заполнение текстовых полей и галочек
    def filling_pdf(self, year):
        with open("pdf_fields.json", "r", encoding='utf-8') as fields_file:
            fields_json = json.load(fields_file)
            our_json = fields_json[self.name][str(year)]
        with fitz.open(f"forms/{self.name}/{year}.pdf") as doc:
            for field_our_name, field_value in self.rows.items():
                if not(field_value is None):
                    try:
                        field_name = our_json[field_our_name]
                    except KeyError:
                        #print(self.name, field_our_name)
                        continue
                    for page in doc:
                        for field in page.widgets():
                            if field.field_name == field_name:
                                # print(self.name, field_our_name, field.field_type, type(field_value))
                                # Для чекбоксов
                                if field.field_type == 2:  # Тип 2 = Checkbox
                                    field.field_value = field_value  # True/False
                                # Для текстовых полей
                                elif field.field_type == 1 or field.field_type == 7:
                                    # Установка атрибутов текста
                                    field.text_color = [0, 0, 0]  # Цвет
                                    field.text_font = "Cour"    # Шрифт
                                    field.text_size = 12    # Размер
                                    field.update()
                                    if type(field_value) == int or type(field_value) == float or type(field_value) == float64 or type(field_value) == int64:
                                        field.field_value = "{:,.2f}".format(round(field_value, 2))
                                    else:
                                        field.field_value = str(field_value).upper()
                                field.update()
                                break
                        # else:
                            # print(page, field_our_name)
            doc.save(self.name+"_redacted.pdf")
    #добавление картинок (в уже заполненную форму)
    def insert_image(self, page_num, coords, img_bytes):
        if img_bytes == None:
            return
        #"рокируем" навзвания файлов
        os.rename(self.name+"_redacted.pdf", self.name+"_redacted1.pdf")
        with fitz.open(self.name+"_redacted1.pdf") as doc:
            page = doc[page_num]
            rect = fitz.Rect(*coords)
            page.insert_image(rect, stream=img_bytes.read())
            doc.save(self.name+"_redacted.pdf")
        os.remove(self.name+"_redacted1.pdf")
    #"абстрактный метод"
    def insert_need_images(self):
        pass
    
    def filling_transcript1120(self):
        with fitz.open(f"forms/{self.name}.pdf") as doc:
            for page in doc:
                for field in page.widgets():
                    if field.field_name in self.rows:
                        field_name = field.field_name
                        field_value = self.rows[field_name]
                        if type(field_value) == int or type(field_value) == float or type(field_value) == float64 or type(field_value) == int64:
                            field_value = "$"+"{:,.2f}".format(field_value)
                        else:
                            field_value = str(field_value).upper()
                        if not(field_name in ("Request_Date", "Response_Date", "Tracking_Number", "EIN_Provided", "Tax_Year", "Spouse_SSN", "SSN", "Name", "Address", "Cycle_Posted", "Received_Data", "PTIN", "EIN_Preparer")):
                            #print(field_name, field.text_maxlen)
                            max_len = field.text_maxlen
                            # Формируем строку: значение + точки до max_len
                            filled_text = '.' * (max_len - len(field_value)) + field_value
                            # Заполняем поле
                            field.field_value = filled_text
                        else:
                            field.field_value = field_value
                        field.update()
            doc.save(self.name+"_redacted.pdf")