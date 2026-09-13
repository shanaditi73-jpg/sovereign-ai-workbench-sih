from agent.models import ask_model


print("\n==============================")
print("TEST 1 - GENERAL")
print("==============================")

answer, model, reason = ask_model(
    "What is an AI agent?"
)

print("Model:", model)
print("Reason:", reason)
print("Answer:", answer)


print("\n==============================")
print("TEST 2 - CODING")
print("==============================")

answer, model, reason = ask_model(
    "Write Python code to calculate the average of three numbers."
)

print("Model:", model)
print("Reason:", reason)
print("Answer:", answer)


print("\n==============================")
print("TEST 3 - VISION")
print("==============================")

answer, model, reason = ask_model(
    "Describe this image in detail.",
    images=[r"C:\Users\shana\Downloads\WhatsApp Image 2026-09-10 at 12.38.00 AM.jpeg"]
)

print("Model:", model)
print("Reason:", reason)
print("Answer:", answer)