
import os
import requests
import json

BASE_URL = "http://0.0.0.0:8777/api/local_doc_qa"
def make_new_kb(user_id: str = 'zzp', kb_name: str = 'default'):
    url = f"{BASE_URL}/new_knowledge_base"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "user_id": user_id,
        "kb_name": kb_name
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

def upload_files(kb_id: str, user_id: str = 'zzp', mode: str = "soft", folder_path: str = ".", file_type: list = ["pdf", "docx", "md", "py"]):
    url = f"{BASE_URL}/upload_files"
    data = {
        "user_id": user_id,
        "kb_id": kb_id,
        "mode": mode
    }
    files = []
    for root, dirs, file_names in os.walk(folder_path):
        for file_name in file_names:
            for end in file_type:
                if file_name.endswith(end):  
                    file_path = os.path.join(root, file_name)
                    files.append(("files", open(file_path, "rb")))
    response = requests.post(url, files=files, data=data)
    return response.json()

def upload_url(kb_id: str, user_id: str = 'zzp', focus_url: str = "https://ai.youdao.com/DOCSIRMA/html/trans/api/wbfy/index.html"):
    url = f"{BASE_URL}/upload_weblink"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "user_id": user_id,
        "kb_id": kb_id,
        "url": focus_url
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

def clean_kb_files(kb_id: str, user_id: str = 'zzp', status: str = ["grey", "yellow", "red"]):
    url = f"{BASE_URL}/clean_files"
    headers = {
        "Content-Type": "application/json"
    }
    all_response_json = []
    for color in status:
        data = {
            "user_id": user_id,
            "kb_id": kb_id,
            "status": color
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))
        all_response_json.append(response.json())
    return all_response_json

def ask_kb(kb_id: str, user_id: str = 'zzp', question: str = "How to install python?", history: list = [], rerank: bool = True, streaming: bool = False, networking: bool = False,
           custom_prompt: str = 'You are a patient, friendly, and professional programming robot that can accurately answer various programming questions from users.'):
    url = f"{BASE_URL}/local_doc_chat"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "user_id": user_id,
        "kb_id": kb_id,
        "question": question,
        "history": history,
        "rerank": rerank,
        "streaming": streaming,
        "networking": networking,
        "custom_prompt": custom_prompt
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        return response.json()
    except Exception as e:
        print(f"RAG request failed to send: {e}")
