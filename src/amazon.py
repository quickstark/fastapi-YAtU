"""
Amazon Web Services (AWS) functions
"""

# Import
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile
from sentry_sdk import capture_exception, configure_scope

# Create a new router for Postgres Routes
router_amazon = APIRouter()

# Load dotenv in the base root refers to application_top
APP_ROOT = os.path.join(os.path.dirname(__file__), '..')
dotenv_path = os.path.join(APP_ROOT, '.env')
load_dotenv(dotenv_path)

# Prep our environment variables / upload .env to Railway.ap
AWS_KEY = os.getenv('AMAZON_KEY_ID')
AWS_SECRET = os.getenv('AMAZON_KEY_SECRET')
AWS_BUCKET = os.getenv('AMAZON_S3_BUCKET')

# print the variables above
print(AWS_KEY)
print(AWS_SECRET)
print(AWS_BUCKET)

# Instantiate an AWS Session (orthogonal to Client and Resource)
AWS_SESSION = boto3.Session(
    region_name="us-east-2",
    aws_access_key_id=AWS_KEY,
    aws_secret_access_key=AWS_SECRET
)


@router_amazon.post(path="/upload-image-amazon/")
def amazon_upload(file: UploadFile = File(...)) -> str:
    """Uploads a file to S3

    Args:
        file (IO): A valid image file

    Returns:
        string: The uploaded file URL
    """
    awsclient = AWS_SESSION.resource("s3",)
    bucket = awsclient.Bucket(AWS_BUCKET)
    print("Attempting to upload to S3")
    try:
        # upload_fileobj takes a file-like object but run asycnchronously
        # so we need to check 
        bucket.upload_fileobj(file.file, file.filename)
        response = bucket.Object(file.filename).get()
        print(response)
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return f"https://{AWS_BUCKET}.s3.amazonaws.com/{file.filename}"
        else:
            return "Nothing was uploaded"
    except Exception as err:
        capture_exception(err)


@router_amazon.delete(path="/delete-one-s3/{key}")
async def amazon_delete_one_s3(key: str) -> bool:
    """Deletes a file from S3

    Args:
        key (str): a valid S3 file key (S3 uses the filename as the key)

    Returns:
        bool: True if the file was deleted, False if not
    """
    # Create an S3 Client from our authenticated AWS Session
    # Use to delete our S3 file using the filename
    awsclient = AWS_SESSION.client("s3",)
    try:
        response = awsclient.delete_object(Bucket=AWS_BUCKET, Key=key)
        print(f"Amazon Deletion {response}")
        if response["ResponseMetadata"]["HTTPStatusCode"] == 204:
            return True
        else:
            return False
    except Exception as err:
        capture_exception(err)

@router_amazon.delete(path="/delete-all-s3")
async def amazon_delete_all_s3() -> bool:
    """Deletes all files from S3

    Returns:
        bool: True if the file was deleted, False if not
    """
    # Create an S3 Client from our authenticated AWS Session
    # Use to delete our S3 file using the filename
    awsclient = AWS_SESSION.resource("s3",)
    bucket = awsclient.Bucket(AWS_BUCKET)
    print(f"Attempting to delete all files from S3 {bucket}")
    objects_to_delete = [{'Key': obj.key} for obj in bucket.objects.all()]
    # Delete the objects
    try:
        response = bucket.delete_objects(Delete={'Objects': objects_to_delete})
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print("All objects deleted successfully")
            return True
        else:
            print("Object deletion failed")
            return False
    except Exception as err:
        capture_exception(err)


def amazon_detection(file):
    """Detects labels, text, and moderation in an image

    Args:
        file (IO): A valid image file

    Returns:
        detect_modified_labels, detect_text_list, detect_moderation_list: Labels List, Test List, Moderation List
    """
    awsclient = AWS_SESSION.client("rekognition")
    detect_labels_res = awsclient.detect_labels(
        Image={'S3Object': {'Bucket': AWS_BUCKET, 'Name': file.filename}})
    detect_text_res = awsclient.detect_text(
        Image={'S3Object': {'Bucket': AWS_BUCKET, 'Name': file.filename}})
    detect_moderation_res = awsclient.detect_moderation_labels(
        Image={'S3Object': {'Bucket': AWS_BUCKET, 'Name': file.filename}})

    detect_moderation_list = []
    for label in detect_moderation_res["ModerationLabels"]:
        if label["Confidence"] > 50:
            detect_moderation_list.append(label["Name"])

    detect_labels_list = []
    for label in detect_labels_res["Labels"]:
        if label["Confidence"] > 80:
            detect_labels_list.append(label["Name"])

    detect_text_list = []
    for text in detect_text_res['TextDetections']:
        if text["Type"] == "LINE" and text["Confidence"] > 80:
            detect_text_list.append(text["DetectedText"])

    detect_modified_labels = list(
        map(lambda x: x.replace('Insect', 'Bug'), detect_labels_list))

    print(detect_modified_labels)
    print(detect_text_list)
    print(detect_moderation_list)

    return detect_modified_labels, detect_text_list, detect_moderation_list


def amazon_moderation(moderation: list) -> bool:
    """Moderates an image based on the moderation labels detected

    Args:
        moderation (list): A list of moderation labels

    Returns:
        bool: True if moderation is detected, False if not
    """
    if any('Suggestive'.casefold() or 'Underwear'.casefold() or 'Revealing'.casefold() in text.casefold() for text in moderation):
        return True
    else:
        return False


def amazon_error_text(amztext: list) -> bool:
    """Checks if the word 'error' in the text return from Amazon Rekognition

    Args:
        text (list): A list of text detected

    Returns:
        bool: True if error text is detected, False if not
    """
    # Case insensitive check to see if the image contained the word "error"
    if any('Error'.casefold() or 'Errors'.casefold() in text.casefold() for text in amztext):
        print("Yes, we have identified the word 'Error' in the Text!")
        return True
    else:
        return False


def amazon_error_label(amzlabels: list) -> bool:
    """Checks if a label return from Amazon Rekognition yields the word "bug"

    Args:
        text (list): A list of labels detected

    Returns:
        bool: True if the word "bug" or "insect" is detected, False if not
    """
    # Case insensitive check to see if the image contained a label with the word "bug" or "insect"
    if any('Bug'.casefold() or 'Insect'.casefold() in text.casefold() for text in amzlabels):
        print("Yes, we identified a Bug or Insect in the Label!")
        return True
    else:
        return False
