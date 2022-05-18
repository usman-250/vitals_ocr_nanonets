from os import path, pread
from flask_restful import Resource, Api, reqparse
from werkzeug.utils import secure_filename
from flask import Flask, request
from flask_cors import CORS
from flask import jsonify
import requests
import time
import os

app = Flask(__name__)
CORS(app)

app.config['DEBUG'] = True


api = Api(app)

def get_device_cat(files_add):
    for file in files_add:
        if file:
            filename = secure_filename(file.filename)
            file.save(filename)
            url = 'https://app.nanonets.com/api/v2/ImageCategorization/LabelFile/'
            data = {'file': open(filename, 'rb'), 'modelId': ('', '32b1f182-9c5a-401d-806c-0a81e99bf63c')}
            response = requests.post(url, auth= requests.auth.HTTPBasicAuth('R5vlGbg3aHdy-OFRyF7D7rvPNrcupFvR', ''), files=data)
            response_dict = eval(response.text)

            print('label ',response_dict['result'][0]['prediction'][0]['label'])
            print('score ',response_dict['result'][0]['prediction'][0]['probability'])
            try:
                device_type =  response_dict['result'][0]['prediction'][0]['label']
                device_score = response_dict['result'][0]['prediction'][0]['probability']
            except:
                device_type = None
                device_score= 0

            return device_type,device_score, filename


class device_classification(Resource):
    def post(self):
        try:
            uploaded_files = request.files.get('image')
            # filename = secure_filename(uploaded_files.filename)
            # uploaded_files.save(filename)
            device_type,device_score, filename = get_device_cat([uploaded_files]) #need to pass a list
            if os.path.exists(filename):
                os.remove(filename)
            return {'device_type':device_type, 'cofidence':device_score}
        except:
            if os.path.exists(filename):
                os.remove(filename)
            return {}


def extract_data_from_bp_apparatus(file_path):
    try:
        url = 'https://app.nanonets.com/api/v2/OCR/Model/885d48c5-43bb-4c2e-adbf-ff897ca4ec91/LabelFile/?async=false'
        data = {'file': open(file_path, 'rb')}
        response = requests.post(url, auth=requests.auth.HTTPBasicAuth('R5vlGbg3aHdy-OFRyF7D7rvPNrcupFvR', ''), files=data)
        response_dict = eval(response.text)
        prediction = response_dict['result'][0]['prediction']
        upper = prediction[0]['ocr_text']
        lower = prediction[-1]['ocr_text']
        if os.path.exists(file_path):
            os.remove(file_path)
        return upper, lower
    except:
        if os.path.exists(file_path):
            os.remove(file_path)
        return '',''

class bp_apparatus_ocr(Resource):
    def post(self):
        try:
            uploaded_files = request.files.get('image')
            filename = secure_filename(uploaded_files.filename)
            uploaded_files.save(filename)
            upper, lower = extract_data_from_bp_apparatus(filename)
            # print(upper,lower)
            bp_dict = {'upper':upper, 'lower':lower}
            return bp_dict
        except:
            return {}


def extract_data_from_glucometer(file_path):
    try:
        url = 'https://app.nanonets.com/api/v2/OCR/Model/2717bec5-f548-4759-b910-0674a0c89156/LabelFile/?async=false'
        data = {'file': open(file_path, 'rb')}
        response = requests.post(url, auth=requests.auth.HTTPBasicAuth('R5vlGbg3aHdy-OFRyF7D7rvPNrcupFvR', ''), files=data)
        response_dict = eval(response.text)
        prediction = response_dict['result'][0]['prediction']
        glc = prediction[0]['ocr_text']
        if os.path.exists(file_path):
            os.remove(file_path)
        return glc
    except:
        if os.path.exists(file_path):
            os.remove(file_path)
        return ''

class glocumeter_ocr(Resource):
    def post(self):
        try:
            uploaded_files = request.files.get('image')
            filename = secure_filename(uploaded_files.filename)
            uploaded_files.save(filename)
            glc = extract_data_from_glucometer(filename)
            glc_details = {'glc':glc}

            return glc_details
        except:
            return {}


def prediction(files_add):
    try:
        device_cat,device_score, file_path = get_device_cat(files_add)
        if device_score > 0.9:
            if device_cat == 'glucometer':
                glc_value = extract_data_from_glucometer(file_path)
            elif device_cat == 'bp_apparatus':
                    upper_value, lower_value = extract_data_from_bp_apparatus(file_path)
        ##################################################
            device_name = ""
            device_type = ""
            device_model = ""
            device_make = ""
            device_launch_date = ""
            device_varrient = ""
            company_name = ""

            test_category = ''
            image_path = file_path
            test_details = {}

            if device_cat == 'glucometer':
                device_name = "glucco meter"
                test_category = "gluccos"
                # test_details[test_category] = {}
                test_details["gluccos"] = {"current_value": glc_value, "unit": "mg/dL"}
                test_details["time"] = ""
                test_details["date"] = ""
            elif device_cat == 'bp_apparatus':
                device_name = "BP apparatus"
                test_category = "blood pressure"
                test_details["pulse_rate"] = {"current_value": "", "unit": ""}
                # test_details[test_category] = {}
                test_details["upper"]= {"current_value": upper_value, "unit": "mmHg"}
                test_details["lower"] = {"current_value": lower_value, "unit": "mmHg"}
                test_details["time"] = ""
                test_details["date"] = ""
            # elif test_dropdown == 'temp':
            #     device_name = "thermometer"
            #     test_category = "tempreture"
            #     test_details[test_category] = {}
            #     # test_details[test_category]["temp"] = {"current_value": str(preds[filename][0]), "unit": "°F"}
            #     test_details[test_category]["temp"] = {"current_value": "98.7", "unit": "°F"}

            
            final_preds = make_final_dict(device_make,device_launch_date,device_varrient, device_type,\
                device_name,device_model,company_name, test_category,image_path,test_details)
            ###################################################33

            return final_preds
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
            return {'low_cofidence': 'Device type is ambigous'}
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print("\n\n-------->>> ",e)
        return {}


def make_final_dict(device_make,device_launch_date,device_varrient, device_type, device_name,device_model,company_name, test_category,image_path,test_details):
    
    if device_name == "glucco meter":
        device_model ='G1'
    elif device_name == "BP apparatus":
        device_model ='B1'
    elif device_name == "thermometer":
        device_model ='T1'

    final_preds ={
        "device": {
            "device_name": device_name,
            "device_model": device_model,
            "company_name": company_name,
            "device_type": device_type,
            "device_make": device_make,
            "device_launch_date" : device_launch_date,
            "device_varrient" : device_varrient
        },
        "prediction": {
            "test_category": test_category,
            "image_path": image_path,
            "test_details":test_details,
        }
    }
    return final_preds



class vitals_ocr(Resource):
    def post(self):
        try:
            uploaded_files = request.files.get('image')
            preds = prediction([uploaded_files])
            return preds,200
        except:
            return {},500


api.add_resource(vitals_ocr, '/vitals_ocr', methods=['POST'])
api.add_resource(device_classification, '/device_classification', methods=['POST'])
api.add_resource(bp_apparatus_ocr, '/bp_apparatus_ocr', methods=['POST'])
api.add_resource(glocumeter_ocr, '/glocumeter_ocr', methods=['POST'])