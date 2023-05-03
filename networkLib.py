import pyrf24
import pandas as pd

#Array of link addresses (5 bytes each)
LINK_ADDRESSES = [b'NodeA1', b'NodeA2', b'NodeB1', b'NodeB2', b'NodeC1', b'NodeC2']

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
    Calls sendStatus()
    Calls sendFile()
    Calls sendToken()
    """

#this function has to be executed every time the TR is passed the token
def sendStatus():
    """
    Sends Status Packet to every Link Addresses. 
    Adjust retries and delay btw retries
    Waits for ACKs that have payload. 1 bit token, 1 bit file
    Stores info in a Table together with the corresponding link address. 
        If link address already in table update values, otherwise add new row
    """

def sendFile():
    """
    Send File to transceivers that do not have it already. (Check table)
    If TR stops responding ACKs keep trying during Timeout (think best value).
    If a TR timeouts, eliminate from tb so token is not passed to it.

    """

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
