import logging

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from connection_manager import ConnectionManager
from chat_server import ChatServer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
manager = ConnectionManager()


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>Chat</h1>
        <h2>Room: <span id="room-id"></span><br> Your ID: <span id="client-id"></span></h2>
        <label>Room: <input type="text" id="channelId" autocomplete="off" value="foo"/></label>
        <button onclick="connect(event)">Connect</button>
        <hr>
        <form style="position: absolute; bottom:0" action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = null;
            function connect(event) {
                var client_id = Date.now()
                document.querySelector("#client-id").textContent = client_id;
                document.querySelector("#room-id").textContent = channelId.value;
                if (ws) ws.close()
                ws = new WebSocket(`ws://localhost:8000/ws/${channelId.value}/${client_id}`);
                ws.onmessage = function(event) {
                    console.log(event.data)
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                event.preventDefault()
            }
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
                document.getElementById("messageText").focus()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{channel_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, channel_id: str, client_id: int):
    await manager.connect(websocket)

    chat_server = ChatServer(websocket, channel_id, client_id, logger)
    await chat_server.run()