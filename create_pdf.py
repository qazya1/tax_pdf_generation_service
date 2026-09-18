import fitz, json
import os
from forms_classes import Person, Form_1040, Schedule1, Schedule2, ScheduleB, ScheduleC, ScheduleSE, Authorization, TaxTranscript
from pdf_filling import fill_title_page

def main_tax_return(json_interface, result_name="tax_return.pdf", transcript_name="tax_transcript.pdf"):
    # try:
        person = Person(json_interface)
        f_1040 = Form_1040(json_interface, person)
        s_1 = Schedule1(json_interface, person)
        if person.employee != "Employed":
            s_2 = Schedule2(json_interface, person)
        s_b = ScheduleB(json_interface, person)
        if person.employee != "Employed":
            s_c = ScheduleC(json_interface, person)
            s_se = ScheduleSE(json_interface, person)
            person.se_info = s_c.rows
        auth = Authorization(json_interface, person)
        
        if person.employee == "Employed":
            forms = [auth, f_1040, s_1, s_b]
        else:
            forms = [auth, f_1040, s_1, s_2, s_b, s_c, s_se]
        
        for form in forms:
            form.filling_pdf(person.year)
            form.insert_need_images()
        
        merged_pdf = fitz.open()  # Создаем новый PDF
        if json_interface["preparationType"] != "Self-prepared":
            fill_title_page(json_interface, person.prepared_firm_info)
            pdf = fitz.open("title_redacted.pdf")
            merged_pdf.insert_pdf(pdf)
            pdf.close()
            os.remove("title_redacted.pdf")
        
        for form in forms:
            pdf = fitz.open(form.name+"_redacted.pdf")
            merged_pdf.insert_pdf(pdf)  # Вставляем все страницы
            pdf.close()
            os.remove(form.name+"_redacted.pdf")
        
        merged_pdf.save(result_name)
        merged_pdf.close()
        
        s_transcript = TaxTranscript(json_interface, person)
        transcript_pdf = fitz.open()
        if not('dependents' in json_interface):
            dep_num = 0
        else:
            dep_num = len(json_interface['dependents'])
        first_page = f"page1/dependents_{dep_num}.pdf"
        if person.employee == "Employed":
            main_part = "employed/main_part.pdf"
            last_page = f"employed/page_last/children_{s_transcript.rows['Children_Number']}.pdf"
        else:
            main_part = "se/main_part.pdf"
            last_page = f"se/page_last/children_{s_transcript.rows['Children_Number']}.pdf"
        for doc_name in (first_page, main_part, last_page):
            pdf = fitz.open("forms/tax_transcript/"+doc_name)
            transcript_pdf.insert_pdf(pdf)
            pdf.close()
        transcript_pdf.save(f"{s_transcript.name}.pdf")
        transcript_pdf.close()
        s_transcript.filling_transcript()
        pdf = fitz.open(f"{s_transcript.name}_redacted.pdf")
        pdf.save(transcript_name)
        pdf.close()
        os.remove(f"{s_transcript.name}_redacted.pdf")
        
        return person.prepared_firm_info
##    except BaseException:
##        print("error")
##        for file in os.listdir():
##            if os.path.splitext(file)[1] == "pdf":
##                os.remove(file)

if __name__ == "__main__":
    with open("test.json", "r", encoding='utf-8') as test_file:
        test_json = json.load(test_file)
    main_tax_return(test_json)
