from datetime import datetime
import requests
import json
import pytz
import os
import magic
import urllib.request
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
TELEGRAM_BASE_API_URL = os.getenv("TELEGRAM_BASE_API_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_file(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    req = urllib.request.Request(url, headers=headers)
    
    response = urllib.request.urlopen(req)
    content_length = response.headers.get('content-length')
    
    if content_length:
        bytes_to_read = min(int(content_length), 1024)
    else:
        bytes_to_read = 1024

    with urllib.request.urlopen(req) as response:
        content = response.read(bytes_to_read)

    mime_type = magic.from_buffer(content, mime=True)
    
    if mime_type.startswith('image'):
        file_type = 'photo'
    elif mime_type.startswith('video'):
        file_type = 'video'
    elif mime_type.startswith('audio'):
        file_type = 'audio'
    else:
        file_type = None

    if file_type:
        telegram_api_url = f"{TELEGRAM_BASE_API_URL}{TELEGRAM_BOT_TOKEN}/send{file_type.capitalize()}"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            file_type: url
        }
        response = requests.post(telegram_api_url, headers=headers, data=data)

        if response.status_code != 200:
            print(response.text)
            return False
        return True

def convert_to_input_poll(answers):
    poll_options = []
    correct_indices = []
    
    for index, answer in enumerate(answers):
        poll_options.append({"text": answer["text"]})
        if answer["is_correct"]:
            correct_indices.append(index)
    
    return poll_options, correct_indices

def send_poll(question_obj):
    telegram_api_url=f"{TELEGRAM_BASE_API_URL}{TELEGRAM_BOT_TOKEN}/sendPoll"
    input_poll_options, correct_answers_index = convert_to_input_poll(question_obj["answers"])
    if len(correct_answers_index) > 0:
        if question_obj["file"] is not None:
            send_file(question_obj["file"])
        
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "question": question_obj["question"],
            "type": "quiz",
            "correct_option_id": correct_answers_index[0],
            "options": json.dumps(input_poll_options)
        }
        response = requests.post(telegram_api_url, data=data)

        if response.status_code == 200:
            return True
    return False


def extract_proposition(page_properties, proposition_name):
    answer_text_key = f"{proposition_name} answer"
    text = page_properties[answer_text_key]["rich_text"][0]["plain_text"]
    is_correct = page_properties[proposition_name]["checkbox"]
    return {"text": text, "is_correct": is_correct}

def generate_simple_quiz(page):
    page_properties = page["properties"]
    question_id = page_properties["ID"]["unique_id"]["number"]
    question_text = page_properties["Statement"]["title"][0]["plain_text"]
    propositions = []
    propositions.append(extract_proposition(page_properties, "A"))
    propositions.append(extract_proposition(page_properties, "B"))
    propositions.append(extract_proposition(page_properties, "C"))
    propositions.append(extract_proposition(page_properties, "D"))
    files = page_properties["Attach File"]["files"]
    file_url = None
    if len(files) > 0:
        file_url = files[0]["file"]["url"]
    
    return {
        "id": question_id,
        "question": question_text,
        "answers": propositions,
        "file": file_url
    }
    
def update_status(page_id):
    current_datetime = datetime.now(pytz.timezone('Africa/Douala'))
    formatted_datetime_iso = current_datetime.isoformat()
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": "Bearer " + NOTION_TOKEN,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "properties": {
            "Status": {
                "select": {
                    "name": "Publié"
                }
            },
            "Published Date": {
                "date": {
                    "start": formatted_datetime_iso
                }
            }
	    }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code != 200:
        print(response.text)
    

def get_pages():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": "Bearer " + NOTION_TOKEN,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "filter": {
            "property": "Status",
            "select": {
                "equals": "Prêt"
            }
        },
        "sorts": [
            {
                "timestamp": "created_time",
                "direction": "ascending"
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        data = response.json()
        pages = data["results"]
        if len(pages) > 0:
            page = pages[0]
            if send_poll(generate_simple_quiz(page)):
                update_status(page["id"])
    else:
        print(f"Erreur {response.status_code}: {response.text}")

get_pages()