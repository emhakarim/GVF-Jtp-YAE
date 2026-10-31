"""
Modul Kalkulasi Fisika Galileo Vacuum Fall Experiment
Mengimplementasikan persamaan gerak jatuh bebas, hukum kekekalan energi,
perambatan ketidakpastian (error propagation), dan pemodelan hambatan udara.
"""

import math
from typing import Dict, Tuple

class PhysicsEngine:
    G_STANDARD = 9.80665  # Percepatan gravitasi standar (m/s^2)
    RHO_AIR_STP = 1.225   # Massa jenis udara pada 20°C, 1 atm (kg/m^3)

    def __init__(self, height_meters: float = 2.0, delta_h_meters: float = 0.002):
        self.height = height_meters
        self.delta_h = delta_h_meters

    def theoretical_vacuum_time(self, g: float = G_STANDARD) -> float:
        """Menghitung waktu jatuh teoritis di ruang hampa: t = sqrt(2h / g)"""
        return math.sqrt(2.0 * self.height / g)

    def theoretical_impact_velocity(self, g: float = G_STANDARD) -> float:
        """Menghitung kecepatan akhir saat tiba di dasar: v = sqrt(2gh)"""
        return math.sqrt(2.0 * g * self.height)

    def calculate_gravity_from_time(self, delta_t_seconds: float, delta_t_err: float = 0.010) -> Tuple[float, float]:
        """
        Menghitung percepatan gravitasi g dari waktu jatuh:
        g = 2h / (t^2)
        Ketidakpastian mutlak: dg = g * sqrt((dh/h)^2 + (2*dt/t)^2)
        """
        if delta_t_seconds <= 0:
            return 0.0, 0.0
            
        g_est = (2.0 * self.height) / (delta_t_seconds ** 2)
        
        # Propagasi error fisis
        rel_h_err = self.delta_h / self.height
        rel_t_err = (2.0 * delta_t_err) / delta_t_seconds
        g_err = g_est * math.sqrt(rel_h_err**2 + rel_t_err**2)
        
        return g_est, g_err

    def calculate_gravity_from_velocity(self, impact_velocity: float) -> float:
        """
        Menghitung gravitasi dari kecepatan akhir pada zona dasar:
        g = v^2 / (2h)
        Independen dari waktu pelepasan solenoid/servo.
        """
        if self.height <= 0:
            return 0.0
        return (impact_velocity ** 2) / (2.0 * self.height)

    def simulate_atmospheric_fall(self, mass: float, area: float, cd: float, 
                                  dt: float = 0.001, max_time: float = 5.0) -> Dict[str, float]:
        """
        Simulasi numerik Euler-Cromer jatuh bebas dengan hambatan aerodinamika:
        m * (dv/dt) = m*g - 0.5 * rho * Cd * A * v^2
        Digunakan untuk membandingkan jatuh bulu vs bola di udara bebas.
        """
        t = 0.0
        y = 0.0
        v = 0.0
        
        while y < self.height and t < max_time:
            f_drag = 0.5 * self.RHO_AIR_STP * cd * area * (v ** 2)
            a_net = self.G_STANDARD - (f_drag / mass)
            v += a_net * dt
            y += v * dt
            t += dt
            
        return {
            "fall_time_s": t,
            "final_velocity_ms": v,
            "impact": y >= self.height
        }
