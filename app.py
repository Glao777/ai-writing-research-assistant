import streamlit as st
import streamlit_authenticator as stauth
import openai
import os
import sqlite3
import datetime
import requests
from PyPDF2 import PdfReader
from io import BytesIO
from docx import Document
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
openai.api_key = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")
DB_PATH = "user_logs.db"

# --- AUTHENTICATION ---
names = ['Admin User', 'Basic User']
usernames = ['admin', 'user']
passwords = ['admin_pass', 'user_pass']
hashed_passwords = stauth.Hasher(passwords).generate()
authenticator = stauth.Authenticate(names, usernames, hashed_passwords, 'cookie', 'secret', cookie_expiry_days=1)

name, auth_status, username = authenticator.login('Login', 'main')
is_admin = username == 'admin'

# Track usage limits in session
if 'usage_count' not in st.session_state:
    st.session_state.usage_count = 0

if st.session_state.usage_count >= 5:
    st.warning("🚫 Free usage limit reached for this session (5 requests).")
    st.stop()

# --- DB SETUP ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            username TEXT,
            tool TEXT,
            input TEXT,
            output TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_interaction(username, tool, prompt, response):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs VALUES (?, ?, ?, ?, ?)", 
              (username, tool, prompt, response, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def fetch_logs(username=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if username:
        c.execute("SELECT * FROM logs WHERE username = ?", (username,))
    else:
        c.execute("SELECT * FROM logs")
    return c.fetchall()

init_db()

# --- TEMPLATES ---
PROMPT_TEMPLATES = {
    "Academic Summary": "Summarize the following academic article in simple terms:\n\n",
    "SEO Blog": "Write a blog post with SEO optimization about:\n\n",
    "Email Draft": "Draft a professional email to:\n\n"
}

# --- UTILITIES ---
def extract_text(file):
    if file.type == "application/pdf":
        reader = PdfReader(file)
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    elif file.type == "text/plain":
        return file.read().decode("utf-8")
    return ""

def generate_ai_response(prompt, temperature=0.7):
    response = openai.ChatC
