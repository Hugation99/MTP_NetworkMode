from pyrf24 import RF24, rf24
import pandas as pd
import time
import logging
#Array of link addresses (5 bytes each)
LINK_ADDRESSES = [b'NodeA1', b'NodeA2', b'NodeB1', b'NodeB2', b'NodeC1', b'NodeC2']
OWN_ADDRESS = b'NodeA1'
LINK_ADDRESSES.remove(OWN_ADDRESS) 

#Filename TODO: Change for each team
FILENAME = 'text.txt' 

#Packet size
PACKET_SIZE = 32

#Timeout
TIMEOUT_FILE = 10
TIMEOUT_TOKEN = 1

#Global Table with the reachable transceivers
tb = pd.DataFrame(columns=['Address', 'Token', 'File'])

#Token Info, Each transceiver must know if it has had the token or not
token = False

#File Info, Each TR must know if it has the file or not
file = False

#These packets have no payload, header=packet
TOKEN_PACKET = b'\x0D'

#Headers for packets that need to be built each time they are sent (updated info)
HEADER_STATUS = b'\x0A'
HEADER_STATUS_PACKET_REPLY = b'\x0B'
HEADER_FILE_PACKET = b'\x0C'

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
    radio.ack_payloads = False
    radio.set_retries(5, 15) 
    radio.listen = False

    sendStatus(radio)

    sendFile(radio,FILENAME)

    while not sendToken(radio):
        continue

    del radio
    
    

#this function has to be executed every time the TR is passed the token
def sendStatus(radio):
    """
    Sends Status Packet to every Link Addresses. 
    Adjust retries and delay btw retries
    Waits for ACKs that have payload. 1 bit token, 1 bit file
    Stores info in a Table together with the corresponding link address. 
        If link address already in table update values, otherwise add new row
    """
    radio.open_rx_pipe(1, OWN_ADDRESS)
    for address in LINK_ADDRESSES:
        radio.open_tx_pipe(address)
        response = radio.write(HEADER_STATUS+OWN_ADDRESS)
        if response:
            radio.listen = True
            while not radio.available():    # Timeout ??
                time.sleep(1/1000)
            answer_packet = radio.read(radio.get_dynamic_payload_size())
            radio.listen = False

            if answer_packet[0] == HEADER_STATUS_PACKET_REPLY:
                file_status = int.from_bytes(answer_packet[1], byteorder='big')
                token_status = int.from_bytes(answer_packet[2], byteorder='big')
                new_row = {'Address':address, 'File': file_status, 'Token':token_status}
                if (tb['Address'] == new_row['Address']).any():
                    tb.loc[tb['Address'] == new_row['Address']] = new_row
                else:
                    tb.loc[len(tb)] = new_row

    radio.close_rx_pipe(1)
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

                timed_out = (time.time() - start_time > TIMEOUT_FILE)
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

def sendToken(radio):
    """
    Send Token to TR and keep retrying (Timeout= 5-10 s)
    Look table col 'Token' for priority: First TR with value 0, then TR with value 1 in first position
    If Token is sent to a TR with 'token' = 0, 'token' value is updated to 1 and TR is sent to the last row
    If Token is sent to a TR with 'token' = 1, 'token' TR is sent to the last row
    Returns True if token is passed to another node, False otherwise.
    """
    token_passed = False

    if 0 in tb['Token'].values:
        for index, row in tb.iterrows():
            if row['Token'] == 0:
                start_time = time.time()
                radio.open_tx_pipe(row['Address'])

                token_passed = False
                while (not token_passed or not timed_out):
                    token_passed = radio.write(TOKEN_PACKET)
                    timed_out = (time.time() - start_time > TIMEOUT_TOKEN)
                if token_passed:
                    tb.loc[index,'Token'] = 1
                    tb = tb.append(row).drop(index) #move row to the last position
                    break
        
    if not token_passed: 
        for index, row in tb.iterrows():
            if row['Token'] == 1:
                start_time = time.time()
                radio.open_tx_pipe(row['Address'])
                token_passed = False
                while (not token_passed or not timed_out):
                    token_passed = radio.write(TOKEN_PACKET)
                    timed_out = (time.time() - start_time > TIMEOUT_TOKEN)
                if token_passed:
                    tb = tb.append(row).drop(index) #move row to the last position
                    break

    return token_passed



def receiver():
    """
    Loop until receives a message.
    Take first byte (Header) and identify the message type.
    Call the corresponding function.
    """
    radio = RF24()
    if not radio.begin(4,0): #TODO: Here the 1st pin changes for each team
        raise OSError("nRF24L01 hardware isn't responding")
    radio.payload_size = 32
    radio.channel = 26 #6A 20
    radio.data_rate = rf24.RF24_250KBPS

    radio.set_pa_level(rf24.rf24_pa_dbm_e.RF24_PA_HIGH)
    radio.dynamic_payloads = True
    radio.set_auto_ack(True)
    radio.ack_payloads = False

    radio.set_retries(5,15) 
    radio.open_rx_pipe(1, OWN_ADDRESS) 
    radio.startListening()

    while not radio.available():
        time.sleep(1/1000)
        continue

    
    


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
