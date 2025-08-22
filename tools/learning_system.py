import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import re
from collections import defaultdict, Counter
import statistics

# --- Configuration ---
_LEARNING_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "memory_db")
os.makedirs(_LEARNING_DB_DIR, exist_ok=True)
_TASK_HISTORY_FILE = os.path.join(_LEARNING_DB_DIR, "task_history.json")
_PATTERNS_FILE = os.path.join(_LEARNING_DB_DIR, "execution_patterns.json")
_ADVANCED_PATTERNS_FILE = os.path.join(_LEARNING_DB_DIR, "advanced_patterns.json")


class AdvancedLearningSystem:
    def __init__(self):
        self.task_history = self._load_json(_TASK_HISTORY_FILE, [])
        self.execution_patterns = self._load_json(_PATTERNS_FILE, {})
        self.advanced_patterns = self._load_json(_ADVANCED_PATTERNS_FILE, {
            "context_patterns": {},
            "error_patterns": {},
            "performance_predictions": {},
            "cross_tool_insights": {},
            "adaptive_parameters": {},
            "user_preferences": {},
            "system_health": {}
        })

    def _load_json(self, path: str, default: Any) -> Any:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ [LEARNING] Failed to load {path}: {e}")
        return default

    def _save_json(self, path: str, data: Any) -> None:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"⚠️ [LEARNING] Failed to save {path}: {e}")

    def record_task_execution(self, tool_name: str, user_request: str, parameters: Dict[str, Any], 
                            success: bool, execution_time: float, error_message: str = None, 
                            context: Dict[str, Any] = None) -> str:
        """Record a task execution with advanced learning features"""
        task_record = {
            "tool_name": tool_name,
            "user_request": user_request,
            "parameters": parameters,
            "timestamp": time.time(),
            "success": success,
            "execution_time": execution_time,
            "error_message": error_message,
            "context": context or {},
            "time_of_day": datetime.now().hour,
            "day_of_week": datetime.now().weekday(),
            "request_complexity": self._analyze_request_complexity(user_request),
            "parameter_count": len(parameters)
        }

        self.task_history.append(task_record)
        
        # Keep only last 1000 executions for advanced analysis
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-1000:]
        
        # Update all pattern types
        self._update_basic_patterns(task_record)
        self._update_advanced_patterns(task_record)
        
        self._save_data()
        
        print(f"🧠 [ADVANCED LEARNING] Recorded {tool_name}: {'✅' if success else '❌'}")
        return "recorded"

    def _analyze_request_complexity(self, request: str) -> str:
        """Analyze request complexity for context learning"""
        word_count = len(request.split())
        if word_count < 5:
            return "simple"
        elif word_count < 15:
            return "moderate"
        else:
            return "complex"

    def _update_basic_patterns(self, task_record: Dict[str, Any]):
        """Update basic execution patterns (existing logic)"""
        tool_name = task_record["tool_name"]
        
        if tool_name not in self.execution_patterns:
            self.execution_patterns[tool_name] = {
                "success_count": 0,
                "total_count": 0,
                "avg_time": 0,
                "common_errors": {},
                "successful_params": {}
            }
        
        pattern = self.execution_patterns[tool_name]
        pattern["total_count"] += 1
        
        if task_record["success"]:
            pattern["success_count"] += 1
            
            # Track successful parameters
            for key, value in task_record["parameters"].items():
                if key not in pattern["successful_params"]:
                    pattern["successful_params"][key] = []
                if value not in pattern["successful_params"][key]:
                    pattern["successful_params"][key].append(value)
        else:
            # Track errors
            error_type = "unknown"
            if task_record["error_message"]:
                if "connection" in task_record["error_message"].lower():
                    error_type = "network_error"
                elif "file" in task_record["error_message"].lower():
                    error_type = "file_error"
                elif "permission" in task_record["error_message"].lower():
                    error_type = "permission_error"
            
            pattern["common_errors"][error_type] = pattern["common_errors"].get(error_type, 0) + 1
        
        # Update average time
        recent_times = [t["execution_time"] for t in self.task_history[-50:] 
                       if t["tool_name"] == tool_name and t["success"]]
        if recent_times:
            pattern["avg_time"] = sum(recent_times) / len(recent_times)

    def _update_advanced_patterns(self, task_record: Dict[str, Any]):
        """Update advanced learning patterns"""
        tool_name = task_record["tool_name"]
        
        # 1. Context Patterns
        context_key = f"{task_record['time_of_day']}_{task_record['day_of_week']}_{task_record['request_complexity']}"
        if "context_patterns" not in self.advanced_patterns:
            self.advanced_patterns["context_patterns"] = {}
        if context_key not in self.advanced_patterns["context_patterns"]:
            self.advanced_patterns["context_patterns"][context_key] = {"success": 0, "total": 0}
        
        self.advanced_patterns["context_patterns"][context_key]["total"] += 1
        if task_record["success"]:
            self.advanced_patterns["context_patterns"][context_key]["success"] += 1

        # 2. Error Pattern Recognition
        if not task_record["success"] and task_record["error_message"]:
            error_pattern = self._extract_error_pattern(task_record["error_message"])
            if "error_patterns" not in self.advanced_patterns:
                self.advanced_patterns["error_patterns"] = {}
            if tool_name not in self.advanced_patterns["error_patterns"]:
                self.advanced_patterns["error_patterns"][tool_name] = {}
            
            if error_pattern not in self.advanced_patterns["error_patterns"][tool_name]:
                self.advanced_patterns["error_patterns"][tool_name][error_pattern] = {
                    "count": 0, "solutions": [], "related_errors": []
                }
            
            self.advanced_patterns["error_patterns"][tool_name][error_pattern]["count"] += 1

        # 3. Performance Prediction Data
        if "performance_predictions" not in self.advanced_patterns:
            self.advanced_patterns["performance_predictions"] = {}
        if tool_name not in self.advanced_patterns["performance_predictions"]:
            self.advanced_patterns["performance_predictions"][tool_name] = {
                "execution_times": [], "success_rates": [], "parameter_impact": {}
            }
        
        self.advanced_patterns["performance_predictions"][tool_name]["execution_times"].append(task_record["execution_time"])
        # Keep only last 100 times for prediction
        if len(self.advanced_patterns["performance_predictions"][tool_name]["execution_times"]) > 100:
            self.advanced_patterns["performance_predictions"][tool_name]["execution_times"] = \
                self.advanced_patterns["performance_predictions"][tool_name]["execution_times"][-100:]

        # 4. Cross-Tool Insights
        self._update_cross_tool_insights(task_record)

        # 5. Adaptive Parameters
        if task_record["success"]:
            self._update_adaptive_parameters(task_record)

        # 6. User Preferences
        self._update_user_preferences(task_record)

    def _extract_error_pattern(self, error_message: str) -> str:
        """Extract error patterns for advanced recognition"""
        # Remove specific values but keep error structure
        pattern = re.sub(r'\d+', 'N', error_message)
        pattern = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', 'EMAIL', pattern)
        pattern = re.sub(r'https?://[^\s]+', 'URL', pattern)
        pattern = re.sub(r'[A-Z]:\\[^\s]+', 'PATH', pattern)
        return pattern.strip()

    def _update_cross_tool_insights(self, task_record: Dict[str, Any]):
        """Update cross-tool learning insights"""
        if "cross_tool_insights" not in self.advanced_patterns:
            self.advanced_patterns["cross_tool_insights"] = {}
        
        # Find related tools used in similar contexts
        recent_tasks = [t for t in self.task_history[-20:] if t != task_record]
        for recent_task in recent_tasks:
            if recent_task["user_request"] and task_record["user_request"]:
                # Simple similarity check
                common_words = set(recent_task["user_request"].lower().split()) & \
                             set(task_record["user_request"].lower().split())
                if len(common_words) >= 2:  # At least 2 common words
                    if "related_tools" not in self.advanced_patterns["cross_tool_insights"]:
                        self.advanced_patterns["cross_tool_insights"]["related_tools"] = {}
                    
                    # Use string key instead of tuple for JSON serialization
                    tool_pair_key = f"{recent_task['tool_name']}_{task_record['tool_name']}"
                    if tool_pair_key not in self.advanced_patterns["cross_tool_insights"]["related_tools"]:
                        self.advanced_patterns["cross_tool_insights"]["related_tools"][tool_pair_key] = 0
                    self.advanced_patterns["cross_tool_insights"]["related_tools"][tool_pair_key] += 1

    def _update_adaptive_parameters(self, task_record: Dict[str, Any]):
        """Update adaptive parameter optimization"""
        if "adaptive_parameters" not in self.advanced_patterns:
            self.advanced_patterns["adaptive_parameters"] = {}
        
        tool_name = task_record["tool_name"]
        if tool_name not in self.advanced_patterns["adaptive_parameters"]:
            self.advanced_patterns["adaptive_parameters"][tool_name] = {}
        
        for param, value in task_record["parameters"].items():
            if param not in self.advanced_patterns["adaptive_parameters"][tool_name]:
                self.advanced_patterns["adaptive_parameters"][tool_name][param] = {
                    "values": [], "success_rates": {}, "optimal_value": None
                }
            
            param_data = self.advanced_patterns["adaptive_parameters"][tool_name][param]
            if value not in param_data["values"]:
                param_data["values"].append(value)
            
            if value not in param_data["success_rates"]:
                param_data["success_rates"][value] = {"success": 0, "total": 0}
            
            param_data["success_rates"][value]["total"] += 1
            param_data["success_rates"][value]["success"] += 1
            
            # Update optimal value
            best_value = max(param_data["success_rates"].items(), 
                           key=lambda x: x[1]["success"] / x[1]["total"] if x[1]["total"] > 0 else 0)
            param_data["optimal_value"] = best_value[0]

    def _update_user_preferences(self, task_record: Dict[str, Any]):
        """Update user preference learning"""
        if "user_preferences" not in self.advanced_patterns:
            self.advanced_patterns["user_preferences"] = {}
        
        # Learn from successful executions
        if task_record["success"]:
            for param, value in task_record["parameters"].items():
                if param not in self.advanced_patterns["user_preferences"]:
                    self.advanced_patterns["user_preferences"][param] = {}
                if value not in self.advanced_patterns["user_preferences"][param]:
                    self.advanced_patterns["user_preferences"][param][value] = 0
                self.advanced_patterns["user_preferences"][param][value] += 1

    def get_advanced_suggestions(self, tool_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get advanced suggestions including context-aware and adaptive recommendations"""
        basic_suggestions = self.get_suggestions(tool_name)
        
        advanced_suggestions = {
            **basic_suggestions,
            "context_aware": {},
            "adaptive_parameters": {},
            "performance_prediction": {},
            "cross_tool_recommendations": [],
            "error_prevention": []
        }
        
        # Context-aware suggestions
        if context:
            context_key = f"{context.get('time_of_day', datetime.now().hour)}_{context.get('day_of_week', datetime.now().weekday())}_{context.get('complexity', 'moderate')}"
            if context_key in self.advanced_patterns.get("context_patterns", {}):
                ctx_data = self.advanced_patterns["context_patterns"][context_key]
                success_rate = ctx_data["success"] / ctx_data["total"] if ctx_data["total"] > 0 else 0
                advanced_suggestions["context_aware"] = {
                    "success_rate": success_rate,
                    "recommendation": "Good time for this task" if success_rate > 0.7 else "Consider alternative timing"
                }
        
        # Adaptive parameters
        if tool_name in self.advanced_patterns.get("adaptive_parameters", {}):
            adaptive_params = self.advanced_patterns["adaptive_parameters"][tool_name]
            advanced_suggestions["adaptive_parameters"] = {
                param: data.get("optimal_value") 
                for param, data in adaptive_params.items() 
                if data.get("optimal_value") is not None
            }
        
        # Performance prediction
        if tool_name in self.advanced_patterns.get("performance_predictions", {}):
            perf_data = self.advanced_patterns["performance_predictions"][tool_name]
            if perf_data["execution_times"]:
                avg_time = statistics.mean(perf_data["execution_times"])
                advanced_suggestions["performance_prediction"] = {
                    "expected_time": avg_time,
                    "reliability": "high" if len(perf_data["execution_times"]) > 10 else "medium"
                }
        
        # Cross-tool recommendations
        related_tools = self.advanced_patterns.get("cross_tool_insights", {}).get("related_tools", {})
        for tool_pair_key, frequency in related_tools.items():
            if frequency > 2:
                tools = tool_pair_key.split("_")
                if tool_name in tools and len(tools) == 2:
                    other_tool = tools[1] if tools[0] == tool_name else tools[0]
                    advanced_suggestions["cross_tool_recommendations"].append({
                        "tool": other_tool,
                        "frequency": frequency,
                        "suggestion": f"Often used together with {other_tool}"
                    })
        
        # Error prevention
        if tool_name in self.advanced_patterns.get("error_patterns", {}):
            error_patterns = self.advanced_patterns["error_patterns"][tool_name]
            common_errors = sorted(error_patterns.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
            advanced_suggestions["error_prevention"] = [
                {"pattern": pattern, "frequency": data["count"]} 
                for pattern, data in common_errors
            ]
        
        return advanced_suggestions

    def predict_success_probability(self, tool_name: str, parameters: Dict[str, Any], 
                                  context: Dict[str, Any] = None) -> float:
        """Predict success probability for a tool execution"""
        if tool_name not in self.execution_patterns:
            return 0.5  # Default probability
        
        base_success_rate = self.execution_patterns[tool_name]["success_count"] / \
                           self.execution_patterns[tool_name]["total_count"]
        
        # Adjust based on parameter familiarity
        param_familiarity = 1.0
        if tool_name in self.advanced_patterns.get("adaptive_parameters", {}):
            adaptive_params = self.advanced_patterns["adaptive_parameters"][tool_name]
            familiar_params = 0
            total_params = len(parameters)
            
            for param, value in parameters.items():
                if param in adaptive_params and value in adaptive_params[param]["success_rates"]:
                    familiar_params += 1
            
            if total_params > 0:
                param_familiarity = familiar_params / total_params
        
        # Adjust based on context
        context_factor = 1.0
        if context:
            context_key = f"{context.get('time_of_day', datetime.now().hour)}_{context.get('day_of_week', datetime.now().weekday())}_{context.get('complexity', 'moderate')}"
            if context_key in self.advanced_patterns.get("context_patterns", {}):
                ctx_data = self.advanced_patterns["context_patterns"][context_key]
                if ctx_data["total"] > 0:
                    context_factor = ctx_data["success"] / ctx_data["total"]
        
        # Weighted prediction
        prediction = (base_success_rate * 0.4 + param_familiarity * 0.4 + context_factor * 0.2)
        return min(max(prediction, 0.0), 1.0)

    def get_automatic_optimization(self, tool_name: str) -> Dict[str, Any]:
        """Get automatic optimization recommendations"""
        optimizations = {
            "parameter_tuning": {},
            "timing_optimization": {},
            "error_avoidance": {},
            "performance_improvements": []
        }
        
        # Parameter tuning
        if tool_name in self.advanced_patterns.get("adaptive_parameters", {}):
            adaptive_params = self.advanced_patterns["adaptive_parameters"][tool_name]
            for param, data in adaptive_params.items():
                if data.get("optimal_value") is not None:
                    optimizations["parameter_tuning"][param] = {
                        "current_best": data["optimal_value"],
                        "success_rate": max(data["success_rates"].values(), 
                                          key=lambda x: x["success"] / x["total"] if x["total"] > 0 else 0)
                    }
        
        # Timing optimization
        context_patterns = self.advanced_patterns.get("context_patterns", {})
        best_times = []
        for context_key, data in context_patterns.items():
            if data["total"] > 5:  # Minimum sample size
                success_rate = data["success"] / data["total"]
                if success_rate > 0.8:  # High success rate
                    time_of_day, day_of_week, complexity = context_key.split("_")
                    best_times.append({
                        "time": int(time_of_day),
                        "day": int(day_of_week),
                        "complexity": complexity,
                        "success_rate": success_rate
                    })
        
        if best_times:
            optimizations["timing_optimization"] = {
                "best_times": sorted(best_times, key=lambda x: x["success_rate"], reverse=True)[:3]
            }
        
        # Error avoidance
        if tool_name in self.advanced_patterns.get("error_patterns", {}):
            error_patterns = self.advanced_patterns["error_patterns"][tool_name]
            common_errors = sorted(error_patterns.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
            optimizations["error_avoidance"] = {
                "common_errors": [{"pattern": pattern, "frequency": data["count"]} 
                                for pattern, data in common_errors]
            }
        
        return optimizations

    def get_advanced_insights(self) -> str:
        """Get comprehensive advanced learning insights"""
        if not self.task_history:
            return "No advanced learning data available yet."
        
        insights = []
        
        # Basic performance
        basic_insights = self.get_insights()
        insights.append(basic_insights)
        
        # Advanced patterns
        if self.advanced_patterns.get("context_patterns"):
            insights.append(f"🎯 Context Patterns: {len(self.advanced_patterns['context_patterns'])} learned")
        
        if self.advanced_patterns.get("error_patterns"):
            total_error_patterns = sum(len(patterns) for patterns in self.advanced_patterns["error_patterns"].values())
            insights.append(f"🚨 Error Patterns: {total_error_patterns} recognized")
        
        if self.advanced_patterns.get("adaptive_parameters"):
            total_adaptive_params = sum(len(params) for params in self.advanced_patterns["adaptive_parameters"].values())
            insights.append(f"⚙️ Adaptive Parameters: {total_adaptive_params} optimized")
        
        if self.advanced_patterns.get("cross_tool_insights", {}).get("related_tools"):
            insights.append(f"🔗 Cross-Tool Insights: {len(self.advanced_patterns['cross_tool_insights']['related_tools'])} relationships")
        
        # Performance predictions
        if self.advanced_patterns.get("performance_predictions"):
            tools_with_predictions = len(self.advanced_patterns["performance_predictions"])
            insights.append(f"📊 Performance Predictions: {tools_with_predictions} tools")
        
        return "\n".join(insights)

    def _save_data(self):
        """Save all learning data"""
        self._save_json(_TASK_HISTORY_FILE, self.task_history)
        self._save_json(_PATTERNS_FILE, self.execution_patterns)
        self._save_json(_ADVANCED_PATTERNS_FILE, self.advanced_patterns)

    # Keep existing methods for backward compatibility
    def get_suggestions(self, tool_name: str) -> Dict[str, Any]:
        """Get suggestions for a tool based on learned patterns"""
        if tool_name not in self.execution_patterns:
            return {"success_rate": 0, "suggestions": []}
        
        pattern = self.execution_patterns[tool_name]
        success_rate = pattern["success_count"] / pattern["total_count"] if pattern["total_count"] > 0 else 0
        
        suggestions = []
        
        # Suggest optimal parameters
        if pattern["successful_params"]:
            suggestions.append({
                "type": "optimal_parameters",
                "data": pattern["successful_params"]
            })
        
        # Suggest troubleshooting for common errors
        if pattern["common_errors"]:
            most_common_error = max(pattern["common_errors"].items(), key=lambda x: x[1])
            suggestions.append({
                "type": "troubleshooting",
                "error": most_common_error[0],
                "frequency": most_common_error[1]
            })
        
        return {
            "success_rate": success_rate,
            "avg_time": pattern["avg_time"],
            "suggestions": suggestions
        }

    def get_troubleshooting_help(self, tool_name: str, error_message: str) -> List[str]:
        """Get troubleshooting steps for a tool error"""
        error_type = "unknown"
        if error_message:
            if "connection" in error_message.lower():
                error_type = "network_error"
            elif "file" in error_message.lower():
                error_type = "file_error"
            elif "permission" in error_message.lower():
                error_type = "permission_error"
        
        # Generic troubleshooting steps
        steps = {
            "network_error": [
                "Check internet connection",
                "Verify API endpoints are accessible",
                "Retry with exponential backoff"
            ],
            "file_error": [
                "Verify file path exists",
                "Check file permissions",
                "Ensure file is not locked by another process"
            ],
            "permission_error": [
                "Run with elevated permissions",
                "Check file/folder access rights",
                "Verify user account permissions"
            ],
            "unknown": [
                "Check system logs for details",
                "Verify input parameters",
                "Retry with different parameters"
            ]
        }
        
        return steps.get(error_type, steps["unknown"])

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze overall system performance"""
        if not self.task_history:
            return {"message": "No task history available"}
        
        recent_tasks = self.task_history[-100:]
        success_rate = sum(1 for t in recent_tasks if t["success"]) / len(recent_tasks)
        
        # Tool performance
        tool_performance = {}
        for task in recent_tasks:
            tool = task["tool_name"]
            if tool not in tool_performance:
                tool_performance[tool] = {"success": 0, "total": 0}
            
            tool_performance[tool]["total"] += 1
            if task["success"]:
                tool_performance[tool]["success"] += 1
        
        # Calculate success rates
        for tool, stats in tool_performance.items():
            stats["success_rate"] = stats["success"] / stats["total"]
        
        return {
            "overall_success_rate": success_rate,
            "tool_performance": tool_performance,
            "total_tasks": len(recent_tasks)
        }

    def get_insights(self) -> str:
        """Get human-readable insights"""
        if not self.task_history:
            return "No learning data available yet."
        
        analysis = self.analyze_performance()
        
        insights = []
        insights.append(f"📊 Overall Success Rate: {analysis['overall_success_rate']:.1%}")
        
        # Best performing tools
        tool_perf = analysis['tool_performance']
        if tool_perf:
            best_tool = max(tool_perf.items(), key=lambda x: x[1]['success_rate'])
            insights.append(f"🏆 Best Tool: {best_tool[0]} ({best_tool[1]['success_rate']:.1%} success)")
        
        # Learning patterns
        if self.execution_patterns:
            insights.append(f"🧠 Learned Patterns: {len(self.execution_patterns)} tools")
        
        return "\n".join(insights)


# Singleton
_learning_system = AdvancedLearningSystem()


# --- Public API ---
def record_task_execution(tool_name: str, user_request: str, parameters: Dict[str, Any], 
                         success: bool, execution_time: float, error_message: str = None, 
                         context: Dict[str, Any] = None) -> str:
    return _learning_system.record_task_execution(tool_name, user_request, parameters, 
                                                 success, execution_time, error_message, context)


def get_suggestions(tool_name: str) -> Dict[str, Any]:
    return _learning_system.get_suggestions(tool_name)


def get_advanced_suggestions(tool_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    return _learning_system.get_advanced_suggestions(tool_name, context)


def predict_success_probability(tool_name: str, parameters: Dict[str, Any], 
                              context: Dict[str, Any] = None) -> float:
    return _learning_system.predict_success_probability(tool_name, parameters, context)


def get_automatic_optimization(tool_name: str) -> Dict[str, Any]:
    return _learning_system.get_automatic_optimization(tool_name)


def get_troubleshooting_help(tool_name: str, error_message: str) -> List[str]:
    return _learning_system.get_troubleshooting_help(tool_name, error_message)


def analyze_performance() -> Dict[str, Any]:
    return _learning_system.analyze_performance()


def get_insights() -> str:
    return _learning_system.get_insights()


def get_advanced_insights() -> str:
    return _learning_system.get_advanced_insights()


# --- Tool handlers ---
def learning_analyze_performance() -> str:
    return get_advanced_insights()


def learning_get_suggestions(tool_name: str) -> str:
    suggestions = get_advanced_suggestions(tool_name)
    if suggestions["success_rate"] == 0:
        return f"No data for {tool_name} yet."
    
    result = f"Advanced suggestions for {tool_name} (success rate: {suggestions['success_rate']:.1%}):\n"
    
    # Basic suggestions
    for suggestion in suggestions["suggestions"]:
        if suggestion["type"] == "optimal_parameters":
            result += f"- Optimal parameters: {suggestion['data']}\n"
        elif suggestion["type"] == "troubleshooting":
            result += f"- Common error: {suggestion['error']} ({suggestion['frequency']} times)\n"
    
    # Advanced features
    if suggestions.get("context_aware"):
        ctx = suggestions["context_aware"]
        result += f"- Context success rate: {ctx['success_rate']:.1%} ({ctx['recommendation']})\n"
    
    if suggestions.get("adaptive_parameters"):
        result += f"- Adaptive parameters: {suggestions['adaptive_parameters']}\n"
    
    if suggestions.get("performance_prediction"):
        pred = suggestions["performance_prediction"]
        result += f"- Expected execution time: {pred['expected_time']:.2f}s ({pred['reliability']} confidence)\n"
    
    if suggestions.get("cross_tool_recommendations"):
        result += "- Related tools:\n"
        for rec in suggestions["cross_tool_recommendations"]:
            result += f"  • {rec['tool']} (used together {rec['frequency']} times)\n"
    
    if suggestions.get("error_prevention"):
        result += "- Error prevention:\n"
        for error in suggestions["error_prevention"]:
            result += f"  • {error['pattern']} (occurred {error['frequency']} times)\n"
    
    return result


def learning_get_troubleshooting(tool_name: str, error_description: str) -> str:
    steps = get_troubleshooting_help(tool_name, error_description)
    return f"Troubleshooting for {tool_name}:\n" + "\n".join(f"- {step}" for step in steps)


def learning_predict_success(tool_name: str, parameters: str = "{}") -> str:
    """Predict success probability for a tool execution"""
    try:
        import json
        params = json.loads(parameters) if isinstance(parameters, str) else parameters
        probability = predict_success_probability(tool_name, params)
        return f"Success probability for {tool_name}: {probability:.1%}"
    except Exception as e:
        return f"Error predicting success: {e}"


def learning_get_optimization(tool_name: str) -> str:
    """Get automatic optimization recommendations"""
    optimizations = get_automatic_optimization(tool_name)
    
    result = f"Optimization recommendations for {tool_name}:\n"
    
    if optimizations.get("parameter_tuning"):
        result += "- Parameter tuning:\n"
        for param, data in optimizations["parameter_tuning"].items():
            success_rate = data['success_rate']
            if isinstance(success_rate, dict):
                rate = success_rate['success'] / success_rate['total'] if success_rate['total'] > 0 else 0
            else:
                rate = success_rate
            result += f"  • {param}: {data['current_best']} (success rate: {rate:.1%})\n"
    
    if optimizations.get("timing_optimization"):
        result += "- Timing optimization:\n"
        for time_info in optimizations["timing_optimization"]["best_times"]:
            result += f"  • {time_info['time']}:00 on day {time_info['day']} ({time_info['success_rate']:.1%} success)\n"
    
    if optimizations.get("error_avoidance"):
        result += "- Error avoidance:\n"
        for error in optimizations["error_avoidance"]["common_errors"]:
            result += f"  • {error['pattern']} (avoided {error['frequency']} times)\n"
    
    return result


def get_handlers() -> Dict[str, Any]:
    return {
        "learning_analyze_performance": learning_analyze_performance,
        "learning_get_suggestions": learning_get_suggestions,
        "learning_get_troubleshooting": learning_get_troubleshooting,
        "learning_predict_success": learning_predict_success,
        "learning_get_optimization": learning_get_optimization,
    }


def get_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "learning_analyze_performance",
                "description": "Analyzes Jarvis's advanced learning performance and provides comprehensive insights about success rates, learned patterns, context awareness, and optimization opportunities.",
            }
        },
        {
            "type": "function",
            "function": {
                "name": "learning_get_suggestions",
                "description": "Gets advanced execution suggestions for a specific tool including context-aware recommendations, adaptive parameters, performance predictions, and cross-tool insights.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Name of the tool to get suggestions for"}
                    },
                    "required": ["tool_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "learning_get_troubleshooting",
                "description": "Gets troubleshooting steps for a specific tool error.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Name of the tool that failed"},
                        "error_description": {"type": "string", "description": "Description of the error"}
                    },
                    "required": ["tool_name", "error_description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "learning_predict_success",
                "description": "Predicts the success probability for a tool execution based on learned patterns, parameters, and context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Name of the tool to predict for"},
                        "parameters": {"type": "string", "description": "JSON string of parameters to predict with"}
                    },
                    "required": ["tool_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "learning_get_optimization",
                "description": "Gets automatic optimization recommendations for a tool including parameter tuning, timing optimization, and error avoidance strategies.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string", "description": "Name of the tool to optimize"}
                    },
                    "required": ["tool_name"]
                }
            }
        }
    ]
