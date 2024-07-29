from services import init_google_credentials
from googleapiclient.discovery import build


def read_google_doc(doc_id):
    creds = init_google_credentials(scopes=['https://www.googleapis.com/auth/documents.readonly'])
    service = build('docs', 'v1', credentials=creds)
    document = service.documents().get(documentId=doc_id).execute()
    content = document.get('body').get('content')
    text = ''
    for item in content:
        if 'paragraph' in item:
            elements = item.get('paragraph').get('elements')
            for elem in elements:
                text += elem.get('textRun').get('content')
    return text


if __name__ == "__main__":
    doc_id = '1HAIUP9cLGq3TkZUrxVwjZASJhKInvbzIkc2Ux3N2Q18'
    google_doc_content = read_google_doc(doc_id)
    print("google_doc_content", google_doc_content)