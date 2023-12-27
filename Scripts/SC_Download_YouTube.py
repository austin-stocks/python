import pytube

# We save it in the current working directory
download_loc = './'

# Ask the user to enter the url of YouTube Video
video_url = input ('Enter url : ')

# Create an instance of YouTube Video
video_instance = pytube.YouTube(video_url)
print ('Downloading YouTube video : ', video_instance.title)
stream = video_instance.streams.get_highest_resolution()

# download
stream.download()
print ('Done...')
