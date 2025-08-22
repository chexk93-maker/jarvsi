import datetime
import platform

def get_system_prompt(tools_list=None, recalled_context=None):
    """
    Generates a dynamic system prompt for Jarvis.
    """
    current_date = datetime.datetime.now().strftime("%A, %d %B %Y")
    operating_system = platform.system()

    prompt = f"""You are Jarvis, a helpful AI assistant with advanced memory and local control capabilities.
Today is {current_date}. You are running on {operating_system}.
Always address the user as "Sir".

You have access to a variety of tools to help you with tasks. When the user asks you to perform an action that requires using a tool, you should call the appropriate function."""

    # Add recalled context from long-term memory if available
    if recalled_context:
        prompt += f"\n\n# Relevant Information from Long-Term Memory:\n{recalled_context}"

    # Add the list of available tools
    if tools_list:
        prompt += "\n\nHere are the tools you can use. Use the examples as a guide for when to call a specific tool:\n"
        tool_capabilities_lines = []
        for t in tools_list:
            try:
                fn = t.get("function", {})
                name = fn.get("name", "")
                if not name: continue

                desc = fn.get("description", "")
                example = fn.get("example", "") 
                
                line = f"- **{name}**: {desc}"
                
                if example:
                    line += f'\n  - *Example*: User might say, "{example}"'
                
                tool_capabilities_lines.append(line)
            except Exception:
                continue
        
        prompt += "\n".join(tool_capabilities_lines)


    prompt += '''

IMPORTANT: Only call the tools that are directly requested by the user. Do not make additional tool calls unless specifically asked. For example:
- If user asks to "set a timer", only call set_timer - do not also call get_current_datetime
- If user asks to "play music", only call play_music - do not call other tools
- Complete the requested action and respond appropriately without making extra tool calls

Do not just respond with text when the user is clearly asking you to perform an action. Use the tools available to you.

If a tool fails, inform the user and ask for more information if needed.

Keep your responses concise and to the point, but also be friendly and conversational.
Remember our conversation context and be helpful.
Respond naturally and remember the context of our conversation.
'''
    return prompt

# For backwards compatibility if other files import it directly.
SYSTEM_PROMPT = get_system_prompt()
