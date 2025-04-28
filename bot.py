import os
import uuid
import logging
import io
import re
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
import PyPDF2
from docx2pdf import convert
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import img2pdf
from aiohttp import web

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://your-app.onrender.com/webhook

# Directories
UPLOAD_DIR = "uploads"
CONVERTED_DIR = "converted"
TEMP_DIR = "temp"

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_SECOND_PDF, AWAITING_TEXT, AWAITING_PAGE_NUMBERS = range(3)

# Store temporary data
user_data_store = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome to Any2Any Bot!\n\n"
        "Send me files to convert them or use commands for specific operations:\n"
        "Supported features:\n"
        "- 📄 PDF to Text\n"
        "- 📝 DOCX to PDF\n"
        "- 🖼️ Image to Text (OCR)\n"
        "- 📄 PDF to Images\n"
        "- 📝 Text to PDF - use /text2pdf\n"
        "- 🔄 PDF Merge - use /merge\n"
        "- ✂️ PDF Extract Pages - use /extract\n"
        "- 🔍 File Info - use /info\n"
        "- 🗜️ PDF Compression - use /compress\n\n"
        "Type /help for more info."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📚 How to use Any2Any Bot:\n\n"
        "📄 PDF to Text: Send a PDF file\n"
        "📝 DOCX to PDF: Send a DOCX file\n"
        "🖼️ Image to Text (OCR): Send an image file\n"
        "📄 PDF to Images: Send a PDF with caption /pdf2img\n"
        "📝 Text to PDF: Use /text2pdf and follow instructions\n"
        "🔄 PDF Merge: Use /merge and follow instructions\n"
        "✂️ PDF Extract Pages: Use /extract and follow instructions\n"
        "🔍 File Info: Send any file with caption /info\n"
        "🗜️ PDF Compression: Send a PDF with caption /compress\n\n"
        "I'll process your request and send back the result! 🚀"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    if not document:
        await update.message.reply_text("❗ Please send a valid document.")
        return

    # Check if there's a caption command
    caption = update.message.caption or ""
    if caption.startswith("/"):
        command = caption.split()[0].lower()
        
        if command == "/pdf2img":
            await process_pdf_to_images(update, context)
            return
        elif command == "/info":
            await process_file_info(update, context)
            return
        elif command == "/compress":
            await process_pdf_compression(update, context)
            return

    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    file_extension = os.path.splitext(document.file_name)[1].lower()

    # Create directories if not exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    upload_path = os.path.join(UPLOAD_DIR, f"{unique_id}_{document.file_name}")
    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(upload_path)

    try:
        if file_extension == ".pdf":
            converted_path = convert_pdf_to_text(upload_path, unique_id)
            await send_converted_file(update, context, converted_path, "text/plain")
        elif file_extension == ".docx":
            converted_path = convert_docx_to_pdf(upload_path, unique_id)
            await send_converted_file(update, context, converted_path, "application/pdf")
        elif file_extension in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            await process_image_to_text(update, context, upload_path)
        else:
            await update.message.reply_text("❌ Unsupported file format. Please send a PDF, DOCX, or image file.")
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        await update.message.reply_text(f"⚠️ An error occurred while processing your file: {str(e)}")
    finally:
        # Cleanup uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)

def convert_pdf_to_text(pdf_path: str, unique_id: str) -> str:
    """Convert PDF to text."""
    output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_converted.txt")
    with open(pdf_path, "rb") as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    with open(output_path, "w", encoding="utf-8") as text_file:
        text_file.write(text)
    return output_path

def convert_docx_to_pdf(docx_path: str, unique_id: str) -> str:
    """Convert DOCX to PDF (works only on Windows/macOS with Word installed)."""
    output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_converted.pdf")
    convert(docx_path, output_path)
    return output_path

async def process_image_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE, image_path: str) -> None:
    """Process image to extract text using OCR."""
    await update.message.reply_text("🔍 Processing image with OCR...")
    try:
        # Extract text from image
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        
        if not text.strip():
            await update.message.reply_text("⚠️ No text could be extracted from this image.")
            return
        
        # Save text to file
        unique_id = str(uuid.uuid4())
        output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_ocr_text.txt")
        with open(output_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)
        
        # Send the extracted text
        await send_converted_file(update, context, output_path, "text/plain")
    except Exception as e:
        logger.error(f"OCR error: {e}")
        await update.message.reply_text(f"⚠️ Error extracting text from image: {str(e)}")

async def process_pdf_to_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert PDF to images."""
    document = update.message.document
    if not document or not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❗ Please send a PDF file with /pdf2img caption.")
        return
    
    await update.message.reply_text("🔄 Converting PDF to images...")
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Create directories if not exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    upload_path = os.path.join(UPLOAD_DIR, f"{unique_id}_{document.file_name}")
    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(upload_path)
    
    try:
        # Convert PDF to images
        images = convert_from_path(upload_path)
        
        if not images:
            await update.message.reply_text("⚠️ Could not extract images from this PDF.")
            return
        
        # Save images
        image_paths = []
        for i, image in enumerate(images):
            image_path = os.path.join(CONVERTED_DIR, f"{unique_id}_page_{i+1}.jpg")
            image.save(image_path, "JPEG")
            image_paths.append(image_path)
        
        # Send the images (up to 10 to avoid spam)
        await update.message.reply_text(f"✅ Converted PDF to {len(images)} images.")
        
        for i, image_path in enumerate(image_paths[:10]):
            with open(image_path, "rb") as img_file:
                await update.message.reply_photo(
                    photo=img_file,
                    caption=f"Page {i+1}"
                )
            
        if len(image_paths) > 10:
            await update.message.reply_text("⚠️ Only showing first 10 pages to avoid spam.")
        
        # Clean up
        for image_path in image_paths:
            if os.path.exists(image_path):
                os.remove(image_path)
                
    except Exception as e:
        logger.error(f"PDF to images error: {e}")
        await update.message.reply_text(f"⚠️ Error converting PDF to images: {str(e)}")
    finally:
        # Cleanup uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)

async def process_file_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get information about a file."""
    document = update.message.document
    if not document:
        await update.message.reply_text("❗ Please send a file with /info caption.")
        return
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Create directories if not exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    upload_path = os.path.join(UPLOAD_DIR, f"{unique_id}_{document.file_name}")
    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(upload_path)
    
    try:
        file_extension = os.path.splitext(document.file_name)[1].lower()
        file_size = os.path.getsize(upload_path)
        file_size_kb = file_size / 1024
        file_size_mb = file_size_kb / 1024
        
        info_text = f"📄 File Information:\n\n"
        info_text += f"Name: {document.file_name}\n"
        info_text += f"Type: {document.mime_type}\n"
        info_text += f"Size: {file_size_mb:.2f} MB ({file_size_kb:.2f} KB)\n"
        info_text += f"Extension: {file_extension}\n"
        
        # Additional info for PDF
        if file_extension == ".pdf":
            with open(pdf_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                info_text += f"Pages: {len(reader.pages)}\n"
                
                # Get metadata if available
                metadata = reader.metadata
                if metadata:
                    info_text += "\nMetadata:\n"
                    for key, value in metadata.items():
                        if key and value and key.startswith("/"):
                            info_text += f"- {key[1:]}: {value}\n"
        
        await update.message.reply_text(info_text)
    except Exception as e:
        logger.error(f"File info error: {e}")
        await update.message.reply_text(f"⚠️ Error getting file information: {str(e)}")
    finally:
        # Cleanup uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)

async def process_pdf_compression(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Compress a PDF file."""
    document = update.message.document
    if not document or not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❗ Please send a PDF file with /compress caption.")
        return
    
    await update.message.reply_text("🗜️ Compressing PDF...")
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Create directories if not exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    
    upload_path = os.path.join(UPLOAD_DIR, f"{unique_id}_{document.file_name}")
    output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_compressed.pdf")
    
    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(upload_path)
    
    try:
        # Basic compression by creating a new PDF with reduced quality
        with open(upload_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            writer = PyPDF2.PdfWriter()
            
            # Copy all pages to new PDF
            for page in reader.pages:
                writer.add_page(page)
            
            # Save with compression
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
        
        # Check compression ratio
        original_size = os.path.getsize(upload_path)
        compressed_size = os.path.getsize(output_path)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        await update.message.reply_text(
            f"✅ PDF compressed: {compression_ratio:.1f}% reduction.\n"
            f"Original: {original_size/1024/1024:.2f} MB\n"
            f"Compressed: {compressed_size/1024/1024:.2f} MB"
        )
        
        # Send the compressed file
        await send_converted_file(update, context, output_path, "application/pdf")
    except Exception as e:
        logger.error(f"PDF compression error: {e}")
        await update.message.reply_text(f"⚠️ Error compressing PDF: {str(e)}")
    finally:
        # Cleanup uploaded file
        if os.path.exists(upload_path):
            os.remove(upload_path)

async def send_converted_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str, mime_type: str) -> None:
    """Send the converted file to user."""
    with open(file_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=os.path.basename(file_path),
            caption="✅ Here's your converted file!"
        )
    if os.path.exists(file_path):
        os.remove(file_path)

# Text to PDF conversion
async def text_to_pdf_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📝 Send me the text you want to convert to PDF."
    )
    return AWAITING_TEXT

async def text_to_pdf_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    
    if not text:
        await update.message.reply_text("❗ Please send valid text.")
        return AWAITING_TEXT
    
    await update.message.reply_text("🔄 Converting text to PDF...")
    
    try:
        # Generate unique ID
        unique_id = str(uuid.uuid4())
        output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_text_to_pdf.pdf")
        
        # Create directories if not exist
        os.makedirs(CONVERTED_DIR, exist_ok=True)
        
        # Create PDF
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        # Set font
        c.setFont("Helvetica", 12)
        
        # Split text into lines
        lines = text.split('\n')
        y_position = height - 50
        
        for line in lines:
            # Check if we need a new page
            if y_position < 50:
                c.showPage()
                yposition = height - 50
                c.setFont("Helvetica", 12)
                
            # Add text to PDF
            c.drawString(50, y_position, line)
            y_position -= 15
            
        c.save()
        
        # Send the file
        await send_converted_file(update, context, output_path, "application/pdf")
        
        # End conversation
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Text to PDF error: {e}")
        await update.message.reply_text(f"⚠️ Error converting text to PDF: {str(e)}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current conversation."""
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

# PDF Merge functionality
async def merge_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data_store[user_id] = {"pdfs": []}
    
    await update.message.reply_text(
        "🔄 PDF Merge started. Send me the first PDF file."
    )
    return AWAITING_SECOND_PDF

async def merge_first_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    document = update.message.document
    
    if not document or not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❗ Please send a PDF file.")
        return AWAITING_SECOND_PDF
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Create directories if not exist
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    upload_path = os.path.join(TEMP_DIR, f"{unique_id}_{document.file_name}")
    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(upload_path)
    
    # Save path to user data
    user_data_store[user_id]["pdfs"].append(upload_path)
    
    # Ask for second PDF
    keyboard = [
        [
            InlineKeyboardButton("Merge Now", callback_data="merge_now"),
            InlineKeyboardButton("Cancel", callback_data="cancel_merge")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Received PDF: {document.file_name}\n\n"
        f"Send another PDF to add to the merge, or click 'Merge Now' to complete.",
        reply_markup=reply_markup
    )
    
    return AWAITING_SECOND_PDF

async def merge_pdfs_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "cancel_merge":
        # Clean up temporary files
        if user_id in user_data_store and "pdfs" in user_data_store[user_id]:
            for pdf_path in user_data_store[user_id]["pdfs"]:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            del user_data_store[user_id]
        
        await query.edit_message_text("❌ PDF merge cancelled.")
        return ConversationHandler.END
    
    elif query.data == "merge_now":
        # Check if we have at least one PDF
        if user_id not in user_data_store or "pdfs" not in user_data_store[user_id] or len(user_data_store[user_id]["pdfs"]) < 1:
            await query.edit_message_text("❗ No PDFs to merge.")
            return ConversationHandler.END
        
        # If we only have one PDF, just return it
        if len(user_data_store[user_id]["pdfs"]) == 1:
            await query.edit_message_text("⚠️ Only one PDF received. No merge needed.")
            pdf_path = user_data_store[user_id]["pdfs"][0]
            
            # Send the file
            with open(pdf_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename=os.path.basename(pdf_path),
                    caption="✅ Here's your PDF!"
                )
            
            # Clean up
            os.remove(pdf_path)
            del user_data_store[user_id]
            return ConversationHandler.END
        
        # Merge PDFs
        await query.edit_message_text("🔄 Merging PDFs...")
        
        try:
            # Generate unique ID for output
            unique_id = str(uuid.uuid4())
            output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_merged.pdf")
            
            # Create directories if not exist
            os.makedirs(CONVERTED_DIR, exist_ok=True)
            
            # Merge PDFs
            pdf_merger = PyPDF2.PdfMerger()
            for pdf_path in user_data_store[user_id]["pdfs"]:
                pdf_merger.append(pdf_path)
            
            # Save merged PDF
            with open(output_path, "wb") as output_file:
                pdf_merger.write(output_file)
            
            # Send the merged file
            with open(output_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename=f"merged_pdf_{unique_id}.pdf",
                    caption=f"✅ Here's your merged PDF! ({len(user_data_store[user_id]['pdfs'])} files combined)"
                )
            
            # Clean up
            for pdf_path in user_data_store[user_id]["pdfs"]:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            
            if os.path.exists(output_path):
                os.remove(output_path)
            
            del user_data_store[user_id]
            
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"PDF merge error: {e}")
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"⚠️ Error merging PDFs: {str(e)}"
            )
            
            # Clean up
            if user_id in user_data_store and "pdfs" in user_data_store[user_id]:
                for pdf_path in user_data_store[user_id]["pdfs"]:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                del user_data_store[user_id]
            
            return ConversationHandler.END
    
    return AWAITING_SECOND_PDF

# PDF Extract Pages functionality
async def extract_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_data_store[user_id] = {}
    
    await update.message.reply_text(
        "✂️ PDF Extract Pages started. Send me the PDF file."
    )
    return AWAITING_PAGE_NUMBERS

async def extract_receive_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    document = update.message.document
    
    if not document or not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❗ Please send a PDF file.")
        return AWAITING_PAGE_NUMBERS
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Create directories if not exist
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    upload_path = os.path.join(TEMP_DIR, f"{unique_id}_{document.file_name}")
    file = await context.bot.get_file(document.file_id)
    await file.download_to_drive(upload_path)
    
    # Save path to user data
    user_data_store[user_id]["pdf_path"] = upload_path
    
    # Get page count
    try:
        with open(upload_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            page_count = len(reader.pages)
            user_data_store[user_id]["page_count"] = page_count
            
            await update.message.reply_text(
                f"✅ Received PDF: {document.file_name} ({page_count} pages)\n\n"
                f"Now, send me the page numbers you want to extract.\n"
                f"Examples:\n"
                f"• 1,3,5 (pages 1, 3, and 5)\n"
                f"• 1-5 (pages 1 through 5)\n"
                f"• 1,3-5,7 (pages 1, 3, 4, 5, and 7)"
            )
            
            return AWAITING_PAGE_NUMBERS
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        await update.message.reply_text(f"⚠️ Error processing PDF: {str(e)}")
        
        # Clean up
        if os.path.exists(upload_path):
            os.remove(upload_path)
        
        if user_id in user_data_store:
            del user_data_store[user_id]
        
        return ConversationHandler.END

async def extract_process_pages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    
    if user_id not in user_data_store or "pdf_path" not in user_data_store[user_id]:
        await update.message.reply_text("❗ Please start over with /extract command.")
        return ConversationHandler.END
    
    page_input = update.message.text.strip()
    
    try:
        # Parse page numbers
        page_numbers = parse_page_numbers(page_input, user_data_store[user_id]["page_count"])
        
        if not page_numbers:
            await update.message.reply_text(
                "❗ Invalid page numbers. Please try again with correct page numbers."
            )
            return AWAITING_PAGE_NUMBERS
        
        # Extract pages
        await update.message.reply_text(f"🔄 Extracting pages {', '.join(map(str, page_numbers))}...")
        
        # Generate unique ID for output
        unique_id = str(uuid.uuid4())
        output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_extracted.pdf")
        
        # Create directories if not exist
        os.makedirs(CONVERTED_DIR, exist_ok=True)
        
        # Extract pages
        pdf_path = user_data_store[user_id]["pdf_path"]
        
        with open(pdf_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            writer = PyPDF2.PdfWriter()
            
            # Add selected pages
            for page_num in page_numbers:
                # Convert to 0-indexed
                writer.add_page(reader.pages[page_num - 1])
            
            # Save extracted PDF
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
        
        # Send the extracted file
        with open(output_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"extracted_pages.pdf",
                caption=f"✅ Here are the extracted pages! ({len(page_numbers)} pages)"
            )
        
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        if os.path.exists(output_path):
            os.remove(output_path)
        
        if user_id in user_data_store:
            del user_data_store[user_id]
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"PDF extract error: {e}")
        await update.message.reply_text(f"⚠️ Error extracting pages: {str(e)}")
        
        # Clean up
        if user_id in user_data_store and "pdf_path" in user_data_store[user_id]:
            if os.path.exists(user_data_store[user_id]["pdf_path"]):
                os.remove(user_data_store[user_id]["pdf_path"])
        
        if user_id in user_data_store:
            del user_data_store[user_id]
        
        return ConversationHandler.END

def parse_page_numbers(page_input: str, max_pages: int) -> List[int]:
    """Parse page numbers from user input."""
    page_numbers = []
    
    # Split by comma
    parts = page_input.split(',')
    
    for part in parts:
        part = part.strip()
        
        # Check if it's a range
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start < 1 or end > max_pages or start > end:
                    return []
                page_numbers.extend(range(start, end + 1))
            except ValueError:
                return []
        else:
            # It's a single page
            try:
                page = int(part)
                if page < 1 or page > max_pages:
                    return []
                page_numbers.append(page)
            except ValueError:
                return []
    
    # Remove duplicates and sort
    return sorted(list(set(page_numbers)))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photos for OCR."""
    photo = update.message.photo[-1]  # Get the largest photo
    
    await update.message.reply_text("🔍 Processing image with OCR...")
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Create directories if not exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    
    image_path = os.path.join(UPLOAD_DIR, f"{unique_id}_photo.jpg")
    file = await context.bot.get_file(photo.file_id)
    await file.download_to_drive(image_path)
    
    try:
        # Extract text from image
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        
        if not text.strip():
            await update.message.reply_text("⚠️ No text could be extracted from this image.")
            return
        
        # Save text to file
        output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_ocr_text.txt")
        with open(output_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)
        
        # Send the extracted text
        await send_converted_file(update, context, output_path, "text/plain")
    except Exception as e:
        logger.error(f"OCR error: {e}")
        await update.message.reply_text(f"⚠️ Error extracting text from image: {str(e)}")
    finally:
        # Cleanup uploaded file
        if os.path.exists(image_path):
            os.remove(image_path)

async def handle_image_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert images to PDF."""
    # Check if it's from a command
    command = False
    if update.message.caption and update.message.caption.startswith("/img2pdf"):
        command = True

    if command:
        # From photo with caption
        if update.message.photo:
            photo = update.message.photo[-1]  # Get the largest photo
            await process_single_image_to_pdf(update, context, photo.file_id)
        # From document with caption
        elif update.message.document:
            document = update.message.document
            if not document.mime_type or not document.mime_type.startswith("image/"):
                await update.message.reply_text("❗ Please send an image file with /img2pdf caption.")
                return
            await process_single_image_to_pdf(update, context, document.file_id)
        else:
            await update.message.reply_text("❗ Please send an image with /img2pdf caption.")
    else:
        # Direct command
        await update.message.reply_text(
            "🖼️ Send me an image with caption /img2pdf to convert it to PDF."
        )

async def process_single_image_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str) -> None:
    """Process a single image to PDF."""
    await update.message.reply_text("🔄 Converting image to PDF...")
    
    # Generate unique filenames
    unique_id = str(uuid.uuid4())
    
    # Create directories if not exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    
    image_path = os.path.join(UPLOAD_DIR, f"{unique_id}_image.jpg")
    output_path = os.path.join(CONVERTED_DIR, f"{unique_id}_image_to_pdf.pdf")
    
    file = await context.bot.get_file(file_id)
    await file.download_to_drive(image_path)
    
    try:
        # Convert image to PDF using img2pdf
        with open(image_path, "rb") as image_file:
            pdf_bytes = img2pdf.convert(image_file)
            
            with open(output_path, "wb") as pdf_file:
                pdf_file.write(pdf_bytes)
        
        # Send the PDF
        await send_converted_file(update, context, output_path, "application/pdf")
    except Exception as e:
        logger.error(f"Image to PDF error: {e}")
        await update.message.reply_text(f"⚠️ Error converting image to PDF: {str(e)}")
    finally:
        # Cleanup uploaded file
        if os.path.exists(image_path):
            os.remove(image_path)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unexpected errors."""
    logger.error(f"Update {update} caused error {context.error}")
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ Unexpected error occurred. Please try again later.")

async def webhook(request: web.Request) -> web.Response:
    """Handle incoming webhook updates from Telegram."""
    update = Update.de_json(await request.json(), application.bot)
    if update:
        await application.process_update(update)
    return web.Response(status=200)

async def setup_application() -> tuple[Application, web.Application]:
    """Set up the Telegram application and aiohttp server."""
    application = Application.builder().token(TOKEN).build()

    # Basic handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Single-command handlers
    application.add_handler(CommandHandler("img2pdf", handle_image_to_pdf))
    
    # Text to PDF conversation handler
    text_to_pdf_handler = ConversationHandler(
        entry_points=[CommandHandler("text2pdf", text_to_pdf_start)],
        states={
            AWAITING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_to_pdf_process)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(text_to_pdf_handler)
    
    # PDF Merge conversation handler
    merge_handler = ConversationHandler(
        entry_points=[CommandHandler("merge", merge_start)],
        states={
            AWAITING_SECOND_PDF: [
                MessageHandler(filters.Document.ALL & ~filters.COMMAND, merge_first_pdf),
                CallbackQueryHandler(merge_pdfs_button, pattern=r"^(merge_now|cancel_merge)$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    application.add_handler(merge_handler)
    
    # PDF Extract Pages conversation handler
    extract_handler = ConversationHandler(
        entry_points=[CommandHandler("extract", extract_start)],
        states={
            AWAITING_PAGE_NUMBERS: [
                MessageHandler(filters.Document.ALL & ~filters.COMMAND, extract_receive_pdf),
                MessageHandler(filters.TEXT & ~filters.COMMAND, extract_process_pages)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    application.add_handler(extract_handler)
    
    # Document handler for file conversions
    application.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, handle_document))
    
    # Photo handler for OCR
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    
    # Error handler
    application.add_error_handler(error_handler)

    # Set up aiohttp server
    app = web.Application()
    app.router.add_post('/webhook', webhook)
    
    return application, app

async def main():
    """Start the bot with webhook."""
    global application
    application, aiohttp_app = await setup_application()
    
    # Set webhook
    await application.bot.set_webhook(url=WEBHOOK_URL)
    
    # Start aiohttp server
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
    await site.start()
    
    print(f"🤖 Bot is running with webhook at {WEBHOOK_URL}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())