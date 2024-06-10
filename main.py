from datetime import datetime
import requests
import json
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
TELEGRAM_BASE_API_URL = os.getenv("TELEGRAM_BASE_API_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def convert_to_input_poll(answers):
    poll_options = []
    correct_indices = []
    
    for index, answer in enumerate(answers):
        poll_options.append({"text": answer["text"]})
        if answer["is_correct"]:
            correct_indices.append(index)
    
    return poll_options, correct_indices

def send_poll(question_obj):
    TELEGRAM_API_URL=f"{TELEGRAM_BASE_API_URL}{TELEGRAM_BOT_TOKEN}/sendPoll"
    input_poll_options, correct_answers_index = convert_to_input_poll(question_obj["answers"])
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": question_obj["question"],
        "type": "quiz",
        "correct_option_id": correct_answers_index[0],
        "options": json.dumps(input_poll_options)
    }
    response = requests.post(TELEGRAM_API_URL, data=data)

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
    
    return {
        "id": question_id,
        "question": question_text,
        "answers": propositions 
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