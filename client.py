from socket import *
import sys
from utilityFunctions import *
from collections import deque
import logging
import traceback



def Client(args):
    sock = socket(AF_INET, SOCK_DGRAM)
    ip,port = args.ip, args.port
    addr = (ip, port)
    
    fileName = args.file
    try:
        with open(fileName) as f:
            pass
    except FileNotFoundError:
        print(f'{fileName} was not found')
        return
    
    window_size = args.window
    Queue = deque()
    Window = deque()
    
    TIMEOUT = 0.5
    sock.settimeout(TIMEOUT)
    
    STATE = "CLOSED"
    print(bcolors.OKBLUE+'\nConnection Establishment Phase:\n'+bcolors.ENDC)
    
    #seqno = 0
    
    while True:
        if STATE == "CLOSED":
            #exp    signal to begin connection establishment to a Host
            packet = create_packet(0,0,8,b'')#------------------------------------------------------
            sock.sendto(packet, addr)     
            print(bcolors.OKBLUE+'SYN packet is sent'+bcolors.ENDC)
            STATE = "SYN_SENT"



        elif STATE == "SYN_SENT":
            sock.settimeout(2*TIMEOUT)#exp will wait for 2*msl before assuming everything to be OK
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                data = packet[6:]
                if syn and ack and not fin and not reset:
                    #exp    got the SYN-ACK packet, as expected.
                    #exp    will send ACK and wait for a green light
                    #exp    to send data
                    print(bcolors.OKBLUE+'SYN-ACK packet is received\nACK packet is sent'+bcolors.ENDC)                
                    packet = create_packet(ackno,seqno+1+len(data),4,b'')#------------------------------------------------------
                    sock.sendto(packet, addr)        
                    while True:
                        #exp    after sending ACK from SYNACK, the client will
                        #exp    wait for 2msl before assuming connection is all good
                        #exp    if an SYNACK packet is received, the client will resend
                        #exp    ACK and wait again.
                        try:
                            packet, addr = sock.recvfrom(1000)
                            seqno, ackno, flags = parse_header(packet)
                            syn, ack, fin, reset = parse_flags(flags)
                            data = packet[6:]
                            #exp    waiting for a unexpected packet that may indicate packetloss
                            if syn and ack and not fin and not reset:
                                #exp    got SYNACK. my ACK packet must have gotten lost
                                #exp    will retransmitt the ACK and wait for another period
                                packet = create_packet(ackno,seqno+1+len(data),4,b'')#------------------------------------------------------
                                sock.sendto(packet, addr)
                                print(bcolors.OKBLUE+'SYN-ACK packet is received\nACK packet is sent'+bcolors.ENDC)
                            else:
                                #exp    i got a packet, but it wasnt a SYNACK, it was
                                #exp    something else. will just close
                                STATE = "CLOSED"
                                sock.settimeout(TIMEOUT)
                                break
                        except timeout:
                            #exp    Nounexpected activity. the Connection is 
                            #exp    now considered established
                            print(bcolors.OKBLUE+'Connection established\n'+bcolors.ENDC)
                            STATE = "ESTABLISHED"
                            sock.settimeout(TIMEOUT)
                            break                        
                elif syn and not ack and not fin and not reset:
                    #exp    got a SYN packet. uh-oh. May indicate
                    #exp    a "Simultaneous Open" situation, where
                    #exp    both parties tries to connect to one another 
                    #exp    I, however, wont let this pass. Will move to connection teardown
                    packet = create_packet(ackno,seqno+1+len(data),8,b'')#------------------------------------------------------
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'SYN packet is received\nSYN ACK packet is sent'+bcolors.ENDC)
                    STATE = "TEARDOWN"#exp same as a SYN_RCVD state, just under diff name
                else: raise timeout
            except timeout:
                #exp    didnt get any response from my SYN packet :(.
                #exp    probably packetloss, so will retransmitt the SYN packet
                STATE = "CLOSED"
                sock.settimeout(TIMEOUT)
                continue



        elif STATE == "ESTABLISHED":    
            print(bcolors.OKBLUE+'\nDATA Transfer:\n'+bcolors.ENDC)             
            #TODO -----------------------------------------------------------------------------------------------------------------------------------------------------
            #       PACKET[  HEADER{  sequence  ,  acknowledge  ,  flags  }  +  DATA  ]
            #   sequence/seqno - i will send this byte
            #   acknowledge/ackno - this is the next byte i expect from you
            #   flags - what kind of packet is this
            #TODO -----------------------------------------------------------------------------------------------------------------------------------------------------         
            EXPECTED_PACKET = seqno +1
            MY_SEQ = ackno
            try:
                getPartFile = readFile(fileName)
                for i in range(0,window_size):
                    try:data = next(getPartFile)
                    except StopIteration:break
                    packet = create_packet(MY_SEQ, EXPECTED_PACKET, 4, data)
                    Window.append(packet)
                    sock.sendto(packet,addr)
                    print(bcolors.OKBLUE+getTimestamp()+f' -- packet with seqno = {parse_header(Window[len(Window)-1])[0]} is sent, sliding window = {getWinSeq(Window)}'+bcolors.ENDC)
                    MY_SEQ+=1            
            except FileNotFoundError:
                print(f'{fileName} was not found')
                STATE = "TEARDOWN"
                continue
            while Window:
                try:
                    packet, addr = sock.recvfrom(1000)
                    seqno, ackno, flags = parse_header(packet)
                    syn, ack, fin, reset = parse_flags(flags)
                    if ackno-1 >= EXPECTED_PACKET:
                        print(bcolors.OKBLUE+getTimestamp()+f' -- ACK for packet {ackno-1} is received'+bcolors.ENDC)
                        while EXPECTED_PACKET != ackno:
                            EXPECTED_PACKET+=1
                            Window.popleft()
                        while len(Window)!=window_size:
                            try:data = next(getPartFile)
                            except StopIteration:break
                            packet = create_packet(MY_SEQ, EXPECTED_PACKET, 4, data)
                            sock.sendto(packet, addr)
                            Window.append(packet)
                            print(bcolors.OKBLUE+getTimestamp()+f' -- packet with seqno = {parse_header(Window[len(Window)-1])[0]} is sent, sliding window = {getWinSeq(Window)}'+bcolors.ENDC)
                            MY_SEQ+=1
                    else:continue
                except timeout:
                    print(bcolors.OKBLUE+f'RTO occured'+bcolors.ENDC)
                    for packet in Window:
                        tmp = parse_header(packet)
                        new = create_packet(tmp[0], EXPECTED_PACKET, tmp[2], packet[6:])
                        sock.sendto(new,addr)
                        print(bcolors.OKBLUE+getTimestamp()+f' -- retransmitting packet with seq {parse_header(packet)[0]}'+bcolors.ENDC)
            #TODO -----------------------------------------------------------------------------------------------------------------------------------------------------          
            print(bcolors.OKBLUE+'\nDATA Finished\n\n'+bcolors.ENDC)            
            print(bcolors.OKBLUE+'Connection Teardown:\n'+bcolors.ENDC)
            STATE = "TEARDOWN"            



        elif STATE == "TEARDOWN":
            #exp    signal to begin closing of the connection is sent
            #exp    This is the FIN (1.step) of the 4-way handskake
            packet = create_packet(ackno,seqno+1,2,b'')#------------------------------------------------------
            sock.sendto(packet, addr)
            print(bcolors.OKBLUE+'FIN packet is sent'+bcolors.ENDC)
            STATE = "FIN_WAIT_1"



        elif STATE == "FIN_WAIT_1":
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                data = packet[6:]
                if not syn and not ack and fin and not reset:
                    #exp    got a FIN packet. ACK may be late 
                    #exp    or lost. will still ACK the FIN tho
                    packet = create_packet(ackno,seqno+1,4,b'')#------------------------------------------------------
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'FIN packet is received\nACK packet is sent'+bcolors.ENDC)
                    STATE = "CLOSING"
                elif not syn and ack and fin and not reset:
                    #exp    got a FIN ACK packet. It came in bulk
                    #exp    but that is OK. will ACK the FIN
                    packet = create_packet(ackno,seqno+1,4,b'')#------------------------------------------------------
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
                data = packet[6:]
                if not syn and ack and not fin and not reset:
                    #exp    got ACK from step 1. already got FIN and sent
                    #exp    an ACK in return for that. Ready for closing
                    print(bcolors.OKBLUE+'ACK packet is received'+bcolors.ENDC)
                    STATE = "TIME_WAIT"
                else: raise timeout
            except timeout:
                #exp    Never got ACK from the first FIN. ACK or FIN
                #exp    got lost. Will retransmitt the FIN and wait for ACK
                packet = create_packet(ackno,seqno+1,2,b'')#------------------------------------------------------
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'FIN packet is sent'+bcolors.ENDC)
                continue



        elif STATE == "FIN_WAIT_2":
            try:
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                data = packet[6:]
                if not syn and not ack and fin and not reset:
                #exp    got FIN packet. Will send ACK and wait 
                #exp    ready for closing
                    packet = create_packet(ackno,seqno+1,4,b'')#------------------------------------------------------
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'FIN packet is received\nACK packet is sent'+bcolors.ENDC)
                    STATE = "TIME_WAIT"
                else: raise timeout
            except timeout:
                #exp    didnt get FIN. will wait for retransmittion
                #exp    from the Host. 
                print(bcolors.WARNING+'did not get FIN'+bcolors.ENDC)
                continue



        elif STATE == "TIME_WAIT":
            sock.settimeout(2*TIMEOUT)#exp will wait for 2*msl before assuming everything to be OK
            try:
                #exp    waiting for closing...
                #exp    if everything goes as planned the timer will run
                #exp    out and will pick up again where the timeout-exception is caught.
                packet, addr = sock.recvfrom(1000)
                seqno, ackno, flags = parse_header(packet)
                syn, ack, fin, reset = parse_flags(flags)
                data = packet[6:]
                if not syn and not ack and fin and not reset:
                    #exp    got a FIN while waiting for 2msl. Must have been
                    #exp    packetloss or smt. will retransmitt ACK and wait again.
                    packet = create_packet(ackno,seqno+1,4,b'')#------------------------------------------------------
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'FIN packet is received\nACK packet is sent'+bcolors.ENDC)
                    continue
                else: raise timeout
            except timeout:
                #exp    didnt get any packets after sending the last ACK
                #exp    all must be good, and i may close the connection in grace
                print(bcolors.OKBLUE+'Connection Closes\n'+bcolors.ENDC)
                sock.close()
                sys.exit()