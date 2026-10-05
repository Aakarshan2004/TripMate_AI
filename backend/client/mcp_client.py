import os
import shutil
import sys
from pathlib import Path
from typing import Any
import asyncio
import certifi

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient


# =========================================================
# Environment setup
# =========================================================

# D:\Tripmate_Ai\backend\client
BASE_DIR = Path(__file__).resolve().parent

# Project root:
# D:\Tripmate_Ai
PROJECT_ROOT = BASE_DIR.parent.parent

# Load .env from project root
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()


os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


# =========================================================
# API Keys
# =========================================================

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

AVIATION_STACK_API_KEY = (
    os.getenv("AVIATION_STACK_API_KEY")
    or os.getenv("AVIATIONSTACK_API_KEY")
)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# =========================================================
# Paths / commands
# =========================================================

WEATHER_SERVER_PATH = BASE_DIR / "weather_mcp.py"

UVX_COMMAND = shutil.which("uvx") or "uvx"


def _require_env(
    name: str,
    value: str | None,
) -> str:
    """Return an environment value or raise a readable setup error."""

    if not value:
        raise RuntimeError(
            f"{name} is missing. "
            f"Add {name}=your_key to the project .env file."
        )

    return value


def _subprocess_env(
    **updates: str | None,
) -> dict[str, str]:
    """
    Preserve the current Windows/Conda environment
    and add MCP API keys.
    """

    env = os.environ.copy()

    for key, value in updates.items():
        if value:
            env[key] = value

    return env


# =========================================================
# LLM
# =========================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=_require_env(
        "GROQ_API_KEY",
        GROQ_API_KEY,
    ),
    max_tokens=256,
)


# =========================================================
# MCP Client
# =========================================================

client = MultiServerMCPClient(
    {
        # -------------------------------------------------
        # Tavily MCP
        # -------------------------------------------------
        "tavily": {
            "transport": "streamable_http",
            "url": (
                "https://mcp.tavily.com/mcp/"
                f"?tavilyApiKey={TAVILY_API_KEY or ''}"
            ),
        },

        # -------------------------------------------------
        # AviationStack MCP
        # -------------------------------------------------
        "aviationstack": {
            "transport": "stdio",
            "command": UVX_COMMAND,
            "args": [
                "--with",
                "mcp<2",
                "aviationstack-mcp",
            ],
            "env": _subprocess_env(
                AVIATION_STACK_API_KEY=AVIATION_STACK_API_KEY,
            ),
        },

        # -------------------------------------------------
        # Weather MCP
        # -------------------------------------------------
        "weather": {
            "transport": "stdio",

            # Current Python environment
            "command": sys.executable,

            # D:\Tripmate_Ai\backend\client\weather_mcp.py
            "args": [
                str(WEATHER_SERVER_PATH),
            ],

            "env": _subprocess_env(
                OPENWEATHER_API_KEY=OPENWEATHER_API_KEY,
            ),
        },
    }
)


# =========================================================
# Load one MCP tool
# =========================================================

async def _get_server_tool(
    server_name: str,
    tool_name: str,
):
    """
    Load one tool from one MCP server.
    """

    if server_name == "tavily":

        _require_env(
            "TAVILY_API_KEY",
            TAVILY_API_KEY,
        )

    elif server_name == "aviationstack":

        _require_env(
            "AVIATION_STACK_API_KEY",
            AVIATION_STACK_API_KEY,
        )

        if shutil.which("uvx") is None:
            raise RuntimeError(
                "uvx was not found. "
                "Install uv, reopen the terminal, "
                "activate the environment, and run "
                "`uvx --version`."
            )

    elif server_name == "weather":

        _require_env(
            "OPENWEATHER_API_KEY",
            OPENWEATHER_API_KEY,
        )

        if not WEATHER_SERVER_PATH.is_file():
            raise FileNotFoundError(
                f"Weather MCP server not found: "
                f"{WEATHER_SERVER_PATH}"
            )

    # Load only requested MCP server
    tools = await client.get_tools(
        server_name=server_name,
    )

    tool = next(
        (
            item
            for item in tools
            if item.name == tool_name
        ),
        None,
    )

    if tool is None:

        available_tools = (
            ", ".join(
                sorted(
                    item.name
                    for item in tools
                )
            )
            or "none"
        )

        raise RuntimeError(
            f"MCP tool '{tool_name}' was not found "
            f"on server '{server_name}'. "
            f"Available tools: {available_tools}"
        )

    return tool


# =========================================================
# MCP connection + schema test
# =========================================================

async def get_all_tools() -> None:
    """
    Test every MCP server and print each tool's
    input schema.

    This helps us understand exactly which arguments
    each AviationStack tool expects.
    """

    for server_name in (
        "tavily",
        "aviationstack",
        "weather",
    ):

        try:

            tools = await client.get_tools(
                server_name=server_name,
            )

            print(f"\n{'=' * 70}")
            print(f"SERVER: {server_name}")
            print(f"{'=' * 70}")

            for tool in tools:

                print(f"\nTool: {tool.name}")

                description = getattr(
                    tool,
                    "description",
                    None,
                )

                if description:
                    print(
                        f"Description: {description}"
                    )

                # Print the arguments expected by
                # this MCP tool.
                args_schema = getattr(
                    tool,
                    "args",
                    None,
                )

                print(
                    f"Input schema: {args_schema}"
                )

        except Exception as exc:

            print(
                f"\n{server_name}: FAILED -> "
                f"{type(exc).__name__}: {exc}"
            )


# =========================================================
# Tavily MCP
# =========================================================

async def tavily_mcp_search(
    query: str,
):
    search_tool = await _get_server_tool(
        "tavily",
        "tavily_search",
    )

    return await search_tool.ainvoke(
        {
            "query": query,
        }
    )


# =========================================================
# AviationStack MCP
# =========================================================

async def aviation_mcp_call(
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
):
    aviation_tool = await _get_server_tool(
        "aviationstack",
        tool_name,
    )

    return await aviation_tool.ainvoke(
        tool_args or {}
    )


# =========================================================
# Weather MCP
# =========================================================

async def weather_mcp_search(
    city: str,
):
    weather_tool = await _get_server_tool(
        "weather",
        "get_current_weather",
    )

    return await weather_tool.ainvoke(
        {
            "city": city,
        }
    )


async def forecast_mcp_search(
    city: str,
):
    forecast_tool = await _get_server_tool(
        "weather",
        "get_forecast",
    )

    return await forecast_tool.ainvoke(
        {
            "city": city,
        }
    )


# =========================================================
# Destination extractor
# =========================================================

def extract_destination(
    query: str,
) -> str:

    prompt = f"""
Extract only the destination city or country
from the travel request.

Travel request:
{query}

Return only the destination name.
Do not add any explanation.
"""

    response = llm.invoke(prompt)

    destination = str(
        response.content
    ).strip()

    if not destination:
        raise ValueError(
            "The destination could not be extracted."
        )

    return destination


# =========================================================
# Local test
# =========================================================

if __name__ == "__main__":
    asyncio.run(get_all_tools())