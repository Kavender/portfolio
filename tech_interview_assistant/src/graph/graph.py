from src.graph.workflow_manager import WorkflowManager

# Create an instance of WorkflowManager
workflow_manager = WorkflowManager()

# Export the graph for langraph studio
workflow = workflow_manager.create_workflow()
graph = workflow.compile()
