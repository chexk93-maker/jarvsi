import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import re
from collections import defaultdict
import statistics

# --- Configuration ---
_LEARNING_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "memory_db")
os.makedirs(_LEARNING_DB_DIR, exist_ok=True)
_ADVANCED_PATTERNS_FILE = os.path.join(_LEARNING_DB_DIR, "advanced_patterns.json")


class AdvancedLearningSystem:
    def __init__(self):
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
            print(f"⚠️ [ADVANCED LEARNING] Failed to load {path}: {e}")
        return default

    def _save_json(self, path: str, data: Any) -> None:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"⚠️ [ADVANCED LEARNING] Failed to save {path}: {e}")

    def record_advanced_execution(self, task_record: Dict[str, Any]):
        """Record advanced learning patterns from a task execution"""
        tool_name = task_record["tool_name"]
        
        # 1. Context Patterns
        context_key = f"{task_record.get('time_of_day', datetime.now().hour)}_{task_record.get('day_of_week', datetime.now().weekday())}_{task_record.get('request_complexity', 'moderate')}"
        if context_key not in self.advanced_patterns["context_patterns"]:
            self.advanced_patterns["context_patterns"][context_key] = {"success": 0, "total": 0}
        
        self.advanced_patterns["context_patterns"][context_key]["total"] += 1
        if task_record["success"]:
            self.advanced_patterns["context_patterns"][context_key]["success"] += 1

        # 2. Error Pattern Recognition
        if not task_record["success"] and task_record.get("error_message"):
            error_pattern = self._extract_error_pattern(task_record["error_message"])
            if tool_name not in self.advanced_patterns["error_patterns"]:
                self.advanced_patterns["error_patterns"][tool_name] = {}
            
            if error_pattern not in self.advanced_patterns["error_patterns"][tool_name]:
                self.advanced_patterns["error_patterns"][tool_name][error_pattern] = {
                    "count": 0, "solutions": [], "related_errors": []
                }
            
            self.advanced_patterns["error_patterns"][tool_name][error_pattern]["count"] += 1

        # 3. Performance Prediction Data
        if tool_name not in self.advanced_patterns["performance_predictions"]:
            self.advanced_patterns["performance_predictions"][tool_name] = {
                "execution_times": [], "success_rates": [], "parameter_impact": {}
            }
        
        self.advanced_patterns["performance_predictions"][tool_name]["execution_times"].append(task_record["execution_time"])
        # Keep only last 100 times for prediction
        if len(self.advanced_patterns["performance_predictions"][tool_name]["execution_times"]) > 100:
            self.advanced_patterns["performance_predictions"][tool_name]["execution_times"] = \
                self.advanced_patterns["performance_predictions"][tool_name]["execution_times"][-100:]

        # 4. Adaptive Parameters
        if task_record["success"]:
            self._update_adaptive_parameters(task_record)

        # 5. User Preferences
        self._update_user_preferences(task_record)

        self._save_data()

    def _extract_error_pattern(self, error_message: str) -> str:
        """Extract error patterns for advanced recognition"""
        # Remove specific values but keep error structure
        pattern = re.sub(r'\d+', 'N', error_message)
        pattern = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', 'EMAIL', pattern)
        pattern = re.sub(r'https?://[^\s]+', 'URL', pattern)
        pattern = re.sub(r'[A-Z]:\\[^\s]+', 'PATH', pattern)
        return pattern.strip()

    def _update_adaptive_parameters(self, task_record: Dict[str, Any]):
        """Update adaptive parameter optimization"""
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
        advanced_suggestions = {
            "context_aware": {},
            "adaptive_parameters": {},
            "performance_prediction": {},
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
        # Base probability (would need basic patterns from main learning system)
        base_probability = 0.5
        
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
        prediction = (base_probability * 0.4 + param_familiarity * 0.4 + context_factor * 0.2)
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

    def _save_data(self):
        """Save advanced learning data"""
        self._save_json(_ADVANCED_PATTERNS_FILE, self.advanced_patterns)


# Singleton
_advanced_learning = AdvancedLearningSystem()


# --- Public API ---
def record_advanced_execution(task_record: Dict[str, Any]) -> str:
    return _advanced_learning.record_advanced_execution(task_record)


def get_advanced_suggestions(tool_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    return _advanced_learning.get_advanced_suggestions(tool_name, context)


def predict_success_probability(tool_name: str, parameters: Dict[str, Any], 
                              context: Dict[str, Any] = None) -> float:
    return _advanced_learning.predict_success_probability(tool_name, parameters, context)


def get_automatic_optimization(tool_name: str) -> Dict[str, Any]:
    return _advanced_learning.get_automatic_optimization(tool_name)
