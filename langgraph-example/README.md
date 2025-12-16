# LangGraph Cloud Example

![](static/agent_ui.png)

This is an example agent to deploy with LangGraph Cloud.

> [!TIP]
> If you would rather use `pyproject.toml` for managing dependencies in your LangGraph Cloud project, please check out [this repository](https://github.com/langchain-ai/langgraph-example-pyproject).

[LangGraph](https://github.com/langchain-ai/langgraph) is a library for building stateful, multi-actor applications with LLMs. The main use cases for LangGraph are conversational agents, and long-running, multi-step LLM applications or any LLM application that would benefit from built-in support for persistent checkpoints, cycles and human-in-the-loop interactions (ie. LLM and human collaboration).

LangGraph shortens the time-to-market for developers using LangGraph, with a one-liner command to start a production-ready HTTP microservice for your LangGraph applications, with built-in persistence. This lets you focus on the logic of your LangGraph graph, and leave the scaling and API design to us. The API is inspired by the OpenAI assistants API, and is designed to fit in alongside your existing services.

In order to deploy this agent to LangGraph Cloud you will want to first fork this repo. After that, you can follow the instructions [here](https://langchain-ai.github.io/langgraph/cloud/) to deploy to LangGraph Cloud.

## Run locally (LangGraph Studio)

You can run this graph locally using the `langgraph` CLI in development mode. This starts a local LangGraph API server and connects it to LangGraph Studio.

### Setup

From this directory (`langgraph-example/`):

	python -m venv .venv
	source .venv/bin/activate
	pip install -r my_agent/requirements.txt

	# Required for `langgraph dev` (in-memory local API server)
	pip install -U "langgraph-cli[inmem]"

	cp .env.example .env

Then edit `.env` and set the required API keys.

### Start

	source .venv/bin/activate
	langgraph dev --config langgraph.json

`langgraph dev` will open your browser and connect to LangGraph Studio by default (defaults to `https://smith.langchain.com`).

Notes:

- If you run `langgraph dev` and see `Required package 'langgraph-api' is not installed`, install `langgraph-cli[inmem]` (shown above).
- If you prefer a Docker-based local server, `langgraph up` exists but requires a running Docker daemon.
