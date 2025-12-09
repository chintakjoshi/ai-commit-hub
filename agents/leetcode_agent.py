import random
import json
from datetime import datetime
from agents.base_agent import BaseAgent, AgentConfig
from typing import Dict

class LeetCodeAgent(BaseAgent):
    def __init__(self, config: AgentConfig, llm_manager, github_manager):
        super().__init__(config, llm_manager, github_manager)
        self.problem_categories = [
            "Array", "String", "Hash Table", "Dynamic Programming",
            "Math", "Sorting", "Greedy", "Depth-First Search",
            "Binary Search", "Database", "Breadth-First Search", "Tree",
            "Matrix", "Two Pointers", "Bit Manipulation", "Stack",
            "Heap", "Graph", "Backtracking", "Sliding Window",
            "Union Find", "Linked List", "Recursion", "Trie",
            "Divide and Conquer", "Monotonic Stack", "Binary Indexed Tree",
            "Segment Tree", "Line Sweep", "Topological Sort"
        ]
        
        self.difficulties = ["Easy", "Medium", "Hard"]
        self.problem_patterns = {
            "problem_and_solution": ["problem", "solution", "test"],
            "problem_only": ["problem"],
            "solution_only": ["solution"],
            "full_solution": ["solution", "test", "explanation"]
        }
    
    async def generate_content(self) -> Dict[str, str]:
        """Generate LeetCode problem and solution based on pattern"""
        
        pattern = self.config.commit_pattern
        difficulty = random.choice(self.difficulties)
        category = random.choice(self.problem_categories)
        
        content_files = {}
        
        if "problem" in pattern or pattern in ["problem_and_solution", "problem_only"]:
            problem_content = await self._generate_problem(difficulty, category)
            content_files.update(problem_content)
        
        if "solution" in pattern or pattern in ["problem_and_solution", "solution_only", "full_solution"]:
            solution_content = await self._generate_solution(
                content_files.get("problem.json", "{}")
            )
            content_files.update(solution_content)
        
        if "test" in pattern or pattern in ["problem_and_solution", "full_solution"]:
            test_content = self._generate_test_files(content_files)
            content_files.update(test_content)
        
        if "explanation" in pattern or pattern == "full_solution":
            explanation_content = await self._generate_explanation(content_files)
            content_files.update(explanation_content)
        
        # Generate README if we have multiple files
        if len(content_files) > 1:
            readme_content = self._generate_readme(content_files, difficulty, category)
            content_files["README.md"] = readme_content
        
        return content_files
    
    async def _generate_problem(self, difficulty: str, category: str) -> Dict[str, str]:
        """Generate problem definition"""
        
        problem_prompt = f"""Create a LeetCode-style coding problem with the following specifications:

Difficulty: {difficulty}
Category: {category}

Requirements:
1. Problem Title: Create a descriptive title
2. Problem Description: Clear description with requirements
3. Examples: At least 3 examples with input/output
4. Constraints: Clear constraints on inputs
5. Follow-up questions: 1-2 follow-up questions (optional)

Format the response as a JSON object with these keys:
- title
- description
- examples (array of objects with input, output, explanation)
- constraints
- follow_up (array of strings)
- difficulty
- category
- hints (array of strings, 2-3 hints)

Make the problem interesting and practical."""

        problem_json = await self.llm.generate_text(
            prompt=problem_prompt,
            system_prompt="You are an expert at creating coding challenges. Create realistic LeetCode-style problems.",
            temperature=0.7
        )
        
        # Clean and parse JSON
        try:
            # Extract JSON if it's wrapped in markdown
            import re
            json_match = re.search(r'\{.*\}', problem_json, re.DOTALL)
            if json_match:
                problem_data = json.loads(json_match.group())
            else:
                problem_data = json.loads(problem_json)
            
            # Ensure all required fields
            if "title" not in problem_data:
                problem_data["title"] = f"{difficulty} {category} Problem"
            if "difficulty" not in problem_data:
                problem_data["difficulty"] = difficulty
            if "category" not in problem_data:
                problem_data["category"] = category
            
            # Create filename from title
            safe_title = problem_data["title"].lower().replace(' ', '_').replace('/', '_')
            filename = f"problems/{safe_title}_{random.randint(1000, 9999)}.json"
            
            return {
                filename: json.dumps(problem_data, indent=2),
                "problem.json": json.dumps(problem_data, indent=2)  # Also keep a generic reference
            }
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            safe_title = f"{difficulty.lower()}_{category.lower()}_problem_{random.randint(1000, 9999)}"
            return {
                f"problems/{safe_title}.txt": problem_json
            }
    
    async def _generate_solution(self, problem_json: str) -> Dict[str, str]:
        """Generate solution for the problem"""
        
        try:
            problem_data = json.loads(problem_json)
            problem_title = problem_data.get("title", "Coding Problem")
            problem_desc = problem_data.get("description", "")
            constraints = problem_data.get("constraints", [])
        except:
            problem_title = "Coding Problem"
            problem_desc = problem_json
            constraints = []
        
        solution_prompt = f"""Solve the following coding problem:

Title: {problem_title}

Description:
{problem_desc}

Constraints:
{json.dumps(constraints, indent=2)}

Provide:
1. Python 3 solution with optimal time/space complexity
2. Explanation of the algorithm
3. Time Complexity: O(?) analysis
4. Space Complexity: O(?) analysis
5. Edge cases considered
6. Alternative approaches (if any)

Format the solution as a JSON object with these keys:
- solution_code (Python code as string)
- explanation (detailed explanation)
- time_complexity (e.g., "O(n)")
- space_complexity (e.g., "O(1)")
- edge_cases (array of strings)
- alternative_approaches (array of objects with name, complexity, pros, cons)"""

        solution_json = await self.llm.generate_text(
            prompt=solution_prompt,
            system_prompt="You are an expert at solving coding problems. Provide optimal solutions with clear explanations.",
            temperature=0.3
        )
        
        try:
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', solution_json, re.DOTALL)
            if json_match:
                solution_data = json.loads(json_match.group())
            else:
                solution_data = json.loads(solution_json)
            
            # Extract code separately
            solution_code = solution_data.get("solution_code", "")
            if not solution_code and "```python" in solution_json:
                # Try to extract from markdown
                code_match = re.search(r'```python(.*?)```', solution_json, re.DOTALL)
                if code_match:
                    solution_code = code_match.group(1).strip()
            
            # Create Python file
            safe_title = problem_title.lower().replace(' ', '_').replace('/', '_')
            solution_filename = f"solutions/{safe_title}_solution.py"
            
            python_content = f'''"""
Solution for: {problem_title}
Difficulty: {problem_data.get('difficulty', 'Unknown')}
Category: {problem_data.get('category', 'Unknown')}

{problem_desc}
"""

{solution_code}

if __name__ == "__main__":
    # Example usage
    solution = Solution()
    print("Solution ready for testing")
'''
            
            return {
                solution_filename: python_content,
                f"solutions/{safe_title}_solution_meta.json": json.dumps(solution_data, indent=2)
            }
            
        except json.JSONDecodeError:
            # Fallback: just save the raw response
            safe_title = problem_title.lower().replace(' ', '_').replace('/', '_')
            return {
                f"solutions/{safe_title}_solution.py": solution_json
            }
    
    def _generate_test_files(self, content_files: Dict[str, str]) -> Dict[str, str]:
        """Generate test files for the solution"""
        
        # Find solution file
        solution_file = None
        solution_content = None
        
        for filename, content in content_files.items():
            if filename.endswith('_solution.py'):
                solution_file = filename
                solution_content = content
                break
        
        if not solution_file or not solution_content:
            return {}
        
        # Extract class name from solution
        import re
        class_match = re.search(r'class\s+(\w+)', solution_content)
        class_name = class_match.group(1) if class_match else "Solution"
        
        test_content = f'''import unittest
import sys
import os

# Add parent directory to path to import solution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solutions.{solution_file.replace('solutions/', '').replace('.py', '')} import {class_name}

class TestSolution(unittest.TestCase):
    def setUp(self):
        self.solution = {class_name}()
    
    def test_example_1(self):
        """Test with example 1 from problem statement"""
        # TODO: Add actual test case
        self.assertTrue(True)
    
    def test_example_2(self):
        """Test with example 2 from problem statement"""
        # TODO: Add actual test case
        self.assertTrue(True)
    
    def test_edge_cases(self):
        """Test edge cases"""
        # TODO: Add edge case tests
        self.assertTrue(True)
    
    def test_large_input(self):
        """Test with large input for performance"""
        # TODO: Add large input test
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main(verbosity=2)
'''
        
        test_filename = f"tests/test_{solution_file.replace('solutions/', '').replace('.py', '')}.py"
        
        return {test_filename: test_content}
    
    async def _generate_explanation(self, content_files: Dict[str, str]) -> Dict[str, str]:
        """Generate detailed explanation of the solution"""
        
        # Find problem and solution metadata
        problem_data = None
        solution_data = None
        
        for filename, content in content_files.items():
            if filename.endswith('problem.json'):
                try:
                    problem_data = json.loads(content)
                except:
                    pass
            elif filename.endswith('_solution_meta.json'):
                try:
                    solution_data = json.loads(content)
                except:
                    pass
        
        if not problem_data:
            return {}
        
        explanation_prompt = f"""Create a detailed explanation for solving this problem:

Problem: {problem_data.get('title', 'Coding Problem')}
Difficulty: {problem_data.get('difficulty', 'Unknown')}
Category: {problem_data.get('category', 'Unknown')}

Description:
{problem_data.get('description', '')}

Provide a comprehensive explanation including:
1. Problem understanding and restatement in your own words
2. Thought process for arriving at the solution
3. Step-by-step walkthrough of the algorithm
4. Visual explanation (describe what diagrams would show)
5. Code walkthrough (line by line explanation)
6. Common mistakes to avoid
7. Related problems to practice
8. Real-world applications (if any)

Format as a well-structured markdown document."""

        explanation = await self.llm.generate_text(
            prompt=explanation_prompt,
            system_prompt="You are an expert educator. Explain coding solutions in a clear, beginner-friendly way.",
            temperature=0.4
        )
        
        safe_title = problem_data.get('title', 'solution').lower().replace(' ', '_').replace('/', '_')
        explanation_filename = f"explanations/{safe_title}_explanation.md"
        
        full_explanation = f"""# Explanation: {problem_data.get('title', 'Coding Problem')}

## Problem Overview
{problem_data.get('description', '')}

## Detailed Explanation
{explanation}

## Key Takeaways
- ...

## Practice Recommendations
1. ...

*Generated by AI LeetCode Agent*
"""
        
        return {explanation_filename: full_explanation}
    
    def _generate_readme(self, content_files: Dict[str, str], difficulty: str, category: str) -> str:
        """Generate README file"""
        
        # Extract problem title
        problem_title = "LeetCode Problem"
        for filename in content_files.keys():
            if filename.endswith('.json') and 'problem' in filename:
                try:
                    content = content_files[filename]
                    data = json.loads(content)
                    if 'title' in data:
                        problem_title = data['title']
                        break
                except:
                    pass
        
        readme_content = f"""# {problem_title}

## Problem Details
- **Difficulty**: {difficulty}
- **Category**: {category}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files
"""
        
        # List all files
        for filename in sorted(content_files.keys()):
            if filename != "README.md":
                readme_content += f"- `{filename}`\n"
        
        readme_content += """
## Solution Approach
Auto-generated solution using AI.

## Testing
Run the tests with:
```bash
python -m pytest tests/
```

## Notes
- This problem and solution were automatically generated by an AI agent
- The solution aims for optimal time and space complexity
- Test cases may need to be completed based on specific problem requirements

## Author
AI LeetCode Agent
"""
        
        return readme_content
    
    def get_commit_message(self, content: Dict[str, str]) -> str:
        """Generate commit message based on content"""
        
        # Try to find problem title
        for filename, file_content in content.items():
            if filename.endswith('.json') and ('problem' in filename or 'meta' in filename):
                try:
                    data = json.loads(file_content)
                    if 'title' in data:
                        return f"Add solution for: {data['title']}"
                    elif 'difficulty' in data and 'category' in data:
                        return f"Add {data['difficulty']} {data['category']} problem"
                except:
                    pass
        
        # Fallback based on file types
        has_problem = any('problem' in fname for fname in content.keys())
        has_solution = any('solution' in fname for fname in content.keys())
        
        if has_problem and has_solution:
            return "Add LeetCode problem with solution"
        elif has_problem:
            return "Add LeetCode problem"
        elif has_solution:
            return "Add LeetCode solution"
        else:
            return "Update LeetCode repository"