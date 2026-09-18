import fitz  # PyMuPDF

def fill_field_with_dots(pdf_path, field_name, value, output_path):
    doc = fitz.open(pdf_path)
    
    for page in doc:
        widgets = page.widgets()
        for widget in widgets:
            if widget.field_name == field_name:
                # Получаем максимальную длину поля
                max_len = widget.text_maxlen
                
                # Формируем строку: значение + точки до max_len
                # print(max_len)
                if len(value) < max_len:
                    filled_text = '.' * (max_len - len(value)) + value
                    # print(filled_text)
                else:
                    filled_text = value
                
                # Заполняем поле
                widget.field_value = filled_text
                widget.update()
    
    doc.save(output_path)
    doc.close()

# Пример использования
fill_field_with_dots("tax_transcript.pdf", "Wages_Salaries_Tips", "$20", "test.pdf")