# Interview Assistant Project

Multi-Agent system built with CrewAI to help automate interview process that used to be human dominated.

## Use Cases

1. **Select Candidate & Generate report** - `interview_assistant_crew.py`, which helps evaluate candidate and generate report to facilitate interview process.
2. **Candidate Analysis** - 

 
## Requirement for Google Authentification
Goal: Obtain credential tokens after pass OAuth2.0 outside of Docker 
- Get OAuth2.0 Credentials from Google Cloud Console
    https://cloud.google.com/docs/authentication/getting-started
    or watch this tutorial to walkthrough
    https://www.youtube.com/watch?v=YdhoXrabVAU&list=PL5xptEJQ3SWDWik9kTJhpz4eZPtGFrTbu&index=2
- Review and decide on the scope used to generate OAuth token file:
    https://developers.google.com/gmail/api/auth/scopes
    Modify the default scopes in `generate_auth_token.py` if necessary.
- Set up Virutal Environment that can execute Google OAuth2.0  (python3.9+)
    - cd portfolio/interview_assistant
    - python3 -m venv virtualenv
    - source virtualenv/bin/activate
    - install required libs either using:
        - pip install --upgrade --quiet  google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
        - pip install -qU langchain-google-community[gmail]
    - create temp folder to execute token generation script
        - mkdir virtualenv/temp_project
        - cp src/data/credentials/credentials.json virtualenv/temp_project
        - cp src/services/generate_auth_token.py virtualenv/temp_project
        - cd virtualenv/temp_project
        - python generate_auth_token.py
        - cp virtualenv/temp_project/gmail_token.json src/data/credentials/
        - once done, deactivate the virtual envs
- Update the GOOGLE_APP_TOKEN in .env as the generated token file destination

