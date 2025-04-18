import yt_dlp

print("The version of yt_dlp is : ", yt_dlp.version.__version__)

url = input("\nEnter the video url : ")
# ydl_opts = {'format':'best[ext=mp4]'}
ydl_opts = {}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
  ydl.download([url])

print ("\nVideo Download Successful")
