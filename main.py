import requests
import json
import random
import jwt
import datetime

from time import sleep
from datetime import date
from selenium import webdriver
from bs4 import BeautifulSoup
from helper import create_hash, alert
from selenium.webdriver.chrome.options import Options

# Set these variables
"""
Mobile =                   mobile number (integer)
Number_hours =             number of hours script should run (integer)
Call_per_min =             number of api calls per min (integer) # eg - 5
Age =                      persons age (integer) # eg - 18 or 45
Dose =                     Dose number (integer) # eg - 1 or 2
Beneficiary_reference_id = Reference id of beneficiary (string), #eg - 19455038804313
District_id =              Reference id of beneficiary (string), #eg - "363"
Pincode_initials =         Substring of pincode (string), #eg - "411"
"""

Mobile = 0
Number_hours = 24
Call_per_min = 3
Age = 0
Dose = 0
Beneficiary_reference_id = "",
District_id = ""
Pincode_initials = ""


class Authentication:
    def __init__(self, mobile_number):
        self.mobile_number = mobile_number
        self.secret = "U2FsdGVkX1/tWTWYx9ENIboK4zw1eR75HNhZi8zpf1MMHY4FZ5IjP9lXwjUWJP1f3Tdx1nKkd/rvB3gZY8XlSg=="

        self.details = {}

    def get_token(self):
        otp_req = self.request_otp()
        if otp_req.get('error') is not None:
            print('--- OTP generation failed ---')
            exit()
        sleep(7)
        otp_raw = self.extract_otp_chrome()

        self.details["otp_hash"] = create_hash(otp_raw)
        self.details["transaction_id"] = otp_req["txnId"]
        response = self.verify_otp(self.details["otp_hash"], self.details["transaction_id"])
        self.details["token"] = "Bearer {0}".format(json.loads(response.content)['token'])

        return self.details["token"]

    def request_otp(self):
        url = """https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP"""

        payload = {"mobile": self.mobile_number,
                   "secret": self.secret}

        headers = {"Connection": "keep-alive",
                   "Host": "cdn-api.co-vin.in",
                   "Origin": "https://selfregistration.cowin.gov.in",
                   "Referer": "https://selfregistration.cowin.gov.in/",
                   "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:88.0) Gecko/20100101 Firefox/88.0"}

        response = requests.post(
            url=url,
            headers=headers,
            json=payload
        )

        response = json.loads(response.content)
        print(response)
        return response

    def verify_otp(self, otp, transaction_id):
        url = """https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp"""
        headers = {"Connection": "keep-alive",
                   "Host": "cdn-api.co-vin.in",
                   "Origin": "https://selfregistration.cowin.gov.in",
                   "Referer": "https://selfregistration.cowin.gov.in/",
                   "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:88.0) Gecko/20100101 Firefox/88.0"}
        payload = {"otp": otp,
                   "txnId": transaction_id}

        response = requests.post(url=url,
                                 headers=headers,
                                 json=payload)
        print(f" --- verification done --- {str(response.status_code)}")
        print(response.content)
        return response

    def extract_otp_chrome(self):
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

        chrome_driver = "/usr/local/Caskroom/chromedriver/91.0.4472.19/chromedriver"
        driver = webdriver.Chrome(chrome_driver, chrome_options=chrome_options)
        print(driver.title)
        htmlcode = driver.page_source.encode('utf-8')

        soup = BeautifulSoup(htmlcode, features="html.parser")

        span_tags = soup.find_all("span")
        for index in range(len(span_tags)):
            if span_tags[index].contents == ['AXNHPSMS']:
                message = span_tags[index + 1].contents.pop()
                otp = eval(message.split('.')[0].split('Your OTP to register/access CoWIN is ')[1])
                print(otp)
                return otp

    def logout(self):
        logout_url = """https://cdn-api.co-vin.in/api/v2/auth/logout"""
        headers = {"Connection": "keep-alive",
                   "Authorization": self.details["token"],
                   "Host": "cdn-api.co-vin.in",
                   "Origin": "https://selfregistration.cowin.gov.in",
                   "Referer": "https://selfregistration.cowin.gov.in/",
                   "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:88.0) Gecko/20100101 Firefox/88.0"}

        response = requests.get(url=logout_url, headers=headers)
        return response

class BookSlot:
    def __init__(self, mobile, number_hours, call_per_min, age, dose, beneficiary_reference_id, district_id,
                 pincode_initials):
        self.call_per_min = call_per_min
        self.time = number_hours * 60 * call_per_min
        self.details = {"expire": 1,
                        "benificiary_reference_id": beneficiary_reference_id,
                        "vaccine": "COVISHIELD",
                        "age": age,
                        "dose": dose,
                        "mobile": mobile,
                        "district_id": district_id,
                        "pincode_initials": pincode_initials}

        self.authentication = Authentication(self.details["mobile"])

    def main_process(self):
        self.auth_proc()
        for i in range(self.time):
            details = self.fetch_details()
            print('-- avail --') if details else print('-- Nothing yet --')
            sleep((60 / self.call_per_min) + random.randint(1, 3))

        self.authentication.logout()

    def auth_proc(self):
        self.details["token"] = self.authentication.get_token()
        jwt_decode = jwt.decode(self.details["token"].split(' ')[1], options={"verify_signature": False})
        self.details["secret_key"] = jwt_decode["secret_key"]
        self.details["expire"] = jwt_decode["exp"]

        self.details["expire"] = datetime.datetime.fromtimestamp(self.details["expire"])

    def fetch_details(self):
        try:
            url = f"""https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByDistrict?district_id={self.details["district_id"]}&date={date.today().strftime("%d-%m-%Y")}"""
            # print(url)
            response = requests.get(
                url=url,
                headers={"Authorization": self.details["token"],
                         "Connection": "keep-alive",
                         "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:88.0) Gecko/20100101 Firefox/88.0"})

            print(response.status_code)
            # print(response.content)

            if response.status_code == 200:
                respo = json.loads(response.content)
                for center in respo["centers"]:
                    if self.details["pincode_initials"] in str(center["pincode"]):
                        sessions = center["sessions"]
                        for session in sessions:
                            # print(session)
                            if session["min_age_limit"] == self.details["age"] and \
                                    session[f"available_capacity_dose{self.details['dose']}"] >= 5 and \
                                    session["vaccine"] == self.details["vaccine"]:
                                print("======== Available ======= ")
                                print("Captured on =", datetime.datetime.now().strftime("%d-%m-%YT%H:%M:%S"))
                                print("Capacity = {0}".format(session["available_capacity"]))
                                print("Date = {0}".format(session["date"]))
                                print("available_capacity_dose1 = {0}".format(session["available_capacity_dose1"]))
                                print("Vaccine = {0}".format(session["vaccine"]))
                                print("Center ID = {0}".format(center["center_id"]))
                                print("Center Name = {0}".format(center["name"]))
                                print("Pincode = {0}".format(center["pincode"]))
                                print("\n")
                                self.book_slot(center["center_id"], session["slots"], session["session_id"])
                                return 1

            else:
                self.authentication.logout()
                self.auth_proc()

        except Exception as error:
            print(f" ============== Errored ============= {str(error)}")

    def book_slot(self, center_id, slots, session_id):
        for slot in slots:
            booking_url = "https://cdn-api.co-vin.in/api/v2/appointment/schedule"
            headers = {"Connection": "keep-alive",
                       "Host": "cdn-api.co-vin.in",
                       "Origin": "https://selfregistration.cowin.gov.in",
                       "Referer": "https://selfregistration.cowin.gov.in/",
                       "Authorization": self.details["token"],
                       "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:88.0) Gecko/20100101 Firefox/88.0"}

            payload = {"center_id": center_id,
                       "session_id": session_id,
                       "beneficiaries": [self.details["benificiary_reference_id"]],
                       "slot": slot,
                       "dose": self.details["dose"]}

            response = requests.post(url=booking_url,
                                     headers=headers,
                                     json=payload)
            if response.status_code == 200:
                alert()
                print("== booked ==")
                exit()
            else:
                print(response.content)


book_slot = BookSlot(mobile=Mobile,
                     number_hours=Number_hours,
                     call_per_min=Call_per_min,
                     age=Age,
                     dose=Dose,
                     beneficiary_reference_id=Beneficiary_reference_id,
                     district_id=District_id,
                     pincode_initials=Pincode_initials)
book_slot.main_process()
