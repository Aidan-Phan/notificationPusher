# tools/scheduler.py

import schedule
import time

def run_scheduled_tasks():
    while True:
        schedule.run_pending()
        time.sleep(1)