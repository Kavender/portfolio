from docx import Document
import os
import PyPDF2
from crewai_tools import BaseTool


def load_text_from_txt(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def load_text_from_docx(file_path):
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        return f"I encountered an error while trying to read the .docx file: {e}"
    

def load_text_from_pdf(file_path):
    pdf_text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            pdf_text += page.extract_text()
    return pdf_text


def read_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileExistsError(f"{file_path} doesn't exist, failed to load.")
    
    if file_path.endswith('.docx'):
        return load_text_from_docx(file_path)
    elif file_path.endswith('.txt'):
        return load_text_from_txt(file_path)
    elif file_path.endswith('.pdf'):
        return load_text_from_pdf(file_path)
    else:
        raise ValueError("Unsupported file format")


class NewFileReadTool(BaseTool):
    name: str = "Read a local file's content from multiple file type"
    description: str ="""Read a file's content(file_path: 'string') - A tool that can be used to read a file's content."""
    
    def _run(self, file_path: str) -> str:
        return read_file(file_path=file_path)


class DocxReadTool(BaseTool):
    name: str = "Microsoft Word .docx file Reader"
    description: str = """It utilizes python-docx lib to read Microsoft Word (.docx) files. 
    This tool is invaluable for data gathering, information management on the specific file type .docx"""

    def _run(self, file_path: str) -> str:
        return load_text_from_docx(file_path=file_path)