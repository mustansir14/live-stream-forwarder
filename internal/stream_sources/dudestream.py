from internal.stream_sources.base import IStreamSource
from internal.stream_sources.exceptions import UnexpectedResponse
from internal.schemas import DudestreamStream
from internal.redis import RedisClient
import time
import uuid
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class DudeStream(IStreamSource):

    def __init__(self, redis_client: RedisClient) -> None:
        self.redis_client = redis_client
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        self.categories = [
            ("Soccer", "https://dudestream.com/category/soccer/",),
            ("MSL", "https://dudestream.com/category/mls/",),
            ("Boxing", "https://dudestream.com/category/boxing/",),
            ("MMA", "https://dudestream.com/category/mma/",),
            ("MLB", "https://dudestream.com/category/mlb/",),
            ("NBA", "https://dudestream.com/category/nba/",),
            ("WNBA", "https://dudestream.com/category/wnba/",),
            ("NHL", "https://dudestream.com/category/nhl/",),
            ("NFL", "https://dudestream.com/category/nfl/",),
            ("CFL", "https://dudestream.com/category/cfl/",),
            ("UFL", "https://dudestream.com/category/ufl/",),
            ("NCCAF", "https://dudestream.com/category/nccaf/",),
            ("NCCAB", "https://dudestream.com/category/nccab/",),
            ("F1", "https://dudestream.com/category/f1/",),
            ("MOTOGP", "https://dudestream.com/category/motogp/",),
            ("TENNIS", "https://dudestream.com/category/tennis/",),
            ("GOLF", "https://dudestream.com/category/golf/",),
            ("WWE", "https://dudestream.com/category/wwe/",),
            ("LIVE TV", "https://dudestream.com/category/live-tv/",),
            ("SCHEDULE", "https://dudestream.com/category/schedule/")
        ]

    def monitor_streams(self):

        for category_name, category_url in self.categories:
            print_with_dudestream_prefix(f"Checking category: {category_name}")
            res = requests.get(category_url, headers=self.headers)
            if res.status_code != 200:
                raise UnexpectedResponse(f"Unexpected status code {res.status_code} from {category_url}")
            soup = BeautifulSoup(res.content, "html.parser")
            articles = soup.find_all("article")
            # delete all existing streams for this category
            self.redis_client.delete_dudestream_category_streams(category_name)
            print_with_dudestream_prefix(f"Found {len(articles)} streams in category: {category_name}")
            for article in articles:
                article_url = article.h4.a["href"]
                res = requests.get(article_url, headers=self.headers)
                if res.status_code != 200:
                    print(f"Unexpected status code {res.status_code} from {article_url}")
                    continue
                soup = BeautifulSoup(res.content, "html.parser")
                stream_title = soup.h1.text.strip()
                stream_date = datetime.strptime(soup.find("span", "mg-blog-date").text.strip(), "%b %d, %Y").date()
                stream_embed_link = soup.iframe["src"]
                stream_id = str(uuid.uuid4())
                stream = DudestreamStream(
                    id=stream_id,
                    name=stream_title,
                    url=stream_embed_link,
                    date=stream_date,
                    category=category_name,
                )
                self.redis_client.add_dudestream_stream(stream)

        print_with_dudestream_prefix(f"All categories checked. Sleeping for 30 minutes.")
        time.sleep(1800)  # Sleep for 30 minutes before checking again


                
def print_with_dudestream_prefix(message: str) -> None:
    print(f"[Dudestream] {message}")
            

        


