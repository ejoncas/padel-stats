from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from botocore.exceptions import ClientError

import json 
import boto3

s3 = boto3.resource('s3')

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1droM8KnYz0MYPHNLgy60jZutQvCmccZiCcKtrZoNuH8'
SAMPLE_RANGE_NAME = 'MEl - Docklands One Padel!A1:D10000'

BUCKET_AUTH_NAME = "padel-google-auth"

def s3_load_json(key):
    try:
        obj = s3.Object(BUCKET_AUTH_NAME, key)
        result = json.loads(obj.get()['Body'].read().decode('utf-8'))
        print("Got JSON file from s3://"+BUCKET_AUTH_NAME+"/" + key)
        print(str(result))
        return result
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            return None
        else:
            raise


def s3_write(key, data):
    obj = s3.Object(BUCKET_AUTH_NAME, key)
    obj.put(Body=data)

    
def write_availability_row(rows):
    token_data = s3_load_json("token.json")
    creds = None
    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(s3_load_json("credentials.json"), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        s3_write("token.json", creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])
    
        print(str(values))
        # How the input data should be interpreted.
        value_input_option = 'RAW'  # TODO: Update placeholder value.
        # How the input data should be inserted.
        insert_data_option = 'INSERT_ROWS'  # TODO: Update placeholder value.
        value_range_body = {
            "values": rows
        }

        request = service.spreadsheets().values().append(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME, valueInputOption=value_input_option, insertDataOption=insert_data_option, body=value_range_body)
        response = request.execute()

    except HttpError as err:
        print(err)

