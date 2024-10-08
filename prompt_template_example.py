# prompt templating and chaining
from langchain import PromptTemplate
# from langchain_core.prompts.PromptTemplate import PromptTemplate
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain


# template for a single variable
# template = "You are a naming consultant for new companies. What is a good name for a company that makes {product}?"

# prompt = PromptTemplate.from_template(template)
# llm = OpenAI(temperature = 0.9)

# chain = LLMChain(llm=llm, prompt=prompt)

# print(chain.run('colorful socks'))


# template for multiple variaables
template = "You are a naming consultant for new companies. What is a good name for a {company} that makes {product}?"

prompt = PromptTemplate.from_template(template)
llm = OpenAI(temperature = 0.9)

chain = LLMChain(llm=llm, prompt=prompt)

print(chain.run({'company':'ABC startup', 'product': 'colorful socks'}))