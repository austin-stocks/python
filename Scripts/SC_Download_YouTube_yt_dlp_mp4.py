import yt_dlp
import os

# Define the YouTube video URL
print("The version of yt_dlp is : ", yt_dlp.version.__version__)

video_url = input("\nEnter the video url : ")
# Define the output directory (optional, current directory if not specified)
# download_path = './downloads'
download_path = './'
if not os.path.exists(download_path):
    os.makedirs(download_path)

# yt-dlp configuration options
ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # Prioritize MP4, then fall back to best available
    'merge_output_format': 'mp4', # Ensure the final merged file is MP4
    'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'), # Output file naming template
    'noplaylist': True, # Download only a single video if the URL is part of a playlist
    'quiet': False, # Show download progress
    'progress_hooks': [lambda d: print(d['status']) if d['status'] == 'finished' else None] # Optional: print status on completion
}

# You might need to specify the ffmpeg location if it's not in your PATH
# ydl_opts['ffmpeg_location'] = '/path/to/your/ffmpeg/executable' 

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    print(f"Video downloaded successfully to {download_path}")
except Exception as e:
    print(f"An error occurred: {e}")
