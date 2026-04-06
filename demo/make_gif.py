import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg


def main() -> None:
    root = Path(__file__).resolve().parent
    in_path = root / "demo.mp4"
    out_path = root / "demo.gif"
    duration_s = "8"
    fps = "12"
    width = "900"
    scale = f"scale={width}:-1:flags=lanczos"

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.TemporaryDirectory() as tmpdir:
        palette = Path(tmpdir) / "palette.png"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-ss",
                "0",
                "-t",
                duration_s,
                "-i",
                str(in_path),
                "-vf",
                f"fps={fps},{scale},palettegen",
                str(palette),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-ss",
                "0",
                "-t",
                duration_s,
                "-i",
                str(in_path),
                "-i",
                str(palette),
                "-lavfi",
                f"fps={fps},{scale} [x]; [x][1:v] paletteuse",
                "-loop",
                "0",
                str(out_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    main()

