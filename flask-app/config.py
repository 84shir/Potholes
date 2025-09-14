import os

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_URL = os.getenv("AWS_ENDPOINT_URL_S3", "https://fly.storage.tigris.dev/")
BUCKET_NAME = "pothole-images"
