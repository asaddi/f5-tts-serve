import argparse
import asyncio
from collections import namedtuple
import contextlib
import gc
import io
import logging
import os
import pprint
import threading
from typing import Any, AsyncGenerator, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from kokoro import KPipeline
import numpy as np
from pydantic import BaseModel
import soundfile as sf
import torch
import uvicorn


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


# TODO Need a better way of doing this
VOICES = [
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_bella",
    "af_jessica",
    "af_kore",
    "af_nicole",
    "af_nova",
    "af_river",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
]


Format = namedtuple("Format", ["api_fmt", "mime_type", "subtype"])


# soundfile format -> (API format, MIME-type, subtype)
POSSIBLE_FORMATS = {
    # Might also want to reference:
    # https://www.iana.org/assignments/media-types/media-types.xhtml#audio
    "MP3": Format("mp3", "audio/mpeg", None),
    "OGG": Format("opus", "audio/ogg", "OPUS"),  # NB defaults to vorbis otherwise
    "FLAC": Format("flac", "audio/flac", None),
    "WAV": Format("wav", "audio/wav", None),  # This MIME-type isn't listed?
    # No idea if this is correct for 'pcm'. What about no. of channels?!
    "RAW": Format(
        "pcm", "audio/l16", "PCM_16"
    ),  # From testing, this is signed 16-bit little endian with 1 channel
    # Guess no AAC?
}


# Globals
TTS: KPipeline | None = None
SUPPORTED_FORMATS: dict[str, tuple[str, Format]] = {}
LOCK = threading.Lock()


@contextlib.asynccontextmanager
async def setup_teardown(_app):
    global TTS

    SUPPORTED_FORMATS.update(
        {
            fmt.api_fmt: (sf_fmt, fmt)
            for sf_fmt, fmt in POSSIBLE_FORMATS.items()
            if sf_fmt in sf.available_formats()
        }
    )
    logging.info(f"""Supported formats: {', '.join(SUPPORTED_FORMATS.keys())}""")

    # For now, hardcode American English
    TTS = KPipeline(lang_code="a")
    try:
        yield
    finally:
        # We're on our way out already, so there's probably no need for this.
        TTS = None
        gc.collect()
        torch.cuda.empty_cache()


app = FastAPI(
    title="Basic OpenAI-compatible server for Kokoro", lifespan=setup_teardown
)


class CreateSpeechRequest(BaseModel):
    model: str
    input: str
    voice: str
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "mp3"
    speed: float = 1.0


async def audio_generator(
    format: str, subtype: str, wave: np.ndarray, rate: int
) -> AsyncGenerator[Any, Any]:
    logger.info(f"Converting audio to {format}/{subtype}")
    # The file-like passed to sf.write must support seek/tell/write.
    # So we can't use a pipe or similar non-seekable file-like.
    audio_file = io.BytesIO()
    # TODO Is this potentially blocking?
    sf.write(audio_file, wave, rate, format=format, subtype=subtype)

    logger.info("Streaming result...")
    audio_file.seek(0)
    try:
        while True:
            # This is technically blocking, but we're reading from memory...
            chunk = audio_file.read(32 * 1024)
            if chunk == b"":
                break
            yield chunk
    finally:
        audio_file.close()
        logger.info("Done with request")


def dump_request(request: CreateSpeechRequest, **kwargs):
    # Make a copy
    req = request.model_dump(mode="json")
    # Some semblance of privacy
    req["input"] = "<omitted>"
    return pprint.pformat(req, **kwargs)


@app.post("/v1/audio/speech")
async def create_speech(request: CreateSpeechRequest) -> StreamingResponse:
    assert TTS is not None

    logger.info(
        f"Received speech creation request =\n{dump_request(request, indent=4)}"
    )

    if request.response_format not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"""response_format: Must be {', '.join([repr(k) for k in SUPPORTED_FORMATS.keys()])}""",
        )

    sf_fmt, fmt = SUPPORTED_FORMATS[request.response_format]

    # TODO validate model?

    voice = request.voice
    if voice not in VOICES:
        voice = VOICES[0]

    def infer():
        # Not sure if it's thread-safe, so just serialize inference.
        with LOCK:
            generator = TTS(
                request.input,
                voice=voice,
                speed=request.speed,
                split_pattern=r"\n+",
            )
            wave = [v[2] for v in generator]
            return torch.cat(wave), 24000

    wave, rate = await asyncio.to_thread(infer)

    return StreamingResponse(
        audio_generator(sf_fmt, fmt.subtype, wave, rate),
        headers={"Content-Type": fmt.mime_type},
    )


def main():
    host = "127.0.0.1"
    port = 8000

    parser = argparse.ArgumentParser("Basic OpenAI-compatible server for Kokoro")

    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default=host,
        help=f"Host interface to listen on (default: {host})",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=port,
        help=f"Port to listen on (default: {port})",
    )

    args = parser.parse_args()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
    )


if __name__ == "__main__":
    main()
