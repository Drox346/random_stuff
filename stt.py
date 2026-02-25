import queue
import re
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd
import torch
import whisper

SAMPLE_RATE = 16000
CHANNELS = 1

FRAME_SAMPLES = 512  # Silero VAD frame size at 16 kHz
VAD_THRESHOLD = 0.6
MAX_SEGMENT_S = 30.0
MIN_SEGMENT_S = 0.45
MIN_SEGMENT_RMS = 0.012

KWS_MODEL_NAME = "small"
TRANSCRIBE_MODEL_NAME = "turbo"  # or "turbo"
KWS_LANGUAGE = "en"
TRANSCRIBE_LANGUAGE = "en"
KEYWORD_REGEX = re.compile(r"computer", re.IGNORECASE)
USE_GPU = True

KWS_WINDOW_SEC = 1.5
KWS_STEP_SEC = 0.4
KWS_REARM_COOLDOWN_S = 0.5
assert KWS_STEP_SEC < KWS_WINDOW_SEC


def choose_input_device() -> int | None:
    devices = sd.query_devices()
    input_devices = []
    for idx, dev in enumerate(devices):
        if int(dev["max_input_channels"]) > 0:
            input_devices.append((idx, dev))

    if not input_devices:
        raise RuntimeError("No input audio devices found.")

    default_input_idx = sd.default.device[0]
    print("Available input devices:")
    for idx, dev in input_devices:
        marker = " (default)" if idx == default_input_idx else ""
        print(f"{idx}: {dev['name']}{marker}")

    while True:
        choice = input("Select input device index (Enter for default): ").strip()
        if choice == "":
            return None
        if not choice.isdigit():
            print("Please enter a valid numeric index.")
            continue

        selected_idx = int(choice)
        if any(selected_idx == idx for idx, _ in input_devices):
            return selected_idx
        print("That device index is not a valid input device.")


def int16_to_float32(x: np.ndarray) -> np.ndarray:
    if x.dtype != np.int16:
        x = x.astype(np.int16, copy=False)
    return x.astype(np.float32) / 32768.0


class KeywordVADWhisper:
    def __init__(self):
        torch.set_num_threads(1)
        gpu_available = torch.cuda.is_available()
        self._device_reason = ""
        self.whisper_device = "cuda" if USE_GPU and gpu_available else "cpu"
        self.use_fp16 = self.whisper_device == "cuda"

        if not USE_GPU:
            self._device_reason = "USE_GPU=False"
        elif not gpu_available:
            self._device_reason = "USE_GPU=True but torch.cuda.is_available() is False"
            print("USE_GPU=True but torch.cuda.is_available() is False. Falling back to CPU.")
        else:
            self._device_reason = "USE_GPU=True and torch.cuda.is_available() is True"

        if self.whisper_device == "cuda":
            try:
                # Some ROCm setups report CUDA available but fail on the first kernel launch.
                _ = (torch.randn(8, device="cuda") * 2).cpu()
            except Exception as e:
                print(f"GPU self-test failed ({type(e).__name__}): {e}")
                print("Falling back to CPU.")
                self.whisper_device = "cpu"
                self.use_fp16 = False
                self._device_reason = (
                    f"GPU self-test failed ({type(e).__name__}); likely ROCm/PyTorch/GPU mismatch"
                )
            else:
                self._device_reason = "GPU self-test passed"

        print(f"Whisper device: {self.whisper_device}")
        print(f"Whisper device reason: {self._device_reason}")

        print(f"Loading KWS model: {KWS_MODEL_NAME}")
        self.kws_model = whisper.load_model(KWS_MODEL_NAME, device=self.whisper_device)

        print(f"Loading transcription model: {TRANSCRIBE_MODEL_NAME}")
        self.stt_model = whisper.load_model(
            TRANSCRIBE_MODEL_NAME, device=self.whisper_device
        )

        self.vad_model, self.vad_iterator = self._init_silero_vad()

        self.frame_q: queue.Queue[np.ndarray] = queue.Queue(maxsize=400)
        self.stop_flag = threading.Event()

        self._leftover = np.zeros(0, dtype=np.int16)
        self._listening = False  # True after keyword, False after VAD end
        self._in_speech = False
        self._segment_frames: list[np.ndarray] = []

        self._kws_window_samples = int(KWS_WINDOW_SEC * SAMPLE_RATE)
        self._kws_step_samples = int(KWS_STEP_SEC * SAMPLE_RATE)
        self._kws_buffer = np.zeros(self._kws_window_samples, dtype=np.float32)
        self._kws_filled = 0
        self._total_samples = 0
        self._next_kws_at = self._kws_step_samples

    def _reset_kws_state(self, cooldown_s: float = 0.0):
        # Clear rolling KWS context so old audio (including the wake word) cannot retrigger.
        self._kws_buffer.fill(0.0)
        self._kws_filled = 0
        cooldown_samples = int(max(0.0, cooldown_s) * SAMPLE_RATE)
        self._next_kws_at = self._total_samples + max(self._kws_step_samples, cooldown_samples)

    def _init_silero_vad(self):
        try:
            from silero_vad import VADIterator, load_silero_vad

            vad_model = load_silero_vad()
            vad_iterator = VADIterator(
                vad_model,
                sampling_rate=SAMPLE_RATE,
                threshold=VAD_THRESHOLD,
            )
            return vad_model, vad_iterator
        except Exception:
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
            )
            (_, _, _, VADIterator, _) = utils
            vad_iterator = VADIterator(
                model,
                sampling_rate=SAMPLE_RATE,
                threshold=VAD_THRESHOLD,
            )
            return model, vad_iterator

    def _reset_vad_state(self):
        self._in_speech = False
        self._segment_frames = []
        if hasattr(self.vad_iterator, "reset_states"):
            self.vad_iterator.reset_states()

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            pass

        mono = np.asarray(indata[:, 0], dtype=np.float32)
        x = np.clip(mono, -1.0, 1.0)
        int16 = (x * 32767.0).astype(np.int16)
        self._chunk_and_queue(int16)

    def _chunk_and_queue(self, samples: np.ndarray):
        buf = np.concatenate([self._leftover, samples])
        i = 0
        n = buf.shape[0]

        while i + FRAME_SAMPLES <= n:
            frame = buf[i:i + FRAME_SAMPLES].copy()
            try:
                self.frame_q.put_nowait(frame)
            except queue.Full:
                try:
                    self.frame_q.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.frame_q.put_nowait(frame)
                except queue.Full:
                    pass
            i += FRAME_SAMPLES

        self._leftover = buf[i:]

    def _update_kws_buffer(self, frame: np.ndarray):
        chunk = int16_to_float32(frame)
        n = chunk.shape[0]
        self._total_samples += n

        if n >= self._kws_window_samples:
            self._kws_buffer[:] = chunk[-self._kws_window_samples :]
            self._kws_filled = self._kws_window_samples
            return

        self._kws_buffer = np.roll(self._kws_buffer, -n)
        self._kws_buffer[-n:] = chunk
        self._kws_filled = min(self._kws_window_samples, self._kws_filled + n)

    def _try_keyword_spot(self) -> bool:
        if self._kws_filled == 0 or self._total_samples < self._next_kws_at:
            return False

        self._next_kws_at = self._total_samples + self._kws_step_samples

        if self._kws_filled < self._kws_window_samples:
            decode_audio = self._kws_buffer[-self._kws_filled :]
        else:
            decode_audio = self._kws_buffer

        result = self.kws_model.transcribe(
            decode_audio,
            language=KWS_LANGUAGE,
            fp16=self.use_fp16,
            condition_on_previous_text=False,
            verbose=False,
        )

        for seg in result.get("segments", []):
            text = (seg.get("text") or "").strip()
            if text and KEYWORD_REGEX.search(text):
                self._listening = True
                self._reset_vad_state()
                self._reset_kws_state(cooldown_s=KWS_REARM_COOLDOWN_S)
                print("keyword detected -> listening=True", flush=True)
                return True

        return False

    def _decode_segment(self, segment_int16: np.ndarray) -> str:
        audio_f32 = int16_to_float32(segment_int16)
        result = self.stt_model.transcribe(
            audio_f32,
            language=TRANSCRIBE_LANGUAGE,
            task="transcribe",
            beam_size=2,
            best_of=2,
            temperature=0.0,
            condition_on_previous_text=False,
            fp16=self.use_fp16,
            verbose=None,
        )
        return (result.get("text") or "").strip()

    def _finalize_segment(self):
        if not self._segment_frames:
            return

        segment = np.concatenate(self._segment_frames)
        self._segment_frames = []

        duration_s = segment.shape[0] / SAMPLE_RATE
        rms = (
            float(np.sqrt(np.mean(np.square(int16_to_float32(segment)))))
            if segment.size
            else 0.0
        )

        if duration_s < MIN_SEGMENT_S or rms < MIN_SEGMENT_RMS:
            print("segment dropped (too short/quiet)", flush=True)
            return

        text = self._decode_segment(segment)
        if text:
            print(text, flush=True)

    def _process_listening_frame(self, frame: np.ndarray):
        audio_tensor = torch.from_numpy(int16_to_float32(frame))
        vad_event = self.vad_iterator(audio_tensor)

        if vad_event and "start" in vad_event:
            self._in_speech = True
            self._segment_frames = [frame]
            return

        if not self._in_speech:
            return

        self._segment_frames.append(frame)

        max_segment_frames = int(MAX_SEGMENT_S * SAMPLE_RATE / FRAME_SAMPLES)
        if vad_event and "end" in vad_event:
            self._finalize_segment()
            self._reset_vad_state()
            self._listening = False
            self._reset_kws_state(cooldown_s=KWS_REARM_COOLDOWN_S)
            print("vad end -> listening=False", flush=True)
            return

        if len(self._segment_frames) >= max_segment_frames:
            self._finalize_segment()
            self._reset_vad_state()
            self._listening = False
            self._reset_kws_state(cooldown_s=KWS_REARM_COOLDOWN_S)
            print("max segment -> listening=False", flush=True)

    def process_loop(self):
        while not self.stop_flag.is_set():
            try:
                frame = self.frame_q.get(timeout=0.1)
            except queue.Empty:
                continue

            self._update_kws_buffer(frame)

            if not self._listening:
                self._try_keyword_spot()
                continue

            self._process_listening_frame(frame)

    def run(self, device: Optional[int] = None):
        t = threading.Thread(target=self.process_loop, daemon=True)
        t.start()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=0,
            callback=self.audio_callback,
            device=device,
        ):
            print("Idle (keyword spotting)... Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(0.2)
            except KeyboardInterrupt:
                self.stop_flag.set()

        if self._in_speech:
            self._finalize_segment()
        t.join(timeout=1.0)


if __name__ == "__main__":
    selected_device = choose_input_device()
    KeywordVADWhisper().run(device=selected_device)
