# Experiments with https://python.langchain.com

Create a python 3.11 environment and install the following dependencies (somewhat convoluted because of dependency
problems):

`pip install typing-inspect==0.8.0 typing_extensions==4.5.0`
`pip install pydantic -U`
`pip install pydantic==1.10.11`
`pip install python-dotenv langchain langchain-cli openai huggingface_hub langchain_openai`
`pip install text-generation transformers numexpr langchainhub sentencepiece jinja2`

You need to copy `.env.dist` to `.env` and add values for the `OPENAI_API_KEY` and `HUGGINGFACEHUB_API_TOKEN`
emvironment variables.


