import functools
import inspect
from typing import Callable, Any
import time
import os
from datetime import datetime
import json
import sys
import traceback
import numpy
from argparse import ArgumentParser

def format_value(value: Any) -> str:
    """Helper function to format values for logging"""
    if isinstance(value, ArgumentParser):
        return "ArgumentParser()"
    if isinstance(value, numpy.ndarray):
        return f"ndarray(shape={value.shape}, dtype={value.dtype})"
    elif isinstance(value, (list, tuple)):
        return f"{type(value).__name__}(len={len(value)})"
    elif isinstance(value, dict):
        return f"dict(keys={list(value.keys())})"
    elif hasattr(value, '__dict__'):  # For custom objects
        return f"{value.__class__.__name__}()"
    return str(value)

def log_call_path(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Create log file with timestamp and function-specific log
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f'facefusion_{timestamp}.log')
        func_log_file = os.path.join(log_dir, f'facefusion_{func.__name__}_{timestamp}.log')
        
        # Get caller frame and stack info
        caller_frame = inspect.currentframe().f_back
        caller_name = caller_frame.f_code.co_name if caller_frame else "unknown"
        caller_file = caller_frame.f_code.co_filename.split('/')[-1] if caller_frame else "unknown"
        
        # Get function details
        func_name = func.__name__
        func_file = inspect.getfile(func).split('/')[-1]
        
        # Get full call stack
        stack = inspect.stack()
        call_stack = ' -> '.join([f"{f.filename.split('/')[-1]}::{f.function}" for f in stack[1:]])
        
        # Start time
        start_time = time.time()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # Format arguments safely
        try:
            args_repr = [format_value(arg) for arg in args]
            kwargs_repr = {k: format_value(v) for k, v in kwargs.items()}
        except Exception as e:
            args_repr = ["<error formatting args>"]
            kwargs_repr = {"error": str(e)}
        
        # Prepare detailed log entry
        log_entry = [
            f"\n{'='*100}",
            f"[TIMESTAMP] {current_time}",
            f"[CALL STACK] {call_stack}",
            f"[FUNCTION] {func_file}::{func_name}",
            f"[CALLER] {caller_file}::{caller_name}",
            f"[ARGS] {args_repr if args else 'None'}",
            f"[KWARGS] {kwargs_repr if kwargs else 'None'}",
            f"[START] Function execution started"
        ]
        
        # Write to both main and function-specific log files
        for file_path in [log_file, func_log_file]:
            with open(file_path, 'a', encoding='utf-8') as f:
                for line in log_entry:
                    print(line)
                    f.write(line + '\n')
        
        # Execute function and track nested calls
        try:
            # Create a list to store nested function calls
            nested_calls = []
            
            def trace_calls(frame, event, arg):
                if event == 'call':
                    code = frame.f_code
                    func_name = code.co_name
                    if not func_name.startswith('_'):  # Skip internal functions
                        try:
                            # Get function arguments safely
                            args_info = inspect.getargvalues(frame)
                            args_dict = {
                                'function': func_name,
                                'file': code.co_filename.split('/')[-1],
                                'args': {name: format_value(args_info.locals[name]) 
                                       for name in args_info.args if name in args_info.locals}
                            }
                            nested_calls.append(args_dict)
                        except Exception as e:
                            nested_calls.append({
                                'function': func_name,
                                'file': code.co_filename.split('/')[-1],
                                'args': f"<error getting args: {str(e)}>"
                            })
                return trace_calls
            
            # Enable call tracing
            sys.settrace(trace_calls)
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Disable call tracing
            sys.settrace(None)
            
            # End time
            duration = time.time() - start_time
            
            # Format result safely
            try:
                result_repr = format_value(result)
            except Exception as e:
                result_repr = f"<error formatting result: {str(e)}>"
            
            # Prepare completion log entry with nested calls
            completion_entry = [
                f"\n[NESTED CALLS]",
                *[f"  {json.dumps(call, indent=2)}" for call in nested_calls],
                f"\n[RESULT] {result_repr}",
                f"[DURATION] {duration:.4f} seconds",
                f"[END] Function execution completed successfully",
                f"{'='*100}\n"
            ]
            
            # Write completion to both log files
            for file_path in [log_file, func_log_file]:
                with open(file_path, 'a', encoding='utf-8') as f:
                    for line in completion_entry:
                        print(line)
                        f.write(line + '\n')
                    
            return result
            
        except Exception as e:
            # Log error with traceback
            duration = time.time() - start_time
            error_entry = [
                f"\n[ERROR] Exception in {func_name}: {str(e)}",
                f"[TRACEBACK] {traceback.format_exc()}",
                f"[DURATION] {duration:.4f} seconds",
                f"[END] Function execution failed",
                f"{'='*100}\n"
            ]
            
            # Write error to both log files
            for file_path in [log_file, func_log_file]:
                with open(file_path, 'a', encoding='utf-8') as f:
                    for line in error_entry:
                        print(line)
                        f.write(line + '\n')
            raise
            
    return wrapper