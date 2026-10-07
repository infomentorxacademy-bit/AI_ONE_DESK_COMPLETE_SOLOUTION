"""spike/spike_interrupt.py : proves a graph can PAUSE for a human and RESUME (the heart of the approval gate).

Run from app/:  python spike/spike_interrupt.py   Expected: "PAUSED: {...}" then "RESUMED with approve"
"""
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver   # stores the paused run (a checkpointer is REQUIRED)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt          # interrupt() pauses; Command(resume=...) continues


class State(TypedDict, total=False):
    decision: str


def ask_human(state: State) -> State:
    answer = interrupt({"question": "Approve refund of Rs 24000?"})   # <-- graph stops here
    return {"decision": answer}


graph = StateGraph(State)
graph.add_node("ask_human", ask_human)
graph.add_edge(START, "ask_human")
graph.add_edge("ask_human", END)
app = graph.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "demo-1"}}        # the SAME thread_id must be used to resume
paused = app.invoke({}, config)
print("PAUSED:", paused["__interrupt__"][0].value)
resumed = app.invoke(Command(resume="approve"), config)
print("RESUMED with", resumed["decision"])
