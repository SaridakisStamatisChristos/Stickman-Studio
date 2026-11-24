"""Original deterministic 10-second ambient soundtrack, standard library only."""
import math
import pathlib
import struct
import wave

RATE = 24000
DURATION = 10
OUT = pathlib.Path(__file__).resolve().parents[1] / "public" / "soundtrack.wav"
OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(RATE)
    buf = bytearray()
    for n in range(RATE * DURATION):
        t = n / RATE
        fade = max(0, min(1.0, t / 0.6, (DURATION - t) / 0.7))
        drone = .085 * math.sin(2*math.pi*74*t) + .045 * math.sin(2*math.pi*111*t)
        hum = .025 * math.sin(2*math.pi*185*t) * (.65 + .35*math.sin(2*math.pi*.35*t))
        chirp = 0
        for start in (3.75, 4.15, 4.55, 6.9):
            dt = t-start
            if 0 <= dt < .32:
                chirp += .18 * (1-dt/.32)**1.8 * math.sin(2*math.pi*(580*dt+210*dt*dt))
        sample = max(-1, min(1, fade*(drone+hum+chirp)))
        buf.extend(struct.pack('<h', int(sample*32767)))
    wav.writeframes(buf)
print("Generated", OUT)
