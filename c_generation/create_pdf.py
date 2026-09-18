import fitz
import os
from forms_classes import *
from fast_api_models import *
import copy
import logging
import traceback
from datetime import datetime

# Настройка логирования
os.makedirs("./logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"./logs/tax_return_generator_{datetime.today().strftime("%Y-%m-%d-%H-%M")}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tax_return_generator")

def create_one_return(year_info, result_name="tax_return.pdf", transcript_name="tax_transcript.pdf", firm=Firm()):
    try:
        logger.info(f"Начало создания налоговой декларации для года: {year_info.filing_year}")
        
        if year_info.sells_products_or_services == "Products":
            logger.info("Создание формы 1125A для продажи продуктов")
            f_1125a = Form_1125A(year_info, firm)
        else:
            f_1125a = None
            logger.info("Форма 1125A не требуется (услуги)")

        logger.info("Создание формы 8949")
        f8949 = Form8949(year_info, firm)
        
        if year_info.company_type == "C corp":
            logger.info("Создание формы 1120 для C корпорации")
            f_1120 = Form_1120(year_info, firm)
        else:
            logger.info("Создание формы 1120S для S корпорации")
            f_1120 = Form_1120S(year_info, firm)
            
        if firm.gross_income >= 500000:
            logger.info(f"Создание формы 1125E (доход >= 500000: {firm.gross_income})")
            f_1125e = Form_1125E(year_info, firm)
        else:
            f_1125e = None
            logger.info(f"Форма 1125E не требуется (доход < 500000: {firm.gross_income})")
        
        s_g_flag = False
        for owner in year_info.owners:
            if owner.ownership_percentage > 20:
                s_g_flag = True
                logger.info(f"Владелец {owner.name} имеет долю > 20%: {owner.ownership_percentage}%")
                break
        
        if s_g_flag:
            logger.info("Создание Schedule G (найдены владельцы с долей > 20%)")
            s_g = ScheduleG(year_info, firm)
        else:
            s_g = None
            logger.info("Schedule G не требуется (нет владельцев с долей > 20%)")
            
        if year_info.company_type == "C corp":
            logger.info("Создание Schedule D для C корпорации")
            s_d = ScheduleD(year_info, firm)
        else:
            logger.info("Создание Schedule D для S корпорации")
            s_d = ScheduleD_S(year_info, firm)
            
        logger.info("Создание авторизации фирмы")
        firm_auth = FirmAuthorization(year_info, firm)
        
        forms = [firm_auth, f_1120]
        if year_info.sells_products_or_services == "Products":
            forms.append(f_1125a)
        if firm.gross_income >= 500000:
            forms.append(f_1125e)
        if s_g_flag:
            forms.append(s_g)
        forms += [f8949, s_d]
        
        if year_info.company_type == "S corp":
            logger.info(f"Создание Schedule K1 для {len(year_info.owners)} владельцев S корпорации")
            forms += [Schedule_K1(year_info, owner, firm) for owner in year_info.owners]
        
        logger.info(f"Объединение {len(forms)} форм в PDF")
        merged_pdf = fitz.open()
        for i, form in enumerate(forms):
            logger.info(f"Обработка формы {i+1}/{len(forms)}: {form.name}")
            form.filling_pdf(year_info.filing_year)
            form.insert_need_images()
            pdf = fitz.open(form.name+"_redacted.pdf")
            merged_pdf.insert_pdf(pdf)
            pdf.close()
            os.remove(form.name+"_redacted.pdf")
            logger.info(f"Форма {form.name} успешно добавлена")
        
        logger.info(f"Сохранение объединенного PDF: {result_name}")
        merged_pdf.save(result_name)
        merged_pdf.close()
        
        logger.info("Создание налоговой транскрипции")
        s_transcript = TaxTranscript1120(year_info, f_1120, f_1125a)
        s_transcript.filling_transcript1120()
        pdf = fitz.open(f"{s_transcript.name}_redacted.pdf")
        pdf.save(transcript_name)
        pdf.close()
        os.remove(f"{s_transcript.name}_redacted.pdf")
        
        logger.info(f"Налоговая декларация успешно создана: {result_name}, транскрипт: {transcript_name}")
        
    except Exception as e:
        logger.error(f"Ошибка в create_one_return для года {year_info.filing_year}: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def create_personal_return(year, owner, common_info, firm, officer, result_name="personal_tax_return.pdf"):
    try:
        logger.info(f"Начало создания личной налоговой декларации для {owner.name}, год: {year}")
        
        person = Person()
        f_1040 = Form_1040(owner, common_info, person, firm, year, officer)
        s_1 = Schedule1(owner, person)
        s_b = ScheduleB(owner, person)
        auth = Authorization(year, owner, person)
        
        forms = [auth, f_1040, s_1, s_b]
        
        logger.info(f"Заполнение {len(forms)} форм для личной декларации")
        for form in forms:
            logger.info(f"Заполнение формы: {form.name}")
            form.filling_pdf(year)
            form.insert_need_images()
        
        logger.info("Объединение форм личной декларации в PDF")
        merged_pdf = fitz.open()
        
        for form in forms:
            pdf = fitz.open(form.name+"_redacted.pdf")
            merged_pdf.insert_pdf(pdf)
            pdf.close()
            os.remove(form.name+"_redacted.pdf")
        
        logger.info(f"Сохранение личной налоговой декларации: {result_name}")
        merged_pdf.save(result_name)
        merged_pdf.close()
        
        logger.info(f"Личная налоговая декларация успешно создана: {result_name}")
        
    except Exception as e:
        logger.error(f"Ошибка в create_personal_return для {owner.name}, год {year}: {str(e)}")
        logger.error(traceback.format_exc())
        raise

def main_tax_return(req_body, result_name="tax_return.pdf", transcript_name="tax_transcript.pdf", return_folder="", transcript_folder="", personal_folder=""):
    try:
        logger.info("=" * 50)
        logger.info(f"ЗАПУСК ПРОЦЕССА СОЗДАНИЯ НАЛОГОВЫХ ДЕКЛАРАЦИЙ")
        logger.info(f"Год подачи: {req_body.filing_year}")
        logger.info(f"Тип компании: {req_body.company_type}")
        logger.info(f"Количество владельцев: {len(req_body.owners)}")
        logger.info(f"Многолетняя обработка: {req_body.need_multiple_years}")
        logger.info("=" * 50)
        
        resp = {
            "f1120_returns": {},
            "f1120_transcripts": {},
            "f1040_returns": {}
        }
        
        firm = Firm()
        logger.info("Создание основной налоговой декларации")
        create_one_return(req_body, return_folder+"/"+str(req_body.filing_year)+"_"+result_name, transcript_folder+"/"+str(req_body.filing_year)+"_"+transcript_name, firm)
        resp["f1120_returns"][str(req_body.filing_year)] = return_folder+"/"+str(req_body.filing_year)+"_"+result_name
        resp["f1120_transcripts"][str(req_body.filing_year)] = transcript_folder+"/"+str(req_body.filing_year)+"_"+transcript_name
        
        start_firm = copy.deepcopy(firm)
        last_info = req_body
        
        print(req_body.need_multiple_years)
        if req_body.need_multiple_years:
            logger.info(f"Обработка многолетних данных")
            if req_body.future_years:
                logger.info(f"Обработка {req_body.years_needed} будущих лет с детальными данными")
                for i, year_info in enumerate(req_body.future_years):
                    logger.info(f"Обработка будущего года {i+1}/{req_body.years_needed}: {year_info.year}")
                    new_info = create_info_next_year(last_info, year_info)
                    create_one_return(new_info, return_folder+"/"+str(year_info.year)+"_"+result_name, transcript_folder+"/"+str(year_info.year)+"_"+transcript_name, firm)
                    resp["f1120_returns"][str(year_info.year)] = return_folder+"/"+str(year_info.year)+"_"+result_name
                    resp["f1120_transcripts"][str(year_info.year)] = transcript_folder+"/"+str(year_info.year)+"_"+transcript_name
                    last_info = new_info
            else:
                logger.info(f"Обработка {req_body.years_needed} будущих лет с процентными данными")
                for i, year_info in enumerate(req_body.future_years_percents_income):
                    logger.info(f"Обработка будущего года {i+1}/{req_body.years_needed}: {year_info.year}")
                    new_info = create_info_next_year_with_percents(last_info, year_info)
                    create_one_return(new_info, return_folder+"/"+str(year_info.year)+"_"+result_name, transcript_folder+"/"+str(year_info.year)+"_"+transcript_name, firm)
                    resp["f1120_returns"][str(year_info.year)] = return_folder+"/"+str(year_info.year)+"_"+result_name
                    resp["f1120_transcripts"][str(year_info.year)] = transcript_folder+"/"+str(year_info.year)+"_"+transcript_name
                    last_info = new_info
        
        # Обработка личных налоговых деклараций
        personal_return_count = 0
        for owner in req_body.owners:
            if owner.generate_personal_tax_return:
                personal_return_count += 1
                logger.info(f"Создание личной налоговой декларации для владельца: {owner.name}")
                
                need_officer = None
                for officer in req_body.officers:
                    if officer.name == owner.name:
                        need_officer = officer
                        break
                
                if not need_officer:
                    logger.warning(f"Офицер не найден для владельца {owner.name}, пропуск личной декларации")
                    continue
                
                resp["f1040_returns"][owner.name] = {}
                create_personal_return(req_body.filing_year, owner, req_body, start_firm, need_officer, personal_folder+"/"+owner.name+"_"+str(req_body.filing_year)+"_"+result_name)
                resp["f1040_returns"][owner.name][str(req_body.filing_year)] = personal_folder+"/"+owner.name+"_"+str(req_body.filing_year)+"_"+result_name
                
                if owner.generate_future_returns:
                    logger.info(f"Создание {owner.generate_future_returns} будущих личных деклараций для {owner.name}")
                    for year in range(req_body.filing_year, req_body.filing_year+owner.generate_future_returns+1):
                        create_personal_return(year, owner, req_body, start_firm, need_officer, personal_folder+"/"+owner.name+"_"+str(year)+"_"+result_name)
                        resp["f1040_returns"][owner.name][str(year)] = personal_folder+"/"+owner.name+"_"+str(year)+"_"+result_name
        
        logger.info(f"УСПЕШНО ЗАВЕРШЕНО: создано {personal_return_count} личных деклараций")
        logger.info(f"Общее количество корпоративных деклараций: {len(resp['f1120_returns'])}")
        logger.info("=" * 50)
        
        return resp

    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА в main_tax_return: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Очистка временных файлов при ошибке
        logger.info("Очистка временных PDF файлов из-за ошибки")
        try:
            for file in os.listdir():
                if os.path.splitext(file)[1] == ".pdf":
                    os.remove(file)
                    logger.info(f"Удален файл: {file}")
        except Exception as cleanup_error:
            logger.error(f"Ошибка при очистке файлов: {cleanup_error}")
        
        raise

# if __name__ == "__main__":
    # main_tax_return(tax_return)