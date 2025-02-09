# twitter_scraper/twitter_scraper/middlewares.py
import logging

class RedirectLoggerMiddleware:
    def process_spider_output(self, response, result, spider):
        logging.info(f"Final URL: {response.url}")
        for item in result:
            yield item