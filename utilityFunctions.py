from struct import *
from datetime import datetime
import os

header_format = '!HHH'

def create_packet(seq, ack, flags, data):
    """
    *   creates a packet with a parameter sequence number,
    *   acknowlegdement number, specified flags and some data.
    *   the header gets converted to a byte-string that is in the format
    *   of the header_format variable, and gets conbined with the data byte-string
    *   before being returned.
    """
    header = pack(header_format, seq, ack, flags)
    return header + data

def parse_header(packet):
    """
    *   This function unpacks the datapacket and returns the header only.
    *   the unpack funciton takes the header_format and the datapackets header as arguments
    *   and returns a touple of the parsed header elements.
    """
    return unpack(header_format, packet[:6])

def parse_flags(flags):
    """
    *   This function takes the flag from a packet header and returns the flags as a touple.
    *   it checks every bit, and if the current bit is set the corresponding flag will be a
    *   True value (non-zero integer), else it will be a False value (zero). 
    """
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    reset = flags & (1 << 0)
    return syn, ack, fin, reset

class bcolors:
    """
    *   colours that are used in prints for better visibility
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
    *   a generator function that opens a specified file and reads it out 
    *   to the user in chunks. The while loop will run as long as f.read(994) is
    *   not a False value, aka the part variable that gets the data-value from f.read()
    *   is not empty.
    """
    with open(fileName, 'rb') as f:
        while part := f.read(994):
            yield part



def getTimestamp():
    """
    *   returns the current timestamp, formated with Hours:Minuttes:seconds.Milliseconds
    """
    return datetime.now().strftime('%H:%M:%S.%f')

def getWinSeq(list):
    """
    *   takes in a list of packets and returns a new list that contains the sequence numbers
    *   of the original packets. It exstracts the sequence numbers from the packets, basicly.
    *   It also removes the bracets [] and replaces them with curly bracets {} in order to mimic
    *   the output snippet in the task. The curly bracets thing is not necessary.
    """
    arr = []
    for i in list:
        arr.append(parse_header(i)[0])
    ret = '{' + ', '.join([str(x) for x in arr]) + '}'
    return ret

def calcThroughput(size, time):
    """
    *   throughput value to a string. then finds the position of the comma. 
    *   then iterates over every number and finds the first non zero number.
    *   it then returns the meassured throughtput with two non-zero decimals  in it.
    *   as done in the server output snippet in the task.
    """
    if not size: return 0
    num_str = str(size/time)
    decimal_index = str(size/time).index('.') + 1
    while num_str[decimal_index] == '0':
        decimal_index += 1
    return num_str[:decimal_index + 2]

def nextnonexistent(f):
    fnew = f
    root, ext = os.path.splitext(f)
    i = 0
    while os.path.exists(fnew):
        i += 1
        fnew = '%s_%i%s' % (root, i, ext)
    return fnew