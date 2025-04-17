import os
from langchain_community.tools import TavilySearchResults

os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

tool = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False,
    # name="...",            # overwrite default tool name
    # description="...",     # overwrite default tool description
)