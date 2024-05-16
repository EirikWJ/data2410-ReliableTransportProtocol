from socket import * #import socket module
import sys # In order to terminate the program
from utilityFunctions import *
from collections import deque
import logging
import traceback
import time                                                                                                                                                                                         



def Server(args):                                                                                               
    sock = socket(AF_INET, SOCK_DGRAM)
    ip,port = args.ip,args.port 
    sock.bind((ip, port))
    
    
    INTENTIONAL_DROP = args.discard
    INTENTIONAL_DROP_ACK1 = False
    
    TIMEOUT = 0.5
    
    ORG_TIMEOUT = 30#TODO sette denne til None før levering. eller la den bli på 30? har ikke bestemt enda    
    sock.settimeout(ORG_TIMEOUT)
    start_time, end_time = 0,0
    TOTAL_DATASIZE = 0
        
    STATE = "LISTEN"
    print(bcolors.OKBLUE+'\nServer Listening...\n'+bcolors.ENDC)
    
    #seqno = 0
    
    while True:
        if STATE == "LISTEN":
            packet, addr = sock.recvfrom(1000)
            seqno, ackno, flags = parse_header(packet)
            syn, ack, fin, reset = parse_flags(flags)
            data = packet[6:]
            if syn and not ack and not fin and not reset:
                #exp    received a SYN packet. will resent a SYN-ACK packet
                #exp    back to the sender
                EXPECTED_PACKET = seqno+1
                packet = create_packet(ackno, EXPECTED_PACKET, 12, b'')#------------------------------------------------------
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'SYN packet is received\nSYN-ACK packet is sent'+bcolors.ENDC)
                STATE = "SYN_RCVD"



        elif STATE == "SYN_RCVD":
            sock.settimeout(TIMEOUT)
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                data = packet[6:]
                if not syn and ack and not fin and not reset:
                    #exp    got ACK from the previous SYN-ACK packet
                    #exp    the connection is all good.
                    print(bcolors.OKBLUE+'ACK packet is received\nConnection established\n'+bcolors.ENDC)
                    STATE = "ESTABLISHED"
                    EXPECTED_PACKET = 1
                    sock.settimeout(ORG_TIMEOUT)
                    start_time = time.time()
                    MY_SEQ = 0
                    TOTAL_DATA = b''
                else: raise timeout
            except timeout:
                #exp    never got ACK packet from the sent SYN-ACK
                #exp    Will retransmitt the SYN-ACK packet 
                EXPECTED_PACKET = seqno+1 
                packet = create_packet(ackno, EXPECTED_PACKET, 12, b'')#------------------------------------------------------
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'SYN-ACK packet is resent'+bcolors.ENDC)
                continue


        elif STATE == "ESTABLISHED":
            packet, addr = sock.recvfrom(1000)
            seqno, ackno, flags = parse_header(packet)
            syn, ack, fin, reset = parse_flags(flags)
            data = packet[6:]
            
            
            if not syn and not fin and not reset:
            #TODO ---------------------------------------------------------------------------------------------------------------
            #       PACKET[  HEADER{  sequence  ,  acknowledge  ,  flags  }  +  DATA  ]
            #   sequence/seqno - i will send this byte
            #   acknowledge/ackno - this is the next byte i expect from you
            #   flags - what kind of packet is this
            #TODO --------------------------------------------------------------------------------------------------------------------------------
                if seqno == INTENTIONAL_DROP:#!drops packet
                    print(bcolors.WARNING+f' -- packet {seqno} is dropped'+bcolors.ENDC)
                    INTENTIONAL_DROP = False
                    continue
                if seqno == EXPECTED_PACKET:#*Packet received IN-ORDER
                    print(bcolors.OKBLUE+getTimestamp()+f' -- packet {seqno} is received'+bcolors.ENDC)
                    print(bcolors.OKBLUE+getTimestamp()+f' -- sending ack for the received {seqno}'+bcolors.ENDC)
                    EXPECTED_PACKET=seqno+1
                    MY_SEQ+=1
                    TOTAL_DATA += data
                else:
                    print(bcolors.OKBLUE+getTimestamp()+f' -- out-of-order packet {seqno} is received'+bcolors.ENDC)
                packet = create_packet(MY_SEQ,EXPECTED_PACKET,4,b'')
                if seqno != 5 and seqno!=6 and seqno!=False:sock.sendto(packet,addr)#!drops ack
                
            #TODO -------------------------------------------------------------------------------------------------------------------
            elif not syn and not ack and fin and not reset:
                #exp    got a FIN packet while the connection is established. 
                #exp    initiating a connection close by sending ACK, then moving
                #exp    to another STATE and then sending FIN.
                packet = create_packet(ackno, seqno+1, 4, b'')#------------------------------------------------------
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'\nFIN packet is received\nACK packet is sent'+bcolors.ENDC)
                STATE = "CLOSE_WAIT"



        elif STATE == "CLOSE_WAIT":
            end_time = time.time()
            #exp    sending FIN packet, im expecting a ACK packet from
            #exp    this packet before i will close the connection
            packet = create_packet(ackno, seqno+1, 2, b'')#------------------------------------------------------
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
            sock.settimeout(2*TIMEOUT)
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                data = packet[6:]
                if not syn and not ack and fin and not reset:
                    print(bcolors.OKBLUE+'FIN packet received\nACK packet is sent'+bcolors.ENDC)
                    packet = create_packet(ackno,seqno+1,4,b'')#------------------------------------------------------
                    sock.sendto(packet,addr)
                else:raise timeout
            except timeout:
                file = nextnonexistent("../Photo/recPhoto.jpg")
                with open(file,'bx') as f:
                    f.write(TOTAL_DATA)
                    print('wrote Data to file')
                TOTAL_DATASIZE = (len(TOTAL_DATA)*8)/10**6 # Byte*8 = bit -> bit /10^6 = Mb
                Throughput = calcThroughput(TOTAL_DATASIZE,end_time-start_time)
                print(bcolors.OKBLUE+f'Total size:', TOTAL_DATASIZE,'Mb',bcolors.ENDC)
                print(bcolors.OKBLUE+f'Transfertime:', round(end_time-start_time,3),'s',bcolors.ENDC)
                print(bcolors.OKBLUE+f'The throughput is {Throughput} Mbps')
                print(bcolors.OKBLUE+'Connection Closes\n'+bcolors.ENDC)
                #!sock.close()
                #!sys.exit()
                sock.settimeout(ORG_TIMEOUT)
                STATE = "LISTEN"
                print('-----------------------------------------------------------------------')
                print(bcolors.OKBLUE+'\nServer Listening...\n'+bcolors.ENDC)
                seqno = 0