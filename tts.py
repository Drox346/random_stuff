2026-02-25 08:41:59 wget https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/kokoro-v1.0.onnx
2026-02-25 08:41:55 wget https://github.com/nazdridoy/kokoro-tts/releases/download/v1.0.0/voices-v1.0.bin

2026-02-25 08:39:29 pip install -r requirements.txt
2026-02-25 08:39:17 cd kokoro-tts/
2026-02-25 08:39:13 git clone https://github.com/nazdridoy/kokoro-tts

import re
import queue
import threading
import time
import numpy as np
import sounddevice as sd

from kokoro_onnx import Kokoro  # installed as a dependency in many Kokoro setups


def chunk_text(text: str, max_chars: int = 80):
    """
    Simple chunker: sentence-ish splits, then hard-wrap if still too big.
    Keeps chunks reasonably sized so you get early playback.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    parts = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    cur = ""
    for p in parts:
        if not p:
            continue
        if len(cur) + len(p) + 1 <= max_chars:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)

    final = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
        else:
            for i in range(0, len(c), max_chars):
                final.append(c[i : i + max_chars])
    return final


def benchmark_tts_generation(player, text: str, runs: int = 5):
    chunks = chunk_text(text, max_chars=player.max_chars)
    if not chunks:
        print("Benchmark skipped: empty text")
        return

    # Warmup to avoid one-time initialization noise.
    player.kokoro.create(
        text=chunks[0], voice=player.voice, speed=player.speed, lang=player.lang
    )

    print("\nTTS generation benchmark (generation only, no playback)")
    for run in range(runs):
        total_gen_s = 0.0
        total_samples = 0
        sample_rate = None
        first_chunk_s = None

        for i, chunk in enumerate(chunks):
            t0 = time.perf_counter()
            samples, sr = player.kokoro.create(
                text=chunk, voice=player.voice, speed=player.speed, lang=player.lang
            )
            dt = time.perf_counter() - t0

            if i == 0:
                first_chunk_s = dt
                sample_rate = int(sr)
            elif int(sr) != sample_rate:
                raise RuntimeError(f"Sample rate changed during benchmark: {sample_rate} -> {sr}")

            total_gen_s += dt
            total_samples += len(np.asarray(samples))

        audio_s = total_samples / sample_rate if sample_rate else 0.0
        rtf = (total_gen_s / audio_s) if audio_s > 0 else float("inf")
        x_realtime = (audio_s / total_gen_s) if total_gen_s > 0 else float("inf")
        print(
            f"run {run + 1}: "
            f"first_chunk={first_chunk_s * 1000:.1f} ms, "
            f"gen={total_gen_s:.3f}s, audio={audio_s:.3f}s, "
            f"RTF={rtf:.3f}, speed={x_realtime:.2f}x realtime"
        )


class KokoroPlayer:
    def __init__(
        self,
        model_path: str,
        voices_path: str,
        voice: str = "af_sarah",
        lang: str = "en-us",
        speed: float = 1.0,
        max_chars: int = 80,
    ):
        self.voice = voice
        self.lang = lang
        self.speed = speed
        self.max_chars = max_chars

        # Keep the model loaded for low latency across repeated calls.
        self.kokoro = Kokoro(model_path=model_path, voices_path=voices_path)

        self._stream = None
        self._samplerate = None
        self._stream_lock = threading.Lock()

        self._audio_queue: queue.Queue[object] = queue.Queue()
        self._requests: queue.Queue[tuple[str, threading.Event | None]] = queue.Queue()
        self._pending_buf = np.array([], dtype=np.float32)
        self._pending_offset = 0

        self._worker = threading.Thread(target=self._tts_worker, daemon=True)
        self._worker.start()

    def _ensure_stream(self, samplerate: int):
        with self._stream_lock:
            if self._stream is not None:
                if samplerate != self._samplerate:
                    raise RuntimeError(
                        f"Sample rate changed: {self._samplerate} -> {samplerate}"
                    )
                return

            self._samplerate = int(samplerate)
            self._stream = sd.OutputStream(
                samplerate=self._samplerate,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
                blocksize=0,
            )
            self._stream.start()

    def _audio_callback(self, outdata, frames, time_info, status):
        if status:
            pass

        out = np.zeros((frames,), dtype=np.float32)
        filled = 0

        while filled < frames:
            if self._pending_offset < self._pending_buf.shape[0]:
                remaining = self._pending_buf.shape[0] - self._pending_offset
                n = min(frames - filled, remaining)
                start = self._pending_offset
                end = start + n
                out[filled : filled + n] = self._pending_buf[start:end]
                self._pending_offset = end
                filled += n

                if self._pending_offset >= self._pending_buf.shape[0]:
                    self._pending_buf = np.array([], dtype=np.float32)
                    self._pending_offset = 0
                continue

            try:
                item = self._audio_queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, tuple) and item and item[0] == "done":
                done_event = item[1]
                if done_event is not None:
                    done_event.set()
                continue

            self._pending_buf = item
            self._pending_offset = 0

        outdata[:, 0] = out

    def _tts_worker(self):
        while True:
            text, done_event = self._requests.get()
            try:
                chunks = chunk_text(text, max_chars=self.max_chars)
                if not chunks:
                    done_event.set()
                    continue

                first_samples, sr = self.kokoro.create(
                    text=chunks[0],
                    voice=self.voice,
                    speed=self.speed,
                    lang=self.lang,
                )
                self._ensure_stream(int(sr))
                self._audio_queue.put(np.asarray(first_samples, dtype=np.float32))

                for chunk in chunks[1:]:
                    samples, sr2 = self.kokoro.create(
                        text=chunk,
                        voice=self.voice,
                        speed=self.speed,
                        lang=self.lang,
                    )
                    if int(sr2) != self._samplerate:
                        raise RuntimeError(
                            f"Sample rate changed: {self._samplerate} -> {sr2}"
                        )
                    self._audio_queue.put(np.asarray(samples, dtype=np.float32))
            finally:
                # Mark completion after all audio for this request has been queued.
                self._audio_queue.put(("done", done_event))

    def enqueue_text(self, text: str):
        self._requests.put((text, None))

    def play_text(self, text: str):
        done_event = threading.Event()
        self._requests.put((text, done_event))
        done_event.wait()


def make_tts_callback(player: KokoroPlayer):
    def on_text_message(text: str):
        # Non-blocking: queue for playback and return immediately to the receiver.
        player.enqueue_text(text)

    return on_text_message


def demo_text_message_receiver(on_text_message):
    text1 = "This is the first demo sentence. It plays through the shared function."
    text2 = "This is the second text block. You can replace it with anything from your app."
    text3 = "This is the third example. Each string calls the same playback function."

    print("START")
    on_text_message(text1)
    # on_text_message(text2)
    # on_text_message(text3)


def main():
    model_path = "kokoro-v1.0.onnx"
    voices_path = "voices-v1.0.bin"

    player = KokoroPlayer(model_path=model_path, voices_path=voices_path)
    on_text_message = make_tts_callback(player)

    RUN_BENCHMARK = True
    if RUN_BENCHMARK:
        benchmark_text = (
            "This is a benchmark sample for Kokoro text to speech generation. "
            "It measures first chunk latency and total synthesis speed relative to real time. "
            "Use a few sentences so chunking behaves similarly to production messages."
        )
        benchmark_tts_generation(player, benchmark_text, runs=5)

    demo_text_message_receiver(on_text_message)

    # Stand-in for a real receiver loop (socket server, etc.).
    # Ctrl+C exits the process and stops the daemon worker thread.
    while True:
        sd.sleep(250)


if __name__ == "__main__":
    main()
