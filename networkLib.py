from pyrf24 import RF24, rf24
import pandas as pd
import time
import logging
#Array of link addresses (5 bytes each)
LINK_ADDRESSES = [b'NodeA1', b'NodeA2', b'NodeB1', b'NodeB2', b'NodeC1', b'NodeC2']

#Filename TODO: Change for each team
filename = 'text.txt' 

#Packet size
PACKET_SIZE = 32

#Timeout
TIMEOUT = 10

#Global Table with the reachable transceivers
tb = pd.DataFrame(columns=['Address', 'Token', 'File'])

#Token Info, Each transceiver must know if it has had the token or not
token = False

#File Info, Each TR must know if it has the file or not
file = False

#Status Packet is always the same (these packets have no payload, header=packet)
STATUS_PACKET = b'\x0A'
TOKEN_PACKET = b'\x0D'

#Headers for packets that need to be built each time they are sent (updated info)
HEADER_STATUS_PACKET_REPLY = b'\x0B'
HEADER_FILE_PACKET = b'\x0C'
HEADER_TOKEN_PACKET_REPLY = b'\x0E'

def transmitter():
    """
    Initializes radio
    Calls sendStatus()
    Calls sendFile()
    Calls sendToken()
    """

    radio = RF24()
    if not radio.begin(4,0): #TODO: Here the 1st pin cahnegs for each team
        raise OSError("nRF24L01 hardware isn't responding")
    radio.payload_size = 32
    radio.channel = 26 #6A 20
    radio.data_rate = rf24.RF24_1MBPS
    radio.set_pa_level(rf24.rf24_pa_dbm_e.RF24_PA_HIGH)
    radio.dynamic_payloads = True
    radio.set_auto_ack(True)
    radio.ack_payloads = True
    radio.set_retries(5, 15) 
    radio.listen = False
    

#this function has to be executed every time the TR is passed the token
def sendStatus(radio):
    """
    Sends Status Packet to every Link Addresses. 
    Adjust retries and delay btw retries
    Waits for ACKs that have payload. 1 bit token, 1 bit file
    Stores info in a Table together with the corresponding link address. 
        If link address already in table update values, otherwise add new row
    """
    for address in LINK_ADDRESSES:
        radio.open_tx_pipe(address)
        response = radio.write(STATUS_PACKET)
        if response:
            if radio.available():
                ack_payload = radio.read(radio.get_dynamic_payload_size())
                file_status = int.from_bytes(ack_payload[0], byteorder='big')
                token_status = int.from_bytes(ack_payload[1], byteorder='big')
                new_row = {'Address':address, 'File': file_status, 'Token':token_status}
                if (tb['Address'] == new_row['Address']).any():
                    tb.loc[tb['Address'] == new_row['Address']] = new_row
                else:
                    tb.loc[len(tb)] = new_row
    logging.debug('sendStatus():')                
    logging.debug(tb)              
            


def sendFile(radio,filename):
    """
    Send File to transceivers that do not have it already. (Check table)
    If TR stops responding ACKs keep trying during Timeout (think best value).
    If a TR timeouts, eliminate from tb so token is not passed to it.
    """
    
    file = readFile(filename)
    for index, row in tb.iterrows():
        if row['File'] == 0:
            radio.open_tx_pipe(row['Address'])
            packet_id = b'\x00'
            start_time = time.time()
            for i in range(0, len(file),PACKET_SIZE-2):
                message = HEADER_FILE_PACKET + packet_id + file[i:i+PACKET_SIZE-2]

                timed_out = (time.time() - start_time > TIMEOUT)
                while (not radio.write(message) or not timed_out):
                    continue
                if timed_out:
                    tb = tb.drop(index) 
                    break
                int_value = int.from_bytes(packet_id, byteorder='big')  # convert byte to integer
                if int_value == 255:
                    int_value = 0
                else:
                    int_value += 1  # increment integer
                packet_id = int_value.to_bytes(1, byteorder='big')  # convert integer back to byte

def readFile():
    return

def sendToken():
    """
    Send Token to TR and keep retrying (Timeout= 5-10 s)
    Look table col 'Token' for priority: First TR with value 0, then TR with value 1 in first position
    If Token is sent to a TR with 'token' = 0, 'token' value is updated to 1 and TR is sent to the last row
    If Token is sent to a TR with 'token' = 1, 'token' TR is sent to the last row
    """

    

def receiver():
    """
    Loop until receives a message.
    Take first byte (Header) and identify the message type.
    Call the corresponding function.
    """

def receiveStatus():
    """
    Build packet using the token and file global variables.
    Send it back to sender (timeout=5-10s)
    """

def receiveFile():
    """
    Loop to receive file until an end of transmission is received (or timeout)
    Save the file to USB
    """

def receiveToken():
    """
    When token packet is received. 
    Send Token Reply. Update token variable
    Then start transmitting mode (send status,...)
    """
