"""Unified LLM gateway supporting local and remote providers."""
from __future__ import annotations
from typing import AsyncIterator, Optional
from ftcoding.kernel.config import Config


class LLMGateway:
    """Gateway for LLM calls with fallback support."""

    def __init__(self, config: Config):
        self.config = config
        self.provider = config.llm_provider
        self.model = config.llm_model
        self.api_base = config.llm_api_base
        self.api_key = config.llm_api_key

    def _build_messages(self, prompt: str, system: Optional[str] = None) -> list[dict]:
        """Build message list for chat completion."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> dict:
        """Send chat request and return response."""
        try:
            if self.provider == "ollama":
                return await self._chat_ollama(prompt, system, temperature, max_tokens)
            else:
                return await self._chat_litellm(prompt, system, temperature, max_tokens)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": None
            }

    async def _chat_ollama(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> dict:
        """Chat via local Ollama API."""
        import aiohttp

        messages = self._build_messages(prompt, system)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_base}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return {
                            "success": False,
                            "error": f"Ollama error {resp.status}: {text}",
                            "response": None
                        }
                    data = await resp.json()
                    return {
                        "success": True,
                        "response": data.get("message", {}).get("content", ""),
                        "model": self.model
                    }
            except aiohttp.ClientConnectorError:
                return {
                    "success": False,
                    "error": "Ollama not running. Start it with: ollama serve",
                    "response": None
                }

    async def _chat_litellm(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> dict:
        """Chat via LiteLLM (OpenAI-compatible)."""
        try:
            import litellm
            litellm.set_verbose = False

            messages = self._build_messages(prompt, system)
            response = await litellm.acompletion(
                model=f"{self.provider}/{self.model}" if self.provider != "openai" else self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_base=self.api_base,
                api_key=self.api_key
            )

            return {
                "success": True,
                "response": response.choices[0].message.content,
                "model": self.model
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": None
            }

    async def stream_chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """Stream chat responses."""
        result = await self.chat(prompt, system, temperature)
        if result["success"]:
            yield result["response"]
        else:
            yield f"Error: {result['error']}"

    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[str] = None
    ) -> dict:
        """Generate code from description."""
        system = f"You are an expert {language} developer. Generate clean, well-documented code."
        prompt = f"Generate {language} code for: {description}"
        if context:
            prompt += f"\n\nContext:\n{context}"

        return await self.chat(prompt, system=system, temperature=0.2)
