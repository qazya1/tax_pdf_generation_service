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

def fill_title_page(json_interface, CPA_firm_serie):
    CPA_name = CPA_firm_serie["CPA FIRM NAME"]
    CPA_info = CPA_name + "\n" + CPA_firm_serie["CPA FIRM ADDRESS"] + "\n" + CPA_firm_serie["CPA FIRM TOWN"] + ", " + CPA_firm_serie["CPA FIRM STATE"] + " " +CPA_firm_serie["CPA FIRM ZIP CODE"]
    CPA_phone = CPA_firm_serie["CPA FIRM PHONE NUMBER"]
    if CPA_phone == "ADD PHONE":
        CPA_phone = ""
    client_info = json_interface["firstName"] + " " + json_interface["lastName"] + "\n" + json_interface["residentialAddress"] + "\n" + json_interface["town"] + ", " + json_interface["state"] + " " +json_interface["zipCode"]
    rows = {
        "CPA_firm_info_title": CPA_info,
        "Client_info_title": client_info,
        "CPA_firm_info_1": CPA_info+"\n"+CPA_phone,
        "Client_info_1": client_info,
        "Client_name_1": json_interface["firstName"],
        "year": str(json_interface["year"]),
        "CPA_firm_name_1": CPA_name,
        "CPA_firm_info_2": CPA_info+"\n"+CPA_phone,
        "year2": str(json_interface["year"]),
        "Date1": datetime(year=json_interface["year"]+1, day=random.randint(1,28), month=random.randint(1,6)).strftime("%B %d, %Y"),
        "Client_info_2": client_info,
        "Client_name_2": json_interface["firstName"],
        "CPA_firm_name_2": CPA_name,
        "Client_name_3": json_interface["firstName"] + " " + json_interface["lastName"],
        "Date2": datetime(year=json_interface["year"]+1, day=random.randint(1,30), month=random.randint(7,12)).strftime("%B %d, %Y"),
        "CPA_firm_info_3": CPA_info
    }
    #bold_fields = ("Client_info_title", "CPA_firm_info_1", "CPA_firm_info_2", "year2")
    with fitz.open("forms/title.pdf") as doc:
        for field_name, field_value in rows.items():
            for page in doc:
                for field in page.widgets():
                    if field.field_name == field_name:
                        # print(self.name, field_name, field.field_type, type(field_value))
                        # Для текстовых полей
                        if field.field_type == 1 or field.field_type == 7:
                            # Установка атрибутов текста
                            field.text_color = [0, 0, 0]  # Цвет
                            # if field_name in bold_fields:
                                # field.text_font = "CoBo"
                            # else:
                                # field.text_font = "Cour"    # Шрифт
                            # if field_name == "year":
                                # field.text_size = 7
                            # else:
                                # field.text_size = 10    # Размер
                            field.update()
                            if type(field_value) == int or type(field_value) == float or type(field_value) == float64:
                                field.field_value = "{:,.2f}".format(field_value)
                            else:
                                field.field_value = str(field_value).upper()
                        field.update()
                        break
                # else:
                    # print(page, field_name)
        doc.save("title_redacted.pdf")

#работа непосредственно с pdf
class Form:
    def __init__(self, name):
        self.rows = {}
        self.name = name
    #заполнение текстовых полей и галочек
    def filling_pdf(self, year):
        year = min(2024, year)
        with open("pdf_fields.json", "r", encoding='utf-8') as fields_file:
            fields_json = json.load(fields_file)
            our_json = fields_json[self.name][str(year)]
        with fitz.open(f"forms/{self.name}/{year}.pdf") as doc:
            for field_our_name, field_value in self.rows.items():
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
                                    field.field_value = "{:,.2f}".format(field_value)
                                else:
                                    field.field_value = str(field_value).upper()
                            field.update()
                            break
                    # else:
                        # print(page, field_our_name)
            doc.save(self.name+"_redacted.pdf")
    #добавление картинок (в уже заполненную форму)
    def insert_image(self, page_num, coords, img_bytes):
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
    
    def filling_transcript(self):
        if self.name == "tax_transcript_employed" or self.name == "tax_transcript_se":
            with fitz.open(f"{self.name}.pdf") as doc:
                for page in doc:
                    for field in page.widgets():
                        field_name = field.field_name
                        field_value = self.rows[field_name]
                        if field_name == "Refund_Balance_Due":
                            name, value = field_value.split(",")
                            value = "$"+"{:,.2f}".format(float(value))
                            max_len = field.text_maxlen
                            filled_text = name + ":" + '.' * (max_len - len(value) - len(name) - 1) + value
                            field.field_value = filled_text
                        else:
                            if type(field_value) == int or type(field_value) == float or type(field_value) == float64 or type(field_value) == int64:
                                field_value = "$"+"{:,.2f}".format(field_value)
                            else:
                                field_value = str(field_value).upper()
                            if not(field_name in ("Request_Date", "Response_Date", "Tracking_Number", "SSN_Provided", "Tax_Year", "Spouse_SSN", "SSN", "Name", "Address", "Cycle_Posted", "Received_Data", "Dependent_Name1", "Dependent_Name2", "Dependent_Name3", "Dependent_Name4", "Dependent_SSN1", "Dependent_SSN2", "Dependent_SSN3", "Dependent_SSN4", "PTIN", "EIN_Preparer")):
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
            os.remove(f"{self.name}.pdf")