import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PAGE_LOAD_WAITS = 3


def login_to_interview_query(driver, login_page_url, login_button_css):
    driver.get(login_page_url)

    email_input = WebDriverWait(driver, PAGE_LOAD_WAITS).until(
    EC.visibility_of_element_located((By.NAME, 'email'))
    )
    password_input = WebDriverWait(driver, PAGE_LOAD_WAITS).until(
    EC.visibility_of_element_located((By.NAME, 'password'))
    )
    
    email_input.clear()
    email_input.send_keys(os.getenv("MY_EMAIL"))
    password_input.clear()
    password_input.send_keys(os.getenv("INTERVIEW_QUERY_PWD"))
    try:
        login_button = WebDriverWait(driver, PAGE_LOAD_WAITS).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, login_button_css))
        )
        login_button.click()
        # login_button = driver.find_element(By.CSS_SELECTOR, 
        #                                    'a.button_button__gKKlC.button_inline__x6ymw.button_md__Rhx_O.button_outline__NR_bV.button_orange__kgblN')
        # login_button.click()
        print("Login button clicked successfully!")
    except Exception as e:
        print(f"Error finding the login button: {e}")


def select_tab(driver, tab_name):
    """ Function to click on a tab based on tab_name provided. """
    try:
        tab = WebDriverWait(driver, PAGE_LOAD_WAITS).until(
            EC.element_to_be_clickable((By.XPATH, 
                                        f"//button[contains(@class, 'tabs_tabButton__qb4ok') and text()='{tab_name}']"))
        )
        tab.click()
        print(f"{tab_name} tab clicked successfully!")
    except Exception as e:
        print(f"Error clicking on {tab_name} tab: {e}")


def extract_content_from_tab(driver, tab_name):
    """ Extracts displayed content from the active tab. """
    select_tab(driver, tab_name)  # Switch to the tab

    # Wait for the content of the tab to load
    content = WebDriverWait(driver, PAGE_LOAD_WAITS).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "text_container_container__h7h20"))
    )
    return content.text