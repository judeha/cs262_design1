# CS262 Design Challenge #1: Multi-Client Server Chat

### Description
In this design excercise, we built a simple, client-server chat application that allows multiple users to send and receive text messgages from a centralized server. The application allows the following operations: 
1. Check if an account exists: supply a unique username. If an account exists, you will be taken to login; otherwise you will be taken to account creation
2. Create an account: supply a unique username, password, and text bio.
3. Log in to an account
**All passwords are encrypted! **
4. List accounts: Users are able to see a list of existing accounts on the server. You can enter a search pattern in the text box below the "List Account" button to search for specific users; leaving the box blank will list all accounts instead.
5. Send a message to a recipient: If the recipient is logged in, deliver immediately; if not the message will be stored and delivered once the recipient logs in and requests to see it.
6. Read messages: If another user sends you a message when you are logged in, you will see it immediately. If you want to see messages sent while you were logged out, specify a number of messages to read in the text box below the "See new messages" button
7. Read archived messages: You can see previously read messages by specifying a number in the text box below the "See older messages" button.
8. Delete a message or set of messages: When on the GUI, to delete messages, type in the list of message ids you want to delete in the text box below the "Delete messages" button. Ids must be separated by commas. Ex: <5,6>. You can only delete messages you have received.
9. Delete an account
10. EXTRA FEATURE: "Find my nemesis" -- in honor of all the single people on Valentine's day, find the user you are most incompatible with based on your bios. It'll be hate at first text <3

### Usage Instructions
1. Download the repository
2. Setup: we use [uv] (https://docs.astral.sh/uv/getting-started/installation/#standalone-installer) manager. To set up your environment, run:
```
uv sync
source .venv/bin/activate
```
3. In terminal:
To run gRPC: run
```python server_grpc.py```
To run our custom or JSON protocol: run
```python server.py --host <HOST> --port <PORT> --protocol <PROTOCOL>```
Default settings are 127.0.0.1, 65432, and 0. The 0 flag indicates a JSON protocol, and the 1 flag indicates a custom protocol. To host on multiple machines, get your IP address by running
```ipconfig getifaddr en0```
4. In new terminal:
To run gRPC: run
```python client_grpc.py```
To run our custom or JSON protocol: run
 ```python client_gui.py --host --port --protocol```.


### System Design 
**Stack**
- Backend: Python, SQLITE (database) 
- Frontend: Tkinter 

**File Structure:**
- client_gui.py: contains class definition for the GUI and starts the connection to client
- server.py: starts the connection to server
- database.py: contains all relevant queries to the database
- database_setup.py: initializes the database
- client_handler.py: handles sending requests and processing requests from the server on the client side.
- server_handler.py: handles processing requests from and sending responses to the client.
- codes.py: classifications for each request type 
- utils.py: contains functions for password hashing and using the custom protocol. 

**Protocols** 
  
There are two different types of protocols available: JSON and a custom wire protocol. Both protocols utilize a message structure consisting of a protoheader, header, and content:
- Protoheader: a fixed 4-byte header that contains information about the protocol version + header length
- Header: a variable-length header that contains metadata about the content of the message (encoding, length, and requested operation)
- Content: the client request/server response that contains actionable information and data 
The JSON protocol serializes/deserializes objects via JSON string, whereas our custom protocol encodes/decodes bytes. Initially, our wire protocol relied on piping (delimiting arguments with pipes '|'), but we have since switched to a recursive encoding/decoding protocol that prefixes all arguments with a "miniheader" containing their type and length. This allows us to reduce fragile casting, parse nested structures like lists or tuples, and place less restrictions on the types of messages a user is able to send over the network.

Example of recursive encoding:
- Raw data: [200, "hello", [8, False, 9]]
- Encoded data: <list,3><int,3>200<str,5>hello<list,3><int,1>8<bool,1>False<int,1>9

To see our engineering notebook, click [here](https://docs.google.com/document/d/1VgRHjW2I94al2vKQbMXU5OTpYC9vVg0mS-7m-KCjAWU/edit?usp=sharing).

Any and all feedback is appreciated! 



