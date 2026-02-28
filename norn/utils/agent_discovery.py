#!/usr/bin/env python3
"""
Norn Agent Discovery
Analyzes agent code to discover capabilities, tools, and potential issues
"""

import ast
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional
import importlib.util
import sys


class AgentDiscovery:
    """
    Discovers agent capabilities by analyzing code
    """
    
    def __init__(self, agent_path: Path, main_file: str):
        self.agent_path = agent_path
        self.main_file = main_file
        self.main_file_path = agent_path / main_file
        # Set working directory to main file's directory for local package detection
        self.working_dir = self.main_file_path.parent
        
    def discover(self) -> Dict[str, Any]:
        """
        Full discovery of agent capabilities
        
        Returns:
            Dict with discovered information
        """
        print(f"🔍 Discovering agent capabilities...")
        print(f"   Path: {self.agent_path}")
        print(f"   File: {self.main_file}")
        
        result = {
            "status": "success",
            "tools": [],
            "functions": [],
            "classes": [],
            "imports": [],
            "dependencies": [],
            "potential_issues": [],
            "agent_type": "unknown",
            "entry_points": []
        }
        
        try:
            # Parse AST
            with open(self.main_file_path) as f:
                code = f.read()
            
            tree = ast.parse(code)
            
            # Discover tools (functions with @tool decorator)
            result["tools"] = self._find_tools(tree)
            
            # Discover functions
            result["functions"] = self._find_functions(tree)
            
            # Discover classes
            result["classes"] = self._find_classes(tree)
            
            # Discover imports
            result["imports"] = self._find_imports(tree)
            
            # Detect agent type
            result["agent_type"] = self._detect_agent_type(tree, code)
            
            # Find entry points
            result["entry_points"] = self._find_entry_points(tree)
            
            # Check dependencies
            result["dependencies"] = self._check_dependencies(result["imports"])
            
            # Analyze potential issues
            result["potential_issues"] = self._analyze_issues(tree, code, result)
            
            print(f"✅ Discovery complete!")
            print(f"   Tools: {len(result['tools'])}")
            print(f"   Functions: {len(result['functions'])}")
            print(f"   Classes: {len(result['classes'])}")
            print(f"   Agent Type: {result['agent_type']}")
            print(f"   Entry Points: {result['entry_points']}")
            
            if result["potential_issues"]:
                print(f"   ⚠️  Issues: {len(result['potential_issues'])}")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"❌ Discovery failed: {e}")
        
        return result
    
    def _find_tools(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Find functions decorated with @tool"""
        tools = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for @tool decorator
                has_tool_decorator = any(
                    (isinstance(d, ast.Name) and d.id == 'tool') or
                    (isinstance(d, ast.Attribute) and d.attr == 'tool')
                    for d in node.decorator_list
                )
                
                if has_tool_decorator:
                    # Get docstring
                    docstring = ast.get_docstring(node) or "No description"
                    
                    # Get parameters
                    params = [arg.arg for arg in node.args.args if arg.arg != 'self']
                    
                    tools.append({
                        "name": node.name,
                        "description": docstring.split('\n')[0],
                        "parameters": params,
                        "line": node.lineno
                    })
        
        # Also check for external tool imports and usage
        external_tools = self._find_external_tools(tree)
        tools.extend(external_tools)
        
        return tools
    
    def _find_external_tools(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Find tools imported from external packages"""
        tools = []
        
        # Look for tool-related imports
        tool_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and any(keyword in node.module.lower() for keyword in ['tool', 'amadeus', 'langchain']):
                    for alias in node.names:
                        tool_imports.append({
                            "module": node.module,
                            "name": alias.name,
                            "line": node.lineno
                        })
        
        # Look for Agent initialization with tools parameter
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if it's Agent(...) or similar
                if isinstance(node.func, ast.Name) and node.func.id in ['Agent', 'agent']:
                    for keyword in node.keywords:
                        if keyword.arg == 'tools':
                            # Found tools parameter
                            if isinstance(keyword.value, ast.List):
                                for tool in keyword.value.elts:
                                    tool_name = self._extract_tool_name(tool)
                                    if tool_name:
                                        tools.append({
                                            "name": tool_name,
                                            "description": "External tool",
                                            "parameters": [],
                                            "line": node.lineno,
                                            "source": "external"
                                        })
        
        # Look for use_* function calls (like use_amadeus())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name.startswith('use_'):
                        # This is likely a tool registration function
                        tool_package = func_name.replace('use_', '')
                        tools.append({
                            "name": f"{tool_package}_tools",
                            "description": f"Tools from {tool_package} package",
                            "parameters": [],
                            "line": node.lineno,
                            "source": "package"
                        })
        
        # Add info from tool imports
        for imp in tool_imports:
            if imp["name"] not in [t["name"] for t in tools]:
                tools.append({
                    "name": imp["name"],
                    "description": f"Imported from {imp['module']}",
                    "parameters": [],
                    "line": imp["line"],
                    "source": "import"
                })
        
        return tools
    
    def _extract_tool_name(self, node: ast.AST) -> Optional[str]:
        """Extract tool name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
        return None
    
    def _find_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Find all functions"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node) or ""

                functions.append({
                    "name": node.name,
                    "description": docstring.split('\n')[0] if docstring else "",
                    "line": node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef)
                })
        
        return functions
    
    def _find_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Find all classes"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                
                # Get base classes
                bases = [self._get_name(base) for base in node.bases]
                
                classes.append({
                    "name": node.name,
                    "description": docstring.split('\n')[0] if docstring else "",
                    "bases": bases,
                    "line": node.lineno
                })
        
        return classes
    
    def _find_imports(self, tree: ast.AST) -> List[str]:
        """Find all imports"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        return list(set(imports))
    
    def _detect_agent_type(self, tree: ast.AST, code: str) -> str:
        """Detect what type of agent this is"""
        code_lower = code.lower()
        
        # Check for Strands Agent
        if 'from strands import agent' in code_lower or 'strands.agent' in code_lower:
            return "Strands Agent"
        
        # Check for LangChain
        if 'langchain' in code_lower:
            return "LangChain Agent"
        
        # Check for AutoGPT
        if 'autogpt' in code_lower:
            return "AutoGPT"
        
        # Check for custom agent patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if 'agent' in node.name.lower():
                    return "Custom Agent"
        
        return "Unknown"
    
    def _find_entry_points(self, tree: ast.AST) -> List[str]:
        """Find possible entry points (main, run, etc.)"""
        entry_points = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in ['main', 'run', 'start', 'execute']:
                    entry_points.append(node.name)

            # Check for if __name__ == "__main__"
            if isinstance(node, ast.If):
                if (isinstance(node.test, ast.Compare) and
                        isinstance(node.test.left, ast.Name) and
                        node.test.left.id == "__name__" and
                        len(node.test.comparators) == 1 and
                        isinstance(node.test.comparators[0], ast.Constant) and
                        node.test.comparators[0].value == "__main__" and
                        any(isinstance(op, ast.Eq) for op in node.test.ops)):
                    entry_points.append("__main__")
        
        # Check for Agent instance
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'agent':
                        entry_points.append("agent (variable)")
        
        return list(set(entry_points))
    
    def _check_dependencies(self, imports: List[str]) -> List[Dict[str, Any]]:
        """Check if dependencies are installed"""
        dependencies = []
        
        for imp in imports:
            # Skip standard library
            if imp in ['os', 'sys', 'json', 'time', 'datetime', 'pathlib']:
                continue
            
            # Check if it's a local package (exists in agent directory)
            module_name = imp.split('.')[0]
            # Check in working directory (where main file is)
            local_package_path = self.working_dir / module_name
            
            # Also check with dashes (e.g., strands_amadeus -> strands-amadeus)
            local_package_path_dash = self.working_dir / module_name.replace('_', '-')
            
            if local_package_path.exists() and local_package_path.is_dir():
                # It's a local package
                dependencies.append({
                    "name": imp,
                    "status": "local",
                    "path": str(local_package_path)
                })
                continue
            elif local_package_path_dash.exists() and local_package_path_dash.is_dir():
                # It's a local package with dashes
                dependencies.append({
                    "name": imp,
                    "status": "local",
                    "path": str(local_package_path_dash)
                })
                continue
            
            try:
                importlib.import_module(module_name)
                status = "installed"
            except ImportError:
                status = "missing"
            
            dependencies.append({
                "name": imp,
                "status": status
            })
        
        return dependencies
    
    def _analyze_issues(self, tree: ast.AST, code: str, discovery: Dict) -> List[Dict[str, Any]]:
        """Analyze potential issues"""
        issues = []
        
        # Check for missing dependencies
        missing_deps = [d for d in discovery["dependencies"] if d["status"] == "missing"]
        if missing_deps:
            # Check if these are external tool packages (less critical)
            external_tool_packages = [d for d in missing_deps if any(
                keyword in d["name"].lower() for keyword in ['tool', 'amadeus', 'langchain', 'crewai']
            )]
            
            critical_missing = [d for d in missing_deps if d not in external_tool_packages]
            
            if critical_missing:
                issues.append({
                    "type": "MISSING_DEPENDENCIES",
                    "severity": "HIGH",
                    "description": f"Missing dependencies: {', '.join(d['name'] for d in critical_missing)}"
                })
            
            if external_tool_packages:
                issues.append({
                    "type": "MISSING_TOOL_PACKAGES",
                    "severity": "LOW",
                    "description": f"External tool packages not installed: {', '.join(d['name'] for d in external_tool_packages)}"
                })
        
        # Check for no entry points
        if not discovery["entry_points"]:
            issues.append({
                "type": "NO_ENTRY_POINT",
                "severity": "HIGH",
                "description": "No clear entry point found (main, run, agent variable)"
            })
        
        # Check for no tools (only if no external tools detected)
        has_external_tools = any(t.get("source") in ["external", "package", "import"] for t in discovery["tools"])
        if discovery["agent_type"] == "Strands Agent" and not discovery["tools"]:
            issues.append({
                "type": "NO_TOOLS",
                "severity": "MEDIUM",
                "description": "Strands agent with no @tool decorated functions"
            })
        elif discovery["agent_type"] == "Strands Agent" and not has_external_tools and len(discovery["tools"]) == 0:
            issues.append({
                "type": "NO_TOOLS",
                "severity": "MEDIUM",
                "description": "No tools detected in agent"
            })
        
        # Check for hardcoded credentials (basic check)
        if 'api_key' in code.lower() or 'password' in code.lower():
            issues.append({
                "type": "POTENTIAL_CREDENTIALS",
                "severity": "MEDIUM",
                "description": "Potential hardcoded credentials detected"
            })
        
        return issues
    
    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "unknown"


def main():
    """CLI entry point"""
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python agent_discovery.py <agent_path> <main_file>")
        sys.exit(1)
    
    agent_path = Path(sys.argv[1])
    main_file = sys.argv[2]
    
    discovery = AgentDiscovery(agent_path, main_file)
    result = discovery.discover()
    
    print("\n" + "="*60)
    print("DISCOVERY_JSON_START")
    print(json.dumps(result, indent=2))
    print("DISCOVERY_JSON_END")


if __name__ == "__main__":
    main()
