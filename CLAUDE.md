# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram Time Tracker Bot written in Python that helps users track time spent on various activities. The bot integrates with Google Sheets for data persistence and provides categorized activity tracking with reminder functionality.

## Architecture

- **Main Bot File**: `bot.py` - Contains all bot logic including handlers, menu systems, and Google Sheets integration
- **Data Storage**: 
  - Google Sheets via `gspread` for activity records
  - Local JSON files for user preferences:
    - `goals.json` - User-specific goals
    - `record.json` - Personal best records (in seconds)
    - `user_intervals.json` - Reminder interval preferences
- **Authentication**: Google service account credentials in `marcandre-344817-1f31cc621f75.json`

## Key Components

- **Session Management**: `active_sessions` dict tracks ongoing activities per user
- **Categories**: Fixed set of activity categories (Work, Sport, Rest, Study, Other)
- **State Management**: Multiple awaiting states for user input flows
- **Reminder System**: Job queue-based notifications at user-configured intervals

## Development Commands

Run the bot locally:
```bash
python bot.py
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run with Docker Compose:
```bash
docker-compose up -d
```

Stop Docker container:
```bash
docker-compose down
```

## Data Persistence

- Activity logs are written to Google Sheets with columns: Activity Name, Category, Start Time, End Time, Duration
- Duration format is `m:ss` (minutes:seconds)
- Personal records stored as total seconds in `record.json`
- User preferences persist across bot restarts via JSON files

## Bot Token and Credentials

- Telegram bot token is hardcoded in `bot.py` (line 214)
- Google Sheets service account file: `marcandre-344817-1f31cc621f75.json`
- Target spreadsheet: "Time Tracker" (first worksheet)