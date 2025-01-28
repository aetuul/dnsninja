# DNSNinja

This project implements a simple DNS-based Command and Control (C2) system. It consists of:
- A **server** that listens for DNS requests from agents and communicates with operators.
- A **client agent** that polls for commands and executes them on the target system.
- An **operator client** that allows operators to interact with connected agents.

## Features

### Agent Features
- Polls the C2 server for commands using DNS TXT queries.
- Executes shell commands on the target system.
- Sends encrypted output back to the server.
- Generates a unique `CLIENT_ID` in the format `agent-username@hostname`.

### Server Features
- Listens on two ports:
  - **Port 9053**: Handles DNS-based communication with agents.
  - **Port 9000**: Handles operator connections.
- Supports multiple sessions by maintaining unique agent IDs.
- Allows operators to select and interact with specific agents.
- Displays output from agents in real-time.

### Operator Client Features
- Connects to the server on port **9000**.
- Lists active sessions using the `sessions` command.
- Allows selecting an active session using `select <session_number>`.
- Supports executing shell commands on connected agents.
- Displays output from agents in a clean format.

## Usage

### 1. Starting the Server

Run the server script to start listening for both DNS and operator connections:
```bash
python server.py
```

### 2. Running the Agent

Run the generated agent script on the target machine:
```bash
python agent.py
```

### 3. Using the Operator Client

Run the operator client to connect to the server:
```bash
python operator.py
```

#### Operator Commands
- `sessions`: Lists all active sessions.
- `select <session_number>`: Selects an active session for interaction.
- `shell <command>`: Executes a shell command on the selected agent.
- `exit`: Exits the operator client.

## Security

- Communication between the agent and server is encrypted using AES with a configurable secret key.
- Unique session IDs ensure that multiple agents can be managed simultaneously.

## Limitations

- Currently supports only shell command execution.
- File upload and download are **not supported**.

## Future Improvements

- Implement file upload and download functionality.
- Add better error handling and logging.


