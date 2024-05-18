import sys
import argparse
from server import Server
from client import Client

def modeValid(args): #takes in the argument list
    if args.server & args.client: #turning on server and client?
        print("You cannot use both at the same time")
        return False
    elif args.server: #turning on server
        return"server"
    elif args.client: #turning on client
        return "client"
    else: #option of server or client is not specified
        print("You should run either in server or client mode")
        return False

def ipValid(args):#takes in the argument list
    ip = args.ip.split(".") #splits IP-adress so it may be checked
    if len(ip) != 4: #if there isnt 4 numbers in the adress
        print("Invalid IP. It must be in this format: 10.1.2.3")
        return False
    for e in ip:#goes through every number, e, in the ip
        if int(e) not in range(0,256): #returns false if its not a valid number
            print(f'Invalid IP. {e} in {args.ip} must be in range [0,255]')
            return False
    return True #everything is cool

def portValid(args):#takes in the argument list
    if args.port not in range(1024, 65536): #if its not a valid port
        print("Invalid port. It must be within the range [1024, 65535]")
        return False
    return True #everything is cool

def windowValid(args):
    if args.window < 0:
        print('Invalid window size. Must  be greater than 0')
        return False
    return True

def fileValid(args):
    if args.server and args.file:
        print('Invalid direction of filetransfer.')
        return False
    if not args.file and args.client:
        print('File is required')
        return False
    #exp    checks if the file that is supposed to be sent 
    #exp    exists so i dont have to check in the code. 
    #exp    gives better readablilty
    try:
        if not args.server:
            with open(args.file) as f:
                pass
    except FileNotFoundError:
        print(f'{args.file} was not found')
        return False
    except IOError:
        print(f'could not open file')
        return False
    return True

def discardValid(args):
    if args.discard < 0:
        print('Invalid seqno for packet to be discarded. Must be greater than 0')
        return False
    if args.client and args.discard:
        print('Invalid option --discard with client')
        return False
    if args.discard: print(f'Packet {args.discard} will be dropped intentionally')
    return True

def processInputs(args):#takes in the argument list
    mode = modeValid(args) #checks the server og client option
    if not mode: return #false startup mode 
    if not ipValid(args): return #false ip-adress
    if not portValid(args): return #false port
    if not windowValid(args): return
    if not discardValid(args): return 
    if not fileValid(args): return

    print(f'\n[{mode.upper()}] Running with IP = {args.ip} and port = {args.port}\n\n')
    if args.server: Server(args)
    if args.client: Client(args)

#defines the argumentparser
parser = argparse.ArgumentParser(
    description="Specify options for the server or client side")
#adds argument of server and client, both with boolean values 
parser.add_argument("-s","--server", action="store_true")
parser.add_argument("-c","--client", action="store_true")
#adds argument of port, defualt 8088
parser.add_argument("-p", "--port", type=int, default=8088)
#adds argument of ipadress, defualt 10.0.0.2
parser.add_argument("-i", "--ip", type=str, default='127.0.0.1')

parser.add_argument("-w", "--window", type=int, default=3)
parser.add_argument("-f", "--file", type=str)
parser.add_argument("-d","--discard", type=int, default = False)

args = parser.parse_args()
#sends the inputs of the arguments to be validated
processInputs(args)