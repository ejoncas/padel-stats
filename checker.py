import requests
import json
import re
from datetime import datetime  
from datetime import date
from datetime import timedelta  
import os
import spreadsheet_writer
import pytz


class DayOfBookings:

    def __init__(self, start_time, finish_time, frequency_minutes):
        self.start_time = datetime.fromisoformat(start_time)
        self.finish_time = datetime.fromisoformat(finish_time)
        self.frequency_minutes = frequency_minutes
        self.slots = []
        current_time = self.start_time
        total_slots = 0
        while current_time < self.finish_time:
            total_slots = total_slots + 1
            self.slots.append({
                'date': current_time,
                'booked': True
            })
            current_time = current_time + timedelta(minutes = self.frequency_minutes) 

    def all_slots(self):
        return self.slots;

    def to_string(self):
        print("start=" + str(self.start_time) + " end=" + str(self.finish_time))
        for idx, slot in enumerate(self.slots):
            date_slot = str(self.start_time + timedelta(minutes = (self.frequency_minutes * idx)))
            print(date_slot + "=" + str("X" if slot['booked'] else "0"))


        booked_slots = [x for x in self.slots if x['booked']]
        available_slots = [x for x in self.slots if not x['booked']]
        total_minutes = len(self.slots) * self.frequency_minutes
        available_minutes = len(available_slots) * self.frequency_minutes
        booked_minutes = len(booked_slots) * self.frequency_minutes

        ## General Stats
        print("")
        print("frequency_minutes="+str(self.frequency_minutes))
        print("total_slots="+str(len(self.slots)))
        print("total_minutes="+str(total_minutes))

        ## Booked Stats
        print("")
        print("booked_slots="+str(len(booked_slots)))
        print("booked_minutes="+str(booked_minutes))

        ## Available Stats
        print("")
        print("available_slots="+str(len(available_slots)))
        print("available_minutes="+str(available_minutes))

        ## Allocation Ratio
        print("")
        print("available_ratio="+str("{:.2%}".format(available_minutes / total_minutes)))
        print("booked_ratio="+str("{:.2%}".format(booked_minutes / total_minutes)))


    def available(self, start, duration):
        start_available = datetime.fromisoformat(start)
        current_slot = 0
        current_time = self.start_time
        while current_time < self.finish_time:
            current_time = current_time + timedelta(minutes = self.frequency_minutes) 
            if current_time > start_available and current_time <= start_available + timedelta(minutes=duration):
                self.slots[current_slot]['booked'] = False
            current_slot = current_slot + 1



# Map court_id => rea_search

# 19cbcdfd-33b0-4023-a985-6b6258091d75 PAN 1
# a800ad11-f3f1-4707-ab4b-e2d54f4abfad PAN 2
# 2042d774-0fa2-4d0f-81a1-f6aba49558f1 PAN 3

# 0 is monday ...
opening_hours = {
    "0": {
        "opening_time": "16:00",
        "closing_time": "22:00"
    },
    "1": {
        "opening_time": "16:00",
        "closing_time": "22:00"
    },
    "2": {
        "opening_time": "16:00",
        "closing_time": "22:00"
    },
    "3": {
        "opening_time": "16:00",
        "closing_time": "22:00"
    },
    "4": {
        "opening_time": "09:30",
        "closing_time": "22:00"
    },
    "6": {
        "opening_time": "09:00",
        "closing_time": "15:00"
    },
     "5": {
        "opening_time": "09:00",
        "closing_time": "15:00"
    }
}

def get_open_time():
    weekday = date.today().weekday()
    return opening_hours.get(str(weekday)).get("opening_time")

def get_close_time():
    weekday = date.today().weekday()
    return opening_hours.get(str(weekday)).get("closing_time")
    

def court_name(id):
    if id == "19cbcdfd-33b0-4023-a985-6b6258091d75":
        return "Panoramic 1"
    elif id == "a800ad11-f3f1-4707-ab4b-e2d54f4abfad":
        return "Panoramic 2"
    elif id == "2042d774-0fa2-4d0f-81a1-f6aba49558f1":
            return "Panoramic 3"
    else:
        return "Unknown ID: " + id

def booked_str(b):
    if b:
        return "X"
    else:
        return ""


DATE_ADD = 0

def check_padel_bookings(event, context):            
    try:
        # Tenant by ID https://playtomic.io/api/v1/tenants/916ccd8a-d212-43c8-98fd-5f2eec2ea4f1  -> $.opening_hours.(MONDAY | TUESDAY | etc).(opening_time | closing_time)
        # Returns available slots. Missing slots are considered taken on bussiness hours https://playtomic.io/api/v1/availability?user_id=me&tenant_id=916ccd8a-d212-43c8-98fd-5f2eec2ea4f1&sport_id=PADEL&local_start_min=2022-06-02T00%3A00%3A00&local_start_max=2022-06-02T23%3A59%3A59 

        # Abre de 16 a 22 de lun a viernes
        my_date = datetime.now(pytz.timezone('Australia/Melbourne'))
        date_to_check =  my_date.date()
        date_to_check = date_to_check + timedelta(days = DATE_ADD)
        check_from = date_to_check.isoformat() + "T00:00:00"
        check_to = date_to_check.isoformat() + "T23:59:59"
        url = "https://playtomic.io/api/v1/availability?user_id=me&tenant_id=916ccd8a-d212-43c8-98fd-5f2eec2ea4f1&sport_id=PADEL&local_start_min=" + check_from + "&local_start_max=" + check_to
        print("URL is " + url)
        result = requests.get(url)
        availability_array = result.json()

        courts_to_booking = {}
        for a in availability_array:
            resource = a['resource_id']
            date_part = a['start_date']
            print("***** Court ID: " + court_name(resource) + "*********** ")
            dob = DayOfBookings(date_part + "T"+get_open_time()+":00.000+10:00", date_part +"T"+get_close_time()+":00.000+10:00", 30)
            courts_to_booking[resource] = dob
            for s in a['slots']:
                d = date_part + 'T' + s['start_time'] + ".000+00:00"
                dob.available(d, int(s['duration']))
            dob.to_string()
            print("\n\n")

        values_to_write = []
        print(courts_to_booking)
        court1 = courts_to_booking.get("19cbcdfd-33b0-4023-a985-6b6258091d75", None)
        court2 = courts_to_booking.get("a800ad11-f3f1-4707-ab4b-e2d54f4abfad", None)
        court3 = courts_to_booking.get("2042d774-0fa2-4d0f-81a1-f6aba49558f1", None)

        run_at = datetime.now()
        if court1 and court2 and court3:
            for idx, s in enumerate(court1.all_slots()):
                values_to_write.append([
                    str(run_at),
                    str(s['date']), 
                    booked_str(s['booked']), 
                    booked_str(court2.all_slots()[idx]['booked']), 
                    booked_str(court3.all_slots()[idx]['booked'])
                ])

            spreadsheet_writer.write_availability_row(values_to_write)
        
    except Exception as e:
        raise ValueError("Failed to execute: " + str(e))
