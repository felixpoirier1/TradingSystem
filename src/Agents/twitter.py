import asyncio
from twscrape import API, gather
from twscrape.logger import set_log_level

async def main():
    api = API()  # or API("path-to.db") - default is `accounts.db`

    # ADD ACCOUNTS (for CLI usage see BELOW)
    cookies = "abc=12; ct0=xyz"  # or '{"abc": "12", "ct0": "xyz"}'

    await api.pool.add_account("GustavoMed96357", "Adpqwert_1234", "r6c9u@e-record.com", "mail_pass1", cookies=cookies)
    await api.pool.login_all()

    # NOTE 1: gather is a helper function to receive all data as list, FOR can be used as well:
    async for tweet in api.search("Donald Trump"):
        print("-"*20, "\n", tweet.date, tweet.id, tweet.user.username, tweet.rawContent)  # tweet is `Tweet` object


if __name__ == "__main__":
    asyncio.run(main())

