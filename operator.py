import socket
import threading
import readline

SERVER_HOST = "127.0.0.1"  # Change to your server's IP
SERVER_PORT = 9000  # Port for operator communication
BLUE = "\033[94m"
RESET = "\033[0m"

# List of supported commands for auto-completion
COMMANDS = ["sessions", "select", "shell", "exit"]

# Event to signal when a response is ready
response_ready = threading.Event()


def completer(text, state):
    """Auto-completion function for commands."""
    options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
    if state < len(options):
        return options[state]
    return None


def handle_server_response(sock):
    """Handle responses from the server."""
    while True:
        try:
            response = sock.recv(4096).decode()
            if response:
                print(f"\n{BLUE}{response}{RESET}")  # Print response on a new line
                response_ready.set()  # Signal that a response is ready
        except Exception as e:
            print(f"Error receiving response from server: {e}")
            break


def main():
    print("Connecting to DNS C2 server...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    print("Connected. Type 'sessions' to view active sessions or 'exit' to quit.")

    # Set up auto-completion
    readline.parse_and_bind("tab: complete")
    readline.set_completer(completer)

    # Create and start the thread for server responses
    response_thread = threading.Thread(target=handle_server_response, args=(sock,))
    response_thread.start()

    try:
        while True:
            command = input("C2> ").strip()
            if command.lower() == "exit":
                print("Exiting.")
                break

            if command:
                response_ready.clear()  # Reset the flag before sending the command
                sock.sendall(command.encode())
                if not response_ready.wait(timeout=5):  # Wait for response with a timeout
                    print("No response received from server. Try again.")

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        response_ready.set()  # Ensure the thread can exit
        response_thread.join()  # Wait for the response thread to finish
        print("Server response thread has finished.")
        sock.close()


if __name__ == "__main__":
    main()
