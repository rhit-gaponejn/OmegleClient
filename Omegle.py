import json
import time
from threading import Thread
import aiohttp
import random
import asyncio
from urllib.parse import urlencode, quote_plus
from aiohttp import ClientTimeout, TCPConnector


class ThreadedOmegle(Thread):
    """
    Just alot of weird threading stuff here...
    """

    def __init__(self, instance):
        self.instance = instance
        super().__init__()

    def run(self):
        """
        Block this thread with an instance of the Omegle base Client

        """
        self.instance.run()


def generate_random_id_and_get_server():
    SERVER_LIST = [f'front{n}' for n in range(1, 48)]
    SERVER = random.choice(SERVER_LIST)
    _RANDOM_ID_POOL = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(_RANDOM_ID_POOL) for _ in range(8)), SERVER


RANDOM_ID, Server = generate_random_id_and_get_server()


class Client:
    """
    Note:
    OmeglePy wasn't getting updates, so I made my own omegle client :)

    Gotta have this because It's just really helpful:
    https://gist.github.com/nucular/e19264af8d7fc8a26ece
    """

    def __init__(self, loop=None):
        self.Client_ID = str
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.thread = None
        self.topics = list
        self.unmonitored = True
        self.AutoReconnect = True
        self.Message = str
        self.GotMessage: bool = False
        self.Connected: bool = False

    @staticmethod
    async def Make_Request(url: str, data, server=Server):
        """Makes the requests to Omegle"""
        try:
            session_timeout: ClientTimeout = aiohttp.ClientTimeout(total=None, sock_connect=300,
                                                                   sock_read=300)
            connector: TCPConnector = aiohttp.TCPConnector(force_close=True)

            async with aiohttp.ClientSession(connector=connector, timeout=session_timeout) as s:
                if data == "status":
                    async with await s.get(f"https://{server}.omegle.com/" + url, data=data) as result:
                        try:
                            response = await result.json()
                        except:
                            response = {'response': await result.text(), 'url': url}
                elif server != Server:
                    async with await s.post(f"https://{server}/" + url, data=data) as result:
                        try:
                            response = await result.json()
                        except:
                            response = {'response': await result.text(), 'url': url}
                else:
                    async with await s.post(f"https://{server}.omegle.com/" + url, data=data) as result:
                        try:
                            response = await result.json()
                        except:
                            response = {'response': await result.text(), 'url': url}
        except Exception as e:
            return {'response': '500', 'error': str(e)}

        return response

    async def ConnectToOmegle(self) -> None:
        """
        Makes the first connection to Omegle
        """
        # Connect to status server                                    0.4695589093025774
        results = await self.Make_Request(f"status", data={'nocache': random.random(), 'randid': RANDOM_ID})
        print(f"Connection to status server:\n {results}")

        # connect to check server to get cc string
        cc = "2eebb771d9109efb34ada30e8f65c3aa2e98b563"
        antinudeservers = results.get('antinudeservers')

        if antinudeservers:
            server = random.choice(antinudeservers)
            cc = await self.Make_Request("check", data={}, server=server)
            if cc['response']:
                cc = cc['response']
            else:
                print("didnt get the cc for some reason: " + cc)

        # Connect to start server
        data = {'randid': RANDOM_ID}

        encoded_topics = ''
        if self.topics:
            encoded_topics = urlencode({'topics': json.dumps(self.topics)}, quote_via=quote_plus)
            print(encoded_topics)

        url = f"start?caps=recaptcha2,t3&firstevents=1&spid=&randid=&cc={cc}&{encoded_topics}&lang=en"

        if self.unmonitored:
            url += '&group=unmon'

        # print(url)

        results = await self.Make_Request(url, data=data)

        print(f"\nConnection to start server:\n {results}")

        self.Client_ID: str = results["clientID"]
        print("\nClient ID is: " + self.Client_ID)

    async def GetEvent(self) -> None:
        """
        Gets the events from the Omegle server
        """

        while True:
            time.sleep(1)
            async with asyncio.Semaphore(10):
                response = await self.Make_Request(f"events", data={'id': self.Client_ID})
                if isinstance(response, list) and len(response) > 0:
                    event = response[0]
                    if event[0] == 'gotMessage':
                        print("Player:", event[1])
                        self.GotMessage = True
                        self.Message = str(event[1])

                        # Vars.loop.create_task(Send("hey m"))
                    else:
                        self.GotMessage = False
                        if event[0] == 'connected':
                            print("connected to player")
                            self.Connected = True
                        elif event[0] == 'strangerDisconnected':
                            print("Player: disconnected")
                            self.Connected = False
                            if self.AutoReconnect:
                                self.loop.create_task(self.Disconnect())
                                self.loop.create_task(self.ConnectToOmegle())

    async def Send(self, message: str) -> None:
        """
        Sends a message to the connected stranger

        :param message: The message to send
        """
        task = self.loop.create_task(self.Make_Request(f"send", data={'msg': message, 'id': self.Client_ID}))
        await task
        res = task.result()['response']
        if res == "win":
            print(f"Game: {message}")
        else:
            print("Error in sending the message. it might not have gone through. Response:", res)

    async def Disconnect(self) -> None:
        """
        Disconnects from the current conversation
        """
        task = self.loop.create_task(self.Make_Request("disconnect", data={'id': self.Client_ID}))
        await task
        res = task.result()
        print(res)

    async def Skip(self) -> None:
        """
        Skips the current Stranger by disconnecting and reconnecting
        """
        task = self.loop.create_task(self.Disconnect())
        await task
        print(task.result())
        task = asyncio.create_task(self.ConnectToOmegle())
        await task
        print(task.result())

    def run(self):
        """
        Why is there both a run and a start? idk threading is weird... just call Start() to start the client

        """
        self.loop.create_task(self.ConnectToOmegle())

        self.loop.create_task(self.GetEvent())
        self.loop.run_forever()

    def start(self, Topics: list, Unmonitored: bool = False, AutoReconnect: bool = True):
        """
        Starts the client and connects to Omegle.

        :param AutoReconnect: Set to True if you want to auto reconnect after disconnecting from a chat
        :param Topics: Topics for interests chat leave blank for non interest chat.
        :param Unmonitored: Unmonitored set to true if your banned and wanna still chat or if you just wanna be in the unmonitored section

        """
        self.AutoReconnect = AutoReconnect
        self.topics = Topics
        self.unmonitored = Unmonitored
        try:
            self.thread = ThreadedOmegle(self)
            self.thread.start()
        except:
            print('Thread failure')

        return self
    