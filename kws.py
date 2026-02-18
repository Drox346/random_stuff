import sys
import re
import time
import queue
import threading
import numpy as np
import sounddevice as sd
import torch
import whisper

MODEL_NAME  = "small"
SAMPLE_RATE = 16000

WINDOW_SEC = 3.0
STEP_SEC   = 1.0 

assert STEP_SEC < WINDOW_SEC

model = whisper.load_model(MODEL_NAME)
USE_FP16 = torch.cuda.is_available()

audio_q = queue.Queue(maxsize=128)

timing_lock = threading.Lock()
total_samples_captured = 0
overflow_events = 0

def callback(indata, frames, time_info, status):
    global total_samples_captured, overflow_events

    chunk = np.asarray(indata, dtype=np.float32).reshape(-1).copy()

    with timing_lock:
        total_samples_captured += chunk.shape[0]
        if status and getattr(status, "input_overflow", False):
            overflow_events += 1

    # Keep latency bounded: if overloaded, drop oldest queued chunk.
    try:
        audio_q.put_nowait(chunk)
    except queue.Full:
        try:
            audio_q.get_nowait()
        except queue.Empty:
            pass
        try:
            audio_q.put_nowait(chunk)
        except queue.Full:
            pass

buf_len = int(WINDOW_SEC * SAMPLE_RATE)
buffer = np.zeros(buf_len, dtype=np.float32)

filled_samples = 0
last_emitted_end_abs = 0.0

print(f"Streaming (~{STEP_SEC:.1f}s updates)... Ctrl+C to stop")

try:
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        callback=callback,
    ):
        next_run = time.monotonic() + STEP_SEC

        while True:
            # Update rolling buffer
            while True:
                try:
                    chunk = audio_q.get_nowait()
                except queue.Empty:
                    break

                n = chunk.shape[0]

                if n >= buf_len:
                    buffer[:] = chunk[-buf_len:]
                else:
                    buffer = np.roll(buffer, -n)
                    buffer[-n:] = chunk

                filled_samples = min(buf_len, filled_samples + n)

            now = time.monotonic()
            if now < next_run:
                time.sleep(0.002)
                continue

            # Avoid catch-up bursts when decoding runs slower than STEP_SEC.
            next_run = now + STEP_SEC

            with timing_lock:
                buffer_end_abs = total_samples_captured / SAMPLE_RATE
                overflows = overflow_events
                overflow_events = 0

            if overflows:
                print(f"warning: input overflow events={overflows}", file=sys.stderr)

            if filled_samples == 0:
                continue

            decode_audio = buffer if filled_samples >= buf_len else buffer[-filled_samples:]
            effective_window_sec = decode_audio.shape[0] / SAMPLE_RATE
            buffer_start_abs = max(0.0, buffer_end_abs - effective_window_sec)

            result = model.transcribe(
                decode_audio,
                language="en",
                fp16=USE_FP16,
                condition_on_previous_text=False,
                verbose=False,
            )

            for seg in result.get("segments", []):
                seg_start_abs = buffer_start_abs + float(seg["start"])
                seg_end_abs   = buffer_start_abs + float(seg["end"])
                text = seg["text"].strip()

                if not text:
                    continue

                if seg_end_abs > last_emitted_end_abs + 0.05:
                    text_segment = f"[{seg_start_abs:7.2f}-{seg_end_abs:7.2f}] {text}"
                    last_emitted_end_abs = seg_end_abs
                    if re.search(r"computer", text, re.IGNORECASE):
                        print("keyword detected")

except KeyboardInterrupt:
    print("Stopped.")
