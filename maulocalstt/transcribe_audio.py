import asyncio
from asyncio import tasks, StreamReader
from typing import Tuple, Any, Optional

from mautrix.util.logging import TraceLogger
from io import BytesIO
import json

from .import_backends import vosk, VOSK_INSTALLED, WhisperModel, WHISPER_INSTALLED

SAMPLE_RATE = 16000

VOSK_CHUNK_SIZE = 16000 * 4 * 10

MIME_FORMAT_MAP = {
    'audio/ogg': 'ogg',
    'audio/mpeg': 'mp3',
    'audio/vnd.wav': 'wav',
    'audio/mp4': 'mp4',
}


async def _run_ffmpeg(data: bytes, mimeType: str, logger: TraceLogger) -> Tuple[StreamReader, StreamReader]:
    if ';' in mimeType:
        mimeType = mimeType[: mimeType.index(';')]
    format = MIME_FORMAT_MAP[mimeType]
    proc = await asyncio.create_subprocess_shell(
        F"ffmpeg -f {format} -i - -ac 1 -c:a pcm_s16le -ar {SAMPLE_RATE} -f s16le -",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    # stdout, stderr = await proc.communicate(input=data)
    proc.stdin.write(data)
    await proc.stdin.drain()
    proc.stdin.close()
    # stdout, stderr = await proc.communicate()
    # stdout, stderr = await tasks.gather(proc.stdout.read(),proc.stderr.read())
    return proc.stdout, proc.stderr
    # logger.debug(stderr.decode('utf8'))

async def transcribe_audio_whisper(data: bytes, whisper_model: WhisperModel, lang: str, translate: bool,
                                   logger: TraceLogger) -> str:
    if not WHISPER_INSTALLED:
        return ""

    file = BytesIO(data)

    if translate:
        action = "translate"
    else:
        action = "transcribe"
        
    if lang != 'auto':
        segments, logger = whisper_model.transcribe(file, language=lang, task=action)
    else:
        segments, logger = whisper_model.transcribe(file, task=action)
    
    result = "".join([segment.text for segment in segments])

    return result


def _run_vosk(vosk_rec: vosk.KaldiRecognizer, data: bytes, logger: TraceLogger) -> Optional[bool]:
    try:
        return vosk_rec.AcceptWaveform(data)
    except Exception as e:
        logger.exception("Exception when running Vosk", exc_info=e)
    return None


async def transcribe_audio_vosk(data: bytes, vosk_model: vosk.Model, mimeType: str, logger: TraceLogger) -> str:
    if not VOSK_INSTALLED:
        return ""

    stdout, stderr = await _run_ffmpeg(data, mimeType, logger)
    rec = vosk.KaldiRecognizer(vosk_model, SAMPLE_RATE)

    loop = asyncio.get_event_loop()

    transcriptions = list()

    run = True
    while run:
        data = await stdout.read(VOSK_CHUNK_SIZE)
        if len(data) == 0:
            break
        has_result = await loop.run_in_executor(None, _run_vosk, rec, data, logger)
        if has_result:
            result = rec.Result()
            logger.debug(F"Vosk Result: {result}")
            transcriptions.append(json.loads(result)['text'])

    result = rec.FinalResult()
    transcriptions.append(json.loads(result)['text'])
    logger.debug(F"Vosk final result: {result}")
    del rec
    return " ".join(transcriptions)
