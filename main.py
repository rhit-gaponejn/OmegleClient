import Omegle


client = Omegle.Client()

client.start(Unmonitored=False, Topics=['BOT_TEST'], AutoReconnect=False)


def send(msg):
    client.loop.create_task(client.Send(msg))


while True:
    if client.Connected:
        send("Hello nice to meet you!")
        break

while True:
    if client.GotMessage:
        send("thanks")
        client.Message = ""
        client.GotMessage = False
