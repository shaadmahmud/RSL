"""
FSR FUNCTIONS
The purpose of this script is to hold functions relative to the Tekscan FSRS A401-100 and A301-100.
These functions are mainly used for:
    - Converting an ADC voltage to a resistance measure
    - Converting a resistance measure to a force measure
"""

class a301:
    def __init__(self) -> None:
        self.bits = 12                              # ADC bit resolution
        self.adc_scale = 3.3/pow(2,self.bits)       # ADC resolution per volt
        self.rf = 1.302e6                           # feedback resistance value in ohms

    def ohm(self, vref: int, vout: int) -> float:
        """Calculates the resistance measure (ohms) of a FSR
        
        Args:
            vref: The raw ADC value of the reference voltage
            vout: The raw ADC value of the output voltage

        Returns:
            The resistance measure in ohms of a FSR sensor
        """
        Rfs = self.rf*((vref/vout)*self.adc_scale)
        return Rfs

    def force1(self, Rfs: float) -> float:
        """Calculates the force measure (lbs) of a FSR
        
        Args:
            Rfs: the measured resistance of a FSR sensor

        Returns:
            The force measure in pounds of a FSR sensor
        """

        F = 2520438*pow(Rfs, -1.128)
        return F

    def force2(self, vref: int, vout: int) -> float:
        """Calculates the force measure (lbs) of a FSR
                
        Args:
            vref: The raw ADC value of the reference voltage
            vout: The raw ADC value of the output voltage

        Returns:
            The force measure in pounds of a FSR sensor
        """
        Rfs = self.rf*((vref/vout)*self.adc_scale)
        F = 2520438*pow(Rfs, -1.128)
        return F



class a401:
    def __init__(self) -> None:
        self.bits = 12                              # ADC bit resolution
        self.adc_scale = 3.3/pow(2,self.bits)       # ADC resolution per volt
        self.rf = 1.302e6                           # feedback resistance value in ohms
   
    def ohm(self, vref: int, vout: int) -> float:
        """Calculates the resistance measure (ohms) of a FSR

        Args:
            vref: The raw ADC value of the reference voltage
            vout: The raw ADC value of the output voltage

        Returns:
            The resistance measure in ohms of a FSR sensor
        """
        Rfs = self.rf*((vref/vout)*self.adc_scale)
        return Rfs

    def force(self, Rfs: float) -> float:
        """Calculates the force measure (lbs) of a FSR

        Args:
            Rfs: the measured resistance of a FSR sensor

        Returns:
            The force measure in pounds of a FSR sensor
        """

        F = 493e3*pow(Rfs, -0.8125)
        return F

    def force2(self, vref: int, vout: int) -> float:
        """Calculates the force measure (lbs) of a FSR
       
        Args:
            vref: The raw ADC value of the reference voltage
            vout: The raw ADC value of the output voltage

        Returns:
            The force measure in pounds of a FSR sensor
        """
        Rfs = self.rf*((vref/vout)*self.adc_scale)
        F = 493e3*pow(Rfs, -0.8125)
        return F

