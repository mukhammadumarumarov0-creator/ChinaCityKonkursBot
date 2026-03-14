from google.oauth2 import service_account
from googleapiclient.discovery import build
import asyncio
from decouple import config
from datetime import datetime
from datetime import datetime
import asyncio


SERVICE_ACCOUNT_FILE = config("SERVICE_ACCOUNT_FILE")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)
sheets_service = build('sheets', 'v4', credentials=credentials)
SPREADSHEET_ID = config("SPREADSHEET_ID")  


def write_user_to_sheet_sync(chat_id, full_name,telegram_username ,phone, sheets_service, spreadsheet_id):
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    values = [[full_name,telegram_username,phone,chat_id,date,]]

    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Лист1!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()


async def write_user_to_sheet(chat_id, full_name, phone,telegram_username,sheets_service, spreadsheet_id):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, write_user_to_sheet_sync,chat_id,telegram_username ,full_name, phone, sheets_service, spreadsheet_id)
    return True


async def write_user_to_sheet_bg(chat_id, username, full_name, phone):
    try:
        await write_user_to_sheet(
            chat_id=chat_id,
            telegram_username=username,
            full_name=full_name,
            phone=phone,
            sheets_service=sheets_service,
            spreadsheet_id=SPREADSHEET_ID
        )
    except Exception as e:
        print("⚠️ Google Sheets error:", e)




