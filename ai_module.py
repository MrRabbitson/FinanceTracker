import re
from huggingface_hub import InferenceClient

client = None
model = None

def init_client(token, ai_model):
    global client, model
    try:
        client = InferenceClient(token=token)
        model = ai_model
    except Exception as e:
        client = None

def markdown_to_html(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'\n', r'<br>', text)
    return text

def generate_response(prompt):
    if client is None:
        raise Exception("Клиент не инициализирован.")
    try:
        response = client.chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        raw_response = response['choices'][0]['message']['content'].strip()
        return markdown_to_html(raw_response)
    except Exception as e:
        raise Exception(f"Ошибка генерации ответа ИИ: {str(e)}")