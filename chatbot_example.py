from langchain import OpenAI, ConversationChain

llm = OpenAI(temperature = 0)
conversation = ConversationChain(llm = llm, verbose = False) # verbose = True for the thinking process

print("Welcome to your AI chatbot! What's on your mind?")

# for _ in range(0, 3):
while True:
    human_input = input("You: ")
    if human_input.lower() == 'end':
        break
    ai_reponse = conversation.predict(input = human_input)
    print(f"AI: {ai_reponse}")

# print(conversation.memory)