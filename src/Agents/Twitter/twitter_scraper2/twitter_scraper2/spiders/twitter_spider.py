import scrapy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time  # For potential explicit waits

class TwitterSpider(scrapy.Spider):
    name = "twitter_spider"
    start_urls = ["https://x.com/POTUS"]  # Or a logged-in start URL

    def __init__(self):
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # Headless if needed
        self.driver = webdriver.Chrome(options=options)

    def close(self, reason):
        self.driver.quit()

    def parse(self, response):
        # 1. Login (if not already logged in):
        # Check if already logged in (e.g., look for a specific element)
        if not self.is_logged_in():  # Implement this check (see below)
            self.login()

        # 2. Get Cookies (after login):
        cookies = self.driver.get_cookies()
        # Convert Selenium cookies to Scrapy cookies
        scrapy_cookies = {}
        for cookie in cookies:
            scrapy_cookies[cookie['name']] = cookie['value']

        # 3. Load the target URL with the cookies
        self.driver.get(response.url)

        # ... (wait for page load, extract data as before)

        # Example of yielding with cookies:
        yield scrapy.Request(
            url=response.url,
            callback=self.parse_tweet_page,  # New callback for the actual scraping
            cookies=scrapy_cookies, # Pass the cookies to the request
            meta={'selenium_cookies': cookies} # Pass the cookies to the meta for potential later use
        )

    def is_logged_in(self):
        # Implement a check to determine if the user is already logged in.
        # This could involve looking for a specific element on the page
        # that is only present when the user is logged in.
        try:
            # Example: Check if the user's profile icon is present
            self.driver.find_element(By.CSS_SELECTOR, '[data-testid="User-Avatar"]')  # Replace with actual selector
            return True
        except:
            return False

    def login(self):
        # Implement your login logic here.
        # This will usually involve finding the login form elements
        # and submitting the form with the user's credentials.

        # Example (adapt to Twitter's current login form):
        self.driver.get("https://x.com/login")  # Go to the login page
        time.sleep(2) # Wait for the page to load
        username_input = self.driver.find_element(By.NAME, "text")  # Replace with the actual input name/selector
        password_input = self.driver.find_element(By.NAME, "password")  # Replace with the actual input name/selector
        username_input.send_keys("your_username")
        password_input.send_keys("your_password")
        password_input.submit()

        # IMPORTANT: Add explicit waits after login to make sure the page has loaded
        # before proceeding.
        time.sleep(5)  # Adjust the wait time as needed.
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="User-Avatar"]'))  # Check for an element after login
        )

    def parse_tweet_page(self, response):
        # Now you're on the page with cookies set by the previous request
        # You can use Scrapy selectors to extract the data.
        tweets = response.css('article[role="article"]')
        # ... (rest of your scraping logic as before)