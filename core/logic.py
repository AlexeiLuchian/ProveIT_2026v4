class DrivingLogic:
    def __init__(self):
        self.state = {
            "brake_decision": "none",
            "speed_decision": "increase",
            "risk_level": "low",
            "lane_decision": "keep_lane"
        }

    def update(self, objects):
        self.state["brake_decision"] = "none"
        self.state["speed_decision"] = "increase"
        self.state["risk_level"] = "low"
        self.state["lane_decision"] = "keep_lane"

        vehicles = ["car", "truck", "bus"]

        # Pre-calcul: banda dreaptă e liberă dacă nu există vehicule
        # cu offset lateral > 1.5m (dreapta) și distanță < 30m
        right_lane_clear = not any(
            obj["pos_rel"][0] > 1.5
            and obj["pos_rel"][1] < 30
            and obj["label"] in vehicles
            for obj in objects
        )

        # Sortăm după distanță — cel mai aproape primul
        sorted_objects = sorted(objects, key=lambda x: x["pos_rel"][1])

        for obj in sorted_objects:
            label  = obj["label"]
            dist_z = obj["pos_rel"][1]
            rel_x  = abs(obj["pos_rel"][0])

            # 1. Semafor
            if label == "traffic light":
                tc = obj.get("tl_color", "")
                if tc == "ROSU":
                    self.state["brake_decision"] = "strong"
                    self.state["speed_decision"] = "decrease"
                    self.state["risk_level"] = "high"
                    break
                elif tc == "GALBEN" and self.state["risk_level"] != "high":
                    self.state["brake_decision"] = "light"
                    self.state["speed_decision"] = "decrease"
                    self.state["risk_level"] = "medium"

            # 2. Stop sign
            elif label == "stop sign":
                self.state["brake_decision"] = "strong"
                self.state["speed_decision"] = "decrease"
                self.state["risk_level"] = "high"
                break

            # 3. Pieton — frânare bazată pe distanță (cu lățime realistă 0.5m)
            elif label == "person":
                if dist_z < 10:
                    self.state["brake_decision"] = "strong"
                    self.state["speed_decision"] = "decrease"
                    self.state["risk_level"] = "high"
                    break
                elif dist_z < 25 and self.state["risk_level"] != "high":
                    self.state["brake_decision"] = "light"
                    self.state["speed_decision"] = "decrease"
                    self.state["risk_level"] = "medium"

            # 4. Vehicule — distanță + poziție laterală + verificare bandă dreaptă
            elif label in vehicles:
                in_our_lane  = rel_x < 1.5
                merging_risk = 1.5 <= rel_x < 3.5

                if in_our_lane:
                    if dist_z < 8:
                        # Pericol iminent — schimbă banda dacă e liberă, altfel frânează
                        self.state["brake_decision"] = "strong"
                        self.state["speed_decision"] = "decrease"
                        self.state["risk_level"] = "high"
                        self.state["lane_decision"] = "change_lane" if right_lane_clear else "keep_lane"
                        break
                    elif dist_z < 25 and self.state["risk_level"] != "high":
                        self.state["brake_decision"] = "light"
                        self.state["speed_decision"] = "maintain"
                        self.state["risk_level"] = "medium"
                        # Schimbă banda doar dacă dreapta e liberă
                        if right_lane_clear:
                            self.state["lane_decision"] = "change_lane"

                elif merging_risk and dist_z < 4 and self.state["risk_level"] not in ["high", "medium"]:
                    self.state["brake_decision"] = "light"
                    self.state["speed_decision"] = "maintain"
                    self.state["risk_level"] = "medium"

        return self.state