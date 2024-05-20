from socket import * #import socket module
import sys # In order to terminate the program
import time #used to take the time of the transmission        
from utilityFunctions import waitFor2MSL  #didnt work to import this with *                                                                                                                                                                       
from utilityFunctions import * #gets alle the util functions



def Server(args):  
    """
    *   Description:
    *   Uses a UDP socket
    *   Listens to packets in order to make a 3-way handshake with a client and establish a connection 
    *   Listens for datapackets and sends ACKs for the received packets. 
    *   Initiats a closedown when a FIN packet is received and responds accordingly
    *   in order to make a 4-way handskake with the client to ensure a propper closing of the connection
    *   Arguments:
    *   args: the arguments specified by the user in the startup phase
    *       ip: holds the ip address of the server
    *       port: port number of the server
    *       discard: custom testcase to skip a received packet with seq = parameter
    *   Returns:
    *   None
    """
    
    sock = socket(AF_INET, SOCK_DGRAM)
    try:sock.bind((args.ip, args.port))
    except OSError: #error if the port cannot be accessed
        print(colours.BLUE+'Port already in use'+colours.WHITE)
        return
    
    
    INTENTIONAL_DROP = args.discard #which packet do you want to drop?
    
    TIMEOUT = 0.5    #used when the server is waiting for a response
    ORG_TIMEOUT = None #the default
    sock.settimeout(ORG_TIMEOUT)
    
    start_time, end_time = 0,0#initialising some variables
    TOTAL_DATASIZE = 0
    
    STATE = "LISTEN" #initialising base state
    print(colours.BLUE+'\nServer Listening...\n'+colours.WHITE)



    while True:
        if STATE == "LISTEN":
            packet, addr = sock.recvfrom(1000)
            seqno, ackno, flags = parse_header(packet)
            syn, ack, fin, reset = parse_flags(flags)
            if syn and not ack and not fin and not reset:
                #exp    received a SYN packet. will send a SYN-ACK packet
                #exp    back to the sender
                EXPECTED_PACKET = seqno+1
                packet = create_packet(ackno, EXPECTED_PACKET, 12, b'')
                sock.sendto(packet, addr)
                print(colours.BLUE+'SYN packet is received\nSYN-ACK packet is sent'+colours.WHITE)
                STATE = "SYN_RCVD"



        elif STATE == "SYN_RCVD":
            sock.settimeout(TIMEOUT) #will wait for a response for a TIMEOUT amount of time
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                if not syn and ack and not fin and not reset:
                    #exp    got ACK from the previous SYN-ACK packet
                    #exp    the connection is all good.
                    print(colours.BLUE+'ACK packet is received\nConnection established\n'+colours.WHITE)
                    STATE = "ESTABLISHED"
                    EXPECTED_PACKET = 1 #i want 1 from the client next
                    SEQ = 1 #i am going to send 1 to the client
                    out_of_order_count = 0 #initialising the out-of-order count
                    sock.settimeout(ORG_TIMEOUT) #back to the original timeout
                    start_time = time.time() #what time does the transfer start?
                    TOTAL_DATA = b'' #total data transferred is initialised
                else: raise timeout
            except timeout:
                #exp    never got ACK packet from the sent SYN-ACK
                #exp    Will retransmitt the SYN-ACK packet 
                packet = create_packet(ackno, seqno+1, 12, b'')
                sock.sendto(packet, addr)
                print(colours.BLUE+'SYN-ACK packet is resent'+colours.WHITE)
                continue



        elif STATE == "ESTABLISHED":
            packet, addr = sock.recvfrom(1000)
            seqno, ackno, flags = parse_header(packet)
            syn, ack, fin, reset = parse_flags(flags)
            data = packet[6:]          
            if not syn and not fin and not reset:
                if seqno == INTENTIONAL_DROP :#exp  drops packet args.dicard
                    print(colours.YELLOW+getTimestamp()+f' -- packet {seqno} is dropped'+colours.WHITE)
                    INTENTIONAL_DROP = False #wont stumble here again
                    continue                
                if seqno == EXPECTED_PACKET:
                    #exp    the next "in-order" packet arrived. sets expected_packet
                    #exp    to the next "in-order" packet Sequence num and sends an ack
                    #exp    before incrementing the sequence num as well. Saves all data in
                    #exp    a variable before waiting for a new packet
                    print(colours.BLUE+getTimestamp()+f' -- Packet {seqno} is received'+colours.WHITE)
                    last_packet = data #got this packet
                    EXPECTED_PACKET+=1 #i want the next packet in-order to be this one!
                    TOTAL_DATA+=last_packet #all the data received
                    SEQ+=1 #updating the sequence number as i send new acks
                    out_of_order_count = 0 #i have gotten 0 out-of-order packets now
                    print(colours.BLUE+getTimestamp()+f' -- sending ack for the received {seqno}'+colours.WHITE)
                else:
                    #exp    sends ack for the last received packet
                    #exp    Server wants 2 but got 3, sends:
                    #exp    I want 3, I want 3, I want 3... until it gets 3
                    print(colours.BLUE+getTimestamp()+f' -- out-of-order packet {seqno} is received'+colours.WHITE)
                    out_of_order_count +=1   #got out of order; increasing the count
                #exp    if the server got an in-order packet                  
                packet = create_packet(SEQ, EXPECTED_PACKET, 4, b'')
                if out_of_order_count<3:sock.sendto(packet,addr) #aint sending acks for out of order packets if i get more than 3 out of order packets ina  row
            elif not syn and not ack and fin and not reset:
                #exp    got a FIN packet while the connection is established. 
                #exp    initiating a connection close by sending ACK, then moving
                #exp    to another STATE and then sending FIN.
                end_time = time.time() #the time which the transfer stopped
                packet = create_packet(ackno, seqno+1, 4, b'')
                sock.sendto(packet, addr)
                print(colours.BLUE+'\nFIN packet is received\nACK packet is sent'+colours.WHITE)
                STATE = "CLOSE_WAIT"



        elif STATE == "CLOSE_WAIT":
            #exp    sending FIN packet, im expecting a ACK packet from
            #exp    this packet before i will close the connection
            packet = create_packet(ackno, seqno+1, 2, b'')
            sock.sendto(packet, addr)
            print(colours.BLUE+'FIN packet is sent'+colours.WHITE)
            STATE = "LAST_ACK"



        elif STATE == "LAST_ACK":
            sock.settimeout(TIMEOUT)
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                data = packet[6:]
                if not syn and ack and not fin and not reset:
                    #exp    yay, i got an ACK from my FIN packet.
                    #exp    that means the sender got the FIN packet
                    #exp    and i may close the connection with grace
                    print(colours.BLUE+'ACK packet is received'+colours.WHITE)
                    sock.settimeout(ORG_TIMEOUT)
                    STATE = "CLOSING"              
                else:raise timeout
            except timeout:
                #exp    It seems i never got an ACK packet. 
                #exp    no matter. Will resend the FIN and wait for a new ACK.
                STATE = "CLOSE_WAIT"
                continue
            
            
        
        elif STATE == "CLOSING":
            if waitFor2MSL(sock,addr,TIMEOUT):
                lengthOfData = len(TOTAL_DATA) #all the data i got
                TOTAL_DATA = TOTAL_DATA[:lengthOfData-len(last_packet)] #all the data i got - the last packet i got. removing the last packet since it only contains the file type.
                file = uniqueFilename("../recFile"+last_packet.decode())
                try:
                    if not file:
                        print(colours.RED+f'OSError while creating new fileName {file}'+colours.WHITE)
                    else:
                        with open(file,'bx') as f:
                            f.write(TOTAL_DATA) #writes and creates a file of the data that i got
                            print(colours.GREEN+f'{file} was created'+colours.WHITE)
                except FileNotFoundError:
                    print(colours.RED+f'there is no such file'+colours.WHITE)
                TOTAL_DATASIZE = (lengthOfData*8)/10**6 # Byte*8 = bit -> bit /10^6 = Mb
                Throughput = calcThroughput(TOTAL_DATASIZE,end_time-start_time)
                print(colours.GREEN+f'{TOTAL_DATASIZE} Mb was sent in {round(end_time-start_time,3)} s',colours.WHITE)
                print(colours.BLUE+f'The throughput is {Throughput} Mbps')
                print(colours.BLUE+'Connection Closes\n'+colours.WHITE)
                sock.close()
                sys.exit()
                #!if the server should stay open/listening, you may comment out "sock.close() and sys.exit()"
                INTENTIONAL_DROP = args.discard #dropping the packet again
                sock.settimeout(ORG_TIMEOUT) #reset the timeout
                STATE = "LISTEN"
                print('-----------------------------------------------------------------------')
                print(colours.BLUE+'\nServer Listening...\n'+colours.WHITE)
                seqno = 0 #reseting the sequence number
            else:continue #will wait some more, cause i got a packet i didnt want