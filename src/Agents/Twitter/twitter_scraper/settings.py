# twitter_scraper/twitter_scraper/settings.py
# ... other settings

SPIDER_MIDDLEWARES = {
    'twitter_scraper.middlewares.RedirectLoggerMiddleware': 540,  # Use your project name
}

# Configure logging (optional, but good practice):
LOG_LEVEL = 'INFO'  # Set the desired logging level
# LOG_FILE = 'scrapy.log' # Optional: save logs to a file