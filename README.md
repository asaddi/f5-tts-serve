# kokoro-serve

A simple wrapper around [Kokoro-82M]https://huggingface.co/hexgrad/Kokoro-82M) that provides an OpenAI-compatible API endpoint for speech generation (`/v1/audio/speech`).

This is just a toy, a POC, not suitable for production or multi-user use.

This is a quick & dirty conversion of my [f5-tts-serve](https://github.com/asaddi/f5-tts-serve).

Also I've only tested/used the Docker version, because...

For *whatever reason*, the Python package `misaki` (a dependency of `kokoro`, by the same author) indirectly brings in this wheel at *run time*:

    server-1  | Collecting en-core-web-sm==3.8.0
    server-1  |   Downloading https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl (12.8 MB)

Just a word of warning. Always be suspicious of Python wheels coming in from unknown sources.

## Features

* Provides an OpenAI-compatible API endpoint for `/v1/audio/speech`

   My testing consisted of using `curl`, Open-WebUI, and SillyTavern as frontends.

* Multiple voices are supported. Note: At the moment, the `model` parameter (which is usually given the value `tts-1` or `tts-1-hd`) is totally ignored. Only `voice` matters. (See [the kokoro's VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) for valid voices for American English. It will default to `af_heart` if given an invalid voice.)

* Can also specify the speaking rate

* The supported audio formats are based on the formats supported by the [soundfile](https://pypi.org/project/soundfile/) Python package, which itself seems to be based off of [libsndfile](http://www.mega-nerd.com/libsndfile/).

   Basically, this means every format listed in the OpenAI API spec *except* for AAC should be supported:

   * WAV
   * MP3
   * FLAC
   * OPUS (in .ogg container)
   * PCM (signed 16-bit little-endian)

### ToDo

* [x] Dockerfile
* [ ] More robustness, especially in code that executes in background threads
* [ ] API key support?
* [ ] AAC support? Are there any frontends that demand AAC?

## Installation

Create a venv/virtualenv (or use conda) and then install the requirements:

    pip install -r requirements.txt

If you'd like to use something other than CPU inference, specify `--extra-index-url` with the desired torch URL, for example:

    pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124

### Docker

Sorry, I don't have a pre-built image. But you can easily build one with:

    docker compose build

## Running

With your venv/virtualenv/conda environment active:

    python server.py

By default, it will listen to `127.0.0.1` port 8000. You can change this by adding the `--host` and `--port` arguments to the above.

### Docker

See the included `docker-compose.yml` file. But typically, you can run it with:

    docker compose up

### Example Client Usage (using curl)

    curl -o test.wav http://localhost:8000/v1/audio/speech \
      -H "Content-Type: application/json" \
      -d '{
      "model": "tts-1",
      "input": "That quick beige fox jumped in the air over each thin dog. Look out, I shout, for he'\''s foiled you again, creating chaos.",
      "voice": "af_heart",
      "response_format": "wav"
    }'

The parameter `response_format`, if omitted, defaults to `mp3`.

The API documentation can be found [here](https://platform.openai.com/docs/api-reference/audio).

## License

Licensed under [the MIT license](https://opensource.org/license/mit).
