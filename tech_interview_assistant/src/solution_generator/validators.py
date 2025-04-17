import re
from typing import Dict, Any, List, Optional, Tuple

class SolutionValidator:
    """
    Class for validating solutions to technical interview questions.
    """
    
    @staticmethod
    def has_code(solution: Dict[str, Any]) -> bool:
        """
        Check if a solution contains code.
        
        Args:
            solution: Solution to check
            
        Returns:
            True if the solution contains code, False otherwise
        """
        # Check if the solution has a candidate
        if "candidate" not in solution:
            return False
        
        candidate = solution["candidate"]
        
        # Check if the candidate is a dictionary with a codebase
        if isinstance(candidate, dict) and "codebase" in candidate:
            codebase = candidate["codebase"]
            # Check if the codebase has code
            if "code" in codebase and codebase["code"]:
                return True
        
        # If the candidate is a string, check if it contains code-like patterns
        if isinstance(candidate, str):
            code_patterns = [
                r'def\s+\w+\s*\(',  # Python function definition
                r'class\s+\w+\s*[:\(]',  # Python class definition
                r'import\s+\w+',  # Python import statement
                r'from\s+\w+\s+import',  # Python from import statement
                r'```python',  # Markdown Python code block
                r'```\s*\n\s*def',  # Markdown code block with function
                r'```\s*\n\s*class'  # Markdown code block with class
            ]
            
            for pattern in code_patterns:
                if re.search(pattern, candidate):
                    return True
        
        return False
    
    @staticmethod
    def extract_code_blocks(text: str) -> List[str]:
        """
        Extract code blocks from text.
        
        Args:
            text: Text to extract code blocks from
            
        Returns:
            List of extracted code blocks
        """
        # Extract markdown code blocks
        markdown_blocks = re.findall(r'```(?:python)?\s*\n(.*?)\n```', text, re.DOTALL)
        
        # If no markdown blocks found, try to extract Python-like code
        if not markdown_blocks:
            # Look for indented blocks that look like Python code
            python_blocks = []
            lines = text.split('\n')
            current_block = []
            in_block = False
            
            for line in lines:
                # Check if line looks like Python code
                if re.match(r'^\s*(def|class|import|from|if|for|while|return|print|#)', line):
                    in_block = True
                    current_block.append(line)
                elif in_block and line.strip() == '':
                    # Empty line might end a block
                    if current_block:
                        python_blocks.append('\n'.join(current_block))
                        current_block = []
                    in_block = False
                elif in_block and line.strip():
                    # Non-empty line in a block
                    current_block.append(line)
            
            # Add the last block if there is one
            if current_block:
                python_blocks.append('\n'.join(current_block))
            
            return python_blocks
        
        return markdown_blocks
    
    @staticmethod
    def validate_python_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Python syntax.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to compile the code
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def check_solution_completeness(solution: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if a solution is complete.
        
        Args:
            solution: Solution to check
            
        Returns:
            Tuple of (is_complete, missing_components)
        """
        missing_components = []
        
        # Check if the solution has a candidate
        if "candidate" not in solution:
            missing_components.append("candidate")
            return False, missing_components
        
        candidate = solution["candidate"]
        
        # Check if the candidate is a dictionary with required components
        if isinstance(candidate, dict):
            required_components = ["codebase"]
            for component in required_components:
                if component not in candidate:
                    missing_components.append(component)
            
            # Check codebase components if present
            if "codebase" in candidate:
                codebase = candidate["codebase"]
                required_codebase_components = ["reasoning", "pseudocode", "code"]
                for component in required_codebase_components:
                    if component not in codebase or not codebase[component]:
                        missing_components.append(f"codebase.{component}")
        
        return len(missing_components) == 0, missing_components
