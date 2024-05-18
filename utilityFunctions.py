from struct import *
from datetime import datetime
import os
from socket import timeout

header_format = '!HHH'#exp  the header format used in the programme. 6 bytes in total. 2+2+2. seq, ack and flags

def GBN(Window, sock, addr, EXPECTED_PACKET):
    """
    *   Description:
    *   resends all the packets that are currently in the Window queue with same
    *   sequence number and data, but with updated acknowledgement number to match
    *   what the client is expecting. 
    *   Arguments:
    *   Window: the Window deque that holds the packets that are in the sendingwindow
    *   sock: holds the UDP socketobject 
    *   addr: holds the address used to transfer data between the server and client
    *   EXPECTED_PACKET: the next sequence number that the programme is expecting to receive.
    *   Returns:None
    """
    for packet in Window:
        seqno, ackno, flags = parse_header(packet)
        packet = create_packet(seqno, EXPECTED_PACKET, flags,packet[6:])
        print(bcolors.OKBLUE+getTimestamp()+f' -- retransmitting packet with seq = {seqno}'+bcolors.ENDC)
        sock.sendto(packet, addr)

def create_packet(seq, ack, flags, data):
    """
    *   Description:
    *   creates a packet with a parameter sequence number,
    *   acknowlegdement number, specified flags and some data.
    *   the header gets converted to a byte-string that is in the format
    *   of the header_format variable, and gets conbined with the data byte-string
    *   before being returned.
    *   Arguments:
    *   seq: Holds the sequence number of the packet
    *   ack: Holds the acknowledgement number of the packet
    *   flags: Holds the flags of the packet in decimal format (5 = 0101)
    *   data: Holds the data that gets packed in the packet
    *   Returns: the finished packet in byte format. Used to make a propper packet that may easily be deconstructed later
    """
    header = pack(header_format, seq, ack, flags)
    return header + data

def parse_header(packet):
    """
    *   Description:
    *   This function unpacks the datapacket and returns the header only.
    *   the unpack funciton takes the header_format and the datapackets header as arguments
    *   and returns a touple of the parsed header elements.
    *   Arguments:
    *   packet: Contains the packet in byte format
    *   Returns: a touple containing the seq,ack and flags of the packet. used to get information about the packet easily
    """
    return unpack(header_format, packet[:6])

def parse_flags(flags):
    """
    *   Description:
    *   This function takes the flag from a packet header and returns the flags as a touple.
    *   it checks every bit, and if the current bit is set the corresponding flag will be a
    *   True value (non-zero integer), else it will be a False value (zero). 
    *   Arguments:
    *   flags: contains the flags of the packet in decimal format. (5 = 0101) 
    *   Returns:
    *   A touple containing the syn,ack,fin and reset flag og the packet that holds the passed the flags. 
    *   used to easily read out data from a received packet.
    """
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    reset = flags & (1 << 0)
    return syn, ack, fin, reset

class bcolors:
    """
    !   Not my code
    *   colours that are used in prints for better readability
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
def readFile(fileName):
    """
    *   Description:
    *   a generator function that opens a specified file and reads it out 
    *   to the user in chunks. The while loop will run as long as f.read(994) is
    *   not a False value, aka the part variable that gets the data-value from f.read()
    *   is not empty. Will only work for python 3.8 and up, since thats when the := operator 
    *   was added
    *   Arguments:
    *   fileName: Holds the filename of the desired file to be transferred.
    *   Returns/yields:
    *   part: a cronological datapiece of the file that is suppossed to be transferred. Used to send the file in small spieces..
    *   b'0': in the case of an error it returns nothing
    """
    try:
        with open(fileName, 'rb') as f:
            while part := f.read(994):
                yield part
    except IOError:
        return b''



def getTimestamp():
    """
    *   Description:
    *   returns the current timestamp
    *   Returns:
    *   the current time formated in Hours:Minuttes:seconds.Milliseconds. Used for readability in prints
    """
    return datetime.now().strftime('%H:%M:%S.%f')

def parse_window(list):
    """
    !   Not my code
    *   Description:
    *   takes in a list of packets and returns a new list that contains the sequence numbers
    *   of the original packets. It exstracts the sequence numbers from the packets, basicly.
    *   It also removes the bracets [] and replaces them with curly bracets {} in order to mimic
    *   the output snippet in the task. The curly bracets thing is not necessary.
    *   Arguments:
    *   list: the list that is wished to be parsed
    *   Returns:
    *   A list of the sequence numbers of the packets that are currently in the sending window. Used for clearity in prints
    """
    arr = []
    for i in list:
        arr.append(parse_header(i)[0])
    ret = '{' + ', '.join([str(x) for x in arr]) + '}'
    return ret

def calcThroughput(size, time):
    """
    !   Not my code
    *   Description:
    *   throughput value to a string. then finds the position of the comma. 
    *   then iterates over every number and finds the first non zero number.
    *   it then returns the meassured throughtput with two non-zero decimals  in it.
    *   as done in the server output snippet in the task.
    *   Arguments:
    *   size: the total size of the sent data in megabits
    *   time: the total time spent transferring data in seconds
    *   Returns:
    *   the throughput in megabits per second with 2 non-zero decimals. In order to meassure the effectiveness of the programme   
    """
    if not size: return 0
    num_str = str(size/time)
    decimal_index = str(size/time).index('.') + 1
    while num_str[decimal_index] == '0':
        decimal_index += 1
    return num_str[:decimal_index + 2]

def nextnonexistent(f):
    """
    !   Not my code
    *   Description:
    *   Code to check if a file named what the server wants to name the recreated 
    *   the received picture/file exists in the specified location. In the case
    *   of an already existing file with the same name, the server will name the file
    *   FILENAME +_i, where i is the next positive integer.
    *   Arguments:
    *   f: holds the filename of the file that should hold the transferred data
    *   Returns:
    *   fnew: the new and unique filename. Used to save the transferred data to disk without running into duplicate filenames
    *   False: in case of error in creating a new filename
    """
    try:
        fnew = f
        root, ext = os.path.splitext(f)
        i = 0
        while os.path.exists(fnew):
            i += 1
            fnew = '%s_%i%s' % (root, i, ext)
        return fnew
    except OSError:
        return False

def waitFor2MSL(sock,addr,TIMEOUT):
    """
    *   Description:
    *   the client or server enters a state of waiting, where it will wait for 2*msl (2*normal timeout)
    *   to ensure that the last packet is received without receiving an ack. Normally happens when the client
    *   send ACK in the 3-way handshake, or ACK in the 4-way handshake. For the server, this happens when it received
    *   ACK from the server's FIN in the 4-way handshake. it waits to ensure the other party has nothing more to say
    *   before closing
    *   Arguments:
    *   sock: holds the UDP socketobject 
    *   addr: holds the address used to transfer data between the server and client
    *   TIMEOUT: holds the timeout of the client and or the server. 
    *   Returns: 
    *   False: if the programme received a non-expected packet. E.G not SYN-ACK of FIN. Usecases may vary, depending where in the programme the funciton is used
    *   True: if the programme did not get any packets in the waitingperiod. used to confirm that packets arrived without packetloss
    """
    while True:
        sock.settimeout(2*TIMEOUT)#exp will wait for 2*msl before assuming everything to be OK
        try:
            packet, addr = sock.recvfrom(1000)
            seqno, ackno, flags = parse_header(packet)
            syn, ack, fin, reset = parse_flags(flags)
            #exp    waiting for a unexpected packet that may indicate packetloss
            if syn and ack and not fin and not reset:
                #exp    got SYNACK. my ACK packet must have gotten lost
                #exp    will retransmitt the ACK and wait for another period
                packet = create_packet(ackno,seqno+1,4,b'')
                sock.sendto(packet, addr)
                print(bcolors.OKBLUE+'SYN-ACK packet is received\nACK packet is sent'+bcolors.ENDC)
            elif not syn and not ack and fin and not reset:
                    #exp    got a FIN. Must have been packetloss or something. 
                    #exp    will retransmitt ACK and wait again.
                    packet = create_packet(ackno,seqno+1,4,b'')
                    sock.sendto(packet, addr)
                    print(bcolors.OKBLUE+'FIN packet is received\nACK packet is sent'+bcolors.ENDC)
            else:
                #exp    got a packet from the server, but it wasnt SYN-ACK
                #exp    or FIN. will handle this diffrently depending
                #exp    if im in opening or closing
                sock.settimeout(TIMEOUT)
                return False
        except timeout:
            #exp    Did not get any packets from the server. Normal flow
            #exp    and i may consider the sent packet received by the server           
            sock.settimeout(TIMEOUT)
            return True