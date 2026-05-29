# rikis

Lightweight agent that connects your local LLM runtimes to [Protorikis Bench](https://bench.protorikis.com) and runs benchmark jobs on them.

> rikis only runs inference - it never executes generated code locally

## Install

```
pipx install rikis
```

## Usage

**1. Get a token** from [Protorikis Bench](https://bench.protorikis.com) → Endpoints → Add Endpoint

**2. Log in:**
```
rikis login --token <token>
```

**3. Add a runtime:**
```
rikis config --add-runtime ollama --url http://localhost:11434
rikis config --add-runtime llama.cpp --url http://localhost:8080
rikis config --add-runtime lmstudio --url http://localhost:1234
```

**4. Start the agent:**
```
rikis start
```

The agent polls Protorikis Bench for benchmark jobs, runs inference locally, and returns results.

## Commands

| Command | Description |
|---------|-------------|
| `rikis login --token <token>` | Authenticate with Protorikis Bench |
| `rikis config --add-runtime <type> --url <url>` | Add a local LLM runtime |
| `rikis config --remove-runtime <url>` | Remove a runtime |
| `rikis start` | Start the agent |
| `rikis status` | Show current configuration |

## Dependencies

rikis is intentionally lightweight and uses only these libraries:

- `httpx` - HTTP client
- `Typer` - CLI framework
