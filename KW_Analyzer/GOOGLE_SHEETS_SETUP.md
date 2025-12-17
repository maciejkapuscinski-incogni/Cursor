# Google Sheets API Setup Guide

Follow these steps to configure Google Sheets API access:

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click **"New Project"**
4. Enter a project name (e.g., "KW Analyzer")
5. Click **"Create"**

## Step 2: Enable Required APIs

1. In your new project, go to **"APIs & Services"** > **"Library"**
2. Search for **"Google Sheets API"** and click on it
3. Click **"Enable"**
4. Go back to the Library
5. Search for **"Google Drive API"** and click on it
6. Click **"Enable"**

## Step 3: Create a Service Account

1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"Create Credentials"** > **"Service Account"**
3. Enter a name (e.g., "kw-analyzer-service")
4. Click **"Create and Continue"**
5. Skip the optional steps and click **"Done"**

## Step 4: Create and Download Service Account Key

1. Click on the service account you just created
2. Go to the **"Keys"** tab
3. Click **"Add Key"** > **"Create new key"**
4. Select **"JSON"** format
5. Click **"Create"**
6. The JSON file will download automatically

## Step 5: Save the Credentials File

1. Move the downloaded JSON file to your project's `credentials/` folder
2. Rename it to `google-sheets-credentials.json` (or keep the original name)
3. Note the full path to this file

## Step 6: Share Your Google Sheet

1. Open your Google Sheet
2. Click the **"Share"** button (top right)
3. Copy the **service account email** from the JSON file (it's the `client_email` field)
4. Paste the service account email in the share dialog
5. Give it **"Viewer"** permissions (or "Editor" if you want to write data)
6. Click **"Send"** (you can uncheck "Notify people")

## Step 7: Get Your Spreadsheet ID

1. Open your Google Sheet
2. Look at the URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
3. Copy the `SPREADSHEET_ID` part (the long string between `/d/` and `/edit`)

## Step 8: Update .env File

1. Open the `.env` file in your project
2. Update these values:
   - `GOOGLE_SHEETS_CREDENTIALS_PATH`: Path to your JSON file (e.g., `./credentials/google-sheets-credentials.json`)
   - `GOOGLE_SHEETS_SPREADSHEET_ID`: Your spreadsheet ID from Step 7

## Example .env Configuration

```
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/google-sheets-credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

## Troubleshooting

- **"File not found" error**: Make sure the path in `.env` is correct relative to the project root
- **"Permission denied" error**: Make sure you shared the sheet with the service account email
- **"API not enabled" error**: Make sure both Google Sheets API and Google Drive API are enabled

## Security Note

- Never commit the `.env` file or `credentials/` folder to git
- Keep your service account JSON file secure
- The `.gitignore` file already excludes these files

