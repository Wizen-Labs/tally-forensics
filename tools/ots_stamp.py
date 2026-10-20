"""OpenTimestamps stamp and upgrade without the `ots` command, whose Bitcoin library needs an OpenSSL DLL that
Windows lacks. The steps are the same as `ots stamp` and `ots upgrade`: only the file's SHA-256 (with a random nonce)
is sent to the public calendars. The resulting `.ots` proof verifies with the standard client (`ots verify FILE.ots`)
on any machine, once the calendars have anchored it in a Bitcoin block (a few hours).

Usage: python tools/ots_stamp.py stamp FILE   |   python tools/ots_stamp.py upgrade FILE.ots
"""

import os
import sys

from opentimestamps.calendar import RemoteCalendar
from opentimestamps.core.notary import PendingAttestation
from opentimestamps.core.op import OpAppend, OpSHA256
from opentimestamps.core.serialize import StreamDeserializationContext, StreamSerializationContext
from opentimestamps.core.timestamp import DetachedTimestampFile

CALENDARS = ["https://a.pool.opentimestamps.org", "https://b.pool.opentimestamps.org",
             "https://a.pool.eternitywall.com", "https://ots.btc.catallaxy.com"]


def stamp(path: str) -> None:
    with open(path, "rb") as fd:
        dtf = DetachedTimestampFile.from_fd(OpSHA256(), fd)
    root = dtf.timestamp.ops.add(OpAppend(os.urandom(16))).ops.add(OpSHA256())
    ok = 0
    for url in CALENDARS:
        try:
            root.merge(RemoteCalendar(url).submit(root.msg, timeout=15))
            ok += 1
            print("submitted:", url)
        except Exception as e:
            print("failed:", url, type(e).__name__, e)
    if not ok:
        sys.exit("no calendar accepted the stamp")
    with open(path + ".ots", "wb") as fd:
        dtf.serialize(StreamSerializationContext(fd))
    print(f"wrote {path}.ots (sha256 {dtf.file_digest.hex()}), {ok} calendars")


def upgrade(ots_path: str) -> None:
    with open(ots_path, "rb") as fd:
        dtf = DetachedTimestampFile.deserialize(StreamDeserializationContext(fd))
    done = 0
    for sub in list(dtf.timestamp.all_attestations()):
        stamp_, att = sub
        if isinstance(att, PendingAttestation):
            try:
                stamp_.merge(RemoteCalendar(att.uri).get_timestamp(stamp_.msg, timeout=15))
                done += 1
            except Exception as e:
                print("pending:", att.uri, type(e).__name__)
    with open(ots_path, "wb") as fd:
        dtf.serialize(StreamSerializationContext(fd))
    kinds = sorted({type(a).__name__ for _, a in dtf.timestamp.all_attestations()})
    print(f"upgraded {done} attestation(s); now: {kinds}")


if __name__ == "__main__":
    {"stamp": stamp, "upgrade": upgrade}[sys.argv[1]](sys.argv[2])
