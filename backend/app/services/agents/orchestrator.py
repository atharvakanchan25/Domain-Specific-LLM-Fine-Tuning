"""
Module 7: Multi-Agent Orchestrator (LangGraph)
Planner routes the query to the right specialist agents,
then a synthesis node combines outputs via LLM.
"""
from __future__ import annotations
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from app.services.agents.llm_client import generate, SYSTEM_PROMPT
from app.core.logging import logger


class AgentState(TypedDict):
    query: str
    entity_hint: str | None
    plan: str
    agent_outputs: Annotated[list[dict], operator.add]
    citations: list[dict]
    graph_context: list[dict]
    answer: str
    confidence: float


# ── Dependency container (set once at app startup) ────────────────
_deps: dict = {}


def set_dependencies(deps: dict) -> None:
    """Called from main.py lifespan with initialised services."""
    _deps.update(deps)


# ── Nodes ─────────────────────────────────────────────────────────

async def planner_node(state: AgentState) -> AgentState:
    plan = await generate(
        system_prompt=(
            "You are a query router. Given a developer question, decide which agents are needed.\n"
            "Respond with a comma-separated list from: code_analysis, architecture, bug_diagnosis, org_memory\n"
            "Only include agents relevant to the question."
        ),
        user_message=state["query"],
        max_tokens=64,
    )
    logger.info("planner", plan=plan)
    return {**state, "plan": plan}


async def code_analysis_node(state: AgentState) -> AgentState:
    agent = _deps.get("code_analysis_agent")
    if agent is None:
        return {**state, "agent_outputs": []}
    result = await agent.run(state["query"])
    return {**state, "agent_outputs": [result]}


async def architecture_node(state: AgentState) -> AgentState:
    agent = _deps.get("architecture_agent")
    if agent is None:
        return {**state, "agent_outputs": []}
    result = await agent.run(state["query"], state.get("entity_hint"))
    return {**state, "agent_outputs": [result],
            "graph_context": result.get("graph_context", [])}


async def bug_diagnosis_node(state: AgentState) -> AgentState:
    agent = _deps.get("bug_diagnosis_agent")
    if agent is None:
        return {**state, "agent_outputs": []}
    result = await agent.run(state["query"])
    return {**state, "agent_outputs": [result]}


async def org_memory_node(state: AgentState) -> AgentState:
    agent = _deps.get("org_memory_agent")
    if agent is None:
        return {**state, "agent_outputs": []}
    result = await agent.run(state["query"])
    return {**state, "agent_outputs": [result]}


async def synthesis_node(state: AgentState) -> AgentState:
    combined = "\n\n".join(
        f"[{o['agent'].upper()}]\n{o.get('answer', '')}"
        for o in state["agent_outputs"]
    )
    citations = []
    for o in state["agent_outputs"]:
        citations.extend(o.get("citations", []))

    answer = await generate(
        system_prompt=SYSTEM_PROMPT,
        user_message=(
            f"Agent findings:\n{combined}\n\n"
            f"Original question: {state['query']}\n\n"
            "Synthesise a clear, comprehensive answer."
        ),
        max_tokens=1500,
    )
    return {**state, "answer": answer, "citations": citations}


async def validator_node(state: AgentState) -> AgentState:
    # Simple heuristic: longer, more specific answers score higher
    confidence = min(0.95, 0.5 + len(state["answer"]) / 3000)
    return {**state, "confidence": round(confidence, 2)}


def build_graph() -> StateGraph:
    g = StateGraph(AgentState)
    for node in [planner_node, code_analysis_node, architecture_node,
                 bug_diagnosis_node, org_memory_node, synthesis_node, validator_node]:
        g.add_node(node.__name__.replace("_node", ""), node)

    g.set_entry_point("planner")
    for node in ["code_analysis", "architecture", "bug_diagnosis", "org_memory"]:
        g.add_edge("planner", node)
        g.add_edge(node, "synthesis")
    g.add_edge("synthesis", "validator")
    g.add_edge("validator", END)
    return g


agent_graph = build_graph().compile()
