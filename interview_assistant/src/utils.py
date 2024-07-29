import os
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

                                                                                                           # the format for that file is (without the comment)                                                                                                                                       #API_KEYNAME=AStringThatIsTheLongAPIKeyFromSomeService
def load_env():
    _ = load_dotenv(find_dotenv())


def get_env_api_key(api_name: str) -> str:
    load_env()
    api_key = os.getenv(api_name)
    return api_key


def pretty_print_result(result, line_width=120):
  parsed_result = []
  for line in result.split('\n'):
      if len(line) > line_width:
          words = line.split(' ')
          new_line = ''
          for word in words:
              if len(new_line) + len(word) + 1 > line_width:
                  parsed_result.append(new_line)
                  new_line = word
              else:
                  if new_line == '':
                      new_line = word
                  else:
                      new_line += ' ' + word
          parsed_result.append(new_line)
      else:
          parsed_result.append(line)
  return "\n".join(parsed_result)


def activate_llm():
    default_llm_provider = get_env_api_key("DEFAULT_LLM_PROVIDER")

    if default_llm_provider == "openai":
        os.environ["OPENAI_API_KEY"] = get_env_api_key("OPENAI_API_KEY")
        os.environ["OPENAI_ORGANIZATION"] = get_env_api_key("OPENAI_ORGANIZATION")
        llm = ChatOpenAI(model=get_env_api_key("OPENAI_LLM_MODEL"),
                        temperature=get_env_api_key("TEMPERATURE"),
                        tiktoken_model_name=get_env_api_key("OPENAI_TOKENIZER"),
                        max_retries=2,
                        )
    elif default_llm_provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = get_env_api_key("ANTHROPIC_API_KEY")
        llm = ChatAnthropic(model=get_env_api_key("ANTHROPIC_LLM_MODEL"))
    else:
        llm = None
    return llm