import serial
import time, sys
import serial.tools.list_ports
from rich.console import Console
from rich.table import Table

class Keithley():

    def __init__(self, PORT:str = None) -> None:
        if PORT == None:
            print("Provide path to Keithley's port.")
            return

        self.port = PORT

        self.ser = serial.Serial(
            port=self.port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3
        )

        time.sleep(0.5)

    def idn(self) -> str:
        idn = self.query("*IDN?")
        print(f"{idn}")
        return idn

    def send(self, cmd:str, delay:float=0.1) -> None:
        """Send an SCPI command terminated with newline."""
        self.ser.write((cmd + '\n').encode('ascii'))
        time.sleep(delay)
        return None

    def query(self, cmd:str, delay:float=0.1) -> str:
        """Send a query and return the response string."""
        self.send(cmd, delay)
        return self.ser.readline().decode('ascii', errors='ignore').strip()

    def setup(self, wait:float = None, relative:bool = None) -> None:

        # --- Initialization Sequence ---
        self.send("*RST")           
        self.send("*CLS")           
        self.send(":FUNC 'CURR'")   

        # --- Zero Correction Sequence ---
        self.send(":SYST:ZCH ON")       
        time.sleep(4)                   
        self.send(":CURR:RANG 2E-9")     
        time.sleep(1)
        # self.send(":SYST:ZCOR:ACQ")     
        self.send(":SYST:ZCOR ON")      
        time.sleep(1)
        self.send(":SYST:ZCH OFF")
        time.sleep(1)

        # --- Measurement Configuration ---
        self.send(":CURR:NPLC 10")      
        time.sleep(1)
        self.send(":CURR:AVER:STAT OFF")
        time.sleep(1)
        self.send(":CURR:RANG:AUTO OFF") 
        time.sleep(1)
        
        self.send(":FORM:ELEM READ")    
        self.send(":SYST:AZER ON")
        time.sleep(1)

        # --- Display measurements relative to baseline ---
        # if relative:
        #     try:
        # self.send(":SYST:REL:STAT ON")
        #     except Exception:

        # self.send(":REL:STAT ON")

        # --- Wait after setup to allow communication to finish
        if wait != None:
            time.sleep(wait)

        return

    # def setup(self, wait:float = None, relative:bool = None) -> None:

    #     # --- Initialization Sequence ---
    #     self.send("*RST")           
    #     self.send("*CLS")           
    #     self.send(":FUNC 'CURR'")   

    #     # --- Zero Correction Sequence ---
    #     self.send(":SYST:ZCH ON")       
    #     time.sleep(2)                   
    #     self.send(":CURR:RANG 2E-9")    
    #     self.send("INIT")

    #     self.send(":SYST:ZCOR:STAT OFF")
    #     self.send(":SYST:ZCOR:ACQ")

    #     # self.send(":SYST:ZCOR:ACQ")     
    #     self.send(":SYST:ZCOR ON")      
    #     self.send(":SYST:ZCH OFF")

    #     # # --- Measurement Configuration ---
    #     # self.send(":CURR:NPLC 10")      
    #     # self.send(":CURR:AVER:STAT OFF")
    #     # self.send(":CURR:RANG:AUTO OFF") 
        
    #     self.send(":FORM:ELEM READ")    
    #     # self.send(":SYST:AZER ON")

    #     # --- Display measurements relative to baseline ---
    #     # if relative:
    #     #     try:
    #     # self.send(":SYST:REL:STAT ON")
    #     #     except Exception:

    #     # self.send(":REL:STAT ON")

    #     # --- Wait after setup to allow communication to finish
    #     if wait != None:
    #         time.sleep(wait)

    #     return

    def measure(self, wait:float = 0.2):
        self.send(":INIT")         
        time.sleep(wait)            
        reading = self.query(":FETCH?")
        # print(f"Measured current: {reading} A")
        return reading

    def close(self):
        self.ser.close()
        return