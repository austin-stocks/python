import yt_dlp



# I checked it out on 4/20/2024 - it works
url = input("Enter the video url : ")

# ydl_opts = {'format':'best[ext=mp4]'}
ydl_opts = {}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
  ydl.download([url])

print ("Video Download Successful")
