import multiprocessing
import os
import shutil
import time
import uuid
from typing import Dict, Generator, List
import json
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from internal.message_parser import MessageParser
from internal.redis import RedisClient
from internal.schemas import BaseChatMessage, TRWStream, TRWStreamChatMessage, TRWCampus
from internal.stream_sources.base import IStreamSource
from internal.utils import *
from internal.otp_fetcher import OTPFetcher

CHANNELS_TO_MONITOR = [
    (TRWCampus.BUSINESS_MASTERY, "https://app.jointherealworld.com/chat/01GVZRG9K25SS9JZBAMA4GRCEF/01JDEQ9MJA984M1NSPQZGM5BZC"),
    (TRWCampus.CRYPTO_CURRENCY_INVESTING, "https://app.jointherealworld.com/chat/01GGDHGV32QWPG7FJ3N39K4FME/01GHHNFJ8H56EY45HTHESZTZGJ"),
    (TRWCampus.COPYWRITING, "https://app.jointherealworld.com/chat/01GGDHGYWCHJD6DSZWGGERE3KZ/01GHHMNMCRY7YMRWD9MQPJ2H0Q"),
    (TRWCampus.STOCKS, "https://app.jointherealworld.com/chat/01GGDHHZ377R1S4G4R6E29247S/01GHSBDYFPFBMQ1Y8B787ANNFA"),
    (TRWCampus.CRYPTO_TRADING, "https://app.jointherealworld.com/chat/01GW4K82142Y9A465QDA3C7P44/01GKDTJZ2YCBW2FJKEN99F2NEQ"),
    (TRWCampus.ECOMMERCE, "https://app.jointherealworld.com/chat/01GGDHHAR4MJXXKW3MMN85FY8C/01GHK58VJV5AV7T1DY83PGKSJW"),
    (TRWCampus.SOCIAL_MEDIA_CLIENT_ACQUISITION, "https://app.jointherealworld.com/chat/01GGDHHJJW5MQZBE0NPERYE8E7/01GHP2BTZKB71RJRQ48KN5KK7G"),
    (TRWCampus.AI_AUTOMATION_AGENCY, "https://app.jointherealworld.com/chat/01HZFA8C65G7QS2DQ5XZ2RNBFP/01GXNM8K22ZV1Q2122RC47R9AF"),
    (TRWCampus.CRYPTO_DEFI, "https://app.jointherealworld.com/chat/01GW4K766W7A5N6PWV2YCX0GZP/01GKDTKWTF7KWYQM9JPZNDE5E8"),
    (TRWCampus.CONTENT_CREATION_AI_CAMPUS, "https://app.jointherealworld.com/chat/01GXNJTRFK41EHBK63W4M5H74M/01GXNM8K22ZV1Q2122RC47R9AF"),
    (TRWCampus.HUSTLERS_CAMPUS, "https://app.jointherealworld.com/chat/01HSRZK1WHNV787DBPYQYN44ZS/01HST8F8W7P3VYBXCSDAVSS0GF"),
    (TRWCampus.THE_REAL_WORLD, "https://app.jointherealworld.com/chat/01GGDHJAQMA1D0VMK8WV22BJJN/01J4RER9MEEWZSV4R14AP1WXGT"),
    (TRWCampus.HEALTH_FITNESS, "https://app.jointherealworld.com/chat/01GVZRNVT519Q67C8BQGJHRDBY/01HPPX86PZ4QMEAZ35SZTBVGR6")
]

DISPLAY_PORT_START = 100


class TRW(IStreamSource):

    def __init__(
        self,
        username: str,
        password: str,
        rtmp_server_key: str,
        destination_rtmp_server: str,
        redis_client: RedisClient,
        openai_api_key: str,
        otp_email: str,
        otp_email_password: str,
        debug: bool = False,
    ) -> None:
        self.username = username
        self.password = password
        self.rtmp_server_key = rtmp_server_key
        self.destination_rtmp_server = destination_rtmp_server
        self.redis_client = redis_client
        self.channel_stream_ids: Dict[str, str] = {}
        self.channel_last_messages: Dict[str, TRWStreamChatMessage] = {}
        self.message_parser = MessageParser(openai_api_key)
        self.otp_fetcher = OTPFetcher(otp_email, otp_email_password)
        self.debug = debug

    def monitor_streams(self):

        chromedriver_path = ChromeDriverManager().install()
        print_with_process_id("Initializing driver")
        display_port = f":{DISPLAY_PORT_START - 1}"
        virtual_sink_name = f"virtual_sink_trw_main"
        driver = self.initialize_trw(
            chromedriver_path, -1, virtual_sink_name, display_port,
        )
        i = -1
        while True:
            try:
                i = (i + 1) % len(CHANNELS_TO_MONITOR)
                campus_channel = CHANNELS_TO_MONITOR[i]
                campus = campus_channel[0]
                channel = campus_channel[1]


                # if stream already running, skip
                stream_id = self.channel_stream_ids.get(channel)
                if stream_id and self.redis_client.get_trw_running_stream(stream_id):
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
                finally:
                    driver.save_screenshot("test.png")
                    # check for upcoming stream messages
                    self.__check_upcoming_stream_messages(driver, channel, campus)

                print_with_process_id("stream found")

                stream_id = str(uuid.uuid4())
                self.channel_stream_ids[channel] = stream_id

                process = multiprocessing.Process(
                    target=self.__start_stream,
                    args=(
                        stream_id,
                        self.destination_rtmp_server,
                        channel,
                        campus,
                        chromedriver_path,
                        i,
                    ),
                )
                process.start()
            except Exception as e:
                print_with_process_id("Main process exception, restarting..." + str(e))
                try:
                    self.logout(driver)
                except:
                    pass
                driver = self.initialize_trw(
                    chromedriver_path,
                    -1,
                    virtual_sink_name,
                    display_port,
                )

    def __start_stream(
        self,
        stream_id: str,
        destination_rtmp_server: str,
        channel: str,
        campus,
        chromedriver_path: str,
        stream_number: int,
    ) -> None:

        while True:
            print_with_process_id("starting streaming")

            display_port = f":{DISPLAY_PORT_START + stream_number}"
            virtual_sink_name = f"virtual_sink_{stream_number}"

            stream_process = None

            try:

                driver = self.initialize_trw(
                    chromedriver_path,
                    stream_number,
                    virtual_sink_name,
                    display_port,
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
                                By.TAG_NAME,
                                "video",
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

                driver.execute_script("document.body.style.cursor = 'none';")

                try:
                    driver.execute_script(
                        'document.getElementsByTagName("video")[0].play()'
                    )
                except:
                    pass

                stream_url = destination_rtmp_server + "/" + stream_id
                stream = TRWStream(
                    id=stream_id,
                    name=stream_name,
                    url=stream_url,
                    campus=campus,
                )
                print_with_process_id("Relaying stream to destination")
                stream_process = relay_stream_to_destination(
                    stream_url + "?key=" + self.rtmp_server_key,
                    virtual_sink_name,
                    display_port,
                )
                self.redis_client.add_trw_running_stream(stream)
                # stream_process.wait()

                for stream_message in self.__get_stream_messages(driver, video):
                    self.redis_client.enqueue_trw_stream_message(stream_id, stream_message)

                self.redis_client.delete_trw_stream_by_id(stream_id)
                stream_process.kill()
                self.logout(driver)
                return
            except Exception as e:
                print_with_process_id("Error in process " + str(e))
                print_with_process_id("Restarting process")
                if stream_process:
                    try:
                        stream_process.kill()
                    except:
                        pass
                try:
                    self.redis_client.delete_trw_stream_by_id(stream_id)
                except:
                    pass
                try:
                    self.logout(driver)
                except:
                    pass

    def __get_stream_messages(
        self,
        driver: webdriver.Chrome,
        video: WebElement,
    ) -> Generator[TRWStreamChatMessage, None, None]:

        existing_messages_elements = get_chat_messages(driver)
        for message in existing_messages_elements:
            try:
                parsed_message = parse_message_element(message)
                yield parsed_message
            except Exception as e:
                print_with_process_id("error parsing message " + str(e))

        while True:
            current_message_elements = get_chat_messages(driver)
            if len(current_message_elements) != len(existing_messages_elements):
                new_messages_count = len(current_message_elements) - len(
                    existing_messages_elements
                )
                new_message_elements = current_message_elements[-new_messages_count:]
                for message in new_message_elements:
                    try:
                        parsed_message = parse_message_element(message)
                        yield parsed_message
                    except Exception as e:
                        print_with_process_id("error parsing message " + str(e))
                existing_messages_elements += new_message_elements
            try:
                if not video.is_displayed():
                    print_with_process_id("stream ended")
                    return
            except Exception:
                print_with_process_id("stream ended")
                return
            try:
                driver.execute_script(
                    'document.getElementsByTagName("video")[0].play()'
                )
            except:
                pass
            time.sleep(0.5)

    def __check_upcoming_stream_messages(
        self, driver: webdriver.Chrome, channel: str, campus: TRWCampus
    ) -> None:
        chat_messages = get_chat_messages(driver)
        chat_messages.reverse()

        if not chat_messages:
            return

        channel_last_message = self.channel_last_messages.get(channel)

        for i, chat_message in enumerate(chat_messages[:5]):
            try:
                message = parse_message_element(chat_message)
                if i == 0:
                    self.channel_last_messages[channel] = message

                if channel_last_message and message.id == channel_last_message.id:
                    break

                upcoming_streams = self.message_parser.parse(message, campus)
                for upcoming_stream in upcoming_streams:
                    print_with_process_id("found upcoming stream " + str(upcoming_stream))
                    self.redis_client.add_trw_upcoming_stream(upcoming_stream)
            except Exception as e:
                print_with_process_id("error parsing message " + str(e))


    def initialize_trw(
        self,
        chromedriver_path: str,
        number: str,
        virtual_sink_name: str,
        display_port: str,
    ) -> webdriver.Chrome:
        chrome_opt = Options()
        if not self.debug:
            print_with_process_id("Creating virtual sink")
            create_virtual_sink(virtual_sink_name)
            print_with_process_id("Starting xvfb")
            start_xvfb(display_port)
            os.environ["DISPLAY"] = display_port
            os.environ["PULSE_SINK"] = virtual_sink_name
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
        driver.find_element(By.ID, "email").send_keys(self.username)
        driver.find_element(By.ID, "password").send_keys(self.password)
        driver.find_element(By.CLASS_NAME, "btn-primary.btn-no-effects").click()
        print_with_process_id("logged in")
        time.sleep(5)
        
        # wait for 2fa popup
        try:
            popup = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "modal-body.relative.flex.flex-col.bg-neutral.shadow-xl"))
            )
            if "verification" in popup.text.lower() or "verify" in popup.text.lower():
                print_with_process_id("2fa popup found")
                otp_counter = 0
                while True:
                    time.sleep(15)
                    otp = self.otp_fetcher.fetch_otp()
                    if otp:
                        print_with_process_id("got otp " + otp)
                        break
                    otp_counter += 1
                    if otp_counter == 10:
                        print_with_process_id("Waiting for two minutes but no otp found. Exiting and restarting flow...")
                        try:
                            self.logout()
                        except:
                            pass
                        return self.initialize_trw(chromedriver_path, number, virtual_sink_name, display_port)
                
                popup.find_element(By.TAG_NAME, "input").send_keys(otp)
                popup.find_element(By.CLASS_NAME, "btn.btn-primary").click()
                time.sleep(5)
                print_with_process_id("2fa entered")
        except Exception as e:
            if self.debug:
                print_with_process_id(e)
            print_with_process_id("2fa popup not found")

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
    
    def logout(self, driver: webdriver.Chrome):
        token = json.loads(driver.execute_script("return window.localStorage.getItem(\"rauth\");")).get("token")
        if not token:
            print_with_process_id("Token not found")
            return
        url = "https://api.therealworld.ag/auth/session/logout"

        headers = {
            'sec-ch-ua-platform': '"Linux"',
            'Referer': 'https://app.jointherealworld.com/',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'X-Session-Token': token,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'X-Client-Version': '2.5.338'
        }

        response = requests.request("POST", url, headers=headers)
        if response.status_code != 204:
            print_with_process_id("Logout failed with status code: " + str(response.status_code))
            return
        print_with_process_id("Logout Sucessful.")
        driver.quit()


def parse_message_element(message_element: WebElement) -> TRWStreamChatMessage:

    message = TRWStreamChatMessage(
        id=message_element.get_attribute("id"),
        message=message_element.find_element(
            By.CLASS_NAME, "custom-break-words.break-words.text-sm"
        ).text,
        author=message_element.find_element(
            By.CLASS_NAME, "inline-flex.items-center.cursor-pointer.font-medium.text-xs"
        ).text.strip(),
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
    return WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (
                By.CLASS_NAME,
                "group.relative.cursor-pointer.border.border-neutral.border-b.bg-base-200.p-3.mb-3"
            )
        )
    )


def print_with_process_id(message: str):
    print(f"TRW [{os.getpid()}] {message}")


def get_chat_messages(driver: webdriver.Chrome) -> List[WebElement]:
    return driver.find_element(By.ID, "chat-scroller").find_elements(
        By.CLASS_NAME, "chat-message"
    )
