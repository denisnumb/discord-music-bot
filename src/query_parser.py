import sys
import json
import subprocess
from pathlib import Path


class QueryParseError(Exception):
    pass

def yt_dlp_extract_info(query: str) -> dict:
    proc = subprocess.run(
        [sys.executable, Path(__file__).resolve(), query],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if proc.returncode == 0:
        return json.loads(proc.stdout)
    raise QueryParseError(proc.stderr)

if __name__ == "__main__":
    import yt_dlp
    from contextlib import redirect_stdout, redirect_stderr
    from io import StringIO
    from config import Config


    YDL_OPTIONS = {
        'format': 'bestaudio/best', 
        'forcetitle': True, 
        'quiet': True, 
        'playlistend': Config.playlistend, 
        'cookiefile': 'data/cookies.txt'
    }

    query = sys.argv[1]
    stderr = StringIO()

    try:
        with redirect_stdout(stderr), redirect_stderr(stderr):
            ydl = yt_dlp.YoutubeDL(YDL_OPTIONS)
            info = ydl.extract_info(query, download=False)

        print(json.dumps(info))
        sys.exit(0)

    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
