import numpy as np
from scipy.signal import savgol_filter
from scipy import sparse
from scipy.sparse.linalg import spsolve
from sklearn.preprocessing import MinMaxScaler

class RamanPreprocessor:
    """
    拉曼光谱预处理工具类
    包含：平滑、基线校正、归一化
    """

    @staticmethod
    def smooth_savgol(y_data, window_length=11, polyorder=3):
        """
        Savitzky-Golay 平滑
        :param y_data: 光谱强度数组
        :param window_length: 窗口长度 (必须是奇数)
        :param polyorder: 多项式阶数
        :return: 平滑后的数组
        """
        try:
            # 确保 window_length 是奇数且小于数据长度
            if window_length % 2 == 0:
                window_length += 1
            if window_length >= len(y_data):
                window_length = len(y_data) - 1 if len(y_data) % 2 == 0 else len(y_data) - 2
            
            return savgol_filter(y_data, window_length, polyorder)
        except Exception as e:
            print(f"Smoothing error: {e}")
            return y_data

    @staticmethod
    def normalize_minmax(y_data):
        """
        Min-Max 归一化 (0-1)
        """
        y_array = np.array(y_data).reshape(-1, 1)
        scaler = MinMaxScaler()
        return scaler.fit_transform(y_array).flatten()

    @staticmethod
    def baseline_correction_poly(x_data, y_data, degree=5):
        """
        多项式拟合基线校正
        :param x_data: 波数
        :param y_data: 强度
        :param degree: 多项式阶数
        :return: 校正后的强度 (原始 - 基线)
        """
        try:
            coeffs = np.polyfit(x_data, y_data, degree)
            baseline = np.polyval(coeffs, x_data)
            return y_data - baseline
        except Exception as e:
            print(f"Baseline correction error: {e}")
            return y_data

    @staticmethod
    def baseline_als(y_data, lam=100000, p=0.01, niter=10):
        """
        Asymmetric Least Squares Smoothing (ALS) for baseline correction.
        Reference: Eilers, P. H. C. (2004). "Baseline Correction with Asymmetric Least Squares Smoothing".
        """
        L = len(y_data)
        D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
        w = np.ones(L)
        for i in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.transpose())
            z = spsolve(Z, w*y_data)
            w = p * (y_data > z) + (1-p) * (y_data < z)
        return y_data - z

    @staticmethod
    def normalize_snv(y_data):
        """
        Standard Normal Variate (SNV) Normalization
        """
        y_array = np.array(y_data)
        mean = np.mean(y_array)
        std = np.std(y_array)
        if std == 0:
            return y_array
        return (y_array - mean) / std

    @staticmethod
    def derivative(x_data, y_data, order=1):
        """
        Calculate derivative (1st or 2nd)
        Note: This is a simple finite difference. For better results, use SavGol derivative.
        """
        y_array = np.array(y_data)
        x_array = np.array(x_data)
        
        if order == 1:
            dy = np.gradient(y_array, x_array)
            return dy
        elif order == 2:
            dy = np.gradient(y_array, x_array)
            d2y = np.gradient(dy, x_array)
            return d2y
        return y_array

    @staticmethod
    def process_pipeline(x_data, y_data, config=None):
        """
        预处理流水线
        """
        if config is None:
            config = {'smooth': True, 'baseline': True, 'normalize': True, 'baseline_method': 'poly', 'normalize_method': 'minmax', 'derivative': 0}
        
        y_processed = np.array(y_data)

        if config.get('smooth'):
            y_processed = RamanPreprocessor.smooth_savgol(y_processed)
        
        if config.get('baseline'):
            if config.get('baseline_method') == 'als':
                 y_processed = RamanPreprocessor.baseline_als(y_processed)
            else:
                 y_processed = RamanPreprocessor.baseline_correction_poly(x_data, y_processed)
        
        if config.get('derivative', 0) > 0:
            y_processed = RamanPreprocessor.derivative(x_data, y_processed, order=config.get('derivative'))

        if config.get('normalize'):
            if config.get('normalize_method') == 'snv':
                y_processed = RamanPreprocessor.normalize_snv(y_processed)
            else:
                y_processed = RamanPreprocessor.normalize_minmax(y_processed)
            
        return y_processed
