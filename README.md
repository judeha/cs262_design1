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

Our application utilizes tkinter for the graphical interface (GUI) and SQLITE for the database. Further, there are two wire protocols implemented, JSON and custom, of which users can specifiy which protocol they want their messages to use in the command line interface. 

### Instructions for Usage
1. Download the repository
2. On Command Line Interface (CLI) run 'python server.py'
3. Open a new CLI window and run 'python client.py '--host --port --protocol'. We have defualt values for these three parameters. The protocol is set as a default to JSON (0), but you can opt into using the custom protocol by changing the flag to 1.


To learn more about our design and engineering process, particuarly on the thought process behind efficiency and scalability, click [here](https://docs.google.com/document/d/1VgRHjW2I94al2vKQbMXU5OTpYC9vVg0mS-7m-KCjAWU/edit?usp=sharing).

Any and all feedback is appreciated! 



