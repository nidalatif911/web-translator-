"""
Web Translator - Real-Time Translation, Documents, Websites & TTS Service
"""

import os
import sys
import io
import time
import zipfile
import tempfile
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import pymupdf

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import LANGUAGES, LANGUAGE_NAMES, APP_NAME, APP_VERSION
from app.translator import translate_text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=f"{APP_NAME} API",
    version=APP_VERSION,
    description="Real-time voice, text, document, and website translation service."
)

# Static files for branding assets (logos, icons, favicons)
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranslationRequest(BaseModel):
    text: str
    source: str = "English"
    target: str = "Spanish"


class TTSRequest(BaseModel):
    text: str
    lang: str = "Spanish"


class WebsiteRequest(BaseModel):
    url: str
    source: str = "English"
    target: str = "Spanish"


# -------------------------------------------------------------
# Document & Website Helpers
# -------------------------------------------------------------
def extract_text_from_file(filename: str, content_bytes: bytes) -> str:
    """Extracts text from PDF, DOCX, TXT, MD, CSV, JSON files."""
    ext = os.path.splitext(filename.lower())[1]

    if ext == ".pdf":
        doc = pymupdf.open(stream=content_bytes, filetype="pdf")
        pages_text = [page.get_text() for page in doc]
        return "\n\n".join(p.strip() for p in pages_text if p.strip())

    elif ext == ".docx":
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            paragraphs = []
            for p in tree.iter(f"{namespace}p"):
                texts = [node.text for node in p.iter(f"{namespace}t") if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n\n".join(paragraphs)

    else:
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return content_bytes.decode("latin-1", errors="replace")


def split_text_into_chunks(text: str, max_chars: int = 1500) -> List[str]:
    """Splits text into readable paragraph chunks suitable for translation engines."""
    paragraphs = text.split("\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        if current_len + len(p_clean) > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [p_clean]
            current_len = len(p_clean)
        else:
            current_chunk.append(p_clean)
            current_len += len(p_clean)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------
@app.get("/api/languages")
async def get_languages():
    """Returns supported languages metadata."""
    return {
        "languages": [
            {
                "name": name,
                "flag": info["flag"],
                "code": info["google"],
                "stt": info["stt"],
                "tts": info["tts"]
            }
            for name, info in LANGUAGES.items()
        ]
    }


@app.post("/api/translate")
async def handle_translate(req: TranslationRequest):
    """Translates text from source to target language."""
    if not req.text or not req.text.strip():
        return {"translated_text": "", "source": req.source, "target": req.target}

    try:
        translated = translate_text(req.text.strip(), req.source, req.target)
        return {
            "success": True,
            "original_text": req.text,
            "translated_text": translated,
            "source": req.source,
            "target": req.target
        }
    except Exception as e:
        logger.error(f"Translation API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate-document")
async def handle_translate_document(
    file: UploadFile = File(...),
    source: str = Form("English"),
    target: str = Form("Spanish")
):
    """Extracts text from uploaded PDF/DOCX/TXT and translates it."""
    try:
        content_bytes = await file.read()
        extracted_text = extract_text_from_file(file.filename, content_bytes)

        if not extracted_text or not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No readable text found in document.")

        chunks = split_text_into_chunks(extracted_text, max_chars=1200)
        translated_chunks = []

        for chunk in chunks[:15]:
            t_chunk = translate_text(chunk, source, target)
            translated_chunks.append(t_chunk)

        translated_full = "\n\n".join(translated_chunks)

        return {
            "success": True,
            "filename": file.filename,
            "original_text": extracted_text[:5000],
            "translated_text": translated_full,
            "word_count": len(extracted_text.split()),
            "source": source,
            "target": target
        }
    except Exception as e:
        logger.error(f"Document translation error: {e}")
        raise HTTPException(status_code=500, detail=f"Document error: {e}")


@app.post("/api/translate-website")
async def handle_translate_website(req: WebsiteRequest):
    """Fetches a website and translates its main headlines and paragraphs."""
    url = req.url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        orig_title = soup.title.string.strip() if soup.title and soup.title.string else url
        translated_title = translate_text(orig_title, req.source, req.target)

        elements = soup.find_all(["h1", "h2", "h3", "p"])
        extracted_items = []

        for el in elements:
            text = el.get_text().strip()
            if len(text) > 25 and len(extracted_items) < 12:
                extracted_items.append(text)

        translated_items = []
        for item in extracted_items:
            t_text = translate_text(item, req.source, req.target)
            translated_items.append({
                "original": item,
                "translated": t_text
            })

        return {
            "success": True,
            "url": url,
            "original_title": orig_title,
            "translated_title": translated_title,
            "articles": translated_items,
            "source": req.source,
            "target": req.target
        }
    except Exception as e:
        logger.error(f"Website translation error: {e}")
        raise HTTPException(status_code=500, detail=f"Website fetch/translation error: {e}")


@app.post("/api/tts")
async def handle_tts(req: TTSRequest):
    """Generates speech audio from text using gTTS and returns MP3."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    lang_info = LANGUAGES.get(req.lang, {})
    tts_lang = lang_info.get("tts", "en")

    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_path = temp_file.name
        temp_file.close()

        tts = gTTS(text=req.text.strip(), lang=tts_lang, slow=False)
        tts.save(temp_path)

        return FileResponse(
            temp_path,
            media_type="audio/mpeg",
            filename="speech.mp3"
        )
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")


@app.get("/favicon.ico")
async def favicon():
    """Serves the brand favicon."""
    fav_ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon-32.png")
    if os.path.exists(fav_ico):
        return FileResponse(fav_ico, media_type="image/png")
    return HTMLResponse("", status_code=404)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the modern Web Translator application."""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("<h3>Web Translator interface not found.</h3>", status_code=404)
