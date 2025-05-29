import re
import ast
import json
from langchain_core.outputs import Generation
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser


class CustomPydanticOutputParser(PydanticOutputParser):
    """
    Custom parser for handling various LLM output formats.
    Provides robust JSON parsing capabilities to handle Python dict-like syntax
    and other common JSON formatting issues.
    """
    
    def parse_result(self, result):
        """
        Parse the result from the LLM with enhanced error handling.
        
        Args:
            result: Result from the LLM
            
        Returns:
            Parsed result
        """
        # Extract and clean the text
        text = self._clean_text(result[0].text)
        
        if text.lower().startswith("null"):
            return None
        
        # Extract JSON object
        text = self._extract_json_object(text)
        
        # Normalize to valid JSON
        text = self._normalize_to_json(text)
        
        # Try parsing with multiple strategies
        try:
            return super().parse_result([Generation(text=text)])
        except Exception as exc:
            try:
                # Try with our robust JSON parsing
                data = self._robust_json_parse(text)
                if data:
                    return self.pydantic_object.parse_obj(data)
                else:
                    raise OutputParserException(
                        f"Failed to parse output: {str(exc)}", llm_output=result
                    ) from exc
            except Exception as e:
                raise OutputParserException(
                    f"Failed to parse output: {str(e)}", llm_output=result
                ) from e
    
    def _clean_text(self, text):
        """
        Clean the text by removing code blocks and language identifiers.
        
        Args:
            text: Raw text from LLM
            
        Returns:
            Cleaned text
        """
        text = text.replace("```", "")
        text = text.replace("json", "")
        text = text.replace("python", "")
        return text.strip()
    
    def _extract_json_object(self, text):
        """
        Extract a JSON object from text.
        
        Args:
            text: Text that may contain a JSON object
            
        Returns:
            Extracted JSON object text
        """
        # Try to find the first complete JSON object in the text
        json_pattern = re.compile(r'(\{(?:[^{}]|(?:\{[^{}]*\}))*\})', re.DOTALL)
        match = json_pattern.search(text)
        
        if match:
            return match.group(1)
        
        # If no JSON object found, try to extract anything between { and }
        if '{' in text and '}' in text:
            start = text.find('{')
            end = text.rfind('}') + 1
            return text[start:end]
        
        return text
    
    def _normalize_to_json(self, text):
        """
        Normalize text to valid JSON format.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized JSON text
        """
        # Replace single quotes with double quotes for property names
        text = re.sub(r"'([^']+)':", r'"\1":', text)
        
        # Replace single quotes with double quotes for all string values
        text = re.sub(r"'([^']*)'", r'"\1"', text)
        
        # Add quotes around unquoted property names
        text = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', text)
        
        # Clean up any potential double replacements
        text = text.replace('""', '"')
        
        # Clean up any escaped characters
        text = re.sub(r'\\([^"\\/bfnrt])', r'\\\\\1', text)
        
        return text

    def _robust_json_parse(self, text):
        """
        Robust JSON parsing with multiple fallback strategies.
        
        Args:
            text: JSON-like text to parse
            
        Returns:
            Parsed JSON object or None if parsing failed
        """
        # Strategy 1: Direct JSON parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Use ast.literal_eval for Python literals
        try:
            return ast.literal_eval(text)
        except (SyntaxError, ValueError):
            pass
        
        # Strategy 3: Convert Python dict to JSON
        try:
            # Use json.dumps to ensure proper JSON formatting
            python_obj = ast.literal_eval(text)
            json_str = json.dumps(python_obj)
            return json.loads(json_str)
        except:
            pass
        
        # Strategy 4: More aggressive replacements
        try:
            # Replace all remaining single quotes
            text = text.replace("'", '"')
            return json.loads(text)
        except:
            pass
        
        # Strategy 5: Try to fix common JSON syntax errors
        try:
            # Fix trailing commas in arrays and objects
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*]', ']', text)
            return json.loads(text)
        except:
            return None