# 105 - DATA2410 Reliable Transport Protocol - DRTP
<!---
This is a submission for the homeexam for candidate 105. The project is a simple reliable data transfer protocol, that provides reliable data delivery on top of UDP. This protocol ensures that data is reliably delivered in-order without missing data or duplicate data.
-->

## Files

"application.py": contains the executable application

"server.py": contains the server-side code

"client.py": contains the client-side code

"utilityFuncitons.py": contains utility functions used by both the server and client

## Usage

1. download the source code

2. open the terminal in the directory of the "application.py" file

3. run the application with the python command shown bellow:

```sh

#starts the application in server mode

python3  ./application.py  -s

#starts the application is client mode

python3  ./application.py  -c  -f <filename>

```

## Generate Test Data

To test the application to generate data one launch two instances. One in server mode, and one in client mode. once a file transfer is complete, data from the file transfer will be printed out at the bottom of the terminal. To drop a datapacket, use the -d, --discard option with the sequence number of the packet that should be dropped. To increase or decrease the sending window size, use -w, --window option with the size of the sliding window size. To load the connection to procude more packet loss, use a larger file.

```sh

#starts the application in server mode, packet with seq = 8 will be dropped

python3  ./application.py  -s -d 8

#starts the application is client mode, the sliding window is now 10 packets at a time

python3  ./application.py  -c  -f <filename> -w 10

```

## Dependencies


The application was written in Python 3.12
