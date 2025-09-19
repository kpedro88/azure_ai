# azure_ai

Simple environment and interface to send LLM API queries through Azure AI Foundry.

## Setup

```bash
./setup.sh
```

* Creates a virtual environment with necessary packages
* Creates a `secrets.sh` file that should be populated following the [Azure AI Foundry Deep Research guide](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/deep-research-samples?pivots=python)

## Environment

```bash
source init.sh
```

* Enables the virtual environment
* Adds the `secrets.sh` contents to the shell environment
* Requests Azure login (if needed)

## Usage

```bash
python3 query.py -i input.txt -o output.txt
```

* Runs a query and returns the output response
