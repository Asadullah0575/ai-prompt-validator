# app.py

def validate_prompt(prompt):
    issues = []
    prompt_lower = prompt.lower()

    # Check vague phrases
    vague_words = ["if needed", "if possible", "when appropriate", "conditions are met"]
    for word in vague_words:
        if word in prompt_lower:
            issues.append(f"Ambiguous phrase detected: '{word}'")

    # Check missing amount
    if "eth" in prompt_lower and not any(char.isdigit() for char in prompt):
        issues.append("Missing numeric value for ETH")

    # Check missing recipient
    if "send" in prompt_lower and "to" not in prompt_lower:
        issues.append("Missing recipient address")

    # Check unclear condition after 'if'
    if "if" in prompt_lower and ">" not in prompt and "<" not in prompt:
        issues.append("Condition is unclear (no comparison like > or < found)")

    return issues

def suggest_fix(prompt):
    return "Try adding specific conditions, values, and recipient addresses."

if __name__ == "__main__":
    user_input = input("Enter your prompt: ")
    problems = validate_prompt(user_input)

    if problems:
        print("\n⚠️ Issues found:")
        for p in problems:
            print("-", p)
        print("\n💡 Suggestion:")
        print(suggest_fix(user_input))
    else:
        print("\n✅ Prompt looks good!")
