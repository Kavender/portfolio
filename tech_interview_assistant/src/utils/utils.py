import re
import hashlib
from os import path
from pandas import DataFrame
from itertools import islice
from datetime import datetime
from urllib.parse import urlparse


def batch(iterable, batch_size):
    """Yield successive batches of size `batch_size` from `iterable`."""
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, batch_size))
        if not batch:
            break
        yield batch


def convert_timestamp_date(input_dt):
    timestamp = int(input_dt) / 1000.0
    date_time = datetime.fromtimestamp(timestamp).date()
    return date_time


def clean_extracted_text(text, patters_to_remove):
    # Define patterns to remove (regex patterns for the button texts)
    for pattern in patters_to_remove:
        text = re.sub(re.escape(pattern), '', text)  # Remove each pattern
    return text.strip()


def extract_question_from_url(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    # Assume the question name is always the second part of the path
    question_name = path_parts[1] if len(path_parts) > 1 else None
    
    if question_name:
        question_name = question_name.replace('-', '_')

    return question_name


def hash_text_to_digits(text, num_digits):
    hash_object = hashlib.sha256()
    hash_object.update(text.encode())
    hex_dig = hash_object.hexdigest()
    large_int = int(hex_dig, 16)
    fixed_digits_int = large_int % (10**num_digits)
    return fixed_digits_int


def save_to_csv(df: DataFrame, filename: str) -> None:
    if path.exists(filename):
        df.to_csv(filename, mode="a", header=False, index=False)
    else:
        df.to_csv(filename, mode="w", header=True, index=False)

