from socket import * #import socket module
import sys # In order to terminate the program
import time         
from utilityFunctions import waitFor2MSL                                                                                                                                                                                
from utilityFunctions import *



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
    except OSError:
        print(bcolors.OKBLUE+'Port already in use'+bcolors.ENDC)
        return
    
    
    INTENTIONAL_DROP = args.discard
    
    TIMEOUT = 0.5    
    ORG_TIMEOUT = None
    sock.settimeout(ORG_TIMEOUT)
    
    start_time, end_time = 0,0
    TOTAL_DATASIZE = 0
    
    STATE = "LISTEN"
    print(bcolors.OKBLUE+'\nServer Listening...\n'+bcolors.ENDC)



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
                print(bcolors.OKBLUE+'SYN packet is received\nSYN-ACK packet is sent'+bcolors.ENDC)
                STATE = "SYN_RCVD"



        elif STATE == "SYN_RCVD":
            sock.settimeout(TIMEOUT)
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                if not syn and ack and not fin and not reset:
                    #exp    got ACK from the previous SYN-ACK packet
                    #exp    the connection is all good.
                    print(bcolors.OKBLUE+'ACK packet is received\nConnection established\n'+bcolors.ENDC)
                    STATE = "ESTABLISHED"
                    EXPECTED_PACKET = 1
                    SEQ = 1
                    out_of_order_count = 0
                    sock.settimeout(ORG_TIMEOUT)
                    start_time = time.time()
                    TOTAL_DATA = b''
                else: raise timeout
            except timeout:
                #exp    never got ACK packet from the sent SYN-ACK
                #exp    Will retransmitt the SYN-ACK packet 
                packet = create_packet(ackno, seqno+1, 12, b'')
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'SYN-ACK packet is resent'+bcolors.ENDC)
                continue



        elif STATE == "ESTABLISHED":
            packet, addr = sock.recvfrom(1000)
            seqno, ackno, flags = parse_header(packet)
            syn, ack, fin, reset = parse_flags(flags)
            data = packet[6:]          
            if not syn and not fin and not reset:
                if seqno == INTENTIONAL_DROP :#exp  drops packet args.dicard
                    print(bcolors.WARNING+getTimestamp()+f' -- packet {seqno} is dropped'+bcolors.ENDC)
                    INTENTIONAL_DROP = False
                    continue                
                if seqno == EXPECTED_PACKET:
                    #exp    the next "in-order" packet arrived. sets expected_packet
                    #exp    to the next "in-order" packet Sequence num and sends an ack
                    #exp    before incrementing the sequence num as well. Saves all data in
                    #exp    a variable before waiting for a new packet
                    print(bcolors.OKBLUE+getTimestamp()+f' -- Packet {seqno} is received'+bcolors.ENDC)
                    EXPECTED_PACKET+=1
                    TOTAL_DATA+=data
                    SEQ+=1
                    out_of_order_count = 0
                    print(bcolors.OKBLUE+getTimestamp()+f' -- sending ack for the received {seqno}'+bcolors.ENDC)
                else:
                    #exp    sends ack for the last received packet
                    #exp    Server wants 2 but got 3, sends:
                    #exp    I want 3, I want 3, I want 3... until it gets 3
                    print(bcolors.OKBLUE+getTimestamp()+f' -- out-of-order packet {seqno} is received'+bcolors.ENDC)
                    out_of_order_count +=1   
                #exp    if the server got an in-order packet                  
                packet = create_packet(SEQ, EXPECTED_PACKET, 4, b'')
                if out_of_order_count<3:sock.sendto(packet,addr)
            elif not syn and not ack and fin and not reset:
                #exp    got a FIN packet while the connection is established. 
                #exp    initiating a connection close by sending ACK, then moving
                #exp    to another STATE and then sending FIN.
                end_time = time.time()
                packet = create_packet(ackno, seqno+1, 4, b'')
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'\nFIN packet is received\nACK packet is sent'+bcolors.ENDC)
                STATE = "CLOSE_WAIT"



        elif STATE == "CLOSE_WAIT":
            #exp    sending FIN packet, im expecting a ACK packet from
            #exp    this packet before i will close the connection
            packet = create_packet(ackno, seqno+1, 2, b'')
            sock.sendto(packet, addr)
            print(bcolors.OKBLUE+'FIN packet is sent'+bcolors.ENDC)
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
                    print(bcolors.OKBLUE+'ACK packet is received'+bcolors.ENDC)
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
                file = nextnonexistent("../Photo/recPhoto.jpg")
                if not file:break
                with open(file,'bx') as f:
                    f.write(TOTAL_DATA)
                    pass
                TOTAL_DATASIZE = (len(TOTAL_DATA)*8)/10**6 # Byte*8 = bit -> bit /10^6 = Mb
                Throughput = calcThroughput(TOTAL_DATASIZE,end_time-start_time)
                print(bcolors.OKGREEN+f'{TOTAL_DATASIZE} Mb was sent in {round(end_time-start_time,3)} s',bcolors.ENDC)
                print(bcolors.OKBLUE+f'The throughput is {Throughput} Mbps')
                print(bcolors.OKBLUE+'Connection Closes\n'+bcolors.ENDC)
                sock.close()
                sys.exit()
                #!if the server should stay open/listening, you may comment out "sock.close() and sys.exit()"
                sock.settimeout(ORG_TIMEOUT)
                STATE = "LISTEN"
                print('-----------------------------------------------------------------------')
                print(bcolors.OKBLUE+'\nServer Listening...\n'+bcolors.ENDC)
                seqno = 0
            else:continue            