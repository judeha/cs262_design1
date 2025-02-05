import selectors
import socket
import sys
import traceback

import libclient

import tkinter as tk
import threading

sel = selectors.DefaultSelector()

def create_request(action, value):
    if action == "search":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action, value=value),
        )
    else:
        return dict(
            type="binary/custom-client-binary-type",
            encoding="binary",
            content=bytes(action + value, encoding="utf-8"),
        )


def start_connection(host, port, request):
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)


if len(sys.argv) != 5:
    print(f"Usage: {sys.argv[0]} <host> <port> <action> <value>")
    sys.exit(1)

# Tkinter GUI setup
root = tk.Tk()
root.title("Chat Client")

# chat_log = tk.Text(root, state=tk.NORMAL, height=20, width=50)
# chat_log.pack()

BG_GRAY = "#ABB2B9"
BG_COLOR = "#17202A"
TEXT_COLOR = "#EAECEE"
FONT = "Helvetica 14"
FONT_BOLD = "Helvetica 13 bold"

def send():
    send = "You -> " + tk.e.get()
    tk.txt.insert(tk.END, "\n" + send)
 
    user = tk.e.get().lower()
  
    if (user == "hello"):
        txt.insert(tk.END, "\n" + "Bot -> Hi there, how can I help?")
 
    elif (user == "hi" or user == "hii" or user == "hiiii"):
        txt.insert(tk.END, "\n" + "Bot -> Hi there, what can I do for you?")
 
    else:
        txt.insert(tk.END, "\n" + "Bot -> fine! and you")
 
    e.delete(0, tk.END)


lable1 = tk.Label(root, bg=BG_COLOR, fg=TEXT_COLOR, text="Welcome", font=FONT_BOLD, pady=10, width=20, height=1).grid(
    row=0)
 
txt = tk.Text(root, bg=BG_COLOR, fg=TEXT_COLOR, font=FONT, width=60)
txt.grid(row=1, column=0, columnspan=2)
 
scrollbar = tk.Scrollbar(txt)
scrollbar.place(relheight=1, relx=0.974)
 
e = tk.Entry(root, bg="#2C3E50", fg=TEXT_COLOR, font=FONT, width=55)
e.grid(row=2, column=0)
 
send = tk.Button(root, text="Send", font=FONT_BOLD, bg=BG_GRAY,
              command=send).grid(row=2, column=1)

# message_entry = tk.Entry(root, width=40)
# message_entry.pack(side=tk.LEFT)

# send_button = tk.Button(root, text="Send", command=send_message)
# send_button.pack(side=tk.RIGHT)

host, port = sys.argv[1], int(sys.argv[2])
action, value = sys.argv[3], sys.argv[4]
request = create_request(action, value)
start_connection(host, port, request)

# # Start Tkinter event loop
root.mainloop()

try:
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception:
                print(
                    f"Main: Error: Exception for {message.addr}:\n"
                    f"{traceback.format_exc()}"
                )
                message.close()
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()