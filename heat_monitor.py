name: Heat Alert Monitor

on:
  schedule:
    # Runs every 15 minutes
    - cron: '*/15 * * * *'
  workflow_dispatch: # Allows manual trigger from GitHub UI

jobs:
  run-script:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run script
        env:
          FIREBASE_URL: ${{ secrets.FIREBASE_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          OPENWEATHER_API_KEY: ${{ secrets.OPENWEATHER_API_KEY }}
        run: python heat_monitor.py
