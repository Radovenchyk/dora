from dora import Node
import time


node = Node()
time.sleep(5)
for event in node:
    event_type = event["type"]

    if event_type == "INPUT":
        event_id = event["id"]
        send_time = event["value"].to_pylist()[0]
        print("Duration: ", send_time - time.time(), flush=True)
        assert (
            send_time - time.time() < 1.2
        ), f"Duration: {send_time - time.time()} should be less than 1 as we should always pull latest data."
        time.sleep(1)
