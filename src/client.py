from socket import *
import sys
from utilityFunctions import *
from utilityFunctions import waitFor2MSL  
from collections import deque



def Client(args):
    """
    *   Description:
    *   Uses a UDP socket
    *   Uses a 3-way handshake to ensure a connection to the server
    *   Transfers data with the size of the window as a number of in-air packets
    *   and only moving the window when an ACK for the left most packet in the window is received
    *   Uses a 4-way handskake to ensure a propper closing of the connection and the programme.    
    *   Arguments:
    *   args: the arguments specified by the user in the startup phase
    *       ip: holds the ip address of the server
    *       port: port number of the server
    *       windowsize: the size of the sliding window used to transmitt packets
    *       file: The file which is whished to be transferred to the server
    *   Returns:
    *   None
    """
    
    #exp    defines the client socket "sock" and the addres
    #exp    for the server/recipient
    sock = socket(AF_INET, SOCK_DGRAM)
    addr = (args.ip, args.port)
    
    #exp    defines the slidingwindow list and the size of the sliding window
    window_size = args.window
    Window = deque()
    
    #exp    sets the timeout to 500ms
    TIMEOUT = 0.5
    sock.settimeout(TIMEOUT)
    
    #exp    initiates the starting STATE
    STATE = "CLOSED"
    print(bcolors.OKBLUE+'\nConnection Establishment Phase:\n'+bcolors.ENDC)



    while True:
        if STATE == "CLOSED":
            #exp    signal to begin connection establishment to a Host
            #exp    sends SYN to the server
            packet = create_packet(0,0,8,b'')
            sock.sendto(packet, addr)     
            print(bcolors.OKBLUE+'SYN packet is sent'+bcolors.ENDC)
            STATE = "SYN_SENT"



        elif STATE == "SYN_SENT":
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                if syn and ack and not fin and not reset:
                    #exp    got the SYN-ACK packet, as expected.
                    #exp    will send ACK and wait for a green light
                    #exp    to send data
                    print(bcolors.OKBLUE+'SYN-ACK packet is received\nACK packet is sent'+bcolors.ENDC)                
                    packet = create_packet(ackno,seqno+1,4,b'')
                    sock.sendto(packet, addr)   
                    #exp    Waiting for 2msl were i dont expect any packets from the server
                    #exp    in the case i get a packet I will restart the connection establishment     
                    if waitFor2MSL(sock,addr,TIMEOUT):
                        print(bcolors.OKBLUE+'Connection established\n'+bcolors.ENDC)
                        STATE = "ESTABLISHED"
                    else: 
                        print(bcolors.WARNING+'Unexpected packet received in Establishment phase'+bcolors.ENDC)   
                        STATE = "CLOSED"
                        continue
                elif syn and not ack and not fin and not reset:
                    #exp    got a SYN packet. uh-oh. May indicate
                    #exp    a "Simultaneous Open" situation, where
                    #exp    both parties tries to connect to one another 
                    #exp    I, however, wont let this pass. Will move to connection teardown
                    packet = create_packet(ackno,seqno+1,8,b'')
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'SYN packet is received\nSYN ACK packet is sent'+bcolors.ENDC)
                    STATE = "TEARDOWN"#exp same as a SYN_RCVD state, just under diff name
                else: raise timeout
            except ConnectionResetError:
                #exp    there was some connectionproblems to the address
                #exp    will close down
                print(bcolors.OKBLUE+'\nConnection Failed\n'+bcolors.ENDC)
                break
            except timeout:
                #exp    didnt get any response from my SYN packet :(.
                #exp    probably packetloss, so will retransmitt the SYN packet
                print(bcolors.OKBLUE+'\nConnection Failed\n'+bcolors.ENDC)
                STATE = "CLOSED"
                continue



        elif STATE == "ESTABLISHED":    
            print(bcolors.OKBLUE+'\nDATA Transfer:\n'+bcolors.ENDC)        
            EXPECTED_PACKET = seqno+1
            SEQ = ackno
            getPart = readFile(args.file)
            #exp    uses a generator function to call the next part of the file
            #exp    the sequence number is the sequence number of the last packet sent + 1
            #exp    the Window size dictates how many packets should be sent at the beginning.
            for SEQ in range(SEQ, window_size+1):
                try: part = next(getPart)
                except StopIteration: break
                packet = create_packet(SEQ, EXPECTED_PACKET, 4, part)
                sock.sendto(packet,addr)
                Window.append(packet)
                print(bcolors.OKBLUE+getTimestamp()+f' -- packet with seq {SEQ} is sent, sliding window = {parse_window(Window)}'+bcolors.ENDC)
            while Window:
                try:
                    packet, addr = sock.recvfrom(1000)
                    seqno, ackno, flags = parse_header(packet)
                    syn, ack, fin, reset = parse_flags(flags)
                    if EXPECTED_PACKET <= ackno-1:
                        #exp    sends seqno's from the expected packet to the one client just got
                        #exp    happens in the case of cumulative acks received. In regular flow it becomes a list of 
                        #exp    one seqno, which is the next expected packet. 
                        #exp    the length of Acks is how many valid ACKs the client got
                        Acks = list(range(EXPECTED_PACKET, ackno))
                        EXPECTED_PACKET = ackno
                        print(bcolors.OKBLUE+getTimestamp()+f' -- ACK for packet', *Acks,'is received'+bcolors.ENDC)
                        #exp    pops the left-most packet from the window and appends a new packet to the sendingwindow (the sliding window moves)
                        #exp    this happens as many times as the number of valid ACKs received
                        for i in Acks:
                            Window.popleft()
                            try:part = next(getPart)
                            except StopIteration:break
                            packet = create_packet(SEQ:=SEQ+1, EXPECTED_PACKET, 4, part)                            
                            Window.append(packet)
                            sock.sendto(packet, addr)
                            print(bcolors.OKBLUE+getTimestamp()+f' -- packet with seq {SEQ} is sent, sliding window = {parse_window(Window)}'+bcolors.ENDC)
                except timeout:
                    #exp    the sock.recvfrom() threw a timeout exception
                    #exp    means that is didnt get any data from the server
                    #exp    which indicates that not all the packets from the window
                    #exp    made it to the server. Will resend all packets in the window
                    #exp    with updatet acknos so indicate what packet the client wants next
                    print(bcolors.OKBLUE+getTimestamp()+f' -- RTO occured'+bcolors.ENDC)
                    GBN(Window, sock, addr, EXPECTED_PACKET)        
            #exp    the client sent all its packets and got an ack for
            #exp    all the packets sent as well. Moving to connection close.
            print(bcolors.OKBLUE+'\nDATA Finished\n\n'+bcolors.ENDC)            
            print(bcolors.OKBLUE+'Connection Teardown:\n'+bcolors.ENDC)
            STATE = "TEARDOWN"            



        elif STATE == "TEARDOWN":
            #exp    signal to begin closing of the connection is sent
            #exp    This is the FIN (1.step) of the 4-way handskake
            packet = create_packet(ackno,seqno+1,2,b'')
            sock.sendto(packet, addr)
            print(bcolors.OKBLUE+'FIN packet is sent'+bcolors.ENDC)
            STATE = "FIN_WAIT_1"



        elif STATE == "FIN_WAIT_1":
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                if not syn and not ack and fin and not reset:
                    #exp    got a FIN packet. ACK may be late 
                    #exp    or lost. will still ACK the FIN tho
                    packet = create_packet(ackno,seqno+1,4,b'')
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'FIN packet is received\nACK packet is sent'+bcolors.ENDC)
                    STATE = "CLOSING"
                elif not syn and ack and fin and not reset:
                    #exp    got a FIN ACK packet. It came in bulk
                    #exp    but that is OK. will ACK the FIN
                    packet = create_packet(ackno,seqno+1,4,b'')
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'FIN ACK packet is received\nACK packet is sent'+bcolors.ENDC)
                    STATE = "TIME_WAIT"
                elif not syn and ack and not fin and not reset:
                    #exp    got a ACK packet. Expecting FIN after
                    #exp    this packet. will wait :)
                    print(bcolors.OKBLUE+'ACK packet is received'+bcolors.ENDC)
                    STATE = "FIN_WAIT_2"
                else: raise timeout
            except timeout:
                #exp   packetloss or unexpected packet arrived. Will
                #exp    retransmitt packets from the first FIN
                STATE = "TEARDOWN"
                continue            



        elif STATE == "CLOSING":
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                if not syn and ack and not fin and not reset:
                    #exp    got ACK from step 1. already got FIN and sent
                    #exp    an ACK in return for that. Ready for closing
                    print(bcolors.OKBLUE+'ACK packet is received'+bcolors.ENDC)
                    STATE = "TIME_WAIT"
                else: raise timeout
            except timeout:
                #exp    Never got ACK from the first FIN. ACK or FIN
                #exp    got lost. Will retransmitt the FIN and wait for ACK
                packet = create_packet(ackno,seqno+1,2,b'')
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'FIN packet is sent'+bcolors.ENDC)
                continue



        elif STATE == "FIN_WAIT_2":
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                if not syn and not ack and fin and not reset:
                #exp    got FIN packet. Will send ACK and wait 
                #exp    ready for closing
                    packet = create_packet(ackno,seqno+1,4,b'')
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'FIN packet is received\nACK packet is sent'+bcolors.ENDC)
                    STATE = "TIME_WAIT"
                else: raise timeout
            except timeout: continue#exp    didnt get FIN. will wait for retransmittion from the Host.



        elif STATE == "TIME_WAIT":
            #exp    after sending the last ack, the client enters a waiting period
            #exp    if the client gets no packets in this period it will close.
            #exp    else if will send a new packet and enter a new waiting period
            if waitFor2MSL(sock,addr,TIMEOUT):
                print(bcolors.OKBLUE+'Connection Closes\n'+bcolors.ENDC)
                sock.close()
                sys.exit()
            else: continue