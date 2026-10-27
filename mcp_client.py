import asyncio
import os 
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client 

async def main():
    load_dotenv(".env")
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not github_token:
        raise RuntimeError("Github personal access token is missing.")
    
    server_params = StdioServerParameters(
        command="docker",
        args=[
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "-e",
            "GITHUB_READ_ONLY=1",
            "-e",
            "GITHUB_TOOLSETS",
            "ghcr.io/github/github-mcp-server",
        ],
        env={
            **os.environ,
            "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
            "GITHUB_TOOLSETS": "repos,issues",
            "GITHUB_READ_ONLY": "1",
        },
    )
    
    async with stdio_client(server_params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            
            print("Connected to Github MCP server.")
            
            result = await session.list_tools()
            
            print(f"\nAvaiable tools : {len(result.tools)}")
            
            for tool in result.tools:
                print(f"Name:{tool.name}")
                print(f"Description:{tool.description}")
                print(f"Input Schema:{tool.input_schema}")
                print("-"*40)
                
                
            tool_result = await session.call_tool(
                "search_repositories",
                arguments = {
                    "query":"model context protocol language:Python",
                    "perPage":5,
                },
            )
            
            if tool_result.is_error:
                print("Tool Execution failed.")
            else:
                print("Tool Execution Succeeded.")
                
            for item in tool_result.content:
                if hasattr(item,"text"):
                    print(item.text)
                    
if __name__ == "__main__":
    asyncio.run(main())
                
    