
from backend.groq_service import client, MODEL_NAME

print("Connecting to Groq...")

completion = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[
        {
            "role": "user",
            "content": "Reply with exactly: CogniContext Groq is working!"
        }
    ],
    temperature=0.2,
    max_completion_tokens=50
)

print("\nGroq response:")
print(completion.choices[0].message.content)
