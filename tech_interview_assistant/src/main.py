import os
import re
import time
import pandas as pd
from selenium import webdriver
from ipdb import set_trace
from langchain import hub
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain

from services import init_google_credentials
from services.gmail_service import fetch_emails, read_emails_from_senders
from utils.db_utils import initialize_db_connection, build_sql_agent
from utils.utils import (clean_extracted_text, extract_question_from_url, hash_text_to_digits, save_to_csv, batch)
from utils.retrieval_utils import login_to_interview_query, extract_content_from_tab
from utils.constants import QUESTION_PAGE_BUTTON_TEXTS, DB_NAME

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_ORGANIZATION"] = os.getenv("OPENAI_ORGANIZATION")
llm = ChatOpenAI(model=os.getenv("OPENAI_LLM_MODEL"),
                temperature=os.getenv("TEMPERATURE"),
                tiktoken_model_name=os.getenv("OPENAI_TOKENIZER"),
                max_retries=2,
                )

def is_placeholder_content(content):
    # Common placeholder phrases (extend this list based on observations or requirements)
    placeholder_phrases = [
        "Lorem ipsum dolor sit amet",
        "consectetur adipiscing elit",
        "eiusmod tempor incididunt",
        "sunt in culpa qui officia deserunt"
    ]
    # Check if any of the placeholder phrases are in the content
    for phrase in placeholder_phrases:
        if re.search(re.escape(phrase), content, re.IGNORECASE):
            return True
    return False

def collect_questions_from_emails(credentials, sender_lists, limit=1000):
    # emails = fetch_emails(api_resource, sender_address=sender_lists, limit=limit)
    emails = read_emails_from_senders(credentials=credentials,
                                      sender_address=sender_lists,
                                      limit=limit)
    print("emails", len(emails))

    links = []
    for email in emails:
        email_content = email["body"]
        question_match_pattern = r"[-]{80}\s+(.*?)(?=\n[-]{80})"
        solution_link_match = re.search(r'\[(https://www\.interviewquery\.com/questions/.+?solution=true).+?\]', email_content)
        
        question_matches = re.findall(question_match_pattern, email_content, re.DOTALL)
        question = ""
        for match in question_matches:
            # question += re.sub(r'\n+', '\n', match).strip() # remove multiple line breaker
            question += match.strip()
        if "Need a hint first?" in question:
            question, _ = question.split("Need a hint first", 1)
        question_page_link = solution_link_match.group(1) if solution_link_match else "Solution link not found."
        # print("Question:", question)
        # print("Page Link:", question_page_link)
        links.append((question_page_link, question))
    
    return pd.DataFrame(links, columns=["link", "question_content"])

### collecting all qa set
    ## daily or weekly updated to process all recent email from last updated date

### use the full qa set as knowledge base to build conversational bot as mock interview
    # use streamlit ui

# TODO:
# 1. ADD SOLUTION_VALIDATION LOGIC TO REWRITE THE SOLUTION IF INCORRECT OR MISSING
# 2. STORE VALID QUESTION & ANSWER PAIRS PER BATCH INTO DB


if __name__ == "__main__":
    # topic_lists = ["data science", "llm", "machine learning"]
    columns_iq_scrapped = ["id_question", "url", "question_abbr", "question", "solution"]
    fname_question_store = "./src/data/question_store.csv"
    fname_gmail_question_links = "./src/data/iq_email_links.csv"
    # let's start with known sender list
    sender_lists = ["Interview Query <team@interviewquery.com>"]
    credentials = init_google_credentials()
    
    if os.path.exists(fname_gmail_question_links):
        email_questions = pd.read_csv(fname_gmail_question_links, header=0)
    else:
        email_questions = collect_questions_from_emails(credentials, sender_lists, limit=1000)
        save_to_csv(email_questions, fname_gmail_question_links)
    print(email_questions.head(5))
   
    login_page_url = "https://www.interviewquery.com/login"
    login_page_button = "div.button_inner__6ximl.button_center__HXCC_"
    
    driver = webdriver.Chrome()
    login_to_interview_query(driver, login_page_url, login_page_button)


    links = email_questions['link'].tolist()
    for batch_link in batch(links, batch_size=5):
        link_qa_extracted = []
        for link in batch_link:
            try:
                driver.get(link)
                question = extract_question_from_url(link)
                print("navigating to page", link)
                hash_id = hash_text_to_digits(question, num_digits=4)
                question_content = extract_content_from_tab(driver=driver, tab_name="Question")
                question_content = clean_extracted_text(question_content, QUESTION_PAGE_BUTTON_TEXTS)
                solution_content = extract_content_from_tab(driver=driver, tab_name="Solution")
                if is_placeholder_content(solution_content):
                    solution_content = ""
                    login_to_interview_query(driver, login_page_url, login_page_button)
                print("Question Content:", question_content)
                print("Solution Content:", solution_content)
                print("-----")
                time.sleep(5)
                link_qa_extracted.append([hash_id, link, question, question_content, solution_content])
            except Exception as e:
                print(f"{link} is unavailable to extract, {e}")
        df_qa_extracted = pd.DataFrame(link_qa_extracted, columns=columns_iq_scrapped)
        save_to_csv(df_qa_extracted, fname_question_store)
        print(f"done crawling one batch w {df_qa_extracted.shape} stored")

    # df_qa_extracted = pd.read_csv(fname_question_store)
    # print("total question/solution mined", df_qa_extracted.shape, df_qa_extracted.columns, df_qa_extracted.head(5))

    # question = df_qa_extracted["question"].values()[0]
    # print("question", question)
    exit()
    db, connection = initialize_db_connection(db_name=DB_NAME)
    # df_qa_extracted.to_sql(name="interview_query_questions", con=connection)

    prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
    system_message = prompt_template.format(dialect="SQLite", top_k=5)
    agent_executor = build_sql_agent(db, llm, system_message=system_message)
    
    example_query = "What skills does the ds tech question pools listed?"

    events = agent_executor.stream(
        {"messages": [("user", example_query)]},
        stream_mode="values",
    )
    for event in events:
        event["messages"][-1].pretty_print()
