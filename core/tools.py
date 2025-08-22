import asyncio
import json
from datetime import datetime
from tools.music import get_tools as get_music_tools, get_handlers as get_music_handlers
from tools.weather import get_tools as get_weather_tools, get_handlers as get_weather_handlers
from tools.window_ctrl import get_tools as get_window_tools, get_handlers as get_window_handlers
from tools.file_opener import get_tools as get_file_tools, get_handlers as get_file_handlers
from tools.web_search import get_tools as get_web_tools, get_handlers as get_web_handlers
from tools.keyboard_ctrl import get_tools as get_keyboard_tools, get_handlers as get_keyboard_handlers
from tools.reminder import get_tools as get_reminder_tools, get_handlers as get_reminder_handlers
from tools.memory import get_tools as get_memory_tools, get_handlers as get_memory_handlers
from tools.timer import get_tools as get_timer_tools, get_handlers as get_timer_handlers
from tools.learning_system import get_tools as get_learning_tools, get_handlers as get_learning_handlers

def get_all_tools():
    """Get all available tools for the LLM"""
    tools = []
    
    # Import and add all tool definitions
    from tools.music import get_tools as get_music_tools
    from tools.weather import get_tools as get_weather_tools
    from tools.window_ctrl import get_tools as get_window_tools
    from tools.file_opener import get_tools as get_file_tools
    from tools.web_search import get_tools as get_web_tools
    from tools.keyboard_ctrl import get_tools as get_keyboard_tools
    from tools.reminder import get_tools as get_reminder_tools
    from tools.memory import get_tools as get_memory_tools
    from tools.timer import get_tools as get_timer_tools
    from tools.learning_system import get_tools as get_learning_tools

    # Add all tools
    tools.extend(get_music_tools())
    tools.extend(get_weather_tools())
    tools.extend(get_window_tools())
    tools.extend(get_file_tools())
    tools.extend(get_web_tools())
    tools.extend(get_keyboard_tools())
    tools.extend(get_reminder_tools())
    tools.extend(get_memory_tools())
    tools.extend(get_timer_tools())
    tools.extend(get_learning_tools())

    return tools

def get_all_handlers():
    """Get all tool handlers from all modules"""
    handlers = {}
    handlers.update(get_music_handlers())
    handlers.update(get_weather_handlers())
    handlers.update(get_window_handlers())
    handlers.update(get_file_handlers())
    handlers.update(get_web_handlers())
    handlers.update(get_keyboard_handlers())
    handlers.update(get_reminder_handlers())
    handlers.update(get_memory_handlers())
    handlers.update(get_timer_handlers())
    handlers.update(get_learning_handlers())
    return handlers

async def handle_tool_call(tool_name, tool_args):
    """Handle tool calls with proper async execution and learning integration"""
    import time
    from tools.learning_system import record_task_execution, get_suggestions, get_troubleshooting_help, get_advanced_suggestions, predict_success_probability
    
    handlers = get_all_handlers()
    
    if tool_name not in handlers:
        return f"Tool {tool_name} not found. Available tools: {list(handlers.keys())}"
    
    # Record execution start for learning
    start_time = time.time()
    user_request = tool_args.get('user_request', '') if isinstance(tool_args, dict) else ''
    
    try:
        # Parse arguments if they're a JSON string
        if isinstance(tool_args, str):
            args = json.loads(tool_args)
        elif isinstance(tool_args, dict):
            args = tool_args.copy()
        else:
            args = {}
        
        # Apply advanced learned optimal parameters if available (do not overwrite explicit user args)
        try:
            # Get advanced suggestions with context
            context = {
                "time_of_day": datetime.now().hour,
                "day_of_week": datetime.now().weekday(),
                "complexity": "moderate" if len(user_request.split()) < 15 else "complex"
            }
            advanced_suggestions = get_advanced_suggestions(tool_name, context)
            
            # Apply adaptive parameters
            if advanced_suggestions.get("adaptive_parameters"):
                for key, value in advanced_suggestions["adaptive_parameters"].items():
                    if key not in args or args.get(key) in (None, "", []):
                        args[key] = value
            
            # Also apply basic suggestions as fallback
            learned = get_suggestions(tool_name)
            for s in learned.get("suggestions", []):
                if s.get("type") == "optimal_parameters":
                    for key, values in s.get("data", {}).items():
                        if key not in args or args.get(key) in (None, "", []):
                            # Use the first known-good value
                            if isinstance(values, list) and values:
                                args[key] = values[0]
        except Exception:
            pass

        handler = handlers[tool_name]
        
        # Execute handler based on whether it's async or sync
        if asyncio.iscoroutinefunction(handler):
            result = await handler(**args)
        else:
            # Run sync function in executor to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: handler(**args)
            )
        
        # Record successful execution
        execution_time = time.time() - start_time
        record_task_execution(tool_name, user_request, args, True, execution_time)
        
        return result
        
    except Exception as e:
        # First failure encountered
        error_message = str(e)

        # Try targeted single retry based on advanced troubleshooting and success prediction
        retry_result = None
        did_retry = False
        try:
            # Predict success probability for retry
            context = {
                "time_of_day": datetime.now().hour,
                "day_of_week": datetime.now().weekday(),
                "complexity": "moderate" if len(user_request.split()) < 15 else "complex"
            }
            success_prob = predict_success_probability(tool_name, args, context)
            
            steps = get_troubleshooting_help(tool_name, error_message)
            # Advanced heuristics for retry decision
            # - For network/timeouts: short backoff then retry
            # - For other errors: retry if success probability is reasonable (>30%)
            transient = any(k in error_message.lower() for k in ["timeout", "connection", "network", "temporar"]) 
            should_retry = transient or success_prob > 0.3
            
            if should_retry:
                did_retry = True
                await asyncio.sleep(0.75)
                if asyncio.iscoroutinefunction(handlers[tool_name]):
                    retry_result = await handlers[tool_name](**args)
                else:
                    retry_result = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: handlers[tool_name](**args)
                    )
        except Exception:
            retry_result = None

        if did_retry and retry_result is not None:
            # Record success after retry
            execution_time = time.time() - start_time
            record_task_execution(tool_name, user_request, args, True, execution_time)
            return retry_result

        # Record failed execution (after optional retry)
        execution_time = time.time() - start_time
        record_task_execution(tool_name, user_request, args, False, execution_time, error_message)

        # Return helpful error with top troubleshooting hints
        try:
            tips = get_troubleshooting_help(tool_name, error_message)[:3]
            if tips:
                return f"Error executing {tool_name}: {error_message}. Try: " + "; ".join(tips)
        except Exception:
            pass
        return f"Error executing {tool_name}: {error_message}"
