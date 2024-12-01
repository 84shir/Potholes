import os
from kaggle.api.kaggle_api_extended import KaggleApi


# KAGGLE_USERNAME = "bashirabdalla"
S3_URL = "https://fly.storage.tigris.dev/"
TIGRIS_BUCKET_NAME = 'pothole-images'

def kaggle_auth():
    try:
        api = KaggleApi()
        api.authenticate()
        print("Kaggle auth 200 OK")
        return api
    except Exception as e:
        print(f"Failed to authenticate Kaggle: {e}")
    

def pull_images_from_dataset(api: KaggleApi, url: str):
    base_path = "temp"
    os.mkdir(base_path) if not os.path.exists(base_path) else ""
    
    dataset_name = url[url.find("datasets/") + 9:]
    full_output_path = f"{base_path}/{dataset_name}"

    if not os.path.exists(base_path):
        os.mkdir(base_path)
    
    os.makedirs(full_output_path, mode = 511, exist_ok=True)
    
    try:
        api.dataset_download_files(dataset_name, full_output_path, unzip=True)
        print(f"Successfully pulled dataset {dataset_name}.")
        return full_output_path
    except Exception as e:
        print(f"failed to get dataset {dataset_name}: {e}")
    

    
if __name__ == "__main__":
    link =  "https://www.kaggle.com/datasets/sachinpatel21/pothole-image-dataset"
    api = kaggle_auth()
    pull_images_from_dataset(api, link)
    print()
    
    