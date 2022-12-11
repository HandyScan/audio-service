import pyttsx3
import time
import os
import sys
import logging
import jsonpickle
from minio import Minio
from time import sleep
from confluent_kafka import Producer, Consumer
from pymongo import MongoClient

# logging 
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Mongo DB
monogo_user = os.environ.get("MONGO_USERNAME", "handyscan_admin")
mongo_pwd = os.environ.get("MONGO_PASSWORD", "handyscan_admin")
mongo_connection_url = "mongodb+srv://" + monogo_user + ":" + mongo_pwd + "@glasscode.8iobb.mongodb.net/handyscan?retryWrites=true&w=majority"
client = MongoClient(mongo_connection_url)
db = client.handyscan
print("Connected to Mongo")


# Init the pytttsx3 engine with engine voice property
local_tts_engine = pyttsx3.init()
local_tts_engine.setProperty('voice', 'english_rp+f3')
rate = local_tts_engine.getProperty('rate')
local_tts_engine.setProperty('rate', rate-25)
volume = local_tts_engine.getProperty('volume')
local_tts_engine.setProperty('volume', 0.9)

# kafka Config
kafka_bootstrap_server = os.environ.get('KAFKA_BOOTSTRAP', 'pkc-4r087.us-west2.gcp.confluent.cloud:9092')
kafka_api_key = os.environ.get('KAFKA_API_KEY', '4BRDEW6OW6Z35KZK')
kafka_secret_key = os.environ.get('KAFKA_SECRET_KEY', 'pqfV+6B+nDwtrxr0GckMlrqofW5fW/kLPvWL83w+oZoPvkzwOzl5f/rhJbdYJOTn')
kafka_config = {
    'bootstrap.servers':'pkc-4r087.us-west2.gcp.confluent.cloud:9092',
    'security.protocol':'SASL_SSL',
    'sasl.mechanisms':'PLAIN',
    'sasl.username': kafka_api_key,
    'sasl.password': kafka_secret_key,
    'group.id':'ocr_consumer',
    'auto.offset.reset':'earliest'
}

consumer =  Consumer(kafka_config)
print("Connected to kafka")

# Minio Config
minioHost = os.getenv("MINIO_HOST") or "127.0.0.1:9000"
minioUser = os.getenv("MINIO_USER") or "minioadmin"
minioPasswd = os.getenv("MINIO_PASSWD") or "minioadmin"
print(f"Getting minio connection now for host {minioHost}!")

minio_client = None
try:
    minio_client = Minio(minioHost, access_key=minioUser, secret_key=minioPasswd, secure=False)
    print("Got minio connection",minio_client )
except Exception as exp:
    print(f"Exception raised in worker loop: {str(exp)}")


def get_details_from_kafka():
    consumer.subscribe(['tts_topic'])
    file_detail_msg = consumer.poll(1.0)
    if file_detail_msg is None:
        return
    if file_detail_msg.error():
        logger.error('ERROR: Failed to get file details from OCR_TOPIC', str(file_detail_msg.error()))
        return
    file_detail = file_detail_msg.value().decode('utf-8')
    logger.info("Fetched File to process: " + file_detail)

    return jsonpickle.loads(file_detail)


def get_file(file_detail):
    # file_path = os.path.join("/tmp", "input", file_detail['file_name'])
    logger.info("Text File name to be read: " + file_detail['file_name'])
    text = minio_client.get_object(file_detail['bucket'], file_detail['file_name']).data.decode()
    logger.info(text)
    return text, file_detail['file_name']


def generate_audio(text, audio_file_name):
    cwd = os.getcwd()
    logger.info(cwd)
    audio_file_path = os.path.join(cwd, "tmp", audio_file_name)
    logger.info("Genrating audio in location: " + audio_file_path)
    local_tts_engine.save_to_file(text, audio_file_path)
    local_tts_engine.runAndWait()
    # sleep(90)
    logger.info("Done processing audio wrtiten to file")
    logger.info(os.listdir(os.path.join(cwd, "tmp")))
    return audio_file_path


def write_audio_file(file_path, file_name):
    logger.info("Sending audio file to minio")
    return minio_client.fput_object('audio-bucket', object_name=file_name, file_path=file_path)

def update_metadata(file_detail, audio_file_name):
    filter = {'user': file_detail['user_name'], 'collection': file_detail['collection']}
    file_object = db.userRecord.find_one(filter)
    logger.info(file_object)
    update_file_object = file_object['files']
    logger.info("BEFORE UPDATE")
    logger.info(update_file_object)
    update_file_object[file_detail['file_name'].split(".")[0]]['status'] = "DONE"
    update_file_object[file_detail['file_name'].split(".")[0]]['audioFile'] = {
        'bucket': 'audio-bucket', 
        'fileName': audio_file_name
    }

    logger.info("Updating Record Metadata")
    logger.info(update_file_object)
    return db.userRecord.find_one_and_update(
        filter,
        {'$set': {'files' : update_file_object}}    
    )

while True:
    try:
        file_detail = get_details_from_kafka()
        file_path = None
        text = ''
        if file_detail:
            text, file_name = get_file(file_detail)
            if file_name.endswith('txt') and len(text) != 0:
                audio_file_name = file_detail['file_name'].split(".")[0]+".mp3"
                audio_file_path = generate_audio(text, audio_file_name)
                write_audio_file(audio_file_path, audio_file_name)
                update_metadata(file_detail, audio_file_name)
                logger.info("SUCCESS Done processing")
    except Exception as err:
        logger.error(err)
