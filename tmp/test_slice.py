import os
import subprocess
import time

abs_video = "/Users/ngovietthanhbinh/Project/[TDTT] Do An 2/Audio-Guided-Video-Montage/data/normalized/vd00_CP_overview.mp4"
start = 28.92
end = 49.76
duration = end - start

tmp_dir = "/Users/ngovietthanhbinh/Project/[TDTT] Do An 2/Audio-Guided-Video-Montage/tmp"
os.makedirs(tmp_dir, exist_ok=True)
tmp_sliced_path = os.path.join(tmp_dir, "test_slice.mp4")

cmd = [
    "ffmpeg", "-y",
    "-ss", str(start),
    "-i", abs_video,
    "-t", str(duration),
    "-c:v", "libx264", "-preset", "ultrafast",
    "-c:a", "aac",
    tmp_sliced_path
]

print("Running command:", " ".join(cmd))
t0 = time.time()
result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
t1 = time.time()
print(f"Finished in {t1-t0:.2f} seconds. Return code: {result.returncode}")
if result.returncode != 0:
    print(result.stderr.decode('utf-8'))
