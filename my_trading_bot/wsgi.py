"""
WSGI config for my_trading_bot project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
import time
from threading import Thread
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_trading_bot.settings')

application = get_wsgi_application()

def run_bot_continuously():
    while True:
        call_command('run_backtest')  # Call your backtest command
        time.sleep(5)  # Wait for 5 seconds

# Create and start a thread to run the bot
bot_thread = Thread(target=run_bot_continuously)
bot_thread.daemon = True  # Allow the main thread to exit even if the bot thread is running
bot_thread.start()