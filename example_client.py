
"""example_client.py — Minimal demo of calling the download_youtube MCP tool via OpenAI.

Usage:
    python example_client.py <youtube_url>

Requires an OPENAI_API_KEY environment variable.
"""

import asyncio, json, os, sys
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

YT_URL = sys.argv[1] if len(sys.argv) > 1 else ""
MODEL  = "doubao-1-5-pro-32k-250115"
APIKEY = os.getenv("ARK_API_KEY")
BASE   = "https://ark.cn-beijing.volces.com/api/v3"
async def main():
    server = StdioServerParameters(command="uv", args=["run", "video_downloader.py"])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tinfo = await session.list_tools()
            tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in tinfo.tools]

            client = AsyncOpenAI(api_key=APIKEY, base_url=BASE)
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Always call the given tool to handle download requests."},
                {"role": "user", "content": f"Please download this video: {YT_URL}"}
            ]

            resp = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools
            )

            if resp.choices[0].finish_reason == "tool_calls":
                call = resp.choices[0].message.tool_calls[0]
                args = json.loads(call.function.arguments)
                result = await session.call_tool(call.function.name, args)

                messages.append(resp.choices[0].message.model_dump())
                messages.append({
                    "role": "tool",
                    "content": result.content[0].text,
                    "tool_call_id": call.id
                })

                final = await client.chat.completions.create(
                    model=MODEL,
                    messages=messages
                )
            else:
                print("Model did not request tool execution. Full response:", resp)

if __name__ == "__main__":
    asyncio.run(main())
