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

if __name__ == "__main__":
    asyncio.run(main())
                
    