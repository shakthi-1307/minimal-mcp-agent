import asyncio
import json 
import os 
from dotenv import load_dotenv 
from groq import AsyncGroq 
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "openai/gpt-oss-120b"
MAX_TOOL_ROUNDS = 5

ALLOWED_TOOLS = {
    "search_repositories",
    "search_issues",
    "list_issues",
    "issue_read"
}

def validate_arguments(arguments,schema):
    """Basic validation before executing an MCP tool."""
    if not isinstance(arguments,dict):
        raise ValueError("Tool arguments must be JSON object")
    
    properties = schema.get("properties",{})
    required = schema.get("required",[])
    
    missing = [key for key in required if key not in arguments]
    
    if missing:
        raise ValueError(f"Missing required arguments : {missing}")
    
    unknown = set(arguments) - set(properties)
    if unknown:
        raise ValueError(f"Unknown Arguments : {sorted(unknown)}")
    
    for key,value in arguments.items():
        rules = properties[key]
        
        if "enum" in rules and value not in rules["enum"]:
            raise ValueError(f"Invalid value for {key}: {value}")
        
        expected_type = rules.get("type")
        
        if expected_type == "string" and not isinstance(value,str):
            raise ValueError(f"{key} must be a string.")
        
        if (expected_type == "number" or expected_type == "integer") and (
            isinstance(value,bool) or not isinstance(value,(int,float))
        ):
            raise ValueError(f"{key} must be a number.")
        
        if expected_type == "boolean" and not isinstance(value,bool):
            raise ValueError(f"{key} must be a boolean.")
        
        if expected_type == "array" and not isinstance(value,list):
            raise ValueError(f"{key} must be a list.")
    
    return arguments

async def main():
    load_dotenv()
    load_dotenv(".env")
    
    api_key = os.getenv("GROQ_API_KEY")
    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    
    if not api_key:
        raise RuntimeError("GROQ API KEY is missing")
    
    if not github_token:
        raise RuntimeError("Github personal access token is missing")
    
    groq = AsyncGroq(
        api_key = api_key,
        timeout = 60.0,
        max_retries = 0,
    )
    
    server_params = StdioServerParameters(
        command="docker",
        args=[
            "run", "-i", "--rm",
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "-e", "GITHUB_READ_ONLY",
            "-e", "GITHUB_TOOLSETS",
            "ghcr.io/github/github-mcp-server",
        ],
        env={
            **os.environ,
            "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
            "GITHUB_READ_ONLY": "1",
            "GITHUB_TOOLSETS": "repos,issues",
        },
    )
    
    try:
        async with stdio_client(server_params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                
                discovered = await session.list_tools()
                
                mcp_tools = {
                    tool.name:tool 
                    for tool in discovered.tools 
                    if tool.name in ALLOWED_TOOLS
                }
                
                if not mcp_tools:
                    raise RuntimeError("None of the expected tools were exposed by the server.")
                
                
                groq_tools = []

                for tool in mcp_tools.values():
                    groq_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or tool.name,
                            "parameters": tool.input_schema,
                        },
                    })

                print("Tools sent to Groq:")
                for tool_definition in groq_tools:
                    print("-", tool_definition["function"]["name"])

                
                print("Connected to Github MCP Server.")
                print("Tools avaiable to Groq : ",list(mcp_tools))
                
                question = input("\nAsk a github question : ").strip()
                
                if not question:
                    print("Please enter a question.")
                    return 
                
                messages = [
                    {
                        "role":"system",
                        "content": (
                            "You are a GitHub research assistant. "
                            "Use available tools when needed. "
                            "Never invent tool results. "
                            "The tools are read-only. "
                            "If a tool fails, explain the failure."
                            "Do not make your own answers striclty."
                        ),
                    },
                    {"role":"user","content":question}
                ]
                
                for round_numebr in range(MAX_TOOL_ROUNDS):
                    print("Tools sent to Groq:")
                    for tool in groq_tools:
                        print("-", tool["function"]["name"])
                    response = await groq.chat.completions.create(
                        model = MODEL,
                        messages = messages,
                        tools = groq_tools,
                        tool_choice = "auto",
                        temperature = 0,
                        max_completion_tokens=1500,
                    )
                    
                    message = response.choices[0].message
                    messages.append(message.model_dump(exclude_none = True))
                    
                    if not message.tool_calls:
                        print("Agent: ",message.content or "")
                        return 
                    
                    for tool_call in message.tool_calls:
                        name = tool_call.function.name 
                        raw_arguments = tool_call.function.arguments
                        
                        print(f"\nTool requested: {name}")
                        
                        if name not in mcp_tools:
                            result_text = "Error Tool is not allowed"
                        else:
                            try:
                                arguments = json.loads(raw_arguments)
                                
                                arguments = validate_arguments(
                                    arguments,
                                    mcp_tools[name].input_schema,
                                )
                                
                                result = await session.call_tool(
                                    name,
                                    arguments=arguments
                                )
                                print("\n--- RAW MCP TOOL RESULT ---")
                                print(result)
                                print("--- END MCP TOOL RESULT ---\n")
                                
                                result_text = json.dumps(
                                    [
                                        item.model_dump()
                                        for item in result.content
                                    ],
                                    ensure_ascii = False,
                                )
                                
                                if result.is_error:
                                    result_text = f"Tool execution failed: {result.content}"
                                else:
                                    result_text = "\n".join(
                                        item.text
                                        for item in result.content
                                        if hasattr(item, "text")
                                    )
                                    
                            except (json.JSONDecodeError,ValueError) as exc:
                                result_text = f"Invalid tool request: {exc}"
                                
                            
                            except Exception as exc:
                                result_text = (
                                    f"Tool execution failed: "
                                    f"{type(exc).__name__}: {exc}"
                                )
                                
                        messages.append({
                            "role":"tool",
                            "tool_call_id":tool_call.id,
                            "content":result_text[:12000],
                        })
                        
                print(
                    f"\nStopped after {MAX_TOOL_ROUNDS} rounds "
                    "to prevent an unbounded tool-calling loop."
                )

    finally:
        await groq.close()


if __name__ == "__main__":
    asyncio.run(main())

                                