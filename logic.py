class DrivingLogic:
    def __init__(self):
        self.state = {
            "speed_decision": "maintain",
            "lane_decision": "keep_lane",
            "brake_decision": "none",
            "risk_level": "low"
        }

    def update(self, objects):
        # Reset la safe default 
        self.state["brake_decision"] = "none"
        self.state["speed_decision"] = "maintain"
        self.state["risk_level"] = "low"

        for obj in objects:
            label = obj["label"]
            # Prioritate: Frână > Bandă > Viteză 
            if label in ['stop sign', 'person']:
                self.state["brake_decision"] = "strong"
                self.state["speed_decision"] = "decrease"
                self.state["risk_level"] = "high"
                break 
            elif label in ['car', 'truck', 'bus']:
                self.state["brake_decision"] = "light"
                self.state["speed_decision"] = "maintain"
                self.state["risk_level"] = "medium"
        
        return self.state