import os
import json
import uuid
import io
from datetime import datetime

import google.generativeai as genai
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# --------------------------------------------------
# ENV + APP SETUP
# --------------------------------------------------

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Gemini (stable SDK)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize model once (reuse across requests)
model = genai.GenerativeModel("gemini-2.5-flash")

# In-memory storage (replace with DB in production)
generated_books = {}

# --------------------------------------------------
# CONFIGURATIONS
# --------------------------------------------------

FIELD_CONFIGS = {
    'Computer Science': {'text_prompt_prefix': 'Focus on algorithms, programming, and computational thinking. '},
    'Mathematics': {'text_prompt_prefix': 'Focus on logical reasoning, problem-solving, and mathematical concepts. '},
    'Science': {'text_prompt_prefix': 'Focus on scientific method, experiments, and evidence-based learning. '},
    'History': {'text_prompt_prefix': 'Focus on historical context, timelines, and cause-effect relationships. '},
    'Literature': {'text_prompt_prefix': 'Focus on narrative analysis, literary devices, and character development. '},
    'Art & Design': {'text_prompt_prefix': 'Focus on creative expression, design principles, and artistic techniques. '},
    'General Education': {'text_prompt_prefix': 'Focus on comprehensive learning, critical thinking, and interdisciplinary connections. '},
}

BOOK_TYPE_CONFIGS = {
    'Textbook': {
        'structure': '1. Learning Objectives\n2. Key Terms\n3. Detailed Explanation\n4. Examples\n5. Practice Problems\n6. Summary',
        'tone': 'Academic, formal',
    },
    'Exam-prep Notes': {
        'structure': '1. Quick Definition\n2. Key Formulas\n3. Common Questions\n4. Memory Tricks\n5. Mistakes to Avoid',
        'tone': 'Concise, practical',
    },
    'Story-style Guide': {
        'structure': '1. Story Introduction\n2. Character Dialogues\n3. Real-world Analogy\n4. Practical Application\n5. Moral Lesson',
        'tone': 'Narrative, engaging',
    },
    'Research Manual': {
        'structure': '1. Research Context\n2. Methodologies\n3. Case Studies\n4. Data Analysis\n5. References',
        'tone': 'Technical, precise',
    },
    "Beginner's Handbook": {
        'structure': '1. Simple Definition\n2. Step-by-Step Guide\n3. Hands-on Exercise\n4. Common Questions\n5. Progress Checklist',
        'tone': 'Friendly, simple',
    },
}

# --------------------------------------------------
# PROMPT GENERATION
# --------------------------------------------------

def generate_field_specific_prompt(topic, book_type, field, book_name, book_description):
    field_config = FIELD_CONFIGS.get(field, FIELD_CONFIGS['General Education'])
    book_type_config = BOOK_TYPE_CONFIGS.get(book_type, BOOK_TYPE_CONFIGS['Textbook'])

    return f"""
Write a detailed chapter on "{topic}" for a {book_type.lower()} in the field of {field.lower()}.

Book: {book_name}
Field: {field}
Description: {book_description}

{field_config['text_prompt_prefix']}

Structure:
{book_type_config['structure']}

Tone: {book_type_config['tone']}
Style: Educational, engaging, and practical.

Include:
1. Core concepts
2. Clear explanations
3. Examples
4. Applications
5. Summary

Make it comprehensive yet accessible.
"""

# --------------------------------------------------
# PDF GENERATION
# --------------------------------------------------

def generate_pdf(book_data, chapters_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=24, alignment=1, spaceAfter=30
    )

    chapter_title_style = ParagraphStyle(
        'ChapterTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=12
    )

    content_style = ParagraphStyle(
        'Content', parent=styles['Normal'], fontSize=11, leading=14, spaceAfter=8
    )

    story = []

    # Cover Page
    story.append(Paragraph(book_data['book_name'], title_style))
    story.append(Spacer(1, inch))
    story.append(Paragraph(f"{book_data['book_type']} | {book_data['field']}", styles['Heading2']))
    story.append(Spacer(1, inch))
    story.append(Paragraph(book_data.get('book_description', ''), content_style))
    story.append(PageBreak())

    # Table of Contents
    story.append(Paragraph("Table of Contents", styles['Heading1']))
    story.append(Spacer(1, 0.5 * inch))

    for i, topic in enumerate(book_data['topics'], 1):
        story.append(Paragraph(f"Chapter {i}: {topic}", styles['Normal']))

    story.append(PageBreak())

    # Chapters
    for i, chapter in enumerate(chapters_data, 1):
        story.append(Paragraph(f"Chapter {i}: {chapter['topic']}", chapter_title_style))
        story.append(Spacer(1, 0.2 * inch))

        for para in chapter['content'].split("\n\n"):
            if para.strip():
                story.append(Paragraph(para.replace("\n", "<br/>"), content_style))

        if i < len(chapters_data):
            story.append(PageBreak())

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes

# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route('/api/generate-chapter', methods=['POST'])
def generate_chapter():
    data = request.json

    topic = data['topic']
    book_type = data['book_type']
    field = data['field']
    book_name = data['book_name']
    book_description = data.get('book_description', '')

    prompt = generate_field_specific_prompt(topic, book_type, field, book_name, book_description)

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 2048,
        }
    )

    return jsonify({
        "success": True,
        "content": response.text
    })


@app.route('/api/generate-multiple-chapters', methods=['POST'])
def generate_multiple_chapters():
    data = request.json

    topics = data['topics']
    book_type = data['book_type']
    field = data['field']
    book_name = data['book_name']
    book_description = data.get('book_description', '')

    chapters = []

    for topic in topics:
        prompt = generate_field_specific_prompt(topic, book_type, field, book_name, book_description)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 6000,
            }
        )

        chapters.append({
            "topic": topic,
            "content": response.text
        })

    return jsonify({
        "success": True,
        "chapters": chapters,
        "total_chapters": len(chapters)
    })


@app.route('/api/generate-book-pdf', methods=['POST'])
def generate_book_pdf():
    data = request.json

    topics = data['topics']
    book_type = data['book_type']
    field = data['field']
    book_name = data['book_name']
    book_description = data.get('book_description', '')

    chapters = []

    for topic in topics:
        prompt = generate_field_specific_prompt(topic, book_type, field, book_name, book_description)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 6000,
            }
        )

        chapters.append({
            "topic": topic,
            "content": response.text
        })

    book_data = {
        "book_name": book_name,
        "book_type": book_type,
        "field": field,
        "book_description": book_description,
        "topics": topics,
        "generated_date": datetime.now().isoformat(),
        "total_chapters": len(chapters)
    }

    pdf_bytes = generate_pdf(book_data, chapters)

    book_id = str(uuid.uuid4())

    generated_books[book_id] = {
        "book_data": book_data,
        "chapters": chapters,
        "pdf_bytes": pdf_bytes.hex(),
        "created_at": datetime.now().isoformat()
    }

    return jsonify({
        "success": True,
        "book_id": book_id,
        "total_chapters": len(chapters),
        "message": "Book generated successfully"
    })


@app.route('/api/download-book/<book_id>', methods=['GET'])
def download_book(book_id):
    if book_id not in generated_books:
        return jsonify({"error": "Book not found"}), 404

    book_info = generated_books[book_id]
    pdf_bytes = bytes.fromhex(book_info["pdf_bytes"])

    filename = f"{book_info['book_data']['book_name'].replace(' ', '_')}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "AI Book Generator API",
        "total_books": len(generated_books)
    })


# --------------------------------------------------
# RENDER ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

