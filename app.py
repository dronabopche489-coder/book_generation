import os
import json
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Dictionary to store generated PDFs (in production, use a database or file storage)
generated_books = {}

# Field configurations
FIELD_CONFIGS = {
    'Computer Science': {
        'text_prompt_prefix': 'Focus on algorithms, programming, and computational thinking. ',
    },
    'Mathematics': {
        'text_prompt_prefix': 'Focus on logical reasoning, problem-solving, and mathematical concepts. ',
    },
    'Science': {
        'text_prompt_prefix': 'Focus on scientific method, experiments, and evidence-based learning. ',
    },
    'History': {
        'text_prompt_prefix': 'Focus on historical context, timelines, and cause-effect relationships. ',
    },
    'Literature': {
        'text_prompt_prefix': 'Focus on narrative analysis, literary devices, and character development. ',
    },
    'Art & Design': {
        'text_prompt_prefix': 'Focus on creative expression, design principles, and artistic techniques. ',
    },
    'General Education': {
        'text_prompt_prefix': 'Focus on comprehensive learning, critical thinking, and interdisciplinary connections. ',
    },
}

# Book type configurations
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
    'Beginner\'s Handbook': {
        'structure': '1. Simple Definition\n2. Step-by-Step Guide\n3. Hands-on Exercise\n4. Common Questions\n5. Progress Checklist',
        'tone': 'Friendly, simple',
    },
}

def generate_field_specific_prompt(topic, book_type, field, book_name, book_description):
    field_config = FIELD_CONFIGS.get(field, FIELD_CONFIGS['General Education'])
    book_type_config = BOOK_TYPE_CONFIGS.get(book_type, BOOK_TYPE_CONFIGS['Textbook'])

    return f'''Write a chapter on "{topic}" for a {book_type.lower()} in the field of {field.lower()}.

Book: {book_name}
Field: {field}
Description: {book_description}

{field_config['text_prompt_prefix']}

Structure this chapter with:
{book_type_config['structure']}

Tone: {book_type_config['tone']}
Style: Educational, engaging, and practical for {field.lower()} students.

Focus on:
1. Core concepts relevant to {field}
2. Practical applications in {field}
3. Common challenges and solutions
4. Real-world examples from {field}
5. Connections to broader {field} knowledge

Make it comprehensive yet accessible, with clear explanations suitable for learners.'''

def generate_pdf(book_data, chapters_data):
    """Generate PDF from book data and chapters"""
    try:
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=1
        )
        
        chapter_title_style = ParagraphStyle(
            'ChapterTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12
        )
        
        chapter_subtitle_style = ParagraphStyle(
            'ChapterSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.grey
        )
        
        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leading=14
        )
        
        # Build PDF content
        story = []
        
        # 1. Cover Page
        story.append(Paragraph(book_data['book_name'], title_style))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"A {book_data['book_type']} on {book_data['field']}", subtitle_style))
        story.append(Spacer(1, inch))
        
        if book_data.get('book_description'):
            story.append(Paragraph("Description:", styles['Heading3']))
            story.append(Paragraph(book_data['book_description'], content_style))
            story.append(Spacer(1, 0.5*inch))
        
        story.append(Paragraph("Generated with AI Book Creator", ParagraphStyle(
            'Footer',
            parent=styles['Italic'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1
        )))
        
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", 
                              ParagraphStyle('Date', parent=styles['Normal'], fontSize=10, alignment=1)))
        
        story.append(PageBreak())
        
        # 2. Table of Contents
        story.append(Paragraph("Table of Contents", title_style))
        story.append(Spacer(1, 0.5*inch))
        
        for i, topic in enumerate(book_data['topics'], 1):
            story.append(Paragraph(f"Chapter {i}: {topic}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(PageBreak())
        
        # 3. Chapters
        for i, chapter in enumerate(chapters_data, 1):
            topic = book_data['topics'][i-1]
            
            story.append(Paragraph(f"Chapter {i}", chapter_subtitle_style))
            story.append(Paragraph(topic, chapter_title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Add horizontal line
            story.append(Paragraph("<hr/>", ParagraphStyle(
                'Line',
                parent=styles['Normal'],
                textColor=colors.black,
                alignment=1
            )))
            story.append(Spacer(1, 0.3*inch))
            
            # Add chapter content
            content = chapter['content']
            # Split content into paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.replace('\n', '<br/>'), content_style))
                    story.append(Spacer(1, 0.1*inch))
            
            if i < len(chapters_data):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise

@app.route('/api/generate-chapter', methods=['POST'])
def generate_chapter():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['topic', 'book_type', 'field', 'book_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        topic = data['topic']
        book_type = data['book_type']
        field = data['field']
        book_name = data['book_name']
        book_description = data.get('book_description', '')
        
        # Generate prompt
        prompt = generate_field_specific_prompt(
            topic, book_type, field, book_name, book_description
        )
        
        # Generate content using Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": 0.7,
                "max_output_tokens": 2048,
            }
        )
        
        return jsonify({
            'success': True,
            'content': response.text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-multiple-chapters', methods=['POST'])
def generate_multiple_chapters():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['topics', 'book_type', 'field', 'book_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        topics = data['topics']
        book_type = data['book_type']
        field = data['field']
        book_name = data['book_name']
        book_description = data.get('book_description', '')
        
        chapters = []
        
        for topic in topics:
            # Generate prompt for each topic
            prompt = generate_field_specific_prompt(
                topic, book_type, field, book_name, book_description
            )
            
            # Generate content using Gemini
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 10000,
                }
            )
            
            chapters.append({
                'topic': topic,
                'content': response.text
            })
        
        return jsonify({
            'success': True,
            'chapters': chapters,
            'total_chapters': len(chapters)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-book-pdf', methods=['POST'])
def generate_book_pdf():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['topics', 'book_type', 'field', 'book_name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        topics = data['topics']
        book_type = data['book_type']
        field = data['field']
        book_name = data['book_name']
        book_description = data.get('book_description', '')
        
        # First, generate all chapters
        chapters = []
        
        for topic in topics:
            # Generate prompt for each topic
            prompt = generate_field_specific_prompt(
                topic, book_type, field, book_name, book_description
            )
            
            # Generate content using Gemini
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 10000,
                }
            )
            
            chapters.append({
                'topic': topic,
                'content': response.text
            })
        
        # Create book data structure
        book_data = {
            'book_name': book_name,
            'book_type': book_type,
            'field': field,
            'book_description': book_description,
            'topics': topics,
            'generated_date': datetime.now().isoformat(),
            'total_chapters': len(chapters)
        }
        
        # Generate PDF
        pdf_bytes = generate_pdf(book_data, chapters)
        
        # Generate unique book ID
        book_id = str(uuid.uuid4())
        
        # Store book information (in production, save to database)
        generated_books[book_id] = {
            'book_data': book_data,
            'chapters': chapters,
            'pdf_bytes': pdf_bytes.hex(),  # Store as hex string
            'created_at': datetime.now().isoformat()
        }
        
        # Generate filename
        filename = f"{book_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return jsonify({
            'success': True,
            'book_id': book_id,
            'filename': filename,
            'book_info': book_data,
            'total_chapters': len(chapters),
            'message': 'Book generated successfully and ready for download'
        })
        
    except Exception as e:
        print(f"Error in generate_book_pdf: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-book/<book_id>', methods=['GET'])
def download_book(book_id):
    try:
        # Check if book exists
        if book_id not in generated_books:
            return jsonify({'error': 'Book not found'}), 404
        
        book_info = generated_books[book_id]
        pdf_bytes = bytes.fromhex(book_info['pdf_bytes'])
        
        # Generate filename
        book_name = book_info['book_data']['book_name']
        safe_name = ''.join(c for c in book_name if c.isalnum() or c in (' ', '_')).rstrip()
        filename = f"{safe_name}.pdf"
        
        # Create response with PDF
        response = send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
        return response
        
    except Exception as e:
        print(f"Error downloading book: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/book-status/<book_id>', methods=['GET'])
def book_status(book_id):
    """Check if a book exists and get its info"""
    try:
        if book_id in generated_books:
            book_info = generated_books[book_id]
            return jsonify({
                'success': True,
                'exists': True,
                'book_data': book_info['book_data'],
                'created_at': book_info['created_at']
            })
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'message': 'Book not found'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/list-books', methods=['GET'])
def list_books():
    """List all generated books (for debugging)"""
    try:
        books_list = []
        for book_id, book_info in generated_books.items():
            books_list.append({
                'book_id': book_id,
                'book_name': book_info['book_data']['book_name'],
                'field': book_info['book_data']['field'],
                'book_type': book_info['book_data']['book_type'],
                'created_at': book_info['created_at'],
                'total_chapters': len(book_info['chapters'])
            })
        
        return jsonify({
            'success': True,
            'total_books': len(books_list),
            'books': books_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'AI Book Generator API',
        'total_books_generated': len(generated_books)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)