import os

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


class LLM:

    def __init__(self):

        # ----------------------------------------------------
        # API KEY
        # ----------------------------------------------------

        api_key = os.getenv(
            "GROQ_API_KEY"
        )

        if not api_key:

            raise ValueError(
                "GROQ_API_KEY is missing from .env"
            )

        # ----------------------------------------------------
        # MODEL
        # ----------------------------------------------------

        self.model = os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-120b"
        )

        # ----------------------------------------------------
        # GROQ CLIENT
        # ----------------------------------------------------

        self.client = Groq(
            api_key=api_key
        )

    # ========================================================
    # GENERATE
    # ========================================================

    def generate(
        self,
        system_prompt,
        user_prompt
    ):
        """
        Send the operational context and candidate plans
        to the LLM.

        The LLM is responsible for reasoning and explaining
        the recommendation.

        Safety thresholds, rest requirements, deadlines,
        and delay calculations should already have been
        determined by the deterministic backend.
        """

        if not system_prompt:
            raise ValueError(
                "system_prompt cannot be empty."
            )

        if not user_prompt:
            raise ValueError(
                "user_prompt cannot be empty."
            )

        try:

            response = (
                self.client
                .chat
                .completions
                .create(

                    model=self.model,

                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],

                    temperature=0.2
                )
            )

        except Exception as e:

            raise RuntimeError(
                f"Groq LLM request failed: {e}"
            ) from e

        # ----------------------------------------------------
        # RESPONSE VALIDATION
        # ----------------------------------------------------

        if not response.choices:

            raise RuntimeError(
                "Groq returned no response choices."
            )

        message = response.choices[
            0
        ].message

        content = message.content

        if not content:

            raise RuntimeError(
                "Groq returned an empty response."
            )

        return content.strip()

