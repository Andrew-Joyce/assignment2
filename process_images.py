import boto3
import requests
from botocore.exceptions import NoCredentialsError
import json

def download_image(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        return response.content
    else:
        print(f"Error downloading {image_url}")
        return None

def upload_to_s3(bucket_name, image_name, image_data):
    s3 = boto3.client('s3')
    try:
        s3.put_object(Bucket=bucket_name, Key=image_name, Body=image_data)
        print(f"{image_name} uploaded successfully.")
    except NoCredentialsError:
        print("Credentials not available.")

def process_images(json_file_path, bucket_name):
    with open(json_file_path, 'r') as file:
        data = json.load(file)
        songs = data.get('songs', [])
        
        for song in songs:
            artist = song.get('artist').replace("/", "|")  
            img_url = song.get('img_url')
            if img_url:
                image_name = img_url.split('/')[-1]  
                image_data = download_image(img_url)
                if image_data:
                    upload_to_s3(bucket_name, f"artists/{artist}-{image_name}", image_data)

if __name__ == "__main__":
    json_file_path = '/Users/andrewjoyce/Downloads/a2.json'  
    bucket_name = 'ajcloudassignment'  
    process_images(json_file_path, bucket_name)
