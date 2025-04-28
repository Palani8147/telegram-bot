# Any2Any Telegram Bot

A versatile Telegram bot for converting files between various formats, extracting text from images, compressing PDFs, and more.

![image](https://github.com/user-attachments/assets/d8c117d6-0ea4-4269-b4e0-31fd30b57d87)


## Features

- 📄 **PDF to Text** - Extract text content from PDF files
- 📝 **DOCX to PDF** - Convert Word documents to PDF format
- 🖼️ **Image to Text (OCR)** - Extract text from images using OCR
- 📄 **PDF to Images** - Convert PDF pages to individual JPG images
- 📝 **Text to PDF** - Convert text messages into formatted PDF files
- 🔄 **PDF Merge** - Combine multiple PDF files into a single document
- ✂️ **PDF Extract Pages** - Extract specific pages from a PDF file
- 🔍 **File Information** - Get detailed metadata about files
- 🗜️ **PDF Compression** - Reduce PDF file size
- 🖼️ **Image to PDF** - Convert images to PDF format

## Commands

- `/start` - Welcome message and overview of bot capabilities
- `/help` - Detailed help on how to use the bot
- `/text2pdf` - Convert text to PDF
- `/merge` - Start PDF merging process
- `/extract` - Extract specific pages from a PDF
- `/info` - (Use as caption) Get information about a file
- `/compress` - (Use as caption) Compress a PDF file
- `/pdf2img` - (Use as caption) Convert PDF to images
- `/img2pdf` - (Use as caption) Convert image to PDF

## Usage Examples

### PDF to Text
Simply send a PDF file to the bot, and it will extract the text content.

### DOCX to PDF 
Send a DOCX file to convert it to PDF format.

### Image to Text (OCR)
Send an image (photo or file) to extract text using OCR.

### PDF to Images
Send a PDF with the caption `/pdf2img` to convert it to images.

### Text to PDF
1. Type `/text2pdf`
2. Send the text you want to convert
3. Receive the formatted PDF

### PDF Merge
1. Type `/merge`
2. Send the first PDF file
3. Send additional PDFs or click "Merge Now"
4. Receive the merged PDF

### PDF Extract Pages
1. Type `/extract`
2. Send a PDF file
3. Specify pages to extract (e.g., "1,3-5,7")
4. Receive the new PDF with only those pages

## Installation

### Prerequisites
- Python 3.7+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Tesseract OCR (for image to text functionality)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/any2any-bot.git
cd any2any-bot
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install Tesseract OCR:
   - **Windows**: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt install tesseract-ocr`

4. Create a `.env` file with your bot token:
```
BOT_TOKEN=your_bot_token_here
```

5. Run the bot:
```bash
python main.py
```

## Deployment

### Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Fork this repository to your GitHub account
2. Sign up for [Render](https://render.com/)
3. Create a new Web Service and connect your GitHub repository
4. Set the environment variable `BOT_TOKEN`
5. Deploy!

## Dependencies

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [PyPDF2](https://github.com/py-pdf/PyPDF2) - PDF processing
- [docx2pdf](https://github.com/AlJohri/docx2pdf) - Converting DOCX to PDF
- [pytesseract](https://github.com/madmaze/pytesseract) - OCR functionality
- [pdf2image](https://github.com/Belval/pdf2image) - Converting PDF to images
- [reportlab](https://www.reportlab.com/) - Creating PDFs
- [img2pdf](https://github.com/josch/img2pdf) - Converting images to PDF
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Telegram Bot API](https://core.telegram.org/bots/api)
- All the open-source libraries that made this bot possible

---

Created with ❤️ by [Your Name]
