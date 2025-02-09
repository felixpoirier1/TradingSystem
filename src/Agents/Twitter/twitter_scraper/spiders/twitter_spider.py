import scrapy


class TwitterSpiderSpider(scrapy.Spider):
    name = "twitter_spider"
    allowed_domains = ["x.com"]
    start_urls = ["https://x.com"]

    def parse(self, response):
        tweets = response.css('article[role="article"] div[data-testid="tweetText"] span::text').getall()

        for tweet in tweets:
            print(tweet)    