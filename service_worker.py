import pyttsx3
import time
import os

# Init the pytttsx3 engine with engine voice property
local_tts_engine = pyttsx3.init()
local_tts_engine.setProperty('voice', 'english_rp+f3')
rate = local_tts_engine.getProperty('rate')
local_tts_engine.setProperty('rate', rate-25)
volume = local_tts_engine.getProperty('volume')
local_tts_engine.setProperty('volume', 0.9)


def generate_audio():
    '''1. Get file details from kafka
        2. Fetch File from object storage bucket
        3. Check if to use pyttssx3 or Google TTS
        4. Save file to audio bucket.
    '''
    file_details = get_file_from_kafka()
    local_tts = os.getenv("ENABLE_LOCAL_TTS") or True
    if local_tts:
        convert_local_tts(file_details)
    else:
        convert_google_tts(file_details)


# get file details from kafka placeholder
def get_file_from_kafka():
    file_details = dict()
    file_details['text'] = "Hello this is a file details \n dummy, \r joking\
    arround ha ha ha"
    # add extra keys to map to have required meta data going forward
    return file_details


def convert_local_tts(file_details):
    local_tts_engine.save_to_file(file_details['text'], "local_sample.mp3")
    local_tts_engine.runAndWait()


def convert_google_tts(file_details):
    return 'No Service found...'


generate_audio()
