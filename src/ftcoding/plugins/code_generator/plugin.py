"""Code Generator Plugin - AI-powered code generation and explanation."""
from __future__ import annotations
from typing import Optional
from ftcoding.plugins.base import Plugin, PluginContext
from ftcoding.kernel.llm_gateway import LLMGateway


class CodeGeneratorPlugin(Plugin):
    """Plugin for generating code, explaining code, and suggesting refactors."""

    name = "code_generator"
    version = "0.1.0"
    description = "AI-powered code generation, explanation, and refactoring"

    async def initialize(self, ctx: PluginContext) -> None:
        self.ctx = ctx
        self.llm = LLMGateway(ctx.config)

    async def shutdown(self) -> None:
        pass

    async def handle(self, command: str, payload: dict) -> dict:
        handlers = {
            "generate_function": self._generate_function,
            "generate_class": self._generate_class,
            "explain_code": self._explain_code,
            "refactor": self._refactor,
            "fix_error": self._fix_error,
        }

        handler = handlers.get(command)
        if not handler:
            return {"success": False, "error": f"Unknown command: {command}"}

        return await handler(payload)

    async def _generate_function(self, payload: dict) -> dict:
        """Generate a function from description."""
        description = payload.get("description", "")
        language = payload.get("language", "python")
        function_name = payload.get("name", "")

        if not description:
            return {"success": False, "error": "Description is required"}

        prompt = self._build_function_prompt(description, language, function_name)
        result = await self.llm.generate_code(description, language)

        if result.get("success"):
            return {
                "success": True,
                "code": result["response"],
                "language": language,
                "description": description,
            }
        else:
            # Fallback: generate basic template
            code = self._fallback_function(description, language, function_name)
            return {
                "success": True,
                "code": code,
                "language": language,
                "description": description,
                "fallback": True,
                "error": result.get("error"),
            }

    async def _generate_class(self, payload: dict) -> dict:
        """Generate a class from description."""
        description = payload.get("description", "")
        language = payload.get("language", "python")
        class_name = payload.get("name", "")

        if not description:
            return {"success": False, "error": "Description is required"}

        prompt = f"Generate a {language} class"
        if class_name:
            prompt += f" named '{class_name}'"
        prompt += f" that: {description}\n\nInclude docstrings and type hints."

        result = await self.llm.chat(prompt, temperature=0.2)

        if result.get("success"):
            return {
                "success": True,
                "code": result["response"],
                "language": language,
                "description": description,
            }
        else:
            code = self._fallback_class(description, language, class_name)
            return {
                "success": True,
                "code": code,
                "language": language,
                "description": description,
                "fallback": True,
                "error": result.get("error"),
            }

    async def _explain_code(self, payload: dict) -> dict:
        """Explain what code does."""
        code = payload.get("code", "")
        if not code:
            return {"success": False, "error": "Code is required"}

        prompt = f"""Explain what this code does in simple terms:

```python
{code}
```

Provide:
1. A one-sentence summary
2. Step-by-step explanation
3. Key concepts used"""

        result = await self.llm.chat(prompt, temperature=0.3)

        if result.get("success"):
            return {
                "success": True,
                "explanation": result["response"],
                "code": code,
            }
        else:
            # Simple fallback explanation
            lines = code.strip().split("\n")
            explanation = f"This code has {len(lines)} lines.\n"
            if "def " in code:
                funcs = [l.strip().split("(")[0].replace("def ", "") for l in lines if "def " in l]
                explanation += f"Functions: {', '.join(funcs)}\n"
            if "class " in code:
                classes = [l.strip().split(":")[0].split("(")[0].replace("class ", "") for l in lines if "class " in l]
                explanation += f"Classes: {', '.join(classes)}\n"

            return {
                "success": True,
                "explanation": explanation,
                "code": code,
                "fallback": True,
                "error": result.get("error"),
            }

    async def _refactor(self, payload: dict) -> dict:
        """Suggest refactors for code."""
        code = payload.get("code", "")
        if not code:
            return {"success": False, "error": "Code is required"}

        prompt = f"""Suggest improvements for this code. Focus on:
- Readability
- Performance
- Python best practices

```python
{code}
```

Provide the refactored code and explain the changes."""

        result = await self.llm.chat(prompt, temperature=0.3)

        if result.get("success"):
            return {
                "success": True,
                "suggestions": result["response"],
                "code": code,
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Could not generate refactor suggestions"),
                "code": code,
            }

    async def _fix_error(self, payload: dict) -> dict:
        """Fix an error in code."""
        code = payload.get("code", "")
        error = payload.get("error", "")
        if not code or not error:
            return {"success": False, "error": "Both code and error are required"}

        prompt = f"""Fix this error in the code:

Error: {error}

```python
{code}
```

Provide the fixed code and explain what was wrong."""

        result = await self.llm.chat(prompt, temperature=0.2)

        if result.get("success"):
            return {
                "success": True,
                "fixed_code": result["response"],
                "code": code,
                "error": error,
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Could not fix error"),
                "code": code,
            }

    def _build_function_prompt(self, description: str, language: str, name: str) -> str:
        """Build prompt for function generation."""
        prompt = f"Generate a {language} function"
        if name:
            prompt += f" named '{name}'"
        prompt += f" that: {description}\n\nInclude docstring and type hints."
        return prompt

    def _fallback_function(self, description: str, language: str, name: str) -> str:
        """Generate a basic function template when LLM is unavailable."""
        func_name = name or "generated_function"
        if language == "python":
            return f'''def {func_name}():
    """
    TODO: {description}
    """
    # TODO: Implement this function
    pass
'''
        elif language == "javascript":
            return f'''function {func_name}() {{
    // TODO: {description}
}}
'''
        else:
            return f"# TODO: Implement {func_name}\n# {description}\n"

    def _fallback_class(self, description: str, language: str, name: str) -> str:
        """Generate a basic class template when LLM is unavailable."""
        class_name = name or "GeneratedClass"
        if language == "python":
            return f'''class {class_name}:
    """
    TODO: {description}
    """

    def __init__(self):
        pass
'''
        elif language == "javascript":
            return f'''class {class_name} {{
    constructor() {{
    }}
}}
'''
        else:
            return f"# TODO: Implement {class_name}\n# {description}\n"
