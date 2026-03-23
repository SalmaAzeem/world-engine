class Room:
    def __init__(building, room, floor, state):
        self.id = f"b-{building}-{floor}-{room}"
        self.path = f"campus/{self.id}" 
        self.temp = state["temperature"]
        self.humidity = state["humidity"]
        self.occupancy = state["occupancy"]
        self.light_level = state["light_level"]
        self.hvac_mode = state["hvac_mode"]

    def update_temperature(self, outside_temp):
        alpha = 0.01
        beta = 0.2
        if self.hvac_mode == "ON":
            hvac_power=1
        elif self.hvac_mode == "ECO":
            hvac_power = 0.5
        else:
            hvac_power=0
        self.temp = (self.temp + alpha*(outside_temp - self.temp) + beta*hvac_power)
    
    def update_light(self, threshold):
        if self.occupancy == True:
            self.light_level =  max(self.light_level, threshold)
            self.temp+=1 # Occupancy must increase the temperature slightly

    # run simulation function should be implemented here?
    # Night cycle must influence outside temperature (via virtual clock), state = pending
    # add fault modeling

