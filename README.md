# CS262 Design Challenge #1: Multi-Client Server Chat

### Description
In this design excercise, we built a simple, client-server chat application that allows multiple users to send and receive text messgages from a centralized server. The application allows the following operations: 
1. Creating an account. The user supplies a unique (login) name. If there is already an account with that name, the user is prompted for the password. If the name is not being used, the user is prompted to supply a password. The password is encrypted before being sent to the server. 
2. Log in to an account. Using a login name and password, log into an account. An incorrect login or bad user name should display an error. A successful login should display the number of unread messages.
3. List accounts: Users are able to see a list of current accounts on the server.
4. Send a message to a recipient. If the recipient is logged in, deliver immediately; if not the message should be stored until the recipient logs in and requests to see the message.
5. Read messages. If there are undelivered messages, display those messages. The user should be able to specify the number of messages they want delivered at any single time.
6. Delete a message or set of messages. Once deleted messages are gone.
7. Delete an account. You will need to specify the semantics of deleting an account that contains unread messages.

### Usage Instructions
1. Download the repository
2. On Command Line Interface (CLI) run 'python server.py [host] [port] [protocol]', where protocol = 0 refers to the JSON protocol and protocol = 1 refers to the custom protocol. 
3. Open a new CLI window and run 'python client_gui.py --host --port --protocol'. We have defualt values for these three parameters. The protocol is set as a default to JSON (0), but you can opt into using the custom protocol by changing the flag to 1.

When on the GUI, to delete messages, type in the list of message ids separated by commas. Ex: <5,6>. 

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
  
There are two different types of protocols available: JSON and a custom binary protocol. Both protocols use the exact same structure for the requests where there is a protoheader, header, request, and response. The protoheader provides metadata about the header, the header provides metadata about the request, the request specifies the type of request (i.e., login, read_message), and the response contains the information the server will send back to the client. The JSON protocol will encode and decode the request in the form of JSON string, whereas our custom binary protocol encodes/decodes bytes. Initially the custom protocol used to decode by identifying pipes ('|'), but we switched over to utilizing a recursive header to avoid casting everything and also be able to parse lists/tuples. It would also place less restrictions on the user in terms of the types of messages they are able to send over the network. To specify which protocol to use for the application, type 0 for JSON and 1 for custom. 


To learn more about our design and engineering process, particuarly on the thought process behind efficiency and scalability, click [here](https://docs.google.com/document/d/1VgRHjW2I94al2vKQbMXU5OTpYC9vVg0mS-7m-KCjAWU/edit?usp=sharing).

Any and all feedback is appreciated! 



