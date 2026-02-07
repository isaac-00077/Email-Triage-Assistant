import gradio as gr
import requests
import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

SCALEDOWN_API_KEY = os.getenv("SCALEDOWN_API_KEY")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def compress_email(email_text):
    # ScaleDown API endpoint
    url = "https://api.scaledown.xyz/compress/raw/"

    # Your headers (replace YOUR_API_KEY with your actual key)
    headers = {
        'x-api-key': SCALEDOWN_API_KEY,
        'Content-Type': 'application/json'
    }

    payload = {
        "context": email_text,
        "prompt": "Compress this email while preserving key information",
        "scaledown": {
            "rate": "auto",
        }
    }
    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(payload)
    )

    if response.status_code != 200:
        return "Error calling ScaleDown API."

    result = response.json()

    if not result.get("successful"):
        return "Compression failed."

    return result['results']['compressed_prompt']



from groq import Groq

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize_with_llm(compressed_text):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are an intelligent email triage assistant."
                },
                {
                    "role": "user",
                    "content": f"""
                    Analyze the email below and produce THREE things:

                    1. SUMMARY
                    - Give 2–3 concise bullet points.

                    2. PRIORITY
                    - Classify as ONE of:
                    High (urgent / deadline / blocking)
                    Medium (important but not urgent)
                    Low (informational / no action needed)

                    3. SUGGESTED REPLY
                    - Write a short, polite, professional reply.
                    - Do NOT invent information.
                    - Match the urgency based on priority.

                    Format your response EXACTLY like this:

                    SUMMARY:
                    • point 1
                    • point 2

                    PRIORITY:
                    <High | Medium | Low>

                    SUGGESTED REPLY:
                    <reply text>

                    EMAIL:
                    {compressed_text}
                    """
                }
            ],temperature=0.3
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error calling LLM: {str(e)}"




def compress_and_summarize(email_text):
    if not email_text.strip():
        return "", "", "Please paste some text."

    # Step 1: Compress
    compressed = compress_email(email_text)

    if compressed.startswith("Error") or compressed.startswith("Compression failed"):
        return "", "", "Compression failed. Email couldn't be processed."

    # Step 2: LLM analysis
    llm_output = summarize_with_llm(compressed)

    if llm_output.startswith("Error"):
        return "", "", "Email couldn't be summarized."

    # Step 3: Parse output
    summary, priority, reply = parse_llm_output(llm_output)

    return summary, priority, reply


def parse_llm_output(text):
    summary = ""
    priority = ""
    reply = ""

    try:
        # Split by sections
        if "SUMMARY:" in text:
            summary_part = text.split("SUMMARY:")[1].split("PRIORITY:")[0]
            summary = summary_part.strip()

        if "PRIORITY:" in text:
            priority_part = text.split("PRIORITY:")[1].split("SUGGESTED REPLY:")[0]
            priority = priority_part.strip()

        if "SUGGESTED REPLY:" in text:
            reply = text.split("SUGGESTED REPLY:")[1].strip()

    except Exception:
        pass

    return summary, priority, reply


gr.Interface(
    fn=compress_and_summarize,
    inputs=gr.Textbox(
        lines=12,
        placeholder="Paste email thread here (can include quoted replies)"
    ),
    outputs=[
        gr.Textbox(label="📌 Summary"),
        gr.Textbox(label="⚠️ Priority"),
        gr.Textbox(label="✉️ Suggested Reply", lines=5)
    ],
    title="Email Triage Assistant"
).launch()
