import warnings
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import tool
from tools.doc_reader_tools import read_file
from utils import activate_llm

warnings.filterwarnings("ignore")


@tool
def read_document_tool(file_path):
    "Read a file's content(file_path: 'string') - A tool that can be used to read a file's content."
    content = read_file(file_path=file_path)
    return content


@CrewBase
class InterviewerAssistantCrew():
    """Crew to help organize the interview process"""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    llm = activate_llm()
    
    @agent
    def job_descrip_parser(self) -> Agent:
        return Agent(
                config=self.agents_config['job_opportunities_parser'],
                tools=[read_document_tool],
                memory=True,
                verbose=True,
                llm=self.llm,
                # max_iter=3,
                allow_delegation=False
        )

    @agent
    def resume_analyzer(self) -> Agent:
        return Agent(
                config=self.agents_config['resume_reader'],
                tools=[read_document_tool],
                memory=True,
                verbose=False,
                llm=self.llm,
                max_iter=3,
                allow_delegation=False
        )
    
    @agent
    def match_and_scorer(self) -> Agent:
        return Agent(
                config=self.agents_config['candidate_screen_matcher'],
                memory=True,
                verbose=True,
                llm=self.llm,
                max_iter=3,
                allow_delegation=False
        )
    
    @agent
    def assignment_evaluator(self) -> Agent:
        return Agent(
                config=self.agents_config['assignment_evaluator'],
                tools=[read_document_tool],
                memory=True,
                verbose=False,
                llm=self.llm,
                max_iter=3,
                allow_delegation=False
        )
    
    @agent
    def interview_coordinator(self) -> Agent:
        return Agent(
                config=self.agents_config['interview_coordinator'],
                memory=True,
                verbose=False,
                llm=self.llm,
                # max_iter=3,
                allow_delegation=False
        )

    #  TASKS
    @task
    def resume_analysis(self):
        return Task(config=self.tasks_config["read_resume_task"],
        agent=self.resume_analyzer(),
    )

    @task
    def job_descrip_analysis(self):
        return Task(config=self.tasks_config["read_job_descrip_task"],
            agent=self.job_descrip_parser(),
            human_input=True
        )

    @task
    def match_resume_to_job_decrip(self):
        return Task(config=self.tasks_config["match_and_analyze_candidates_task"],
            agent=self.match_and_scorer(),
        )
    
    @task
    def evaluate_takehome_assignment(self):
        return Task(
            config=self.tasks_config["assignment_evaluation_task"],
            agent=self.assignment_evaluator()
        )
    
    @task
    def write_evaluation_report(self):
        return Task(
            config=self.tasks_config["interview_coordination_task"],
            agent=self.interview_coordinator(),
            human_input=True
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Recruitment crew"""
        return Crew(
            agents=[
                    self.job_descrip_parser(), 
                    self.resume_analyzer(),
                    self.match_and_scorer(),
                    self.assignment_evaluator(),
                    self.interview_coordinator()
                    ],
            tasks=[
                   self.job_descrip_analysis(),
                    self.resume_analysis(), 
                    self.match_resume_to_job_decrip(),
                    self.evaluate_takehome_assignment(),
                    self.write_evaluation_report()
                   ],
            process=Process.sequential,
            verbose=2,
        )