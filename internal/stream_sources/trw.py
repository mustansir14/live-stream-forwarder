import multiprocessing
import os
import shutil
import time
import uuid
from typing import Generator, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from internal.enums import StreamSource
from internal.redis import RedisClient
from internal.schemas import BaseChatMessage, Stream, StreamChatMessage
from internal.stream_sources.base import IStreamSource
from internal.utils import *

CHANNELS_TO_MONITOR = [
    "https://app.jointherealworld.com/chat/01GVZRG9K25SS9JZBAMA4GRCEF/01JDEQ9MJA984M1NSPQZGM5BZC",
    "https://app.jointherealworld.com/chat/01GGDHGV32QWPG7FJ3N39K4FME/01GHHNFJ8H56EY45HTHESZTZGJ",
    "https://app.jointherealworld.com/chat/01GGDHGYWCHJD6DSZWGGERE3KZ/01GHHMNMCRY7YMRWD9MQPJ2H0Q",
    "https://app.jointherealworld.com/chat/01GGDHHZ377R1S4G4R6E29247S/01GHSBDYFPFBMQ1Y8B787ANNFA",
    "https://app.jointherealworld.com/chat/01GW4K82142Y9A465QDA3C7P44/01GKDTJZ2YCBW2FJKEN99F2NEQ",
    "https://app.jointherealworld.com/chat/01GGDHHAR4MJXXKW3MMN85FY8C/01GHK58VJV5AV7T1DY83PGKSJW",
    "https://app.jointherealworld.com/chat/01GGDHHJJW5MQZBE0NPERYE8E7/01GHP2BTZKB71RJRQ48KN5KK7G",
    "https://app.jointherealworld.com/chat/01HZFA8C65G7QS2DQ5XZ2RNBFP/01GXNM8K22ZV1Q2122RC47R9AF",
    "https://app.jointherealworld.com/chat/01GW4K766W7A5N6PWV2YCX0GZP/01GKDTKWTF7KWYQM9JPZNDE5E8",
    "https://app.jointherealworld.com/chat/01GXNJTRFK41EHBK63W4M5H74M/01GXNM8K22ZV1Q2122RC47R9AF",
    "https://app.jointherealworld.com/chat/01HSRZK1WHNV787DBPYQYN44ZS/01HST8F8W7P3VYBXCSDAVSS0GF",
    "https://app.jointherealworld.com/chat/01GGDHJAQMA1D0VMK8WV22BJJN/01J4RER9MEEWZSV4R14AP1WXGT",   
]

DISPLAY_PORT_START = 100


class TRW(IStreamSource):

    def __init__(
        self,
        username: str,
        password: str,
        rtmp_server_key: str,
        redis_client: RedisClient,
    ) -> None:
        self.username = username
        self.password = password
        self.rtmp_server_key = rtmp_server_key
        self.redis_client = redis_client
        self.channel_stream_ids = {}

    def monitor_streams(self, destination_rtmp_server: str):

        chromedriver_path = ChromeDriverManager().install()
        print_with_process_id("Initializing driver")
        driver = initialize_trw(
            self.username, self.password, chromedriver_path, -1, "", "", headless=True
        )
        i = -1
        while True:
            i = (i + 1) % len(CHANNELS_TO_MONITOR)
            channel = CHANNELS_TO_MONITOR[i]

            # if stream already running, skip
            stream_id = self.channel_stream_ids.get(channel)
            if stream_id and self.redis_client.get_running_stream(stream_id):
                print_with_process_id("stream already running")
                continue

            print_with_process_id("fetching channel " + channel)
            driver.get(channel)
            # print_with_process_id("Getting youtube")
            # driver.get("https://www.youtube.com/watch?v=k9KhdIxeAVM&ab_channel=shfashowIndia")

            # check if stream is available
            try:
                print_with_process_id("waiting for stream")
                wait_for_stream(driver)
            except Exception as e:
                print_with_process_id("stream not available")
                continue

            print_with_process_id("stream found")

            stream_id = str(uuid.uuid4())
            self.channel_stream_ids[channel] = stream_id

            process = multiprocessing.Process(
                target=self.__start_stream,
                args=(
                    stream_id,
                    destination_rtmp_server,
                    channel,
                    chromedriver_path,
                    i,
                ),
            )
            process.start()

    def __start_stream(
        self,
        stream_id: str,
        destination_rtmp_server: str,
        channel: str,
        chromedriver_path: str,
        stream_number: int,
    ) -> None:

        while True:
            print_with_process_id("starting streaming")

            display_port = f":{DISPLAY_PORT_START + stream_number}"
            virtual_sink_name = f"virtual_sink_{stream_number}"

            stream_process = None

            try:

                driver = initialize_trw(
                    self.username,
                    self.password,
                    chromedriver_path,
                    stream_number,
                    virtual_sink_name,
                    display_port,
                    headless=False,
                )
                print_with_process_id("fetching channel")
                driver.get(channel)

                # check if stream is available
                try:
                    print_with_process_id("finding stream")
                    stream = wait_for_stream(driver)
                except Exception as e:
                    print_with_process_id("stream not available")
                    return

                stream_name = stream.find_element(
                    By.CLASS_NAME, "flex.items-center.gap-1"
                ).text
                # stream_name = "Test stream"

                stream.click()
                time.sleep(10)

                # get stream video div
                try:
                    video = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                "#chat > article > div.absolute.top-0.right-0.left-0.z-20.flex.flex-col > div.relative.z-10.flex.w-full.items-center.justify-center.bg-black",
                            )
                        )
                    )
                except Exception:
                    print_with_process_id("stream video not found")
                    return

                # double click on video to make full screen
                time.sleep(10)
                actionChains = ActionChains(driver)
                actionChains.double_click(video).perform()

                driver.execute_script(
                    'document.getElementsByTagName("video")[0].play()'
                )

                stream_url = destination_rtmp_server + "/" + stream_id
                stream = Stream(
                    id=stream_id,
                    name=stream_name,
                    url=stream_url,
                    source=StreamSource.TRW,
                )
                print_with_process_id("Relaying stream to destination")
                stream_process = relay_stream_to_destination(
                    stream_url + "?key=" + self.rtmp_server_key,
                    virtual_sink_name,
                    display_port,
                )
                self.redis_client.add_running_stream(stream)
                # stream_process.wait()

                for stream_message in self.__get_stream_messages(driver):
                    self.redis_client.enqueue_stream_message(stream_id, stream_message)

                self.redis_client.delete_stream_by_id(stream_id)
                stream_process.kill()
            except Exception as e:
                print_with_process_id("Error in process " + str(e))
                print_with_process_id("Restarting process")
                if stream_process:
                    try:
                        stream_process.kill()
                    except:
                        pass
                try:
                    self.redis_client.delete_stream_by_id(stream_id)
                except:
                    pass
                try:
                    driver.quit()
                except:
                    pass

    def __get_stream_messages(
        self,
        driver: webdriver.Chrome,
    ) -> Generator[StreamChatMessage, None, None]:

        existing_messages_elements = driver.find_element(By.ID, "chat").find_elements(
            By.CLASS_NAME, "chat-message"
        )
        for message in existing_messages_elements:
            try:
                parsed_message = parse_message_element(message)
                yield parsed_message
            except Exception as e:
                print_with_process_id("error parsing message " + str(e))

        while True:
            current_message_elements = driver.find_element(By.ID, "chat").find_elements(
                By.CLASS_NAME, "chat-message"
            )
            if len(current_message_elements) != len(existing_messages_elements):
                new_messages_count = len(current_message_elements) - len(
                    existing_messages_elements
                )
                new_message_elements = current_message_elements[-new_messages_count:]
                for message in new_message_elements:
                    parsed_message = parse_message_element(message)
                    yield parsed_message
                existing_messages_elements += new_message_elements
            try:
                driver.find_element(By.TAG_NAME, "video")
            except Exception:
                print_with_process_id("stream ended")
                return
            time.sleep(0.5)


def initialize_trw(
    username: str,
    password: str,
    chromedriver_path: str,
    number: str,
    virtual_sink_name: str,
    display_port: str,
    headless: bool,
) -> webdriver.Chrome:
    chrome_opt = Options()
    if not headless:
        print_with_process_id("Creating virtual sink")
        create_virtual_sink(virtual_sink_name)
        print_with_process_id("Starting xvfb")
        start_xvfb(display_port)
        os.environ["DISPLAY"] = display_port
        os.environ["PULSE_SINK"] = virtual_sink_name
    else:
        chrome_opt.add_argument("--headless")
    chrome_opt.add_argument("--incognito")
    user_data_dir = f"/tmp/trw_user_data_{number}"
    # delete dir if exists
    if os.path.exists(user_data_dir):
        shutil.rmtree(user_data_dir)
    chrome_opt.add_argument("--user-data-dir=" + user_data_dir)
    chrome_opt.add_argument(
        "--autoplay-policy=no-user-gesture-required"
    )  # Ensure autoplay works for audio
    chrome_opt.add_argument("--use-fake-ui-for-media-stream")
    chrome_opt.add_argument("--window-size=1280,720")
    chrome_opt.add_argument("--no-sandbox")
    chrome_opt.add_argument("--disable-dev-shm-usage")
    chrome_opt.add_argument("--disable-renderer-backgrounding")
    chrome_opt.add_argument("--disable-background-timer-throttling")
    chrome_opt.add_argument("--disable-backgrounding-occluded-windows")
    chrome_opt.add_argument("--disable-client-side-phishing-detection")
    chrome_opt.add_argument("--disable-crash-reporter")
    chrome_opt.add_argument("--disable-oopr-debug-crash-dump")
    chrome_opt.add_argument("--no-crash-upload")
    chrome_opt.add_argument("--disable-low-res-tiling")
    chrome_opt.add_argument("--disable-gpu")

    chrome_opt.add_experimental_option("useAutomationExtension", False)
    chrome_opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=chrome_opt, service=Service(chromedriver_path))
    driver.maximize_window()
    driver.get("https://app.jointherealworld.com/auth/login?a=p86p7wfnzd&subid=login")

    # login
    driver.find_element(By.ID, "email").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CLASS_NAME, "btn-primary.btn-no-effects").click()
    print_with_process_id("logged in")
    time.sleep(5)

    # close modal
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "modal-body"))
        ).find_elements(By.CLASS_NAME, "btn.btn-circle")[1].click()
        print_with_process_id("popup closed")
    except Exception as e:
        print_with_process_id(e)
        print_with_process_id("popup not found")

    return driver


def parse_message_element(message_element: WebElement) -> StreamChatMessage:

    message = StreamChatMessage(
        id=message_element.get_attribute("id"),
        message=message_element.find_element(
            By.CLASS_NAME, "custom-break-words.break-words.text-sm"
        ).text,
        author=message_element.find_element(
            By.CLASS_NAME, "inline-flex.items-center.cursor-pointer.font-medium.text-xs"
        ).text,
        time=message_element.find_element(
            By.CLASS_NAME, "ml-3.cursor-default.text-3xs.opacity-50"
        ).text,
        reply_to=None,
    )

    try:
        reply_to_message = message_element.find_element(
            By.CLASS_NAME, "text-left.font-medium.text-primary.text-xs"
        )
        message.reply_to = BaseChatMessage(
            message=reply_to_message.text,
            author=message_element.find_element(
                By.CLASS_NAME, "relative.flex.items-center.text-left"
            ).text,
        )
    except Exception:
        pass

    return message


def wait_for_stream(driver: webdriver.Chrome) -> WebElement:
    return WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "#three-columns-layout > div:nth-child(1) > menu > section.flex.flex-1.flex-col.overflow-x-hidden.border-grey-secondary.border-r.bg-base-100.pt-inset-top.lg\:border-0 > div.group.relative.cursor-pointer.border.border-neutral.border-b.bg-base-200.p-3.mb-3.hover\:bg-success.hover\:bg-opacity-30",
            )
        )
    )


def print_with_process_id(message: str):
    print(f"[{os.getpid()}] {message}")