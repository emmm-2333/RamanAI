from abc import ABC, abstractmethod
import random
import numpy as np

class SpectrometerDriver(ABC):
    """
    光谱仪硬件抽象层 (HAL)
    """

    @abstractmethod
    def open_device(self):
        """连接设备"""
        pass

    @abstractmethod
    def close_device(self):
        """断开设备"""
        pass

    @abstractmethod
    def capture_spectrum(self, integration_time_ms=100):
        """
        采集光谱
        :return: (wavelengths, intensities)
        """
        pass

class MockSpectrometer(SpectrometerDriver):
    """
    模拟光谱仪 - 用于开发和测试
    """
    def __init__(self):
        self.is_connected = False

    def open_device(self):
        print("Mock Spectrometer Connected.")
        self.is_connected = True
        return True

    def close_device(self):
        print("Mock Spectrometer Disconnected.")
        self.is_connected = False
        return True

    def capture_spectrum(self, integration_time_ms=100):
        if not self.is_connected:
            raise Exception("Device not connected")
        
        # Generate dummy data similar to Raman (400-2200 cm-1)
        wavelengths = np.arange(400, 2201, 1)
        # Random peaks + baseline
        baseline = 100 + 0.1 * wavelengths + np.random.normal(0, 5, len(wavelengths))
        peaks = 1000 * np.exp(-((wavelengths - 1000)**2) / 200) + \
                500 * np.exp(-((wavelengths - 1450)**2) / 300)
        intensities = baseline + peaks
        
        return wavelengths.tolist(), intensities.tolist()
