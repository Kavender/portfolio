# Interview Assistant Project

    Multi-Agent system built with CrewAI to help automate interview process that used to be human dominated.
    - version: 0.2.0 
    - lastest update: 2024-8
    - snap on Miro workflow
<img src="simple_sequential_interview_assistant.png" width="500" height="400" alt="GitHub Logo">


## Use Cases 
    
**Select Candidate & Generate report**
    - `interview_assistant_crew.py`, which helps evaluate candidate and generate report to facilitate interview process.
    - executed with `python src/main.py` after `make sh` into the container

## Other useful tips
### automatic identify dependency file versions
    `pip freeze -q -r requirements.txt | sed '/freeze/,$ d' > requirements-froze.txt`
Credits to https://stackoverflow.com/questions/32390291/pip-freeze-for-only-project-requirements

### Use Llama3.1model as llm instead of paid service
    Tool calling is newly added feature in llama3.1 model with STOA on multiple benchmarks.
    Either run with Ollama setup locally or connect to groq
