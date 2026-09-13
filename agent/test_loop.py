from agent.loop import run_agent


print("\n==============================")
print("TEST 1 - GENERAL")
print("==============================")

result = run_agent(
    "Explain artificial intelligence in simple words."
)

print("Model:", result["model"])
print("Reason:", result["reason"])
print("Tool:", result["tool"])
print("Answer:", result["answer"])


print("\n==============================")
print("TEST 2 - TOOL + LLM")
print("==============================")

result = run_agent(
    "Calculate 125 * 32"
)

print("Model:", result["model"])
print("Reason:", result["reason"])
print("Tool:", result["tool"])
print("Answer:", result["answer"])


print("\n==============================")
print("TEST 3 - CONTEXT / RAG READY")
print("==============================")

result = run_agent(
    "What is the capital of India?",
    context="The capital of India is New Delhi."
)

print("Model:", result["model"])
print("Reason:", result["reason"])
print("Tool:", result["tool"])
print("Answer:", result["answer"])