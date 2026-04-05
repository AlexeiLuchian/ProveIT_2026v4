class DrivingLogic:
    def __init__(self):
        self.state = {
            "brake_decision": "none",
            "speed_decision": "increase",
            "risk_level": "low",
            "lane_decision": "keep_lane"
        }

    def update(self, objects):
        # Default: drum liber
        self.state["brake_decision"] = "none"
        self.state["speed_decision"] = "increase"
        self.state["risk_level"] = "low"
        self.state["lane_decision"] = "keep_lane"

        # Sortăm după distanță (cel mai apropiat pericol primul)
        sorted_objects = sorted(objects, key=lambda x: x["pos_rel"][1])

        for obj in sorted_objects:
            label = obj["label"]
            dist_z = obj["pos_rel"][1]

            # 1. Semafoare
            if label == "traffic light":
                tc = obj.get("tl_color", "")
                if tc == "ROSU":
                    self.state["brake_decision"] = "strong"
                    self.state["speed_decision"] = "decrease"
                    self.state["risk_level"] = "high"
                    break
                elif tc == "GALBEN":
                    self.state["brake_decision"] = "light"
                    self.state["speed_decision"] = "decrease"
                    self.state["risk_level"] = "medium"

            # 2. Stop sign / Pieton -> frânare absolută
            elif label in ["stop sign", "person", "restriction_sign"]:
                self.state["brake_decision"] = "strong"
                self.state["speed_decision"] = "decrease"
                self.state["risk_level"] = "high"
                break

            # 3. Vehicule — decizie bazată pe distanță
            elif label in ["car", "truck", "bus"]:
                if dist_z < 8:
                    self.state["brake_decision"] = "strong"
                    self.state["speed_decision"] = "decrease"
                    self.state["risk_level"] = "high"
                    self.state["lane_decision"] = "change_lane"
                    break
                elif dist_z < 25:
                    self.state["brake_decision"] = "light"
                    self.state["speed_decision"] = "maintain"
                    self.state["risk_level"] = "medium"
                    self.state["lane_decision"] = "change_lane"

        return self.state