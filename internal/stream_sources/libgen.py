from internal.stream_sources.base import IStreamSource
from internal.stream_sources.exceptions import UnexpectedResponse, PageNotFound
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select
import requests
from bs4 import BeautifulSoup
from typing import List
import time

from internal.models.libgen import LibgenBook, LibgenTopic


BASE_URL = "https://libgen.is/"
BASE_URL_DOWNLOAD = "https://libgen.gs/"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}
class Libgen(IStreamSource):

    def __init__(self, db_session: sessionmaker[Session]) -> None:
        self.db_session = db_session

    def monitor_streams(self):
        soup = make_request_and_soup(BASE_URL)
        for listColumn in soup.find(id="menu").find_all("ul", "greybox"):
            for a_tag_main_category in listColumn.find_all("a", "drop"):
                main_category = a_tag_main_category.text.strip()
                print_with_libgen_prefix(f"Processing main category: {main_category}")
                for a_tag_sub_category in a_tag_main_category.find_next("ul").find_all("a"):
                    sub_category = a_tag_sub_category.text.strip()
                    print_with_libgen_prefix(f"Processing sub category: {sub_category}")
                    with self.db_session() as session:
                        subtopic = get_or_create_libgen_topic(session, main_category, sub_category)

                    sub_category_url = a_tag_sub_category["href"]
                    page = 1
                    while True:
                        print_with_libgen_prefix(f"Processing page {page} of {sub_category}")
                        soup = make_request_and_soup(BASE_URL + sub_category_url + f"&page={page}")
                        table = soup.find_all("table")[2]
                        rows = table.find_all("tr")[1:]
                        if len(rows) == 0:
                            break
                        for row in rows:
                            columns = row.find_all("td")
                            if len(columns) < 10:
                                continue
                            libgen_id = columns[0].text.strip()
                            authors = columns[1].text.strip()
                            title = columns[2].text.strip()
                            publisher = columns[3].text.strip()
                            year = columns[4].text.strip()
                            pages = columns[5].text.strip()
                            language = columns[6].text.strip()
                            size = columns[7].text.strip()
                            extension = columns[8].text.strip()
                            download_page = columns[10].find("a")["href"]
                            download_page_soup = make_request_and_soup(download_page)
                            download_link = BASE_URL_DOWNLOAD + download_page_soup.find("table", id="main").tr.find_all("td")[1].a["href"]

                            with self.db_session() as session:
                                create_or_update_libgen_book(
                                    session,
                                    libgen_id,
                                    title,
                                    authors,
                                    publisher,
                                    year,
                                    pages,
                                    language,
                                    size,
                                    extension,
                                    download_link,
                                    subtopic.id
                                )

                        page += 1

                        
                    



def make_request_and_soup(url: str) -> BeautifulSoup:
    """Make a GET request to the specified URL with the headers."""
    response = requests.get(url, headers=REQUEST_HEADERS)
    if response.status_code == 404:
        raise PageNotFound(f"Page not found: {url}")
    if response.status_code != 200:
        raise UnexpectedResponse(f"Unexpected status code {response.status_code} from {url}")
    return BeautifulSoup(response.content, "html.parser")


                
def print_with_libgen_prefix(message: str) -> None:
    print(f"[Libgen] {message}")
            
def get_or_create_libgen_topic(session: Session, topic_name: str, sub_topic_name: str) -> LibgenTopic:
    """Get or create a topic and subtopic in the database."""
    # Check if the main topic exists
    main_topic = session.scalars(select(LibgenTopic).where(LibgenTopic.name == topic_name)).first()
    if not main_topic:
        # Create the main topic if it doesn't exist
        main_topic = LibgenTopic(name=topic_name)
        session.add(main_topic)
        session.commit()

    # Check if the subtopic exists with the correct parent
    subtopic = session.scalars(
        select(LibgenTopic).where(
            LibgenTopic.name == sub_topic_name,
            LibgenTopic.parent_id == main_topic.id
        )
    ).first()
    if subtopic:
        return subtopic

    # Create the subtopic with the main topic as its parent
    subtopic = LibgenTopic(name=sub_topic_name, parent_id=main_topic.id)
    session.add(subtopic)
    session.commit()
    session.refresh(subtopic)  # Refresh to get the ID of the new subtopic

    return subtopic

def create_or_update_libgen_book(
        session: Session, 
        libgen_id: int, 
        title: str, 
        authors: str, 
        publisher: str, 
        year: str,
        pages: str,
        language: str,
        size: str,
        extension: str,
        download_link: str, 
        topic_id: int):
    # Check if the book already exists using libgen_id
    book = session.scalars(
        select(LibgenBook).where(LibgenBook.libgen_id == libgen_id)
    ).first()

    if book:
        # Update the existing book
        book.title = title
        book.authors = authors
        book.publisher = publisher
        book.year = year
        book.pages = pages
        book.language = language
        book.size = size
        book.extension = extension
        book.download_link = download_link
        book.topic_id = topic_id
    else:
        # Create a new book entry
        book = LibgenBook(
            libgen_id=libgen_id,
            title=title,
            authors=authors,
            publisher=publisher,
            year=year,
            pages=pages,
            language=language,
            size=size,
            extension=extension,
            download_link=download_link,
            topic_id=topic_id
        )
        session.add(book)

    # Commit the changes to the database
    session.commit()

    return book

