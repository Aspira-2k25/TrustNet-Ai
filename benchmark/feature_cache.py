"""Append cached features despite brief Windows reader/antivirus locks."""
import json
import time


def append_record(path, record, attempts=40, delay=.25):
    payload=json.dumps(record)+'\n'
    for attempt in range(attempts):
        try:
            stream=path.open('a',encoding='utf-8')
        except PermissionError:
            if attempt+1==attempts:raise
            time.sleep(delay)
        else:
            # Retry only opening: retrying a partial write could duplicate bytes.
            with stream:stream.write(payload)
            return
