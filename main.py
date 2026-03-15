from aioconsole import ainput
from round import Round
from netpeer import NetPeer
from sys import argv
from asyncio import ensure_future, run, Event, CancelledError


async def main(server, role):
    peer = NetPeer(server)

    their_secret = None
    both_ready = Event()
    round_task = None

    @peer.on("secret")
    def on_secret(data):
        nonlocal their_secret
        try:
            their_secret = int(data["value"])
            both_ready.set()
        except (ValueError, KeyError):
            print("Invalid secret received")

    @peer.on("_disconnect")
    def on_disconnect(_):
        print("Peer disconnected!", flush=True)
        both_ready.set()
        if round_task and not round_task.done():
            round_task.cancel()

    if role == "host":
        print("Hosting... run: python main.py join")
        await peer.host()
    else:
        print("Joining...")
        await peer.join()

    print("Peer connected!", flush=True)

    my_secret = int(await ainput("Choose your opponent's secret [0..100]: "))
    peer.send("secret", {"value": my_secret, "from": role})
    print("Waiting for opponent to choose your secret...")

    await both_ready.wait()

    if their_secret is not None and peer.connected:
        round_task = ensure_future(Round(their_secret).run_round())
        try:
            await round_task
        except CancelledError:
            print("Round ended — opponent disconnected.")

    await peer.close()


if __name__ == "__main__":
    role = argv[1] if len(argv) > 1 else "host"
    run(main("http://localhost:8080", role))
