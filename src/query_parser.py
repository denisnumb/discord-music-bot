import sys
import json
import asyncio
from pathlib import Path


class QueryParseError(Exception):
    pass

class YTDLPLogger:
    def __init__(self):
        self.errors = []

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.errors.append(msg)


async def yt_dlp_extract_info(query: str, timeout: int=60) -> dict:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        Path(__file__).resolve(),
        query,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError()

    if proc.returncode != 0:
        raise QueryParseError(stderr.decode())

    return json.loads(stdout.decode())

if __name__ == "__main__":
    import yt_dlp
    from contextlib import redirect_stdout, redirect_stderr
    from io import StringIO
    from config import Config


    logger = YTDLPLogger()

    YDL_OPTIONS = {
        'format': 'bestaudio/best', 
        'forcetitle': True, 
        'quiet': True, 
        'playlistend': Config.playlistend, 
        'cookiefile': 'data/cookies.txt',
        'ignoreerrors': True,
        'logger': logger
    }

    query = sys.argv[1]
    stderr = StringIO()

    try:
        with redirect_stdout(stderr), redirect_stderr(stderr):
            ydl = yt_dlp.YoutubeDL(YDL_OPTIONS)
            info = ydl.extract_info(query, download=False)

        if not info:
            error_msg = logger.errors[-1] if logger.errors else None
            print(error_msg, file=sys.stderr)
            sys.exit(1)

        print(json.dumps(info))
        sys.exit(0)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
