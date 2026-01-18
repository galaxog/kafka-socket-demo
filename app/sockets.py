import socketio

# Socket.IO server (ASGI)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


@sio.event
async def connect(sid, environ, auth):  # noqa: ANN001
    await sio.emit("server_hello", {"message": "connected"}, to=sid)


@sio.event
async def disconnect(sid):  # noqa: ANN001
    # No-op; helpful for debugging
    return
