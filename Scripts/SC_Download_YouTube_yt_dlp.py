import os
import sys
import yt_dlp

print("python :", sys.executable)
print("yt_dlp :", yt_dlp.version.__version__)

try:
  import yt_dlp_ejs
  print("yt_dlp_ejs :", getattr(yt_dlp_ejs, "__version__", "ok"))
except ImportError:
  raise SystemExit(
    "Missing yt_dlp_ejs. In this same Python run:\n"
    "  python -m pip install yt-dlp-ejs"
  )

here = os.path.dirname(os.path.abspath(__file__))
cookiefile = os.path.abspath(os.path.join(here, "..", "User_Files", "cookies.txt"))
deno = os.path.join(os.path.expanduser("~"), ".deno", "bin", "deno.exe")
ffmpeg = os.path.join(here, "ffmpeg.exe")

print("cookiefile :", cookiefile)
print("deno       :", deno)
print("ffmpeg     :", ffmpeg)

if not os.path.isfile(cookiefile):
  raise SystemExit(f"Missing cookies file: {cookiefile}")
if not os.path.isfile(deno):
  raise SystemExit(
    f"Missing Deno JS runtime: {deno}\n"
    "YouTube will only return storyboard images and the download will fail."
  )

# So any child process can find deno even if PATH does not include it
os.environ["PATH"] = os.path.dirname(deno) + os.pathsep + os.environ.get("PATH", "")

ydl_opts = {
  "cookiefile": cookiefile,
  "js_runtimes": {"deno": {"path": deno}},
  "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
  "merge_output_format": "mp4",
  "noplaylist": True,
  "verbose": True,
}
if os.path.isfile(ffmpeg):
  ydl_opts["ffmpeg_location"] = ffmpeg

url = input("\nEnter the video url : ").strip().strip('"').strip("'")
if not url:
  raise SystemExit("No URL given")

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
  ydl.download([url])

print("\nVideo Download Successful")


# import yt_dlp
#
# print("The version of yt_dlp is : ", yt_dlp.version.__version__)
#
# url = input("\nEnter the video url : ")
# # ydl_opts = {'format':'best[ext=mp4]'}
# ydl_opts = {}
# with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#   ydl.download([url])
#
# print ("\nVideo Download Successful")
