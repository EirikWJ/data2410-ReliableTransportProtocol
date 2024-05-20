from socket import * #socket object, sets up the connection
import sys #system, so i may close at the end
from utilityFunctions import * #gets the util functions
from utilityFunctions import waitFor2MSL  #didnt work to import this with *
from collections import deque #used to implement the sliding window protocol



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
    print(colours.BLUE+'\nConnection Establishment Phase:\n'+colours.WHITE)
    synSentCount=0 #keeps count of how many times it has sent syn, so it may terminate if it has sent it waaay to many times


    while True:
        if STATE == "CLOSED":
            #exp    signal to begin connection establishment to a Host
            #exp    sends SYN to the server
            packet = create_packet(0,0,8,b'')
            sock.sendto(packet, addr)     
            print(colours.BLUE+'SYN packet is sent'+colours.WHITE)
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
                    print(colours.BLUE+'SYN-ACK packet is received\nACK packet is sent'+colours.WHITE)                
                    packet = create_packet(ackno,seqno+1,4,b'')
                    sock.sendto(packet, addr)   
                    #exp    Waiting for 2msl were i dont expect any packets from the server
                    #exp    in the case i get a packet I will restart the connection establishment     
                    if waitFor2MSL(sock,addr,TIMEOUT):
                        print(colours.BLUE+'Connection established\n'+colours.WHITE)
                        STATE = "ESTABLISHED"
                        synSentCount = 0 #resetting the count
                    else: 
                        print(colours.YELLOW+'Unexpected packet received in Establishment phase'+colours.WHITE)   
                        STATE = "CLOSED"
                        continue
                elif syn and not ack and not fin and not reset:
                    #exp    got a SYN packet. uh-oh. May indicate
                    #exp    a "Simultaneous Open" situation, where
                    #exp    both parties tries to connect to one another 
                    #exp    I, however, wont let this pass. Will move to connection teardown
                    packet = create_packet(ackno,seqno+1,8,b'')
                    sock.sendto(packet, addr)
                    print(colours.BLUE+'SYN packet is received\nSYN ACK packet is sent'+colours.WHITE)
                    STATE = "TEARDOWN"#exp same as a SYN_RCVD state, just under diff name
                else: raise timeout
            except ConnectionResetError:
                #exp    there was some connectionproblems to the address
                #exp    will close down
                print(colours.BLUE+'\nConnection Failed\n'+colours.WHITE)
                break
            except timeout:
                #exp    didnt get any response from my SYN packet :(.
                #exp    probably packetloss, so will retransmitt the SYN packet
                if synSentCount < 3: 
                    print(colours.BLUE+'\nConnection Failed\n'+colours.WHITE)
                    break
                synSentCount+=1 #syn didnt go through, so ill have to send it agian. incrementing the count by 1
                STATE = "CLOSED"
                continue



        elif STATE == "ESTABLISHED":    
            print(colours.BLUE+'\nDATA Transfer:\n'+colours.WHITE)        
            EXPECTED_PACKET = seqno+1 #usually 1
            SEQ = ackno #usually 1
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
                print(colours.BLUE+getTimestamp()+f' -- packet with seq {SEQ} is sent, sliding window = {parse_window(Window)}'+colours.WHITE)
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
                        print(colours.BLUE+getTimestamp()+f' -- ACK for packet', *Acks,'is received'+colours.WHITE)
                        #exp    pops the left-most packet from the window and appends a new packet to the sendingwindow (the sliding window moves)
                        #exp    this happens as many times as the number of valid ACKs received
                        for i in Acks:
                            Window.popleft()
                            try:part = next(getPart)
                            except StopIteration:break
                            packet = create_packet(SEQ:=SEQ+1, EXPECTED_PACKET, 4, part) #updates the sequence number here by 1                           
                            Window.append(packet)
                            sock.sendto(packet, addr)
                            print(colours.BLUE+getTimestamp()+f' -- packet with seq {SEQ} is sent, sliding window = {parse_window(Window)}'+colours.WHITE)
                except timeout:
                    #exp    the sock.recvfrom() threw a timeout exception
                    #exp    means that is didnt get any data from the server
                    #exp    which indicates that not all the packets from the window
                    #exp    made it to the server. Will resend all packets in the window
                    #exp    with updatet acknos so indicate what packet the client wants next
                    print(colours.BLUE+getTimestamp()+f' -- RTO occured'+colours.WHITE)
                    GBN(Window, sock, addr, EXPECTED_PACKET)        
            #exp    the client sent all its packets and got an ack for
            #exp    all the packets sent as well. Moving to connection close.
            print(colours.BLUE+'\nDATA Finished\n\n'+colours.WHITE)            
            print(colours.BLUE+'Connection Teardown:\n'+colours.WHITE)
            STATE = "TEARDOWN"            



        elif STATE == "TEARDOWN":
            #exp    signal to begin closing of the connection is sent
            #exp    This is the FIN (1.step) of the 4-way handskake
            packet = create_packet(ackno,seqno+1,2,b'')
            sock.sendto(packet, addr) 
            print(colours.BLUE+'FIN packet is sent'+colours.WHITE)
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
                    print(colours.BLUE+'FIN packet is received\nACK packet is sent'+colours.WHITE)
                    STATE = "CLOSING"
                elif not syn and ack and fin and not reset:
                    #exp    got a FIN ACK packet. It came in bulk
                    #exp    but that is OK. will ACK the FIN
                    packet = create_packet(ackno,seqno+1,4,b'')
                    sock.sendto(packet, addr)
                    print(colours.BLUE+'FIN ACK packet is received\nACK packet is sent'+colours.WHITE)
                    STATE = "TIME_WAIT"
                elif not syn and ack and not fin and not reset:
                    #exp    got a ACK packet. Expecting FIN after
                    #exp    this packet. will wait :)
                    print(colours.BLUE+'ACK packet is received'+colours.WHITE)
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
                    print(colours.BLUE+'ACK packet is received'+colours.WHITE)
                    STATE = "TIME_WAIT"
                else: raise timeout
            except timeout:
                #exp    Never got ACK from the first FIN. ACK or FIN
                #exp    got lost. Will retransmitt the FIN and wait for ACK
                packet = create_packet(ackno,seqno+1,2,b'')
                sock.sendto(packet, addr)
                print(colours.BLUE+'FIN packet is sent'+colours.WHITE)
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
                    print(colours.BLUE+'FIN packet is received\nACK packet is sent'+colours.WHITE)
                    STATE = "TIME_WAIT"
                else: raise timeout
            except timeout: continue#exp    didnt get FIN. will wait for retransmittion from the Host.



        elif STATE == "TIME_WAIT":
            #exp    after sending the last ack, the client enters a waiting period
            #exp    if the client gets no packets in this period it will close.
            #exp    else if will send a new packet and enter a new waiting period
            if waitFor2MSL(sock,addr,TIMEOUT):
                print(colours.BLUE+'Connection Closes\n'+colours.WHITE)
                sock.close()
                sys.exit()
            else: continue