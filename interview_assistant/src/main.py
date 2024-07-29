from interviewer_crew import InterviewerAssistantCrew


def run_interview():
    crew=InterviewerAssistantCrew().crew()
    result=crew.kickoff(inputs={
    'hiring_team': 'Data Science (R&D)',
    'score_threshold': 80,
    'job_description_path': './src/data/jobs/DS_JD.docx',
    'resume_path': './src/data/candidates/candidate_Resume.pdf',
    'assignment_path': './src/data/candidates/candidate_homework.docx'
    })
    result=crew.kickoff()
    output_file_path = "./src/data/candidates/candidate_eval_report.md"

    # Store the result as a Markdown file
    with open(output_file_path, 'w') as file:
        file.write(result)


if __name__ == "__main__":
    run_interview()
