# How to Create Venv

Create virtual environment before starting the work. This ensures environment is persisted and Jupyter Kernel is created for environment
### Install
Your workspace for project is /efsMount/<SID>/<Workspace_name>. Please work within this space.
```
user command venv (name mandatory version default to python 3.11 unless specified)
venv -n|--name <virtual_env_name> -v|--version (3.8, 3.9, 3.10, 3.11)
venv -h|--help for help
examples
$ venv -n pyenv -v 3.8
$ venv --name pyenv --version 3.8
$ venv -n|--name pyenv -> This defaults to python 3.11

if you want to activate on your terminal
$ source <virtual_env_name>/bin/activate
$ source pyenv/bin/activate
```
Virtual environment is created along with Jupyter Kernel. You can install libraries inside this environment and do your work

# Enable Qemulator (**RHEL-9 Only**)
Set up the Quantinuum emulator in your workspace

### Install
1. Create virtual environment.

2. Open Terminal and start your virtual environment (`source <venv-name>/bin/activate`).

3. Run `emulator-install` command 

### Emulator Usage
Within the virtual environment

`python qemu.py tests/***` , tests folder will have sample qasm files


# SWORD Jupyter LLM Integration

In your home directory you will have a folder called `jupyter_llm`, which contains a python file called `get_client.py` among other files. You can now use this boilerplate code to interact with an LLM powered agent directly in your Jupyter notebooks! Please consider the following code snippets to get started.

**NOTE**: you will also need to build a venv and install the required libraries from the provided `requirements.txt` file.

```
from jupyter_llm.get_client import get_client, set_openai_model

set_openai_model("o3-mini-2025-01-31")
client = get_client()
```

Currently, `set_openai_model` supports the following strings:
- o1-2024-12-17
- gpt-35-turbo-0125
- gpt-4-0613
- gpt-4-turbo-2024-04-09
- gpt-4o-2024-08-06
- gpt-4o-mini-2024-07-18
- o1-2024-12-17
- o3-mini-2025-01-31

```
import os

msg = """
Explain the difference between proper and improper learning. Use the task of learning circuits from quantum states prepared by these circuits as the example.
""".strip()

messages = [
    {"role":"developer", "content":
             """
You are a helpful research assistant. 
Your objective is to assist a researcher who has a PhD in computer science with a focus on quantum computing. 
Your response should be detailed and have level of technical detail and rigour appropriate for a researcher.
Please respond in valid Jupyter Markdown format that can be rendered in Jupyter. 
Use LaTeX syntax enclosed in $...$ for any mathematical expressions.
""".strip()},
            {"role":"user", "content":f"{msg}"}]

response = client.chat.completions.create(
                model=os.environ["AZURE_OPENAI_MODEL"],
                messages=messages,
                temperature=1,
                reasoning_effort = "high"
            )
```

```
from IPython.display import display, Markdown
reply_text = response.choices[0].message.content
display(Markdown(reply_text))
```