"""
Agent planner with tool interface.
Demonstrates agentic patterns: planning, tool use, and delegation.
"""

import json
from typing import List, Dict, Any, Callable, Optional
from enum import Enum


class ToolType(str, Enum):
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    REASONING = "reasoning"


class Tool:
    """Base tool interface."""
    def __init__(self, name: str, description: str, tool_type: ToolType):
        self.name = name
        self.description = description
        self.tool_type = tool_type

    def execute(self, **kwargs) -> str:
        raise NotImplementedError


class RetrievalTool(Tool):
    """Wraps vector store retrieval."""
    def __init__(self, store):
        super().__init__(
            name="retrieval",
            description="Search knowledge base for relevant documents",
            tool_type=ToolType.RETRIEVAL
        )
        self.store = store

    def execute(self, query: str, top_k: int = 5) -> str:
        results = self.store.similarity_search(query, k=top_k)
        return json.dumps(results, ensure_ascii=False, indent=2)


class GenerationTool(Tool):
    """Wraps LLM generation."""
    def __init__(self, llm_fn: Callable):
        super().__init__(
            name="generation",
            description="Generate text using LLM",
            tool_type=ToolType.GENERATION
        )
        self.llm_fn = llm_fn

    def execute(self, prompt: str) -> str:
        return self.llm_fn(prompt)


class AgentPlan:
    """Represents a plan to solve a user query."""
    def __init__(self, goal: str, steps: List[Dict[str, Any]]):
        self.goal = goal
        self.steps = steps  # Each step: {"tool": tool_name, "input": {...}, "rationale": "..."}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": self.steps,
        }


class AgentPlanner:
    """Simple planner: given a query, decides which tools to use."""
    def __init__(self, tools: List[Tool]):
        self.tools = {t.name: t for t in tools}

    def plan(self, query: str) -> AgentPlan:
        """Generate a simple plan to answer the query."""
        steps = []
        
        # Step 1: Always retrieve relevant docs
        steps.append({
            "tool": "retrieval",
            "input": {"query": query, "top_k": 5},
            "rationale": "Fetch context from knowledge base"
        })
        
        # Step 2: Generate answer using retrieved context
        steps.append({
            "tool": "generation",
            "input": {"prompt": f"Answer this query using the retrieved context:\n{query}"},
            "rationale": "Generate comprehensive answer with context"
        })
        
        return AgentPlan(goal=query, steps=steps)

    def execute_plan(self, plan: AgentPlan):
        """Execute plan steps and yield results."""
        results = {}
        for i, step in enumerate(plan.steps):
            tool_name = step["tool"]
            tool_input = step["input"]
            
            if tool_name not in self.tools:
                yield f"[STEP {i+1}] ERROR: Tool '{tool_name}' not found\n"
                continue
            
            tool = self.tools[tool_name]
            yield f"[STEP {i+1}] Using tool: {tool_name}\n"
            yield f"[REASON] {step['rationale']}\n"
            
            try:
                result = tool.execute(**tool_input)
                results[tool_name] = result
                yield f"[RESULT] {result[:500]}\n"  # Stream first 500 chars
            except Exception as e:
                yield f"[ERROR] {str(e)}\n"
        
        yield f"[PLAN_COMPLETE] Executed {len(plan.steps)} steps\n"
        return results
