import os
import datetime
from pathlib import Path
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import google_auth_httplib2
import httplib2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT / ".env")

class DatabaseManager:
    FALLBACK_STORAGE = {
        "Active_Stream": [],
        "Campus_Schedule": [],
        "Audit_Ledger": []
    }

    TAB_HEADERS = {
        "Active_Stream": ["building_id", "date", "consumption_kwh", "is_faulty"],
        "Campus_Schedule": ["event_name", "date", "start_time", "end_time", "description"],
        "Audit_Ledger": ["timestamp", "building_id", "anomaly_type", "recommendation", "status"]
    }

    def __init__(self):
        self.sheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
        self.creds = None
        self._load_credentials()

    def _load_credentials(self):
        candidate_paths = [
            Path(self.creds_path),
            Path(__file__).resolve().parent.parent / self.creds_path,
            Path.cwd() / self.creds_path,
            ROOT / self.creds_path,
        ]

        for candidate in candidate_paths:
            if candidate.exists():
                try:
                    self.creds = service_account.Credentials.from_service_account_file(
                        str(candidate), scopes=["https://www.googleapis.com/auth/spreadsheets"]
                    )
                    print(f"Google Sheets credentials loaded from: {candidate}")
                    return
                except Exception as e:
                    print(f"Google Sheets credentials could not be loaded from {candidate}: {e}")

        print(
            "Google Sheets credential file not found or could not be loaded. "
            f"Tried: {', '.join(str(p) for p in candidate_paths)}"
        )

    def is_ready(self) -> bool:
        ready = bool(self.sheet_id and self.creds)
        if not ready:
            print(
                "Google Sheets is not ready. "
                f"sheet_id set: {bool(self.sheet_id)}, creds loaded: {bool(self.creds)}"
            )
        return ready

    def _get_service(self):
        """Create a thread-safe service instance for each request."""
        if not self.is_ready():
            raise RuntimeError("Google Sheets is not configured or credentials are missing.")

        http_transport = httplib2.Http(timeout=30)
        authorized_http = google_auth_httplib2.AuthorizedHttp(self.creds, http=http_transport)
        return build("sheets", "v4", http=authorized_http, cache_discovery=False)

    def initialize_workspace(self):
        """Check and create required tabs in the Google Sheet."""
        if not self.is_ready():
            print("Google Sheets not configured — using local demo fallback storage.")
            for tab_name, headers in self.TAB_HEADERS.items():
                self.FALLBACK_STORAGE.setdefault(tab_name, [])
            return

        try:
            service = self._get_service()
            sheet_metadata = service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
            existing_tabs = [sheet.get("properties", {}).get("title") for sheet in sheet_metadata.get("sheets", [])]

            for tab_name, headers in self.TAB_HEADERS.items():
                if tab_name not in existing_tabs:
                    print(f"Creating tab: {tab_name}")
                    batch_update_request = {
                        "requests": [
                            {
                                "addSheet": {
                                    "properties": {
                                        "title": tab_name
                                    }
                                }
                            }
                        ]
                    }
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=self.sheet_id, body=batch_update_request
                    ).execute()
                    self.write_rows(tab_name, [headers])
                else:
                    print(f"Tab already exists: {tab_name}")
                    try:
                        header_range = f"{tab_name}!A1:Z1"
                        header_response = service.spreadsheets().values().get(
                            spreadsheetId=self.sheet_id,
                            range=header_range
                        ).execute()
                        existing_headers = header_response.get("values", [[ ]])[0]
                    except HttpError:
                        existing_headers = []

                    if existing_headers != headers:
                        print(f"Restoring headers for existing tab: {tab_name}")
                        self.write_headers(tab_name, headers)

        except HttpError as err:
            print(f"An error occurred during workspace init: {err}")

    def write_headers(self, tab_name, headers):
        """Force write headers to the first row."""
        body = {"values": [headers]}
        range_name = f"{tab_name}!A1"
        if not self.is_ready():
            self.FALLBACK_STORAGE.setdefault(tab_name, [])
            return

        try:
            service = self._get_service()
            service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
        except HttpError as err:
            print(f"An error occurred writing headers to {tab_name}: {err}")

    def _normalize_cell(self, value):
        if value is None:
            return ""
        # Convert pandas Timestamp and similar objects that provide to_pydatetime()
        if hasattr(value, "to_pydatetime"):
            try:
                py_dt = value.to_pydatetime()
                return py_dt.isoformat()
            except Exception:
                # Fallback to string conversion
                return str(value)
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.isoformat()
        return value

    def _prepare_rows(self, tab_name, rows):
        if not rows:
            return []

        normalized = []
        if isinstance(rows[0], dict):
            headers = self.TAB_HEADERS.get(tab_name)
            if headers:
                for row in rows:
                    normalized.append([self._normalize_cell(row.get(col, "")) for col in headers])
            else:
                for row in rows:
                    normalized.append([self._normalize_cell(row.get(col, "")) for col in row.keys()])
        else:
            for row in rows:
                normalized.append([self._normalize_cell(cell) for cell in row])
        return normalized

    def write_rows(self, tab_name, rows):
        """Append rows to a specific tab."""
        rows = self._prepare_rows(tab_name, rows)
        if not rows:
            return

        if not self.is_ready():
            self.FALLBACK_STORAGE.setdefault(tab_name, [])
            self.FALLBACK_STORAGE[tab_name].extend(rows)
            print(f"Local fallback: appended {len(rows)} rows to {tab_name}.")
            return

        body = {"values": rows}
        range_name = f"{tab_name}!A1:Z"
        try:
            service = self._get_service()
            service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
            print(f"Google Sheets: appended {len(rows)} rows to {tab_name}.")
        except HttpError as err:
            print(f"An error occurred writing to {tab_name}: {err}")
            try:
                print("Retrying write after refreshing workspace...")
                self.initialize_workspace()
                service = self._get_service()
                service.spreadsheets().values().append(
                    spreadsheetId=self.sheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body=body,
                ).execute()
                print(f"Google Sheets: appended {len(rows)} rows to {tab_name} on retry.")
            except Exception as retry_err:
                print(f"Write retry failed for {tab_name}: {retry_err}")

    def clear_tab(self, tab_name):
        """Clear all data and force-restore headers from known config."""
        required_headers = self.TAB_HEADERS

        if not self.is_ready():
            self.FALLBACK_STORAGE[tab_name] = []
            print(f"Local fallback: cleared {tab_name}.")
            return

        try:
            service = self._get_service()
            service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id, range=f"{tab_name}!A1:Z1000"
            ).execute()

            if tab_name in required_headers:
                print(f"Restoring headers for {tab_name}")
                self.write_headers(tab_name, required_headers[tab_name])

        except HttpError as err:
            print(f"An error occurred clearing {tab_name}: {err}")

    def read_tab(self, tab_name):
        """Read data from a tab as a list of dictionaries."""
        if not self.is_ready():
            fallback = self.FALLBACK_STORAGE.get(tab_name, [])
            headers = self.TAB_HEADERS.get(tab_name, [])
            return [dict(zip(headers, row)) for row in fallback]

        try:
            service = self._get_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id, range=f"{tab_name}!A1:Z1000"
            ).execute()
            values = result.get("values", [])
            if not values:
                return []

            headers = values[0]
            rows = values[1:]
            return [dict(zip(headers, row)) for row in rows]
        except HttpError as err:
            print(f"An error occurred reading {tab_name}: {err}")
            return []

    def seed_campus_schedule(self, events=None):
        """Populate Campus_Schedule with dummy events."""
        if events is None:
            events = [
                ["New Year Planning", "2024-01-01", "09:00", "11:00", "Campus operational kickoff"],
                ["Energy Audit Workshop", "2024-01-05", "10:00", "12:00", "Staff training on energy use"],
                ["Winter Sports Fest", "2024-01-10", "09:00", "17:00", "High occupancy sports event"],
                ["Board Meeting", "2024-01-15", "14:00", "16:00", "Executive meeting in admin building"],
                ["Open Day", "2024-01-20", "10:00", "16:00", "Visitor campus event"]
            ]
        
        print(f"Seeding Campus_Schedule with {len(events)} events.")
        # Clear existing rows (except headers)
        self.clear_tab("Campus_Schedule")
        # Write headers back if clear_tab clears everything
        self.write_rows("Campus_Schedule", events)
