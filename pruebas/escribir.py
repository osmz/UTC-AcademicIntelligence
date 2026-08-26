from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
KEY = 'key.json'
# Escribe aqui el ID de tu documento:
SPREADSHEET_ID = '1LLZJ0N3ZjFn0Wji6ZEFf5J4aQe6c46LbD7iVCMlZ5Yk'

creds = None
creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)

service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Debe ser una matriz por eso el doble [][]
values = [['Prueba']]
# Llamada a la api
result = sheet.values().append(spreadsheetId=SPREADSHEET_ID,
                               range='Jenny!A1', 
                               valueInputOption='USER_ENTERED', 
                               body={'values': values}).execute()

print(f"Datos insertados correctamente. \n {(result.get('updates').get('updatedCells'))}")